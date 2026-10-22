"""Replace only the verified idle resident that this project owns on GPU4."""
import os, subprocess, time
import psutil
p=psutil.Process(930273)
assert p.username()=='gaojc'
assert p.cmdline()==['/data2/gaojc/envs/contextual-drag-vllm/bin/python','-m','selective_context.phase0.vllm_resident'],p.cmdline()
assert p.environ()['CUDA_VISIBLE_DEVICES']=='4'
children=p.children(recursive=True)
assert all(c.username()=='gaojc' for c in children)
p.terminate()
for child in children:
    if child.is_running():child.terminate()
_,alive=psutil.wait_procs([p]+children,timeout=30)
assert not alive,[x.pid for x in alive]
time.sleep(3)
memory=int(subprocess.check_output(['nvidia-smi','--id=4','--query-gpu=memory.used','--format=csv,noheader,nounits'],text=True))
assert memory<1000,memory
subprocess.run(['tmux','new-session','-d','-s','night-validation-20260920',
    'bash /data2/gaojc/tmp/math-external-16q-20260920/scripts/night_validation_20260920.sh > /data2/gaojc/tmp/math-external-16q-20260920/outputs/night-validation-20260920.log 2>&1'],check=True)
print('Started approved GPU4 queue: 104 MATH then 64 Game24.')
