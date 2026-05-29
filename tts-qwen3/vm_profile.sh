#!/usr/bin/env bash
set -u
echo "### GPU status (idle) ###"
nvidia-smi --query-gpu=name,memory.used,memory.total,utilization.gpu,clocks.sm,clocks.max.sm --format=csv

echo
echo "### torch / cuda inside container ###"
sudo docker exec qwen3-tts python -c "import torch; print('torch', torch.__version__); print('cuda avail', torch.cuda.is_available()); print('device', torch.cuda.get_device_name(0)); print('cuda ver', torch.version.cuda); print('capability', torch.cuda.get_device_capability(0))" 2>&1

echo
echo "### profile a single generate inside the container ###"
sudo docker exec qwen3-tts python - <<'PY' 2>&1
import time, torch
from server import app, _qwen_synthesize, _load_models
# model is loaded at startup; access via app.state
import server
if not hasattr(server.app.state, "qwen_model"):
    print("model not on app.state; triggering load")
    server._load_models()

txt = "Krishna is a Hindu deity."
# Warmup
t0=time.time(); a,sr=server._qwen_synthesize(txt,"english","serena"); torch.cuda.synchronize(); print("warmup", round(time.time()-t0,2),"s samples",len(a),"sr",sr)
for i in range(3):
    t0=time.time(); a,sr=server._qwen_synthesize(txt,"english","serena"); torch.cuda.synchronize(); print(f"run{i}", round(time.time()-t0,2),"s")
# longer
txt2="Krishna is a principal deity in Hinduism. He is revered as the eighth avatar of Vishnu."
t0=time.time(); a,sr=server._qwen_synthesize(txt2,"english","serena"); torch.cuda.synchronize(); print("two-sentence", round(time.time()-t0,2),"s samples",len(a))
PY

echo
echo "### GPU clocks during load (check throttling/persistence) ###"
nvidia-smi -q -d CLOCK 2>&1 | grep -A2 "Max Clocks" | head -6
