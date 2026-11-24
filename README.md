# Deploy Qwen2.5-7B-Instruct with vLLM on Linux

Run an OpenAI-compatible Qwen API server on an NVIDIA GPU (for example, an RTX 3090 with 24 GiB VRAM). These commands assume your Linux account is `tb` and your Conda environment is named `vllm`.

## 1. Connect to the GPU server

From your local machine:

```bash
ssh tb@192.168.86.173
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

### Reset the prefix cache

Some vLLM versions expose a prefix-cache reset endpoint. Check the OpenAPI paths for it:

```bash
curl -s http://192.168.86.173:8000/openapi.json |
  grep -o '"/[^"]*reset_prefix_cache[^"]*"'
```

If `"/reset_prefix_cache"` is returned, reset the prefix cache with:

```bash
curl -X POST http://192.168.86.173:8000/reset_prefix_cache
```

The prefix cache stores reusable prompt KV blocks. Resetting it is useful for cache-focused testing or cleanup, but the next prompts must rebuild cached prefixes, so a reset may temporarily reduce cache-hit throughput.

### Monitor GPU utilization

On the GPU host, sample GPU power, utilization, clocks, memory, and PCI activity once per second:

```bash
nvidia-smi dmon -s pucvmet -d 1
```

When no requests are running, low SM utilization and power do not necessarily mean the model is unloaded: weights and the KV-cache allocator may still occupy VRAM. Use `nvidia-smi` or the `fb` and `bar1` columns in `dmon` to confirm framebuffer and BAR1 memory usage.

### Monitor the GPU from another machine

`nvidia-smi` only runs on the GPU host. To check the GPU from a laptop (for example, a Mac) without installing anything on it, choose one of these options.

**Option A: run `nvidia-smi` over SSH.** This needs no setup:

```bash
ssh -t tb@192.168.86.173 'nvidia-smi dmon -s pucvmet -d 1'   # Ctrl+C to stop
```

**Option B: run a GPU metrics exporter on the GPU host.** [nvidia_gpu_exporter](https://github.com/utkuozdemir/nvidia_gpu_exporter) wraps `nvidia-smi` and serves Prometheus-format metrics on port 9835. It works on GeForce cards, and clients can read it with plain `curl`, without SSH.

Install and start it on the GPU host:

```bash
cd ~
VER=$(curl -s https://api.github.com/repos/utkuozdemir/nvidia_gpu_exporter/releases/latest | grep -Po '"tag_name": "v\K[^"]+')
echo "version: $VER"   # if empty, download the linux_x86_64 .tar.gz from the Releases page manually
curl -LO https://github.com/utkuozdemir/nvidia_gpu_exporter/releases/download/v${VER}/nvidia_gpu_exporter_${VER}_linux_x86_64.tar.gz
tar xzf nvidia_gpu_exporter_${VER}_linux_x86_64.tar.gz
sudo mv nvidia_gpu_exporter /usr/local/bin/
nohup nvidia_gpu_exporter > ~/gpu_exporter.log 2>&1 &
curl -s localhost:9835/metrics | grep nvidia_smi_power_draw_watts   # verify
```

Like the vLLM server, `nohup` does not survive a reboot; use a `systemd` service for automatic restarts. Port 9835 has no authentication, so keep it on the trusted LAN. If a client can't reach the port, allow it from the LAN only, for example with `sudo ufw allow from 192.168.86.0/24 to any port 9835 proto tcp`.

From the client, read a few values:

```bash
curl -s http://192.168.86.173:9835/metrics |
  grep -E '^nvidia_smi_(power_draw_watts|temperature_gpu|utilization_gpu_ratio|memory_used_bytes)'
```

Or watch them live in a `dmon`-like table with [scripts/gpuwatch.sh](scripts/gpuwatch.sh), which needs only `curl` and `awk`:

```bash
scripts/gpuwatch.sh                    # 192.168.86.173, every 1 s
scripts/gpuwatch.sh 192.168.86.173 2   # explicit host, every 2 s
```

| Script column | `dmon` field | Exporter metric |
|---|---|---|
| `pwr_W` | `pwr` | `nvidia_smi_power_draw_watts` |
| `temp_C` | `gtemp` | `nvidia_smi_temperature_gpu` |
| `sm%` | `sm` | `nvidia_smi_utilization_gpu_ratio` × 100 (the ratio runs from 0 to 1) |
| `mem%` | `mem` | `nvidia_smi_utilization_memory_ratio` × 100 |
| `mclk` / `pclk` | `mclk` / `pclk` | `nvidia_smi_clocks_current_memory_clock_hz` / `..._graphics_clock_hz` |
| `pcap` | roughly `pviol` | `nvidia_smi_clocks_event_reasons_sw_power_cap` (0/1 flag, not a percentage) |
| `tthrot` | roughly `tviol` | `..._hw_thermal_slowdown` + `..._sw_thermal_slowdown` (0/1 flags) |
| `fb_MB` | `fb` | `nvidia_smi_memory_used_bytes` ÷ 1,048,576 (MiB) |
| `bar1_MB` | `bar1` | `nvidia_smi_bar1_memory_used_bytes` ÷ 1,048,576 (MiB) |

The exporter has no direct equivalent of `dmon`'s `pviol` percentage. For cumulative power-cap time, use `nvidia_smi_clocks_event_reasons_counters_sw_power_cap_seconds`. To list every metric name your exporter version reports:

```bash
curl -s http://192.168.86.173:9835/metrics | grep '^nvidia_smi' | cut -d'{' -f1 | sort -u
```

Because both the exporter and vLLM's `/metrics` endpoint use the Prometheus format, you can later point Prometheus and Grafana at `<host>:9835` and `<host>:8000` for dashboards and history. Nothing on the GPU host has to change.

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
| `tar: ... Cannot open: No such file or directory` when installing the exporter | The release archive wasn't downloaded. Run the `curl -LO` step first and check that `echo "version: $VER"` printed a version. |
| `brew: command not found` on the GPU host | Homebrew is for macOS. Run `brew` commands on the Mac, not over SSH on the Linux server. |

## Configuration notes

- `CUDA_VISIBLE_DEVICES=0`: use the first visible NVIDIA GPU.
- `--dtype float16`: load weights in FP16.
- `--max-model-len 4096`: limit maximum context length to 4,096 tokens.
- `--gpu-memory-utilization 0.85`: target up to 85% of available GPU memory for this vLLM instance.
- `--port 8000`: serve the OpenAI-compatible API on TCP port 8000.
# vllm-qwen-serving
