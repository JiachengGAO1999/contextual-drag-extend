"""CPU-only descriptive audit of persisted trajectories. Never loads a model.

Writes only outputs/evidence-audit-phase1-20261013. Input JSONL line numbers are
physical, one based; character offsets are zero based Python Unicode offsets.
No confirmatory hypothesis tests or automatic research-direction selection.
"""
from __future__ import annotations

import hashlib
import json
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from run_identity_mvp_20261011 import audit_expression
from audit_identity_trajectories_20261011 import expression_spans
from run_information_followup_20261005 import same_tree
from selective_context.tasks import extract_math_box
from selective_context.schema import token_ids_sha256

OUT = ROOT / "outputs/evidence-audit-phase1-20261013"
BASE = "outputs/generation-diagnostics-20261005/"
OLD = {
    "selected_8b": ["outputs/game24-dual-anchor-validation-20260918/results.jsonl",
                    "runs/game24_batch02_validation_20260921_raw/results.jsonl",
                    "runs/game24_batch03_validation_20260925_raw/results.jsonl"],
    "selected_32b": ["runs/game24_qwen3_32b_r0_gate_15q_20260922_raw/results.jsonl",
                     "runs/game24_qwen3_32b_r2_r3_15q_20260923_raw/results.jsonl"],
    "selected_gemma": ["runs/game24_gemma4_e4b_r0_20260923_raw/results.jsonl",
                       "runs/game24_gemma4_e4b_r2_r3_20260923_raw/results.jsonl"],
    "math": ["runs/math_external_16q_20260920_raw/results.jsonl"],
    "correct_history": ["runs/game24_correct_draft_specificity_20260922_raw/results.jsonl"],
    "external_uft": ["outputs/game24-uft-external-20q-20260919/results.jsonl"],
}
NEW = ["cross_question_behavior", "identity_mvp", "identity_alias", "candidate_adoption",
       "identity_prospective", "feedback_decoding", "check_rule_transfer",
       "decision_verification", "constraint_coupling", "subject_gated_verification",
       "dependency_natural"]


def dump(name, data):
    (OUT / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf8")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def lines(path):
    for n, line in enumerate((ROOT / path).read_text(encoding="utf8").splitlines(), 1):
        if line.strip():
            yield n, json.loads(line), sha(line.encode("utf8"))


def legal_mentions(text, numbers, bindings=None):
    if not isinstance(numbers, list):
        return []
    thinking = text.split("</think>", 1)[0]
    found = []
    for a, b, expr in expression_spans(thinking):
        # Equality chains are candidates only after splitting explicit equations.
        # Existing extractor is deliberately conservative; non-detection is unknown.
        for piece in expr.split("="):
            piece = piece.strip()
            audited = audit_expression(piece, numbers, bindings, allow_literals=True)
            if audited.get("target_correct") and audited.get("inventory_correct"):
                found.append(dict(start=a, end=b, region_text=text[a:b], expression=piece,
                    audit=audited, context=text[max(0, a-160):b+180]))
    return found


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    assets, records, raw_by_uid = [], [], {}

    def register(path, role):
        p = ROOT / path
        assets.append(dict(path=path, role=role, exists=p.exists(),
            bytes=p.stat().st_size if p.exists() else None,
            sha256=sha(p.read_bytes()) if p.exists() else None))

    def add(row, raw, linehash):
        row["raw_line_sha256_utf8_without_newline"] = linehash
        row["uid"] = f"{row['source']}:{row['line']}"
        row["question_multiset"] = sorted(row["numbers"]) if isinstance(row["numbers"], list) else None
        row["repeated_input"] = len(set(row["numbers"])) < len(row["numbers"]) if isinstance(row["numbers"], list) else None
        row["thinking_closed"] = "</think>" in row["text"]
        row["observable_final"] = row["thinking_closed"] or row.get("thinking_status") == "no_thinking"
        row["exact_final"] = audit_expression(row.get("final") or "", row["numbers"], row.get("bindings"), allow_literals=True) if isinstance(row["numbers"], list) and row["observable_final"] else None
        row["legal_mentions"] = legal_mentions(row["text"], row["numbers"], row.get("bindings")) if row["task"] == "solve" else []
        if row.get("old"):
            row["final_old_ast_reuse"] = same_tree(row["old"], (row["exact_final"] or {}).get("numeric_expression")) if (row["exact_final"] or {}).get("parsed") else None
        raw_by_uid[row["uid"]] = raw
        records.append(row)

    for dataset, paths in OLD.items():
        for path in paths:
            register(path, "primary_raw")
            for line, r, lh in lines(path):
                g, = r["init_response_generations"]
                req = g["selective_context_metadata"].get("request") or r["init_response_generations_metadata"]["intervention"]
                prompt = r.get("init_response_prompt", "")
                draft = prompt.split("-- beginning of the draft --", 1)[-1].split("-- end of the draft --", 1)[0] if "-- beginning of the draft --" in prompt else ""
                if not draft and "-- beginning" in prompt:
                    draft = prompt  # Preserve raw prompt for nonstandard correct-history wrappers.
                add(dict(dataset=dataset, id=str(r["id"]), seed=req["sample_seed"],
                    condition=req["condition_id"], phase=r.get("stratum", "solve"), task="solve",
                    source=path, line=line, numbers=r["answer"], text=g["generated_response"],
                    prompt=prompt, draft=draft, old=extract_math_box(draft) or (draft.strip().splitlines()[-1].split("=", 1)[0].strip() if draft.strip() else None),
                    final=g.get("extracted_answer"), correct=g.get("correctness") is True,
                    thinking_status=r.get("thinking_status"),
                    score_status=g.get("correctness"), finish=g.get("finish_reason"),
                    tokens=len(r.get("generated_token_ids") or []), bindings=None,
                    prompt_hash=req.get("prompt_sha256"), input_hash=req.get("input_ids_sha256"),
                    actual_prompt_hash_valid=sha(prompt.encode("utf8")) == req.get("prompt_sha256"),
                    actual_input_hash_valid=token_ids_sha256(req["input_ids"]) == req.get("input_ids_sha256"),
                    draft_span=req.get("draft_token_span"), first_token=(r.get("generated_token_ids") or [None])[0]), r, lh)

    for dataset in NEW:
        path = BASE + dataset + "/generations.jsonl"
        bp, mp = BASE + dataset + "/behaviour.jsonl", BASE + dataset + "/manifest.json"
        for p, role in [(path, "primary_raw"), (bp, "saved_scoring"), (mp, "design_and_material")]:
            register(p, role)
        manifest = json.loads((ROOT / mp).read_text(encoding="utf8"))
        qs = {str(q["id"]): q for q in manifest["questions"]}
        def key(r):
            return str(r["id"]), r.get("seed"), r["condition"], r.get("phase"), r.get("history")
        scored = {key(r): (ln, r) for ln, r, _ in lines(bp)}
        for line, r, lh in lines(path):
            ln, b = scored[key(r)]
            q = qs.get(str(r["id"]), {})
            numbers = q.get("answer", [])
            task = "solve" if dataset in NEW[:6] and r.get("phase", "NATURAL") != "CANDIDATES" else "verification"
            bindings = q.get("bindings") if r["condition"].startswith(("IDENTITY", "VALUE")) else None
            prompt = r.get("prompt") or q.get("prompt") or q.get("contexts", {}).get(r["condition"], {}).get("text")
            add(dict(dataset=dataset, id=str(r["id"]), seed=r.get("seed"), condition=r["condition"],
                phase=r.get("phase", "NATURAL"), history=r.get("history"), task=task,
                source=path, line=line, scoring_source=bp, scoring_line=ln,
                numbers=numbers, text=r["text"], prompt=prompt,
                draft=q.get("draft", ""), old=q.get("old_expression"),
                final=b.get("extracted_answer"), correct=b.get("correct") is True,
                score_status=b.get("score_status", b.get("correct")), finish=r.get("finish_reason"),
                tokens=r.get("generated_tokens", len(r.get("token_ids", r.get("generated_token_ids", [])))), bindings=bindings,
                saved_reuse=b.get("structural_reuse"), saved_score=b), r, lh)

    register("outputs/validated-probe-20261013/development_joined.json", "previous_single_rater_labels")
    labels = json.loads((ROOT / assets[-1]["path"]).read_text(encoding="utf8"))
    for path, role in [
        ("outputs/game24-uft-external-20q-20260919-prepared/protocol.json", "historical_selection"),
        ("outputs/game24-uft-external-20q-20260919-prepared/pairs.jsonl", "historical_stimuli"),
        (BASE + "cross_question/diagnostics.jsonl", "auxiliary_short_scores"),
        (BASE + "source_partition/scores.jsonl", "auxiliary_short_scores"),
        (BASE + "source_partition/geometry.jsonl", "auxiliary_geometry"),
        ("outputs/late-invalidation-20261012/scores.jsonl", "auxiliary_unvalidated_short_readout"),
    ]:
        register(path, role)
    summary, groups = {}, defaultdict(list)
    for r in records:
        groups[(r["dataset"], r["phase"], r["condition"], r.get("history"))].append(r)
    for k, rs in groups.items():
        parsed = [r for r in rs if (r["exact_final"] or {}).get("parsed")]
        summary["|".join(str(x) for x in k)] = dict(n=len(rs), questions=len({r["id"] for r in rs}),
            correct=sum(r["correct"] for r in rs), finish=dict(Counter(r["finish"] for r in rs)),
            score_null=sum(r["score_status"] is None for r in rs),
            observable_final=sum(r["observable_final"] for r in rs),
            mean_tokens=statistics.mean(r["tokens"] for r in rs), median_tokens=statistics.median(r["tokens"] for r in rs),
            final_exact_parsed=len(parsed), exact_target_wrong=sum(not r["exact_final"]["target_correct"] for r in parsed),
            exact_inventory_wrong=sum(not r["exact_final"]["inventory_correct"] for r in parsed),
            exact_vs_saved_disagreements=[r["uid"] for r in parsed if bool(r["exact_final"]["target_correct"] and r["exact_final"]["inventory_correct"]) != r["correct"]],
            legal_mention_observed=sum(bool(r["legal_mentions"]) for r in rs),
            legal_mention_final_not_correct=[r["uid"] for r in rs if r["legal_mentions"] and not r["correct"]],
            strict_old_reuse=sum(r.get("final_old_ast_reuse") is True for r in rs))

    pair_specs = [(d, a, b) for d in OLD for a, b in [("R2", "R0"), ("R3", "R2"), ("R4", "R3")]]
    pair_specs += [("correct_history", "C_LATE", "C_FULL")]
    pair_specs += [("cross_question_behavior", a, b) for a, b in [("CANDIDATE", "FULL"), ("CONTROL", "FULL"), ("CANDIDATE", "CONTROL")]]
    pair_specs += [(d, pre+"_HISTORY", pre+"_CLEAN") for d, prefixes in [("identity_mvp", ["NUMERIC", "IDENTITY"]), ("identity_alias", ["VALUE"]), ("candidate_adoption", ["COUNT", "IDENTITY"]), ("identity_prospective", ["COUNT", "IDENTITY"])] for pre in prefixes]
    pairs = []
    for d, left, right in pair_specs:
        rs = [r for r in records if r["dataset"] == d]
        idx = {(r["id"], r["seed"], r["phase"], r.get("history"), r["condition"]): r for r in rs}
        joined = []
        for k, a in idx.items():
            if k[-1] != left:
                continue
            b = idx.get(k[:-1] + (right,))
            if b is None:
                continue
            joined.append(dict(id=a["id"], seed=a["seed"], phase=a["phase"], left=a["uid"], right=b["uid"],
                left_correct=a["correct"], right_correct=b["correct"], left_finish=a["finish"], right_finish=b["finish"],
                delta=int(a["correct"])-int(b["correct"]),
                same_prompt=a.get("prompt_hash") == b.get("prompt_hash") if a.get("prompt_hash") else None,
                same_inputs=a.get("input_hash") == b.get("input_hash") if a.get("input_hash") else None,
                same_span=a.get("draft_span") == b.get("draft_span") if a.get("draft_span") else None,
                same_first_token=a.get("first_token") == b.get("first_token") if a.get("first_token") is not None else None))
        for phase in sorted({p["phase"] for p in joined}):
            ps = [p for p in joined if p["phase"] == phase]
            gains = [p for p in ps if p["delta"] == 1]
            harms = [p for p in ps if p["delta"] == -1]
            if ps:
                pairs.append(dict(dataset=d, phase=phase, contrast=f"{left}-{right}", n=len(ps),
                    questions=len({p["id"] for p in ps}), left_correct=sum(p["left_correct"] for p in ps),
                    right_correct=sum(p["right_correct"] for p in ps), gains=len(gains), harms=len(harms),
                    changed_questions=sorted({p["id"] for p in gains+harms}), pairs=ps))

    # Preserve every record's location, outcome and exact-math witnesses, without
    # copying thousands of full traces. Full raw JSON is bundled for selected witnesses.
    index = [{k: v for k, v in r.items() if k not in ("text", "prompt", "draft", "saved_score")} for r in records]
    with (OUT / "trajectory_index.jsonl").open("w", encoding="utf8") as f:
        for r in index:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    witnesses = []
    wanted = set()
    for p in pairs:
        if (p["dataset"] in ("external_uft", "selected_8b", "math", "cross_question_behavior") and p["contrast"] in ("R4-R3", "CANDIDATE-CONTROL", "R3-R2")):
            for x in p["pairs"]:
                if x["delta"]:
                    wanted.update([x["left"], x["right"]])
    for lab in labels:
        if lab["early_adopt"] and lab["final_route_known"] and not lab["final_reuse"]:
            wanted.add(f"{lab['source_raw']}:{lab['source_raw_line']}")
    for r in records:
        if r["legal_mentions"] and not r["correct"] and r["finish"] == "eos" and r["dataset"] in ("cross_question_behavior", "candidate_adoption", "identity_mvp", "identity_alias"):
            wanted.add(r["uid"])
    for r in records:
        if r["uid"] in wanted:
            witnesses.append(dict(index={k: v for k, v in r.items() if k != "text"}, raw_record=raw_by_uid[r["uid"]]))
    with (OUT / "witnesses.jsonl").open("w", encoding="utf8") as f:
        for r in witnesses:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    dump("asset_manifest.json", dict(scope="CPU-only; no new model calls; raw files unchanged", assets=assets,
        raw_records=len(records), witness_records=len(witnesses),
        offsets="zero-based Python Unicode characters; source lines are one-based physical JSONL lines; line hashes exclude newline"))
    dump("condition_summary.json", summary)
    dump("paired_transitions.json", pairs)
    # These controls were already generated: for four distinct numbers, the alias
    # protocol copied the identity prompt verbatim. Compare exact token inputs and
    # outputs, instead of assuming a shared seed guarantees reproducibility.
    m1 = json.loads((ROOT / BASE / "identity_mvp/manifest.json").read_text(encoding="utf8"))
    m2 = json.loads((ROOT / BASE / "identity_alias/manifest.json").read_text(encoding="utf8"))
    q2 = {q["id"]: q for q in m2["questions"]}
    ix = {(r["dataset"], r["id"], r["condition"], r["seed"], r["phase"]): r for r in records}
    repeats = []
    for q in m1["questions"]:
        if len(set(q["answer"])) != 4:
            continue
        for typ in ("CLEAN", "HISTORY"):
            c1, c2 = "IDENTITY_" + typ, "VALUE_" + typ
            a = ix["identity_mvp", q["id"], c1, m1["seed"], "NATURAL"]
            b = ix["identity_alias", q["id"], c2, m1["seed"], "NATURAL"]
            ra, rb = raw_by_uid[a["uid"]], raw_by_uid[b["uid"]]
            repeats.append(dict(id=q["id"], history=typ, left=a["uid"], right=b["uid"],
                same_prompt_and_input_ids=q["contexts"][c1] == q2[q["id"]]["contexts"][c2],
                same_model=ra.get("model") == rb.get("model"), same_sampling=ra.get("sampling") == rb.get("sampling"),
                left_correct=a["correct"], right_correct=b["correct"],
                same_output_tokens=ra["token_ids"] == rb["token_ids"],
                left_finish=a["finish"], right_finish=b["finish"],
                left_tokens=a["tokens"], right_tokens=b["tokens"]))
    candidate_scores = [r["saved_score"] for r in records if r["dataset"] == "candidate_adoption" and r["phase"] == "CANDIDATES"]
    choices = {}
    for c in sorted({r["condition"] for r in candidate_scores}):
        zs = [r for r in candidate_scores if r["condition"] == c]
        choices[c] = dict(n=len(zs), correct=sum(r["correct"] for r in zs),
            old_selected=sum(r["old_selected"] for r in zs),
            correct_both_judgments_but_old_selected=sum(r["judgments_correct"] and r["old_selected"] for r in zs),
            selected_old_and_accepted_old=sum(r["old_selected"] and r["old_accepted"] for r in zs),
            position={str(pos): dict(n=sum(r["old_index"] == pos for r in zs),
                correct=sum(r["old_index"] == pos and r["correct"] for r in zs)) for pos in (1, 2)})
    old_profiles = {}
    for d in ("selected_8b", "external_uft"):
        qs = {r["id"]: r for r in records if r["dataset"] == d and r["condition"] == "R2"}
        old_profiles[d] = [dict(id=r["id"], source=r["uid"], draft_characters=len(r["draft"]),
            expression=r.get("old"), audit=audit_expression((r.get("old") or "").split("=", 1)[0], r["numbers"])) for r in qs.values()]
    dump("secondary_audits.json", dict(identical_prompt_repeats=repeats, candidate_choices=choices,
        old_expression_profiles=old_profiles,
        notes="Descriptive posthoc checks; seed and ordering are not independent factors. Non-detection of an expression is unknown."))
    # Explicit review set, including opposing outcomes and ordinary serialization
    # errors. Selection is posthoc and is never used as a prevalence denominator.
    specs = [
        ("P1", "cross_question_behavior", "285", "FULL", 20261009, "NATURAL"),
        ("P1", "cross_question_behavior", "285", "CANDIDATE", 20261009, "NATURAL"),
        ("P1", "cross_question_behavior", "285", "CONTROL", 20261009, "NATURAL"),
        ("P1", "cross_question_behavior", "1084", "FULL", 20261009, "NATURAL"),
        ("P1", "cross_question_behavior", "1084", "CANDIDATE", 20261009, "NATURAL"),
        ("P1", "cross_question_behavior", "1084", "CONTROL", 20261009, "NATURAL"),
        ("P1", "candidate_adoption", "1057", "COUNT_HISTORY", 20261015, "NATURAL"),
        ("P1", "candidate_adoption", "1057", "COUNT_HISTORY", 20261016, "NATURAL"),
        ("P1", "candidate_adoption", "44", "COUNT_HISTORY", 20261016, "NATURAL"),
        ("ordinary_mapping_error", "identity_mvp", "1261", "IDENTITY_CLEAN", 20261011, "NATURAL"),
    ]
    specs += [("P2", "selected_8b", "1057", c, seed, "solve") for seed in (927001, 927002) for c in ("R0", "R2", "R3", "R4")]
    specs += [("P2", "external_uft", qid, c, seed, "solve") for qid, seed in [("792", 929001), ("412", 929002), ("529", 929002)] for c in ("R0", "R2", "R3", "R4")]
    specs += [("P3", "candidate_adoption", "1057", c, seed, "CANDIDATES") for seed in (20261015, 20261016) for c in ("COUNT_CLEAN", "COUNT_HISTORY")]
    specs += [("P3", "candidate_adoption", qid, c, seed, "CANDIDATES") for qid in ("144", "44") for seed in (20261015, 20261016) for c in ("COUNT_CLEAN", "COUNT_HISTORY")]
    packets = []
    appendix = ["# Phase 1 review packets", "", "Posthoc witnesses and counterexamples; not an independent statistical sample.",
                "Each linked physical JSONL line has a UTF-8 SHA256 in review_packets.json. Full raw records are embedded there.",
                "Character offsets below are zero based in raw text. A detected expression is not a measurement of internal belief.", ""]
    for group, d, qid, c, seed, phase in specs:
        r = ix[d, qid, c, seed, phase]
        packet = dict(group=group, index={k: v for k, v in r.items() if k not in ("text", "prompt", "draft", "saved_score")},
            raw_record=raw_by_uid[r["uid"]], saved_score=r.get("saved_score"),
            review_scope="Local expression context, final answer, supplied prompt and paired terminal outcomes; not exhaustive semantic labeling")
        packets.append(packet)
        appendix += [f"## {group}: {d} / {qid} / {c} / {seed}", "",
            f"Raw: `{r['source']}`, physical line **{r['line']}**; phase `{phase}`.",
            f"Finish: `{r['finish']}`; archived correct: `{r['correct']}`; tokens: {r['tokens']}.",
            f"Final expression: `{r['final']}`.",
            f"Exact final: `{json.dumps(r['exact_final'], ensure_ascii=False)}`.", ""]
        if r["legal_mentions"]:
            z = r["legal_mentions"][0]
            appendix += [f"Legal expression witness at [{z['start']}, {z['end']}): `{z['expression']}`.", "", "```text", z["context"], "```", ""]
        if r.get("saved_score", {}).get("final_json"):
            appendix += ["Emitted final JSON:", "```json", json.dumps(r["saved_score"]["final_json"], ensure_ascii=False), "```", ""]
    dump("review_packets.json", packets)
    (OUT / "review_packets.md").write_text("\n".join(appendix), encoding="utf8")
    dump("early_stance_audit.json", dict(n=len(labels), known=sum(x["final_route_known"] for x in labels),
        cells={f"{c}:{stance}:{outcome}": sum(x["condition"] == c and x["early_adopt"] == stance and (x["final_reuse"] if x["final_route_known"] else None) == outcome for x in labels)
               for c in sorted({x["condition"] for x in labels}) for stance in (True, False) for outcome in (True, False, None)},
        provenance="Existing single-assistant labels; not newly blind or independently relabeled", labels=labels))
    print(json.dumps(dict(raw_records=len(records), witnesses=len(witnesses),
        transitions=[{k: v for k, v in p.items() if k != "pairs"} for p in pairs],
        conditions=summary), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
