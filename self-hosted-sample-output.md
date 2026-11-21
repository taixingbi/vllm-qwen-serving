# Self-hosted Qwen2.5-7B: sample output

> **Self-hosted, no cloud API.** Every response below came from Qwen2.5-7B-Instruct running under vLLM on our own Linux machine with an NVIDIA GPU, reached over the local network. Prompts and responses stay inside the LAN, and there's no per-token billing.

What this page shows:

- **It works:** a standard OpenAI-style chat request returns a correct answer ([section 1](#1-chat-completion)).
- **It has held up under real use:** at capture time the server had been up for about 34 hours, processed about 7.13M prompt tokens, and had no preemptions ([section 2](#2-metrics)).
- **It's a drop-in for OpenAI clients:** it uses the same `/v1/chat/completions` endpoint and response format, so existing OpenAI SDK code only needs a new base URL.

The setup steps are in [README.md](README.md). All requests below were sent from a Mac on the same LAN.

## 1. Chat completion

Request (run from a Mac on the same LAN):

```bash
curl http://192.168.86.173:8000/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "Qwen/Qwen2.5-7B-Instruct",
    "messages": [
      {"role": "user", "content": "Explain vLLM in one sentence."}
    ],
    "max_tokens": 100
  }'
```

Response (pretty-printed):

```json
{
  "id": "chatcmpl-8d2c1bc8a34bc0cf",
  "object": "chat.completion",
  "created": 1795257413,
  "model": "Qwen/Qwen2.5-7B-Instruct",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "vLLM is a high-performance and efficient library for large language models that accelerates inference throughput and reduces memory usage.",
        "refusal": null,
        "annotations": null,
        "audio": null,
        "function_call": null,
        "tool_calls": [],
        "reasoning": null
      },
      "logprobs": null,
      "finish_reason": "stop",
      "stop_reason": null,
      "token_ids": null
    }
  ],
  "service_tier": null,
  "system_fingerprint": null,
  "usage": {
    "prompt_tokens": 38,
    "total_tokens": 63,
    "completion_tokens": 25,
    "prompt_tokens_details": null
  },
  "prompt_logprobs": null,
  "prompt_token_ids": null,
  "kv_transfer_params": null
}
```

Notes:

- The answer text is in `choices[0].message.content`.
- `finish_reason: "stop"` means the model finished on its own, before reaching `max_tokens` (100).
- `usage` shows 38 prompt tokens and 25 completion tokens. The prompt count is higher than the user message alone because the chat template adds a system prompt and role markers.
- curl doesn't print a trailing newline, so zsh shows a `%` right after the JSON. That's normal, not part of the response. To print just the answer, pipe the output through `jq -r '.choices[0].message.content'`.

## 2. Metrics

Request:

```bash
curl -s http://192.168.86.173:8000/metrics
```

Response (first part only; the full output is much longer):

```text
# HELP python_gc_objects_collected_total Objects collected during gc
# TYPE python_gc_objects_collected_total counter
python_gc_objects_collected_total{generation="0"} 33976.0
python_gc_objects_collected_total{generation="1"} 6540.0
python_gc_objects_collected_total{generation="2"} 230.0
# HELP python_gc_objects_uncollectable_total Uncollectable objects found during GC
# TYPE python_gc_objects_uncollectable_total counter
python_gc_objects_uncollectable_total{generation="0"} 0.0
python_gc_objects_uncollectable_total{generation="1"} 0.0
python_gc_objects_uncollectable_total{generation="2"} 0.0
# HELP python_gc_collections_total Number of times this generation was collected
# TYPE python_gc_collections_total counter
python_gc_collections_total{generation="0"} 2873.0
python_gc_collections_total{generation="1"} 261.0
python_gc_collections_total{generation="2"} 9.0
# HELP python_info Python platform information
# TYPE python_info gauge
python_info{implementation="CPython",major="3",minor="11",patchlevel="15",version="3.11.15"} 1.0
# HELP process_virtual_memory_bytes Virtual memory size in bytes.
# TYPE process_virtual_memory_bytes gauge
process_virtual_memory_bytes 1.2131586048e+010
# HELP process_resident_memory_bytes Resident memory size in bytes.
# TYPE process_resident_memory_bytes gauge
process_resident_memory_bytes 1.087504384e+09
# HELP process_start_time_seconds Start time of the process since unix epoch in seconds.
# TYPE process_start_time_seconds gauge
process_start_time_seconds 1.79513450902e+09
# HELP process_cpu_seconds_total Total user and system CPU time spent in seconds.
# TYPE process_cpu_seconds_total counter
process_cpu_seconds_total 431.2
# HELP process_open_fds Number of open file descriptors.
# TYPE process_open_fds gauge
process_open_fds 46.0
# HELP process_max_fds Maximum number of open file descriptors.
# TYPE process_max_fds gauge
process_max_fds 65535.0
# HELP vllm:estimated_flops_per_gpu_total Estimated number of floating point operations per GPU (for Model Flops Utilization calculations).
# TYPE vllm:estimated_flops_per_gpu_total counter
vllm:estimated_flops_per_gpu_total{engine="0",model_name="Qwen/Qwen2.5-7B-Instruct"} 0.0
# HELP vllm:estimated_flops_per_gpu_created Estimated number of floating point operations per GPU (for Model Flops Utilization calculations).
# TYPE vllm:estimated_flops_per_gpu_created gauge
vllm:estimated_flops_per_gpu_created{engine="0",model_name="Qwen/Qwen2.5-7B-Instruct"} 1.795134530075357e+09
# HELP vllm:estimated_read_bytes_per_gpu_total Estimated number of bytes read from memory per GPU (for Model Flops Utilization calculations).
# TYPE vllm:estimated_read_bytes_per_gpu_total counter
vllm:estimated_read_bytes_per_gpu_total{engine="0",model_name="Qwen/Qwen2.5-7B-Instruct"} 0.0
# HELP vllm:estimated_read_bytes_per_gpu_created Estimated number of bytes read from memory per GPU (for Model Flops Utilization calculations).
# TYPE vllm:estimated_read_bytes_per_gpu_created gauge
vllm:estimated_read_bytes_per_gpu_created{engine="0",model_name="Qwen/Qwen2.5-7B-Instruct"} 1.795134530075377e+09
# HELP vllm:estimated_write_bytes_per_gpu_total Estimated number of bytes written to memory per GPU (for Model Flops Utilization calculations).
# TYPE vllm:estimated_write_bytes_per_gpu_total counter
vllm:estimated_write_bytes_per_gpu_total{engine="0",model_name="Qwen/Qwen2.5-7B-Instruct"} 0.0
# HELP vllm:estimated_write_bytes_per_gpu_created Estimated number of bytes written to memory per GPU (for Model Flops Utilization calculations).
# TYPE vllm:estimated_write_bytes_per_gpu_created gauge
vllm:estimated_write_bytes_per_gpu_created{engine="0",model_name="Qwen/Qwen2.5-7B-Instruct"} 1.79513453007539e+09
# HELP vllm:num_requests_running Number of requests in model execution batches.
# TYPE vllm:num_requests_running gauge
vllm:num_requests_running{engine="0",model_name="Qwen/Qwen2.5-7B-Instruct"} 0.0
# HELP vllm:num_requests_waiting Number of requests waiting to be processed.
# TYPE vllm:num_requests_waiting gauge
vllm:num_requests_waiting{engine="0",model_name="Qwen/Qwen2.5-7B-Instruct"} 0.0
# HELP vllm:engine_sleep_state Engine sleep state; awake = 0 means engine is sleeping; awake = 1 means engine is awake; weights_offloaded = 1 means sleep level 1; discard_all = 1 means sleep level 2.
# TYPE vllm:engine_sleep_state gauge
vllm:engine_sleep_state{engine="0",model_name="Qwen/Qwen2.5-7B-Instruct",sleep_state="awake"} 1.0
vllm:engine_sleep_state{engine="0",model_name="Qwen/Qwen2.5-7B-Instruct",sleep_state="weights_offloaded"} 0.0
vllm:engine_sleep_state{engine="0",model_name="Qwen/Qwen2.5-7B-Instruct",sleep_state="discard_all"} 0.0
# HELP vllm:kv_cache_usage_perc KV-cache usage. 1 means 100 percent usage.
# TYPE vllm:kv_cache_usage_perc gauge
vllm:kv_cache_usage_perc{engine="0",model_name="Qwen/Qwen2.5-7B-Instruct"} 0.0
# HELP vllm:prefix_cache_queries_total Prefix cache queries, in terms of number of queried tokens.
# TYPE vllm:prefix_cache_queries_total counter
vllm:prefix_cache_queries_total{engine="0",model_name="Qwen/Qwen2.5-7B-Instruct"} 7.126829e+06
# HELP vllm:prefix_cache_queries_created Prefix cache queries, in terms of number of queried tokens.
# TYPE vllm:prefix_cache_queries_created gauge
vllm:prefix_cache_queries_created{engine="0",model_name="Qwen/Qwen2.5-7B-Instruct"} 1.7951345300754879e+09
# HELP vllm:prefix_cache_hits_total Prefix cache hits, in terms of number of cached tokens.
# TYPE vllm:prefix_cache_hits_total counter
vllm:prefix_cache_hits_total{engine="0",model_name="Qwen/Qwen2.5-7B-Instruct"} 1.194656e+06
# HELP vllm:prefix_cache_hits_created Prefix cache hits, in terms of number of cached tokens.
# TYPE vllm:prefix_cache_hits_created gauge
vllm:prefix_cache_hits_created{engine="0",model_name="Qwen/Qwen2.5-7B-Instruct"} 1.7951345300754995e+09
# HELP vllm:external_prefix_cache_queries_total External prefix cache queries from KV connector cross-instance cache sharing, in terms of number of queried tokens.
# TYPE vllm:external_prefix_cache_queries_total counter
vllm:external_prefix_cache_queries_total{engine="0",model_name="Qwen/Qwen2.5-7B-Instruct"} 0.0
# HELP vllm:external_prefix_cache_queries_created External prefix cache queries from KV connector cross-instance cache sharing, in terms of number of queried tokens.
# TYPE vllm:external_prefix_cache_queries_created gauge
vllm:external_prefix_cache_queries_created{engine="0",model_name="Qwen/Qwen2.5-7B-Instruct"} 1.7951345300755103e+09
# HELP vllm:external_prefix_cache_hits_total External prefix cache hits from KV connector cross-instance cache sharing, in terms of number of cached tokens.
# TYPE vllm:external_prefix_cache_hits_total counter
vllm:external_prefix_cache_hits_total{engine="0",model_name="Qwen/Qwen2.5-7B-Instruct"} 0.0
# HELP vllm:external_prefix_cache_hits_created External prefix cache hits from KV connector cross-instance cache sharing, in terms of number of cached tokens.
# TYPE vllm:external_prefix_cache_hits_created gauge
vllm:external_prefix_cache_hits_created{engine="0",model_name="Qwen/Qwen2.5-7B-Instruct"} 1.7951345300756254e+09
# HELP vllm:mm_cache_queries_total Multi-modal cache queries, in terms of number of queried items.
# TYPE vllm:mm_cache_queries_total counter
vllm:mm_cache_queries_total{engine="0",model_name="Qwen/Qwen2.5-7B-Instruct"} 0.0
# HELP vllm:mm_cache_queries_created Multi-modal cache queries, in terms of number of queried items.
# TYPE vllm:mm_cache_queries_created gauge
vllm:mm_cache_queries_created{engine="0",model_name="Qwen/Qwen2.5-7B-Instruct"} 1.7951345300756366e+09
# HELP vllm:mm_cache_hits_total Multi-modal cache hits, in terms of number of cached items.
# TYPE vllm:mm_cache_hits_total counter
vllm:mm_cache_hits_total{engine="0",model_name="Qwen/Qwen2.5-7B-Instruct"} 0.0
# HELP vllm:mm_cache_hits_created Multi-modal cache hits, in terms of number of cached items.
# TYPE vllm:mm_cache_hits_created gauge
vllm:mm_cache_hits_created{engine="0",model_name="Qwen/Qwen2.5-7B-Instruct"} 1.7951345300756457e+09
# HELP vllm:num_preemptions_total Cumulative number of preemption from the engine.
# TYPE vllm:num_preemptions_total counter
vllm:num_preemptions_total{engine="0",model_name="Qwen/Qwen2.5-7B-Instruct"} 0.0
# HELP vllm:num_preemptions_created Cumulative number of preemption from the engine.
# TYPE vllm:num_preemptions_created gauge
vllm:num_preemptions_created{engine="0",model_name="Qwen/Qwen2.5-7B-Instruct"} 1.7951345300756536e+09
# HELP vllm:prompt_tokens_total Number of prefill tokens processed.
# TYPE vllm:prompt_tokens_total counter
vllm:prompt_tokens_total{engine="0",model_name="Qwen/Qwen2.5-7B-Instruct"} 7.126143e+06
# HELP vllm:prompt_tokens_created Number of prefill tokens processed.
# TYPE vllm:prompt_tokens_created gauge
vllm:prompt_tokens_created{engine="0",model_name="Qwen/Qwen2.5-7B-Instruct"} 1.7951345300756605e+09
# HELP vllm:prompt_tokens_by_source_total Number of prompt tokens by source.
# TYPE vllm:prompt_tokens_by_source_total counter
vllm:prompt_tokens_by_source_total{engine="0",model_name="Qwen/Qwen2.5-7B-Instruct",source="local_compute"} 5.932143e+06
vllm:prompt_tokens_by_source_total{engine="0",model_name="Qwen/Qwen2.5-7B-Instruct",source="local_cache_hit"} 1.19444e+06
vllm:prompt_tokens_by_source_total{engine="0",model_name="Qwen/Qwen2.5-7B-Instruct",source="external_kv_transfer"} 0.0
...
```

How to read this snapshot:

| Metric | Value | Meaning |
|---|---|---|
| `vllm:num_requests_running` / `vllm:num_requests_waiting` | 0 / 0 | The server was idle when this was captured. |
| `vllm:kv_cache_usage_perc` | 0.0 | KV cache is empty, as expected when idle. |
| `vllm:num_preemptions_total` | 0 | No request has ever been evicted for lack of KV-cache space. |
| `vllm:engine_sleep_state{sleep_state="awake"}` | 1 | The engine is awake, with weights loaded on the GPU. |
| `vllm:prompt_tokens_total` | ~7.13M | Total prompt tokens since startup. |
| `vllm:prompt_tokens_by_source_total` | 5.93M computed, 1.19M from cache | About 17% of prompt tokens were served from the prefix cache instead of being recomputed. |
| `vllm:prefix_cache_hits_total` / `vllm:prefix_cache_queries_total` | 1.19M / 7.13M | Same prefix-cache hit rate, about 16.8%. |
| `process_resident_memory_bytes` | ~1.09 GB | CPU RAM used by the API server process. GPU memory isn't included; check it with `nvidia-smi`. |
| `process_start_time_seconds` | 1795134509 | Unix time the process started, about 34 hours before the chat request in section 1. |

Notes:

- Lines starting with `# HELP` describe a metric and lines starting with `# TYPE` give its type: a `counter` only goes up, a `gauge` can go up or down.
- The `*_created` gauges are the Unix times each counter was created, not measurements. You can skip them.
- The `vllm:estimated_*_per_gpu_total` counters are 0 here. This snapshot doesn't show why; they appear to be off unless MFU (Model FLOPs Utilization) tracking is turned on.
- To skip the Python and process metrics, use `curl -s http://192.168.86.173:8000/metrics | grep '^vllm:'`.

### Prefix-cache reset

The server exposes a prefix-cache reset path in this vLLM version:

```bash
curl -s http://192.168.86.173:8000/openapi.json |
  grep -o '"/[^"]*reset_prefix_cache[^"]*"'
```

```text
"/reset_prefix_cache"
```

Reset the cache with:

```bash
curl -X POST http://192.168.86.173:8000/reset_prefix_cache
```

## 3. GPU idle state

On the GPU host, monitor utilization and memory once per second:

```bash
nvidia-smi dmon -s pucvmet -d 1
```

The idle samples looked like this:

```text
# gpu    pwr  gtemp  mtemp     sm    mem    enc    dec    jpg    ofa   mclk   pclk  pviol  tviol     fb   bar1   ccpm  sbecc  dbecc    pci  rxpci  txpci

    0     28     40      -      0      0      0      0      0      0    405    210      0      0  21437      4      0      -      -      0      0      0

    0     19     40      -      0      0      0      0      0      0    405    210     82      0  21437      4      0      -      -      0      0      0

    0     19     40      -      0      0      0      0      0      0    405    210     99      0  21437      4      0      -      -      0      0      0
```

How to read these idle samples:

| Field | Typical value | Meaning |
|---|---:|---|
| `pwr` | 19-29 W | GPU board power draw. |
| `gtemp` | 40 C | GPU temperature. |
| `sm` | 0% | No active streaming-multiprocessor compute. |
| `mem` | 0% | Memory-controller activity; no active memory workload was shown in these samples. |
| `mclk` / `pclk` | 405 / 210 MHz | Idle memory and graphics clocks. |
| `pviol` | 82-99% | Percentage of time in power-violation throttling in the recent sample window. |
| `tviol` | 0 | No thermal throttling. |
| `fb` | 21,437 MB | GPU framebuffer occupied by the loaded model and vLLM allocations. |
| `bar1` | 4 MB | BAR1 memory currently used. |

An idle GPU can therefore still report substantial framebuffer usage because the model remains loaded. Zero SM utilization is expected between requests; it is not evidence that the vLLM process or model weights were unloaded.

### Reading the same GPU state from the Mac

With [nvidia_gpu_exporter](README.md#monitor-the-gpu-from-another-machine) (v2.0.0) running on the GPU host, the Mac reads the GPU directly with `curl`. It needs no SSH and nothing installed on the Mac:

```bash
curl -s http://192.168.86.173:9835/metrics |
  grep -E '^nvidia_smi_(power_draw_watts|temperature_gpu|utilization_gpu_ratio|memory_used_bytes)'
```

```text
nvidia_smi_memory_used_bytes{uuid="a837190a-d9c2-ed45-994b-55319c6e258e"} 2.1186281472e+10
nvidia_smi_power_draw_watts{uuid="a837190a-d9c2-ed45-994b-55319c6e258e"} 29.946
nvidia_smi_temperature_gpu{uuid="a837190a-d9c2-ed45-994b-55319c6e258e"} 44
nvidia_smi_utilization_gpu_ratio{uuid="a837190a-d9c2-ed45-994b-55319c6e258e"} 0
```

| Metric | Raw value | Meaning |
|---|---|---|
| `memory_used_bytes` | `2.1186e+10` | About 20,205 MiB (21.2 GB) of VRAM in use; the model is still loaded. |
| `power_draw_watts` | `29.946` | About 30 W, normal idle power. |
| `temperature_gpu` | `44` | 44 C. |
| `utilization_gpu_ratio` | `0` | 0% SM utilization (the ratio runs from 0 to 1). |

The `uuid` label identifies the GPU and can be ignored on a single-GPU host.

For a live `dmon`-style view, [scripts/gpuwatch.sh](scripts/gpuwatch.sh) polls the exporter once per second:

```text
time      pwr_W temp_C   sm%  mem%   mclk   pclk   pcap tthrot     fb_MB bar1_MB
06:31:30   30.5     44     0     0    405    210      0      0     20204       4
06:31:31   38.9     45     0     0    405    210      0      0     20204       4
06:31:32   31.0     45     0     0    405    210      0      0     20204       4
```

This matches the `dmon` idle samples above: power, clocks and utilization are at idle levels, and about 20 GiB of VRAM is still held by the loaded model.
