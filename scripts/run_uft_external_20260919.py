"""One approved160-request experiment, then retain the same engine on GPU4."""
import code,json,os,time,traceback
from pathlib import Path
from selective_context.vllm_backend import SelectiveVLLMBackend
from selective_context.phase0.vllm_run import main as run

ROOT=Path(__file__).resolve().parents[1]
PREP=ROOT/'outputs/game24-uft-external-20q-20260919-prepared'
OUT=ROOT/'outputs/game24-uft-external-20q-20260919'

def main():
    assert os.environ['CUDA_VISIBLE_DEVICES']=='4'
    assert not OUT.exists()
    assert json.loads((PREP/'preflight.json').read_text())['passed']
    manifest=json.loads((PREP/'manifest.json').read_text());assert len(manifest)==160
    status=ROOT/'outputs/game24-uft-external-20q-20260919-status.json'
    def save(state,**kw):status.write_text(json.dumps(dict(state=state,time=time.time(),**kw),indent=2))
    save('loading_model',total=160)
    backend=SelectiveVLLMBackend('/data2/huangrj/models/qwen3-8b',max_num_seqs=8)
    save('running',total=160)
    try:
        run(['--manifest',str(PREP/'manifest.json'),'--output',str(OUT),'--batch-size','8'],backend=backend)
        save('complete_resident',completed=160)
    except Exception:
        save('failed_no_retry_resident');traceback.print_exc()
    print('EXPERIMENT_STOPPED_NO_EXPANSION; SAME_ENGINE_RESIDENT',flush=True)
    code.interact(banner='Frozen UFT run stopped. Backend remains loaded; no automatic next experiment.',local={'backend':backend})

if __name__=='__main__':main()
