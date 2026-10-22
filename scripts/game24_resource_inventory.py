"""Read-only GPU inventory, also runnable through ssh python3 stdin."""
import datetime
import json
import socket
import subprocess

def query(args):
    return subprocess.check_output(args, text=True, timeout=20).strip()

def main():
    fields=['index','uuid','name','memory.total','memory.used','memory.free','utilization.gpu']
    raw=query(['nvidia-smi','--query-gpu='+','.join(fields),'--format=csv,noheader,nounits'])
    gpus=[]
    for line in raw.splitlines():
        values=[x.strip() for x in line.split(',')]
        r=dict(zip(fields,values)); r['processes']=[]; gpus.append(r)
    processes=query(['nvidia-smi','--query-compute-apps=gpu_uuid,pid,process_name,used_memory','--format=csv,noheader,nounits'])
    for line in processes.splitlines():
        values=[x.strip() for x in line.split(',')]
        if len(values)!=4: continue
        uuid,pid,name,memory=values
        try: owner=query(['ps','-p',pid,'-o','user='])
        except subprocess.CalledProcessError: owner='exited_or_unavailable'
        for gpu in gpus:
            if gpu['uuid']==uuid:
                gpu['processes'].append(dict(pid=int(pid), owner=owner, name=name, memory_mib=memory))
    disk={}
    for path in ['/data2','/data']:
        try: disk[path]=query(['df','-h',path]).splitlines()[-1]
        except subprocess.CalledProcessError: pass
    print(json.dumps(dict(hostname=socket.gethostname(), utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                         gpus=gpus,disk=disk),ensure_ascii=False,indent=2))

if __name__=='__main__': main()
