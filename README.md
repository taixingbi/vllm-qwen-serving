# Deploy Qwen2.5-7B-Instruct with vLLM on Linux

Run an OpenAI-compatible Qwen API server on an NVIDIA GPU (for example, an RTX 3090 with 24 GiB VRAM). These commands assume your Linux account is `tb` and your Conda environment is named `vllm`.

## 1. Connect to the GPU server

From your local machine:

```bash
ssh tb@192.168.86.173
# or
ssh tb@192.168.86.176
```

Replace the IP address if your server is different.

## 2. Check GPU and activate vLLM

```bash
nvidia-smi
conda env list
conda activate vllm
which vllm
vllm --version
```

**Important:** `vllm: command not found` while the prompt shows `(base)` usually means the executable is not on the current environment's `PATH`. Activate the `vllm` environment before starting the server.

If `vllm` is still missing *after activating the intended environment*, check installation:

```bash
python -m pip show vllm
```

If the package is not installed, install it **inside that environment**:

```bash
python -m pip install vllm
```

## 3. Start Qwen 7B in the background

From the activated `(vllm)` environment:

```bash
nohup env CUDA_VISIBLE_DEVICES=0 vllm serve Qwen/Qwen2.5-7B-Instruct \
  --host 0.0.0.0 \
  --port 8000 \
  --dtype float16 \
  --max-model-len 4096 \
  --gpu-memory-utilization 0.85 \
  > ~/vllm.log 2>&1 < /dev/null &
```

The terminal prints a job number and a process ID (PID). This indicates that the command was submitted in the background—not that model startup succeeded. First launch may download the model from Hugging Face.

`nohup` allows the server to keep running after you disconnect SSH, but it **does not restart the server after a machine reboot**. For automatic restarts, use a `systemd` service.

## 4. Verify startup

Check recent logs:

```bash
tail -n 50 ~/vllm.log
```

Follow logs live (press `Ctrl+C` to stop following the log; the server keeps running):

```bash
tail -f ~/vllm.log
```

Check process and GPU usage:

```bash
pgrep -af 'vllm serve'
nvidia-smi
```

After startup, check the local API:

```bash
curl http://192.168.86.173:8000/v1/models
```

A successful response should include `Qwen/Qwen2.5-7B-Instruct` in the available models.

## 5. Send a test chat request

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

From another machine **on your trusted local network**, replace `localhost` with the server IP:

```bash
curl http://192.168.86.173:8000/v1/models
```

**Security:** This example uses `--host 0.0.0.0` without API authentication. Restrict access to trusted machines; do not expose port 8000 to the public internet. For wider access, add authentication and network controls.

## 6. Monitor metrics

vLLM exposes Prometheus-format metrics at `/metrics` on the same port as the API. No extra flags or restart are needed.

Show all metrics:

```bash
curl -s http://192.168.86.173:8000/metrics
```

Show only vLLM's own metrics (skip the Python and process metrics):

```bash
curl -s http://192.168.86.173:8000/metrics | grep '^vllm:'
```

Key metrics to watch:

| Metric | Meaning |
|---|---|
| `vllm:num_requests_running` | Requests currently being processed. |
| `vllm:num_requests_waiting` | Requests queued. A steadily non-zero value means the server is saturated. |
| `vllm:kv_cache_usage_perc` | KV-cache usage from 0 to 1. Near 1.0, requests may be preempted. Older versions call this `vllm:gpu_cache_usage_perc`. |
| `vllm:prompt_tokens_total` | Total prompt (input) tokens processed. Its rate over time is prefill throughput. |
| `vllm:generation_tokens_total` | Total generated (output) tokens. Its rate over time is generation throughput. |
| `vllm:time_to_first_token_seconds` | Histogram of time from request arrival to first output token. |
| `vllm:inter_token_latency_seconds` | Histogram of time between output tokens. Older versions call this `vllm:time_per_output_token_seconds`. |
| `vllm:e2e_request_latency_seconds` | Histogram of total request latency. |

Metric names vary between vLLM versions; use the `grep '^vllm:'` output above to confirm the names your installation reports. Histograms appear as `_bucket`, `_sum`, and `_count` series; `_sum` divided by `_count` gives the mean.

## 7. Stop or restart the server

Find the server PID:

```bash
pgrep -af 'vllm serve'
```

Stop the matching vLLM server process gracefully using its actual PID:

```bash
kill <PID>
```

Replace `<PID>` with the numeric process ID; don't type the angle brackets literally. To restart, run the command in step 3 again and verify the log and API.

## Troubleshooting

| Symptom | What to check |
|---|---|
| `env: 'vllm': No such file or directory` | Run `conda activate vllm`, then `which vllm`; confirm the package is installed in that environment. |
| `curl: (7) Failed to connect` | vLLM may still be starting or may have exited. Check `tail -n 50 ~/vllm.log` and `pgrep -af 'vllm serve'`. |
| CUDA out-of-memory | Confirm other processes are not using VRAM with `nvidia-smi`; try lowering `--max-model-len` or `--gpu-memory-utilization`. |
| Remote access fails but localhost works | Check the server IP, firewall, LAN routing, and whether TCP port 8000 is allowed. |

## Configuration notes

- `CUDA_VISIBLE_DEVICES=0`: use the first visible NVIDIA GPU.
- `--dtype float16`: load weights in FP16.
- `--max-model-len 4096`: limit maximum context length to 4,096 tokens.
- `--gpu-memory-utilization 0.85`: target up to 85% of available GPU memory for this vLLM instance.
- `--port 8000`: serve the OpenAI-compatible API on TCP port 8000.
# vllm-qwen-serving
