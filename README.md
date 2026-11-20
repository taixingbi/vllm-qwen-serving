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

## 6. Stop or restart the server

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
