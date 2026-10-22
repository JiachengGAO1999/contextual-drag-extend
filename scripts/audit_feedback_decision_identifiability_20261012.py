"""Check whether the four-role preview identifies one-shot repair effects.

No model inference. Worlds/actions are bijections, the prior is uniform,
and the objective is exact correctness of one new complete assignment.
The spot checker independently selects an index before checking it.
"""

from fractions import Fraction
from itertools import permutations
import json
from pathlib import Path


def optimal_success(posterior, allowed_actions):
    if not allowed_actions:
        return Fraction(0)
    return max(posterior.get(action, Fraction(0)) for action in allowed_actions)


def audit():
    worlds = list(permutations(range(4)))
    records = []
    full_spot_events = 0
    full_spot_prefix_correct = 0
    for true_world in worlds:
        for old_action in worlds:
            failed = [i for i in range(4) if true_world[i] != old_action[i]]
            if not failed:
                continue
            for inspected_index in failed:
                full_spot_events += 1
                full_spot_prefix_correct += all(
                    true_world[j] == old_action[j]
                    for j in range(inspected_index)
                )
            # This report can be generated under either protocol. Do not
            # include independent-spot reports impossible under first-stop.
            index = failed[0]
            first_worlds = [
                w for w in worlds
                if all(w[j] == old_action[j] for j in range(index))
                and w[index] != old_action[index]
            ]
            spot_worlds = [w for w in worlds if w[index] != old_action[index]]
            # Under independent uniform index selection, each compatible
            # world gives this failure report likelihood 1/4. Thus the
            # conditional posterior is uniform, unlike choosing a failure
            # uniformly from each world's actually failing positions.
            prefix_actions = [
                a for a in worlds
                if all(a[j] == old_action[j] for j in range(index))
                and a[index] != old_action[index]
            ]
            result = {"world": true_world, "old_action": old_action,
                      "reported_index": index}
            for name, support in [("first_stop", first_worlds),
                                  ("independent_spot", spot_worlds)]:
                posterior = {w: Fraction(1, len(support)) for w in support}
                free = optimal_success(posterior, worlds)
                preserve = optimal_success(posterior, prefix_actions)
                result[name] = {
                    "posterior_support_size": len(support),
                    "unrestricted_optimal_success": str(free),
                    "prefix_preserving_optimal_success": str(preserve),
                    "prefix_constraint_regret": str(free - preserve),
                }
            result["spot_probability_prefix_is_all_correct"] = str(Fraction(
                sum(all(w[j] == old_action[j] for j in range(index))
                    for w in spot_worlds), len(spot_worlds)))
            records.append(result)

    classes = []
    for index in sorted({r["reported_index"] for r in records}):
        group = [r for r in records if r["reported_index"] == index]
        # All renamings in a class must share the same decision results.
        signatures = {
            json.dumps({k: r[k] for k in (
                "first_stop", "independent_spot",
                "spot_probability_prefix_is_all_correct")}, sort_keys=True)
            for r in group
        }
        if len(signatures) != 1:
            raise AssertionError("Unexpected structural classes")
        classes.append({"reported_index": index, "enumerated_records": len(group),
                        **json.loads(next(iter(signatures)))})
    nonzero_regret = sum(
        Fraction(r[p]["prefix_constraint_regret"]) != 0
        for r in records for p in ["first_stop", "independent_spot"]
    )
    if len(records) != 552 or nonzero_regret != 0:
        raise AssertionError("Decision-identifiability conclusion changed")
    if full_spot_events != 1728 or full_spot_prefix_correct != 552:
        raise AssertionError("Report-selection conclusion changed")
    return {
        "status": "cpu_oracle_only_no_model_calls",
        "assumptions": {
            "worlds": "uniform over 24 bijections",
            "objective": "one-shot exact full-assignment accuracy",
            "spot_rule": "independently uniformly select index before checking",
            "paired_reports": "first-failure index, also possible under spot rule",
            "comparison": "Bayes-optimal actions, unrestricted vs preserve old prefix",
        },
        "enumerated_records": len(records), "structural_classes": classes,
        "nonzero_prefix_constraint_regret_records_across_protocols": nonzero_regret,
        "sampling_warning": {
            "paired_first_failure_records_actual_prefix_correct_fraction": "1",
            "honest_independent_spot_failure_events": full_spot_events,
            "honest_independent_spot_actual_prefix_correct_fraction": str(
                Fraction(full_spot_prefix_correct, full_spot_events)),
            "meaning": (
                "Keeping first-failure records and merely relabeling the "
                "protocol creates a selected spot dataset. It cannot estimate "
                "honest independent-spot repair performance or calibration. "
                "Posterior calculations above refer to the stated generative "
                "protocol, not the selected empirical paired distribution."
            ),
        },
        "conclusion": (
            "Different posterior evidence does not yield a one-shot optimal "
            "accuracy crossover in this paired preview. Prefix certainty and "
            "decision loss must not be conflated. This does not describe LLM "
            "behavior or multi-step repair."
        ),
        "records": records,
    }


if __name__ == "__main__":
    result = audit()
    output = Path("outputs/generation-diagnostics-20261005/feedback_evidence_preview/")
    output.mkdir(parents=True, exist_ok=True)
    target = output / "decision_identifiability.json"
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                      encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "records"},
                     ensure_ascii=False, indent=2))
