"""Bounded Qwen3 Thinking R0-R4 pilot, with resumable per-generation artifacts."""
from __future__ import annotations

import argparse
import csv
import json
import random
import subprocess
import time
from pathlib import Path

import torch
import transformers
from transformers import AutoModelForCausalLM, AutoTokenizer

from data_generation.initial_sampling_postprocess import parse_thinking_steps
from selective_context.hf_backend import SelectiveHFBackend
from selective_context.phase0.real_smoke import append, evaluate, sanity, save
from selective_context.phase0.paired_report import summarize
from selective_context.prompting import (encode_direct_prompt, encode_prompt, make_request,
    make_r2_r4_requests, persist_request_bundle, load_request_bundle,
    render_chat_prompt, render_official_prompt)
from selective_context.schema import AccessMode


def generation_budget(prompt_tokens, context_size=32768):
    if not 0 < prompt_tokens < context_size:
        raise ValueError("Prompt exceeds total context budget; no truncation permitted")
    return context_size - prompt_tokens


def extract_final_draft(raw_text, prompt, eos_token):
    final, status = parse_thinking_steps(raw_text, prompt, max_response_length=32768*20)
    if eos_token:
        final = final.replace(eos_token, "")
    final = final.strip()
    return final, status


def rows_from(path):
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


INDEPENDENT_SUFFIX = (
    "Solve the original problem independently and provide a complete solution. "
    "You do not need to evaluate or refer to any preceding draft. "
    "Conclude with an expression using the original four numbers exactly once in \\boxed{}."
)


def independent_prompt(problem, draft=None):
    text = f"Original problem:\n{problem}\n"
    if draft is not None:
        text += ("\nThe following draft has an INCORRECT final answer.\n"
                 f"-- beginning of the draft --\n{draft}\n-- end of the draft --\n")
    return text + '\n' + INDEPENDENT_SUFFIX


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--count", type=int, default=3)
    parser.add_argument("--max-candidates", type=int, default=40)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--drafts-only", action="store_true")
    parser.add_argument("--start-index", type=int, default=0)
    parser.add_argument("--fixed-drafts", type=Path)
    parser.add_argument("--evaluation-seed-base", type=int, default=2027)
    parser.add_argument("--independent-solve", action="store_true")
    args = parser.parse_args()
    fixed = json.loads(args.fixed_drafts.read_text(encoding='utf-8')) if args.fixed_drafts else None
    if args.independent_solve and not fixed:
        parser.error("Independent-solve control requires fixed drafts")
    if fixed and (args.drafts_only or args.count != len(fixed['selected'])):
        parser.error("Fixed drafts require paired mode and count equal to selected problems")
    if not 0 <= args.start_index < args.max_candidates:
        parser.error("Require 0 <= start-index < max-candidates (exclusive end index)")
    repo = Path(__file__).resolve().parents[2]
    official = json.loads((repo/'utils/general_inference/eval_models_params.json').read_text())['Qwen3_8B_Thinking']
    assert official['context_length'] == 32768
    sample = official['sampling_params']
    assert (sample['temperature'], sample['top_p'], sample['top_k']) == (.6, .95, 20)
    frozen = dict(model=args.model, input=str(args.input), source_revision=args.source_revision,
        purpose="thinking_quick_scientific_pilot", enable_thinking=True, context_size=32768,
        temperature=.6, top_p=.95, top_k=20, generation_budget="32768 minus full prompt length",
        drafts_per_problem=4, order_seed=2027, draft_seed_base=102027, evaluation_seed_base=args.evaluation_seed_base,
        backend="hf_eager_bfloat16", thinking_removal="upstream parse_thinking_steps; final only in draft context",
        sampling_dtype="float32",
        selection="first fixed-order problems with both completed parseable correct and incorrect responses among four independent Thinking samples; first eligible failed draft; no evaluation outcome filtering",
        deviations="single-model mixed-success selection instead of three-anchor 653 subset; one paired evaluation generation per condition; HF backend instead of vLLM",
        upstream_config=official)
    if fixed:
        frozen.update(fixed_drafts=fixed, selection="Manually audited fixed drafts; no new draft sampling")
    if args.independent_solve:
        frozen.update(purpose="independent_solve_prompt_control", conditions=['R0','R2','R3','R4'],
            independent_suffix=INDEPENDENT_SUFFIX,
            independent_r0_template=independent_prompt('{problem}'),
            independent_r2_template=independent_prompt('{problem}', '{draft}'),
            deviations=frozen['deviations'] + '; new independent-solve prompt replaces upstream critique task; no R1')
    if args.drafts_only:
        frozen.update(purpose="thinking_draft_only_manual_review", start_index=args.start_index,
            selection="Collect all four samples per new problem; official mixed-success failures are candidates pending manual reasoning audit, not accepted pairs",
            deviations="single-model selection instead of three-anchor 653 subset; HF backend instead of vLLM; no paired evaluation in this run")
    elif args.start_index:
        parser.error("start-index is supported only with drafts-only")
    if args.output.exists():
        if not args.resume:
            raise RuntimeError("Output exists; explicit --resume required")
        existing = json.loads((args.output/'config.json').read_text())
        for key, value in frozen.items():
            if existing[key] != value:
                raise RuntimeError(f"Cannot resume with changed {key}")
    else:
        args.output.mkdir(parents=True)
        save(args.output/'config.json', {**frozen,
            'git_head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=repo, text=True).strip(),
            'git_status': subprocess.check_output(['git', 'status', '--short'], cwd=repo, text=True),
            'torch': torch.__version__, 'transformers': transformers.__version__})
    append(args.output/'launches.jsonl', {'target_pairs': args.count, 'candidate_cap': args.max_candidates, 'unix_time': time.time()})
    results_path = args.output/'results.jsonl'
    existing_results = rows_from(results_path)
    done = {(r['id'], r['init_response_generations_metadata']['intervention']['condition_id']): r for r in existing_results}
    draft_records = {r['draft_key']: r for r in rows_from(args.output/'draft_candidates.jsonl')}
    if fixed:
        draft_records = {r['draft_key']: r for r in rows_from(Path(fixed['source']))}
        save(args.output/'fixed_drafts.json', fixed)
    with args.input.open(encoding='utf-8-sig') as handle:
        raw_rows = list(csv.DictReader(handle))
    random.Random(2027).shuffle(raw_rows)
    tokenizer = AutoTokenizer.from_pretrained(args.model, local_files_only=True, use_fast=True)
    model = AutoModelForCausalLM.from_pretrained(args.model, local_files_only=True,
        torch_dtype=torch.bfloat16, attn_implementation='eager', device_map='cuda:0')
    backend = SelectiveHFBackend(model, tokenizer)
    began = time.monotonic()
    completed, seen = 0, set()

    def generate(row, encoded, request, label):
        budget = generation_budget(len(request.input_ids))
        started = time.monotonic()
        print(json.dumps({'event': 'generation_start', 'id': row['id'], 'label': label,
            'prompt_tokens': len(request.input_ids), 'max_new_tokens': budget}), flush=True)
        def progress(tokens):
            print(json.dumps({'event': 'progress', 'id': row['id'], 'label': label,
                'tokens': tokens, 'seconds': round(time.monotonic()-started, 1)}), flush=True)
        result = backend.generate(request, max_new_tokens=budget, temperature=.6, top_p=.95, top_k=20,
            progress_callback=progress)
        record = evaluate(row, encoded, request, result)
        metadata = record['init_response_generations_metadata']
        metadata['enable_thinking'] = True
        metadata['model_config_alias'] = 'Qwen3_8B_Thinking'
        final, thinking_status = extract_final_draft(result.text, encoded.text, tokenizer.eos_token)
        record.update(final_response=final, thinking_status=thinking_status,
            generation_seconds=time.monotonic()-started, max_new_tokens=budget)
        item = record['init_response_generations'][0]
        print(json.dumps({'event': 'generation_finish', 'id': row['id'], 'label': label,
            'correct': item['correctness'], 'finish': result.finish_reason,
            'thinking_status': thinking_status, 'tokens': len(result.generated_token_ids)}), flush=True)
        return record

    for index, raw in enumerate(raw_rows[:args.max_candidates]):
        numbers = [int(x) for x in raw['Puzzles'].split()]
        key = tuple(sorted(numbers))
        if key in seen:
            continue
        seen.add(key)
        if index < args.start_index:
            continue
        row = {'id': str(raw.get('Rank', index)), 'answer': numbers,
            'problem': f"Use the numbers {', '.join(map(str, numbers))} exactly once each, with addition, subtraction, multiplication, division and parentheses, to make 24. Provide an expression using the original four numbers."}
        if fixed and row['id'] not in fixed['selected']:
            continue
        direct = encode_direct_prompt(tokenizer, render_chat_prompt(tokenizer,
            independent_prompt(row['problem']) if args.independent_solve else
            render_official_prompt(repo, 'R0', row['problem']), enable_thinking=True))
        pool = []
        for j in range(4):
            draft_key = f"{row['id']}/{j}"
            if draft_key not in draft_records:
                if fixed:
                    raise RuntimeError(f"Missing fixed source record {draft_key}; no sampling fallback")
                request = make_request(direct, 'R0', AccessMode.FULL, 102027+4*index+j)
                record = generate(row, direct, request, f'draft{j}')
                record['draft_key'] = draft_key
                append(args.output/'draft_candidates.jsonl', record)
                draft_records[draft_key] = record
            pool.append(draft_records[draft_key])
        valid = [r for r in pool if r['init_response_generations'][0]['finish_reason'] == 'eos'
            and r['thinking_status'] == 'parsable_thinking' and r['final_response']]
        correct = [r for r in valid if r['init_response_generations'][0]['correctness'] is True]
        failed = [r for r in valid if r['init_response_generations'][0]['correctness'] is False]
        print(json.dumps({'event': 'pool_summary', 'candidate': index+1, 'id': row['id'],
            'correct': len(correct), 'failed': len(failed), 'selected': bool(correct and failed)}), flush=True)
        if args.drafts_only:
            review_path = args.output/'review_candidates'/f"{row['id']}.json"
            review_path.parent.mkdir(exist_ok=True)
            save(review_path, dict(id=row['id'], answer=numbers, pool_index=index,
                mixed_success=bool(correct and failed), manual_status="pending",
                correct_keys=[r['draft_key'] for r in correct],
                failed_candidates=[dict(draft_key=r['draft_key'], final_response=r['final_response']) for r in failed]))
            completed += 1
            continue
        if not correct or not failed:
            if fixed:
                raise RuntimeError(f"Fixed problem {row['id']} lacks eligible mixed-success samples")
            continue
        if fixed:
            failed = [r for r in failed if r['draft_key'] == fixed['selected'][row['id']]]
            if len(failed) != 1:
                raise RuntimeError("Fixed draft is not a unique eligible failure")
        row.update(traj1=failed[0]['final_response'], draft_key=failed[0]['draft_key'])
        r1 = encode_prompt(tokenizer, render_chat_prompt(tokenizer,
            render_official_prompt(repo, 'R1', row['problem'], row['traj1']), enable_thinking=True))
        r2 = encode_prompt(tokenizer, render_chat_prompt(tokenizer,
            independent_prompt(row['problem'], row['traj1']) if args.independent_solve else
            render_official_prompt(repo, 'R2', row['problem'], row['traj1']), enable_thinking=True))
        seed = args.evaluation_seed_base+index
        bundles = [('r0', direct, [make_request(direct, 'R0', AccessMode.FULL, seed)]),
            ('r1', r1, [make_request(r1, 'R1', AccessMode.FULL, seed)]),
            ('r2_r4', r2, make_r2_r4_requests(r2, seed))]
        if args.independent_solve:
            bundles = [b for b in bundles if b[0] != 'r1']
        if not (args.output/'intervention_sanity.json').exists():
            save(args.output/'intervention_sanity.json', sanity(model, bundles[-1][2][0]))
        pair_path = args.output/'pairs'/f"{row['id']}.json"
        pair_path.parent.mkdir(exist_ok=True)
        save(pair_path, row)
        for suffix, encoded, requests in bundles:
            bundle_path = args.output/'bundles'/f"{row['id']}.{suffix}.json"
            persist_request_bundle(bundle_path, encoded, requests)
            encoded, requests = load_request_bundle(bundle_path)
            for request in requests:
                if (row['id'], request.condition_id) in done:
                    continue
                record = generate(row, encoded, request, request.condition_id)
                append(results_path, record)
                done[(row['id'], request.condition_id)] = record
        assert done[(row['id'], 'R2')]['generated_token_ids'][0] == done[(row['id'], 'R3')]['generated_token_ids'][0]
        completed += 1
        report = summarize(results_path, conditions=['R0','R2','R3','R4'] if args.independent_solve else None)
        save(args.output/'paired_report.json', report)
        print(json.dumps({'event': 'pair_complete', 'pairs': completed, 'seconds': time.monotonic()-began}), flush=True)
        if completed >= args.count:
            print('THINKING_PILOT_TARGET_FINISHED', flush=True)
            return
    if args.drafts_only:
        save(args.output/'draft_only_summary.json', dict(completed_problems=completed,
            start_index=args.start_index, end_index=args.max_candidates,
            raw_records=len(draft_records), manual_review="pending", paired_evaluations=0))
        print('THINKING_DRAFT_ONLY_BATCH_FINISHED', flush=True)
        return
    raise RuntimeError(f"Only {completed} mixed-success pairs within {args.max_candidates} candidate cap; no automatic expansion")


if __name__ == '__main__':
    main()
