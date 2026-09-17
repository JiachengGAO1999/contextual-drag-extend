"""Bounded, frozen fresh-question screening; never auto-accepts reasoning labels."""
import argparse
import csv
import json
import random
from pathlib import Path


def prepare(root, source, destination):
    if destination.exists():
        raise ValueError('Refusing to replace a frozen plan')
    excluded_ids, excluded_numbers, evidence = set(), set(), []
    paths = sorted(set((root/'outputs').rglob('draft_candidates.jsonl')) |
                   set((root/'outputs').rglob('results.jsonl')))
    for path in paths:
        count = 0
        for line in path.read_text(encoding='utf-8').splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            if 'id' in row:
                excluded_ids.add(str(row['id']))
            answer = row.get('answer')
            if isinstance(answer, list) and len(answer) == 4:
                excluded_numbers.add(tuple(sorted(int(x) for x in answer)))
            count += 1
        evidence.append({'path': str(path.relative_to(root)), 'records': count})
    if not evidence:
        raise ValueError('No historical records found; cannot establish fresh questions')
    with source.open(encoding='utf-8-sig') as handle:
        rows = list(csv.DictReader(handle))
    random.Random(20270917).shuffle(rows)
    selected = []
    for row in rows:
        numbers = [int(x) for x in row['Puzzles'].split()]
        key = tuple(sorted(numbers))
        if str(row['Rank']) in excluded_ids or key in excluded_numbers:
            continue
        selected.append(dict(id=str(row['Rank']), answer=numbers,
            problem=f"Use the numbers {', '.join(map(str,numbers))} exactly once each, with addition, subtraction, multiplication, division and parentheses, to make 24. Provide an expression using the original four numbers."))
        excluded_numbers.add(key)
        if len(selected) == 8:
            break
    if len(selected) != 8:
        raise ValueError('Insufficient unseen questions')
    plan = dict(authorized=True, screening_cap=32, evaluation_cap=48,
        max_evaluation_questions=6, samples_per_question=4, order_seed=20270917,
        draft_seed_base=917000, evaluation_seeds=[927001,927002],
        source=str(source), source_revision='8050e67d0e3a0fddc424d7fa5801538722a4c4cc',
        historical_records=evidence, excluded_ids=sorted(excluded_ids), questions=selected,
        selection='fixed question order; mixed completed parseable correct/failed samples; first failed reasoning draft passing frozen X audit; no outcome-based selection',
        annotation_gate='manual textual/arithmetic X audit before any intervention; no automatic guessed spans',
        conditions=['R0','R2','whole_path','X_path'],
        output='outputs/game24-heldout-screen-20260917')
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8')
    return plan


def run(backend, plan_path):
    from selective_context.prompting import encode_direct_prompt, render_chat_prompt, render_official_prompt, make_request
    from selective_context.schema import AccessMode
    from selective_context.phase0.real_smoke import evaluate, save, append
    from selective_context.phase0.thinking_pilot import extract_final_draft
    root=Path(__file__).resolve().parents[2]
    plan=json.loads(Path(plan_path).read_text(encoding='utf-8'))
    assert plan['authorized'] and plan['screening_cap']==32 and len(plan['questions'])==8
    out=root/plan['output']
    if out.exists():
        raise ValueError('Screening already started; explicit review required before resume')
    out.mkdir(parents=True)
    save(out/'config.json',plan)
    candidates=[]
    for index,row in enumerate(plan['questions']):
        enc=encode_direct_prompt(backend.tokenizer,render_chat_prompt(backend.tokenizer,
            render_official_prompt(root,'R0',row['problem']),enable_thinking=True))
        requests=[make_request(enc,'R0',AccessMode.FULL,plan['draft_seed_base']+4*index+j) for j in range(4)]
        results=backend.generate_batch(requests,max_new_tokens=32768,temperature=.6,top_p=.95,top_k=20)
        records=[]
        for j,(request,generation) in enumerate(zip(requests,results)):
            record=evaluate(row,enc,request,generation)
            final,status=extract_final_draft(generation.text,enc.text,backend.tokenizer.eos_token)
            record.update(final_response=final,thinking_status=status,draft_key=f"{row['id']}/{j}")
            record['init_response_generations_metadata'].update(enable_thinking=True,model_config_alias='Qwen3_8B_Thinking')
            append(out/'draft_candidates.jsonl',record)
            records.append(record)
        valid=[r for r in records if r['thinking_status']=='parsable_thinking' and r['final_response'] and r['init_response_generations'][0]['finish_reason']=='eos']
        correct=[r['draft_key'] for r in valid if r['init_response_generations'][0]['correctness'] is True]
        failed=[dict(draft_key=r['draft_key'],text=r['final_response']) for r in valid if r['init_response_generations'][0]['correctness'] is False]
        candidates.append(dict(id=row['id'],answer=row['answer'],correct_keys=correct,
            failed_candidates=failed,mixed_success=bool(correct and failed),annotation_status='pending'))
        save(out/'review_candidates.json',candidates)
        print(json.dumps(dict(event='heldout_screen_progress',completed=(index+1)*4,cap=32,id=row['id'],mixed_success=bool(correct and failed))),flush=True)
    save(out/'completion.json',dict(generations=32,evaluation_generations=0,status='awaiting_X_annotation_audit',mixed_success_questions=sum(r['mixed_success'] for r in candidates)))
    print('HELDOUT_SCREEN_COMPLETE_AWAITING_ANNOTATION',flush=True)


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,required=True);ap.add_argument('--plan',type=Path,required=True)
    args=ap.parse_args();plan=prepare(Path(__file__).resolve().parents[2],args.source,args.plan)
    print(json.dumps({'selected_ids':[q['id'] for q in plan['questions']],'screening_cap':32}))
