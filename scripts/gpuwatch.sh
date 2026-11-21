#!/bin/sh
# Print GPU stats from a remote nvidia_gpu_exporter (port 9835), dmon-style.
# Needs only curl and awk on the client. Ctrl+C to stop.
# Usage: scripts/gpuwatch.sh [host] [interval_seconds]
HOST=${1:-192.168.86.173}; INT=${2:-1}
printf '%-8s %6s %6s %5s %5s %6s %6s %6s %6s %9s %7s\n' time pwr_W temp_C sm% mem% mclk pclk pcap tthrot fb_MB bar1_MB
while :; do
  curl -s --max-time 3 "http://$HOST:9835/metrics" | sed 's/{[^}]*}//' | awk -v t="$(date +%H:%M:%S)" '
    {v[$1]=$2}
    END{printf "%-8s %6.1f %6d %5d %5d %6d %6d %6d %6d %9d %7d\n", t,
      v["nvidia_smi_power_draw_watts"], v["nvidia_smi_temperature_gpu"],
      v["nvidia_smi_utilization_gpu_ratio"]*100, v["nvidia_smi_utilization_memory_ratio"]*100,
      v["nvidia_smi_clocks_current_memory_clock_hz"]/1e6, v["nvidia_smi_clocks_current_graphics_clock_hz"]/1e6,
      v["nvidia_smi_clocks_event_reasons_sw_power_cap"],
      v["nvidia_smi_clocks_event_reasons_hw_thermal_slowdown"]+v["nvidia_smi_clocks_event_reasons_sw_thermal_slowdown"],
      v["nvidia_smi_memory_used_bytes"]/1048576, v["nvidia_smi_bar1_memory_used_bytes"]/1048576}'
  sleep "$INT"
done
