"""CPU-only audit of existing source subtraction and R2/R3 records.

No model imports, requests, forward passes, changes to historical results or masks.
"""
from __future__ import annotations

import hashlib
import json
import math
import statistics
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts")]
from run_identity_mvp_20261011 import audit_expression
from selective_context.diagnostic_data import paired_effect
from selective_context.schema import token_ids_sha256
from selective_context.tasks import extract_math_box

BASE = ROOT / "outputs/generation-diagnostics-20261005"
OUT = ROOT / "outputs/causal-specificity-audit-20261013"
CONDITIONS = ("FULL", "CANDIDATE", "CONTROL")


def load(path):
    return json.loads(path.read_text(encoding="utf8"))


def rows(path):
    return [(i, json.loads(s)) for i, s in enumerate(path.read_text(encoding="utf8").splitlines(), 1) if s.strip()]


def save(name, value):
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf8")


def sign_p(gains, harms):
    n = gains + harms
    return min(1., 2 * sum(math.comb(n, i) for i in range(min(gains, harms) + 1)) / 2**n) if n else 1.


def contrast(pairs, after, before):
    measurements = [dict(id=p["id"], condition=c, accuracy=int(p["results"][c]["correct"]))
                    for p in pairs for c in (before, after)]
    effect = paired_effect(measurements, before, after, field="accuracy")
    gains = [p["id"] for p in pairs if p["results"][after]["correct"] and not p["results"][before]["correct"]]
    harms = [p["id"] for p in pairs if not p["results"][after]["correct"] and p["results"][before]["correct"]]
    both = Counter((p["results"][after]["correct"], p["results"][before]["correct"]) for p in pairs)
    return dict(**effect, gains=gains, harms=harms, both_correct=both[True, True], both_wrong=both[False, False],
                exact_mcnemar_two_sided=sign_p(len(gains), len(harms)))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    assets = []

    def register(path):
        path = Path(path)
        rel = path.relative_to(ROOT).as_posix()
        if not any(x["path"] == rel for x in assets):
            assets.append(dict(path=rel, exists=path.exists(),
                sha256=hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None,
                bytes=path.stat().st_size if path.exists() else None))

    b = BASE / "cross_question_behavior"
    for path in [b / f for f in ("manifest.json", "generations.jsonl", "behaviour.jsonl", "summary.json")]:
        register(path)
    m = load(b / "manifest.json")
    original = load(BASE / "cross_question/manifest.json")
    sourceq = {q["id"]: q for q in original["questions"]}
    raw = {(r["id"], r["seed"], r["condition"]): (n, r) for n, r in rows(b / "generations.jsonl")}
    scored = {(r["id"], r["seed"], r["condition"]): (n, r) for n, r in rows(b / "behaviour.jsonl")}
    assert len(raw) == len(scored) == len(rows(b / "generations.jsonl")) == 72
    assert [q["id"] for q in m["questions"]] == [q["id"] for q in original["questions"]]
    assert len({tuple(sorted(q["answer"])) for q in m["questions"]}) == 24
    assert len(m["heads"]) == len(set(map(tuple, m["heads"]))) == 144
    pairs, score_audits, input_audits = [], [], []
    modes = dict(FULL="FULL", CANDIDATE="VALUE_ZERO", CONTROL="NON_DRAFT_MATCHED")
    source_cache = {}
    for q in m["questions"]:
        req = q["request"]
        assert q["prompt"] == sourceq[q["id"]]["prompt"] and req == sourceq[q["id"]]["request"]
        assert hashlib.sha256(q["prompt"].encode("utf8")).hexdigest() == req["prompt_sha256"]
        assert token_ids_sha256(req["input_ids"]) == req["input_ids_sha256"]
        src = ROOT / q["source"]
        register(src)
        resolved_line = q["source_line"]
        if not src.exists():
            if "batch04-dual-anchor" in q["source"]:
                candidates = sorted((ROOT / "runs/batch04_screen_8b_partial_20260925_1228/Qwen3_8B_Thinking").glob("chunk-*/draft_candidates.jsonl"))
            else:
                filename = src.parent.name.replace("game24-", "") + "-draft_candidates.jsonl"
                candidates = [ROOT / "outputs/baseline-corpus-audit-20260917/server_sources" / filename]
            matches = [(p, ln) for p in candidates if p.exists() for ln, r in rows(p)
                       if str(r["id"]) == q["id"] and r.get("draft_key") == q["source_draft_key"]
                       and r["init_response_generations"][0].get("extracted_answer") == q["old_expression"]]
            assert len(matches) == 1, (q["id"], matches)
            src, resolved_line = matches[0]
            register(src)
        if src not in source_cache:
            source_cache[src] = dict(rows(src))
        origin = source_cache[src][resolved_line]
        og = origin["init_response_generations"][0]
        assert str(origin["id"]) == q["id"] and origin["answer"] == q["answer"]
        assert og["finish_reason"] == "eos" and og["correctness"] is False
        assert og["extracted_answer"] == q["old_expression"] and q["old_expression"] in q["draft"]
        source_final = origin.get("final_response")
        if source_final is None:
            source_final = og["generated_response"].rsplit("</think>", 1)[-1].replace("<|im_end|>", "").strip()
        assert source_final == q["draft"]
        old_audit = audit_expression(q["old_expression"], q["answer"])
        assert old_audit["parsed"] and not old_audit["correct"]
        lo, hi = req["draft_token_span"]
        input_audits.append(dict(id=q["id"], prompt_tokens=len(req["input_ids"]), draft_tokens=hi-lo,
            pre_draft_tokens=lo, suffix_tokens=len(req["input_ids"])-hi, span=[lo, hi],
            prompt_hash_valid=True, input_hash_valid=True, source=q["source"], source_line=q["source_line"],
            resolved_source=src.relative_to(ROOT).as_posix(), resolved_line=resolved_line,
            original_expression_audit=old_audit,
            source_final_body_equal=True,
            supplied_final_response_equal=(origin.get("final_response") == q["draft"])))
        results = {}
        first = []
        for c in CONDITIONS:
            key = q["id"], m["seed"], c
            rn, r = raw[key]
            sn, s = scored[key]
            assert s["raw_line"] == rn and s["raw_source"] == (b / "generations.jsonl").relative_to(ROOT).as_posix()
            assert r["mode"] == modes[c] and r["strength"] == m["strength"] == 1
            assert r["heads"] == (None if c == "FULL" else m["heads"])
            assert r["query_window"] is None and r["draft_token_span"] == req["draft_token_span"]
            assert r["model"] == m["model"] and r["sampling"] == m["sampling"]
            assert r["max_new_tokens"] == q["max_new_tokens"] == 16384
            assert r["source"] == q["source"] and r["source_line"] == q["source_line"]
            assert s["generated_tokens"] == len(r["generated_token_ids"])
            first.append(r["generated_token_ids"][0])
            final_available = "</think>" in r["text"]
            expression = extract_math_box(r["text"].rsplit("</think>", 1)[-1]) if final_available else None
            assert expression == s["extracted_answer"]
            exact = audit_expression(expression or "", q["answer"])
            assert bool(exact["correct"]) == s["correct"]
            assert s["correct"] == (s["score_status"] is True)
            results[c] = dict(correct=s["correct"], expression=expression, finish=r["finish_reason"],
                tokens=len(r["generated_token_ids"]), old_reuse=s["structural_reuse"], raw_line=rn, scoring_line=sn)
            score_audits.append(dict(id=q["id"], condition=c, raw_line=rn, exact=exact,
                extraction_matches=True, correctness_matches=True, final_available=final_available))
        assert len(set(first)) == 1
        pairs.append(dict(id=q["id"], numbers=q["answer"], seed=m["seed"], results=results,
                          delta_candidate_control=int(results["CANDIDATE"]["correct"])-int(results["CONTROL"]["correct"])))
    summaries = {c: dict(n=24, correct=sum(p["results"][c]["correct"] for p in pairs),
        finishes=dict(Counter(p["results"][c]["finish"] for p in pairs)),
        mean_tokens=statistics.mean(p["results"][c]["tokens"] for p in pairs),
        old_reuse=sum(p["results"][c]["old_reuse"] for p in pairs)) for c in CONDITIONS}
    comparisons = {f"{a}-{b}": contrast(pairs, a, b) for a, b in
                   [("CANDIDATE", "CONTROL"), ("CANDIDATE", "FULL"), ("CONTROL", "FULL")]}
    historical = load(b / "summary.json")
    for c in CONDITIONS:
        assert summaries[c]["correct"] == historical["conditions"][c]["correct"]
    for before in ("CONTROL", "FULL"):
        assert comparisons[f"CANDIDATE-{before}"]["ci"] == historical["comparisons"][f"CANDIDATE_minus_{before}"]["accuracy"]["ci"]

    # Independently rejoin existing same-text mask runs; do not modify scores.
    mask_sources = dict(main23=["outputs/game24-dual-anchor-validation-20260918/results.jsonl",
        "runs/game24_batch02_validation_20260921_raw/results.jsonl", "runs/game24_batch03_validation_20260925_raw/results.jsonl"],
        external20=["outputs/game24-uft-external-20q-20260919/results.jsonl"])
    mask_audits = {}
    for pool, paths in mask_sources.items():
        idx = {}
        for path in paths:
            register(ROOT / path)
            for n, r in rows(ROOT / path):
                g, = r["init_response_generations"]
                req = g["selective_context_metadata"].get("request") or r["init_response_generations_metadata"]["intervention"]
                if req["condition_id"] not in ("R2", "R3"):
                    continue
                key = str(r["id"]), req["sample_seed"], req["condition_id"]
                assert key not in idx
                idx[key] = (path, n, r, g, req)
        ps = []
        for (qid, seed, c), (path, n, r, g, req) in idx.items():
            if c != "R2":
                continue
            path3, n3, r3, g3, req3 = idx[qid, seed, "R3"]
            assert r["init_response_prompt"] == r3["init_response_prompt"]
            assert req["input_ids"] == req3["input_ids"] and req["draft_token_span"] == req3["draft_token_span"]
            assert hashlib.sha256(r["init_response_prompt"].encode("utf8")).hexdigest() == req["prompt_sha256"] == req3["prompt_sha256"]
            assert token_ids_sha256(req["input_ids"]) == req["input_ids_sha256"] == req3["input_ids_sha256"]
            assert req["access_mode"] == "full" and req3["access_mode"] == "late_block"
            assert not req3.get("mask_token_spans")
            ps.append(dict(id=qid, seed=seed, r2_correct=g.get("correctness") is True,
                r3_correct=g3.get("correctness") is True, r2_line=n, r3_line=n3,
                r2_source=path, r3_source=path3, same_prompt_input_span=True))
        gains = sum(p["r3_correct"] and not p["r2_correct"] for p in ps)
        harms = sum(p["r2_correct"] and not p["r3_correct"] for p in ps)
        mask_audits[pool] = dict(questions=len({p["id"] for p in ps}), n=len(ps),
            r2_correct=sum(p["r2_correct"] for p in ps), r3_correct=sum(p["r3_correct"] for p in ps),
            gains=gains, harms=harms, pairs=ps)
    for path in ["docs/cross_question_behavior_20261009.md", "docs/cross_question_verification_20261007.md",
        "outputs/generation-diagnostics-20261005/cross_question/manifest.json",
        "scripts/run_cross_question_behavior_20261009.py", "scripts/run_cross_question_verification_20261007.py",
        "selective_context/diagnostics.py", "selective_context/masks.py", "selective_context/diagnostic_data.py",
        "selective_context/tasks.py", "scripts/run_identity_mvp_20261011.py"]:
        register(ROOT / path)
    save("paired_results.json", pairs)
    save("input_and_source_audit.json", input_audits)
    save("raw_output_rescore.json", score_audits)
    save("r2_r3_pair_audit.json", mask_audits)
    result = dict(scope="CPU-only existing files; no model requests or forwards", conditions=summaries,
        comparisons=comparisons, checks=dict(complete_triplets=24, unique_number_multisets=24,
            raw_and_score_records=72, raw_final_extraction_and_exact_score_match=72,
            identical_manifest_prompt_tokens_span_and_first_token=24,
            caveat="Shared actual input follows frozen manifest and runner code; per-generation raw rows do not duplicate input_ids. Historical runtime source hashes and activation telemetry are unavailable."),
        inference="5000 paired question bootstrap, frozen seed 20261005; exact conditional McNemar is descriptive. No seed robustness or population-representative sampling implied.")
    save("summary.json", result)
    save("asset_manifest.json", assets)
    lines = ["| ID | Numbers | FULL | CANDIDATE | CONTROL | C−CONTROL | Raw lines F/C/K |",
             "|---|---|---:|---:|---:|---:|---|"]
    for p in pairs:
        rs = p["results"]
        values = [str(int(rs[c]["correct"])) + (" (length)" if rs[c]["finish"] == "length" else "") for c in CONDITIONS]
        lines.append(f"| {p['id']} | {','.join(map(str,p['numbers']))} | {' | '.join(values)} | {p['delta_candidate_control']:+d} | "
                     + "/".join(str(rs[c]["raw_line"]) for c in CONDITIONS) + " |")
    (OUT / "paired_results.md").write_text("\n".join(lines)+"\n", encoding="utf8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print(json.dumps({k: {a:b for a,b in v.items() if a != "pairs"} for k,v in mask_audits.items()}, indent=2))


if __name__ == "__main__":
    main()
