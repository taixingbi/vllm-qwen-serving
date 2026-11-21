#!/usr/bin/env python3
"""Simple per-tenant prefix-cache accounting demo against a vLLM OpenAI API.

Only client-side simulated tenants; a production gateway must authenticate them.
"""
import argparse
import csv
import json
import secrets
import urllib.error
import urllib.request
from collections import defaultdict
from pathlib import Path

MODEL = "Qwen/Qwen2.5-7B-Instruct"
PROMPTS = {
    "tenant-A": "GPU scheduling and CUDA memory allocation. " * 150,
    "tenant-B": "Molecular biology and protein structures. " * 150,
}


def request_json(base_url, path, payload=None):
    encoded = json.dumps(payload).encode("utf-8") if payload is not None else b""
    request = urllib.request.Request(
        base_url.rstrip("/") + path,
        data=encoded,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            body = response.read()
            return json.loads(body) if body else {}
    except urllib.error.HTTPError as error:
        message = error.read().decode("utf-8", "replace")[:500]
        raise RuntimeError(f"HTTP {error.code} from {path}: {message}") from error


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--reset", action="store_true",
                        help="Reset the server-wide cache before testing (dev-mode API required)")
    parser.add_argument("--salted", action="store_true",
                        help="Use a separate random cache_salt for each simulated tenant")
    parser.add_argument("--output", default="tenant_cache_results.csv")
    args = parser.parse_args()
    if args.repeats < 1:
        parser.error("--repeats must be >= 1")

    if args.reset:
        request_json(args.base_url, "/reset_prefix_cache")
        print("Server-wide prefix cache reset requested.")

    # Stable within a tenant during this run, different across tenants.
    # In production the gateway must generate/store and enforce secret salts.
    salts = {tenant: secrets.token_urlsafe(32) for tenant in PROMPTS} if args.salted else {}
    results = []
    for tenant, prompt in PROMPTS.items():
        print(f"\n=== {tenant} ===")
        for attempt in range(1, args.repeats + 1):
            payload = {
                "model": MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0,
                "max_tokens": 16,
            }
            if args.salted:
                payload["cache_salt"] = salts[tenant]
            response = request_json(args.base_url, "/v1/chat/completions", payload)
            usage = response.get("usage") or {}
            details = usage.get("prompt_tokens_details")
            cached = details.get("cached_tokens") if isinstance(details, dict) else None
            total = usage.get("prompt_tokens")
            if not isinstance(total, int):
                raise RuntimeError(f"Missing prompt_tokens for {tenant}: {usage}")
            if cached is not None and not isinstance(cached, int):
                raise RuntimeError(f"Unexpected cached_tokens for {tenant}: {cached!r}")
            ratio = cached / total if cached is not None and total else None
            results.append({
                "tenant_id": tenant,
                "attempt": attempt,
                "prompt_tokens": total,
                "cached_tokens": cached if cached is not None else "",
                "hit_ratio": f"{ratio:.6f}" if ratio is not None else "",
                "cache_salt_mode": "per-tenant" if args.salted else "shared",
            })
            shown = f"{cached} ({ratio:.1%})" if ratio is not None else "N/A (not reported)"
            print(f"Request {attempt}: prompt={total}, cached={shown}")

    fields = ["tenant_id", "attempt", "prompt_tokens", "cached_tokens", "hit_ratio", "cache_salt_mode"]
    with Path(args.output).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(results)

    grouped = defaultdict(list)
    for row in results:
        grouped[row["tenant_id"]].append(row)
    print("\n=== Per-tenant summary ===")
    for tenant, rows in grouped.items():
        measured = [row for row in rows if row["cached_tokens"] != ""]
        denom = sum(row["prompt_tokens"] for row in measured)
        numer = sum(int(row["cached_tokens"]) for row in measured)
        measured_ratio = f"{numer / denom:.1%}" if denom else "N/A"
        warm = [row for row in measured if row["attempt"] > 1]
        warm_denom = sum(row["prompt_tokens"] for row in warm)
        warm_numer = sum(int(row["cached_tokens"]) for row in warm)
        warm_ratio = f"{warm_numer / warm_denom:.1%}" if warm_denom else "N/A"
        print(f"{tenant}: reported={len(measured)}/{len(rows)} requests, "
              f"reported-only ratio={measured_ratio}, warm-only ratio={warm_ratio}")
    print(f"\nSaved CSV: {args.output}")
    print("N/A is missing telemetry, not necessarily a zero cache hit.")


if __name__ == "__main__":
    main()
