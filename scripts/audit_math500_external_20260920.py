"""CPU-only official scoring of existing public R1 outputs, no generation."""
import argparse,json,hashlib,os
from collections import Counter
from pathlib import Path
from utils.verifiable_evaluation.math_eval.utils.evaluation_utils import evaluate_single_response
from utils.verifiable_evaluation.math_eval.utils.math_utils import is_equivalent_math

def main():
    assert os.environ.get('CUDA_VISIBLE_DEVICES')==''
    root=Path(__file__).resolve().parents[1]
    ap=argparse.ArgumentParser()
    ap.add_argument('--source',type=Path,default=root/'outputs/rasbt_r1.json')
    ap.add_argument('--output',type=Path,default=root/'outputs/math500-external-audit-20260920')
    args=ap.parse_args()
    source=args.source
    out=args.output
    out.mkdir(exist_ok=False)
    rows=json.loads(source.read_text(encoding='utf8'));counts=Counter();reviews=[]
    with (out/'scored.jsonl').open('w',encoding='utf8') as f:
        for i,r in enumerate(rows):
            g=evaluate_single_response({'generated_response':r['message_content']},r['gtruth_answer'],is_equivalent_math)
            cat='correct' if g['correctness'] is True else 'scorer_false' if g['correctness'] is False else 'unparsed'
            counts[cat]+=1
            record=dict(index=i,problem_sha256=hashlib.sha256(r['problem'].encode()).hexdigest(),**r,
                        category=cat,extracted_answer=g['extracted_answer'],source_finish_reason='unknown',manual_status='pending' if cat!='correct' else 'not_requested')
            f.write(json.dumps(record,ensure_ascii=False)+'\n');f.flush()
            if cat!='correct':reviews.append(record)
            if (i+1)%50==0:print(i+1,dict(counts),flush=True)
    (out/'review_queue.json').write_text(json.dumps(reviews,ensure_ascii=False,indent=2),encoding='utf8')
    (out/'summary.json').write_text(json.dumps(dict(rows=len(rows),counts=dict(counts),new_generations=0,manual_review_pending=True,source_sha256=hashlib.sha256(source.read_bytes()).hexdigest()),indent=2))
    print('CPU_AUDIT_COMPLETE',dict(counts),flush=True)

if __name__=='__main__':main()
