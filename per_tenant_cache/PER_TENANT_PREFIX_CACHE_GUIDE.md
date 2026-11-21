# Per-Tenant Prefix Cache Hit — vLLM / Qwen 7B Guide

Practical guidance for testing **per-request, per-tenant prefix KV-cache hits** with a vLLM API server. Applies to the tested **vLLM 0.17.1** deployment on **gpu-node-1** (RTX 3090, `Qwen/Qwen2.5-7B-Instruct`, 4,096-token maximum model length).

> **Meaning of "per-tenant":** vLLM reports cache reuse **per request**, not authenticated tenant identity. A test harness can label its own requests (`tenant-A`, `tenant-B`) and aggregate them. In production or a publishable multi-tenant benchmark, the **gateway must authenticate the API key, assign a trusted `tenant_id`, and join that identity to the returned request usage**. This does *not* itself isolate tenants' caches.

## 1. Required vLLM settings

In an isolated research environment, launch **only one** instance after stopping the existing one and checking that GPU memory is free:

```bash
pgrep -af 'vllm|EngineCore'
nvidia-smi
```

After confirming that old vLLM processes you own have exited, start in the background:

```bash
# Activate the environment first.
source ~/miniconda3/etc/profile.d/conda.sh
conda activate vllm

nohup env CUDA_VISIBLE_DEVICES=0 VLLM_SERVER_DEV_MODE=1 \
  vllm serve Qwen/Qwen2.5-7B-Instruct \
  --host 0.0.0.0 \
  --port 8000 \
  --dtype float16 \
  --max-model-len 4096 \
  --gpu-memory-utilization 0.80 \
  --enable-prefix-caching \
  --enable-prompt-tokens-details \
  > ~/vllm.log 2>&1 < /dev/null &
```

- `--enable-prefix-caching`: enables automatic prefix cache reuse.
- `--enable-prompt-tokens-details`: adds `usage.prompt_tokens_details.cached_tokens` when the server reports a non-null count.
- `VLLM_SERVER_DEV_MODE=1`: enables development-only `/reset_prefix_cache` for controlled experiments. **Never expose this unauthenticated dev-mode server to the public Internet**; the dev mode enables other dangerous endpoints. Use an isolated lab LAN and firewall or bind localhost and use an SSH tunnel.
- `nohup ... &`: preserves service across ordinary SSH disconnection, **not machine reboot**.

Check startup and APIs:

```bash
tail -n 30 ~/vllm.log
curl -f http://127.0.0.1:8000/v1/models
curl -i -X POST http://127.0.0.1:8000/reset_prefix_cache
```

Expected: a model entry for Qwen and `HTTP/1.1 200 OK` for the reset endpoint. A 200 status only confirms the reset request was handled; it does not independently prove cache state. **Reset only when there are no active benchmark requests**; resetting affects the entire vLLM instance, not one tenant.

## 2. Run the tested two-tenant smoke test

Put the accompanying `test_per_tenant_cache.py` in your Linux home folder, for example:

```bash
# From the directory containing the downloaded script:
cp test_per_tenant_cache.py ~/test_per_tenant_cache.py
python ~/test_per_tenant_cache.py --reset --output ~/tenant_cache_results.csv
```

The script uses only the Python standard library. It sends **three identical prompts per simulated tenant**, prints the cache tokens and ratio for every request, and saves CSV. By default it uses the shared prefix cache, which mirrors the baseline shared-tenant deployment.

To point at a remote, trusted lab server:

```bash
python ~/test_per_tenant_cache.py \
  --base-url http://192.168.86.173:8000 \
  --reset \
  --output ~/tenant_cache_results.csv
```

**Important:** `--reset` invokes the global dev-mode API. Omit `--reset` if other tests or workloads are running. `--repeats 3` is the default. Run **one experiment at a time** for this initial diagnostic.

### Example interpretation (from the actual smoke-test outputs)

| Tenant | Request | Prompt tokens | Cached tokens | Ratio |
| --- | ---: | ---: | ---: | ---: |
| A | 1 | 1,080 | null / N/A | not reported |
| A | 2 | 1,080 | 1,072 | 99.3% |
| A | 3 | 1,080 | 1,072 | 99.3% |
| B | 1 | 931 | 16 | 1.7% |
| B | 2 | 931 | 928 | 99.7% |

The third B request was cut off in the shared terminal output, so it is intentionally not reported here. A first-request `null` is **missing telemetry**, not a confirmed zero hit. B's first 16 cached tokens could be shared chat-template/system-prefix blocks; this does not by itself demonstrate a security failure.

## 3. Metrics and null handling

For each request, if the API provides both fields:

```
request_prefix_hit_ratio = cached_tokens / prompt_tokens
```

For an authenticated tenant over a defined time window or experimental arm, the **token-weighted** hit ratio is:

```
tenant_prefix_hit_ratio = sum(cached_tokens for tenant requests)
                          / sum(prompt_tokens for the same requests)
```

Apply the equation **only when the included requests have valid cached-token data**. Do **not** silently treat `prompt_tokens_details: null` as `cached_tokens: 0`. For vLLM 0.17.1, a cold request can return null when there are no reported hits. Report both:

- **Telemetry coverage:** requests with a reported `cached_tokens` value / total requests.
- **Reported-only hit ratio:** token-weighted ratio for requests with a numeric cached-token count; label it clearly. If coverage is less than 100%, **do not present this as the all-request tenant hit ratio**.

For the warm-cache check, a useful supplementary metric is **warm-only hit ratio**, considering requests 2 and 3 of the same repeated prompt. The attached script prints both reported-only and warm-only ratios, and records missing values as blank fields in CSV.

A hit measures **reused prefix prompt tokens** (cache blocks). It is not total GPU memory used, the entire KV-cache occupancy, or direct evidence of cache eviction.

## 4. Shared cache versus tenant isolation

The test harness' tenant names are labels: they are **not passed to vLLM as trusted identities**. By default, requests from different tenants share vLLM's prefix cache.

To test a *per-tenant salted-cache condition*, run:

```bash
python ~/test_per_tenant_cache.py \
  --salted --reset \
  --output ~/tenant_cache_salted.csv
```

The demo generates a random, stable `cache_salt` for each tenant within that test run. In a **real gateway**, create and retain a secret, unguessable salt at the intended trust boundary; reject/override any client-supplied salt rather than trusting it. Different salts limit *cross-tenant* prefix reuse, but do not constitute complete multi-tenant isolation.

**For research:** compare shared-cache and salted-cache conditions separately. Cache salting changes the system under test, so never enable it halfway through a baseline run.

## 5. Integration into the Gateway

At response time, the Gateway should log fields similar to:

```json
{
  "request_id": "uuid-generated-by-gateway",
  "tenant_id": "tenant-A",
  "experiment_arm": "baseline",
  "model": "Qwen/Qwen2.5-7B-Instruct",
  "prompt_tokens": 1080,
  "cached_tokens": 1072,
  "cached_tokens_observed": true,
  "cache_policy": "shared"
}
```

The gateway must authenticate the request (e.g., API key), set `tenant_id` from its trusted authentication context, and prevent an untrusted client from supplying or changing the tenant label. For streaming requests, ensure the final stream usage chunk is collected (`stream_options.include_usage=true` if supported by the client/server). Save usage alongside timestamps, request IDs and experiment-arm IDs. Avoid recording raw confidential prompts in shared logs.

A basic SQL aggregation for **observed** requests:

```sql
SELECT tenant_id, experiment_arm,
       SUM(cached_tokens) * 1.0 / NULLIF(SUM(prompt_tokens), 0) AS reported_only_hit_ratio,
       COUNT(*) AS observed_requests
FROM request_metrics
WHERE cached_tokens_observed = TRUE
GROUP BY tenant_id, experiment_arm;
```

Also compute telemetry coverage against **all** requests in each tenant/arm. Excluding `null` can bias the estimate toward warm requests.

## 6. Benchmark protocol and troubleshooting

1. Confirm only one vLLM server uses the GPU; test `GET /v1/models`.
2. Before each arm, wait for in-flight work to finish; call `/reset_prefix_cache` exactly once if experimenting with a cold start.
3. Keep model, chat template, max sequence length, cache configuration, arrival pattern, and prompt distribution consistent across comparative arms.
4. Run a cold request followed by repeated warm requests; collect request-level cached tokens **and TTFT** when relevant (TTFT must be measured separately; completion-response duration is not TTFT).
5. Record version, GPU, settings, request ordering, `null` coverage, and whether cache salts were used. Repeat trials for confidence intervals.
6. For concurrent attack/victim experiments, record the victim's own per-request hits and TTFT; a server-wide counter alone cannot identify the victim tenant.

| Symptom | Check |
| --- | --- |
| `curl .../v1/models` fails | `pgrep -af 'vllm|EngineCore'`, `tail -n 80 ~/vllm.log`, `nvidia-smi` |
| CUDA out of memory | Stop duplicate services first; don't launch a second Qwen 7B process on an occupied 24 GB GPU |
| `/reset_prefix_cache` returns 404 | Dev mode is absent from the *running* server; verify its environment and restart carefully |
| `prompt_tokens_details` is null for first request | Continue to second/third repeated requests; report null as missing |
| Warm requests also show null | Verify `enable_prompt_tokens_details` and `enable_prefix_caching` in current server logs; check whether prompts match and have a full cacheable prefix block |
| Unexpected small first B hit | Shared template prefix across tenants can yield a small hit; compare with the salted condition |
| Want per-tenant stats from `/metrics` alone | Server-wide cache metrics are not sufficient; attach trusted tenant identity to individual responses at the gateway |

## 7. References

- vLLM v0.17.1 security and dev endpoints: https://docs.vllm.ai/en/v0.17.1/usage/security/
- vLLM security / tenant isolation / `cache_salt`: https://docs.vllm.ai/en/stable/usage/security/
- vLLM prefix caching design: https://docs.vllm.ai/en/stable/design/v1/prefix_caching/

---

**Observed setup:** `gpu-node-1`, Qwen2.5-7B-Instruct, vLLM 0.17.1, RTX 3090, API port 8000. **Observed smoke test:** A request 2/3 hit 1,072/1,080; B request 2 hit 928/931. **Next research step:** trusted Gateway per-tenant aggregation across baseline and attack arms, keeping `null` coverage visible.
