"""CPU-only audit of saved Gate 0 inputs and complete, unfiltered outputs."""
from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gate0_credit_assignment_20261013 import OUT, read, rows, save, analyse

m = read(OUT / "manifest.json")
a = analyse(OUT)
req = rows(OUT / "requests.jsonl")
gen = rows(OUT / "generations.jsonl")
probe = rows(OUT / "probe_scores.jsonl")
audit = read(OUT / "tokenizer_audit.json")
by_id = {q["id"]: q for q in m["tasks"]}
for item in audit["details"]:
    cells = item["cells"]
    for branch in ("A", "B"):
        assert len({tuple(c["input_ids"][slice(*c[branch+"_span"])]) for c in cells}) == 1
    selected = next(c for c in cells if c["source"] == "shared" and c["feedback"] == "local")
    executed = next(r for r in req if r["id"] == item["id"] and r["condition"] == "history")
    assert selected["input_ids"] == executed["input_ids"]
assert len({r["request_id"] for r in gen}) == len(gen) == 72
assert len({r["request_id"] for r in probe}) == len(probe) == 48
for p in probe:
    assert p["spans"]["B"][1]-p["spans"]["B"][0] == p["spans"]["N"][1]-p["spans"]["N"][0]
    assert len(p["candidates"][0]) == len(p["candidates"][1])
    assert p["prefill_repeat_max_abs_diff"] == 0
lengths = {}
for condition in ("clean", "history", "correct_history"):
    values = [len(r["input_ids"]) for r in req if r["condition"] == condition]
    lengths[condition] = dict(min=min(values), max=max(values), mean=sum(values)/len(values))
transitions = {}
for k in ("A", "B", "Y"):
    delta = [r[k] for r in a["paired_item_records"]]
    transitions[k] = dict(damaged=sum(x == 1 for x in delta), recovered=sum(x == -1 for x in delta), unchanged=sum(x == 0 for x in delta))
per_factor = {}
for factor in ("family", "difficulty", "error_position", "order"):
    per_factor[factor] = {}
    for value in sorted({q[factor] for q in m["tasks"]}):
        per_factor[factor][value] = {}
        for condition in ("clean", "history"):
            data = [r for r in gen if r["condition"] == condition and by_id[r["id"]][factor] == value]
            per_factor[factor][value][condition] = dict(n=len(data), joint=sum(r["score"]["joint"] for r in data),
                truncated=sum(r["score"]["truncated"] for r in data), invalid=sum(not r["score"]["format_valid"] for r in data))
signal = a["B_item_records"]
margin = {(p["id"], p["view"], p["mask"]): p["margin"] for p in probe}
views = sorted({(p["id"], p["view"]) for p in probe})
result = dict(input_matching_passed=True, exact_history_tokens_identical_across_six_cells=True,
    all_executed_history_inputs_match_frozen_local_shared_cell=True, duplicate_requests=0,
    input_token_lengths=lengths, generated_tokens=sum(len(r["generated_token_ids"]) for r in gen),
    transitions=transitions, by_factor=per_factor,
    B_positive_items=sum(r["corrected_B_signal"] > 0 for r in signal),
    B_positive_views=sum(v > 0 for r in signal for v in r["by_view"]),
    raw_probe_effect_mean_nats={c: sum(margin[q, v, "full"]-margin[q, v, c] for q, v in views)/len(views)
                               for c in ("late_B", "late_N")},
    max_prefill_repeat_diff=max(r["prefill_repeat_max_abs_diff"] for r in probe),
    B_block_tokens=sorted({p["spans"]["B"][1]-p["spans"]["B"][0] for p in probe}),
    error_delta_counts={str(d): sum(q["delta"] == d for q in m["tasks"]) for d in (-7, 7)},
    propagated_A_error={s: dict(min=min(abs(q["truth"]["A"]-q["old"]["A"]) for q in m["tasks"] if q["error_position"] == s),
        max=max(abs(q["truth"]["A"]-q["old"]["A"]) for q in m["tasks"] if q["error_position"] == s)) for s in ("early", "late")})
save(OUT / "final_audit.json", result)
print(json.dumps(result, indent=2))
