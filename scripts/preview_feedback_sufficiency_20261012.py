"""CPU counterexamples for feedback compression; no model or execution manifest."""
from __future__ import annotations

import itertools
import json
from collections import Counter
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def first_failure(attempt, world):
    return next((i for i, (a, w) in enumerate(zip(attempt, world)) if a != w), None)


def preview():
    worlds = list(itertools.permutations(range(4)))
    counts, supports = Counter(), {}
    lossy = unsafe_events = random_events = 0
    unsafe_probability = Fraction()
    example = None
    # Every world/failed proposal pair gets equal prior weight; this is an
    # exhaustive finite calculation, not independent empirical observations.
    failed_pairs = len(worlds) * (len(worlds) - 1)
    for world in worlds:
        for attempt in worlds:
            k = first_failure(attempt, world)
            if k is None:
                continue
            full = [w for w in worlds if first_failure(attempt, w) == k]
            typed = [w for w in worlds if all(w[i] == attempt[i] for i in range(k))
                     and w[k] != attempt[k]]
            error_only = [w for w in worlds if w[k] != attempt[k]]
            assert full == typed and world in full
            counts[k] += 1
            lossy += full != error_only
            supports[k] = dict(full=len(full), typed=len(typed),
                               error_only=len(error_only), blacklist=23, clear=24)
            if k == 2 and example is None:
                example = dict(world=world, attempt=attempt, first_failed_index=k,
                               full_support=full, error_only_support=error_only)
            # If the checker samples one failed position uniformly instead,
            # the same reported failure cannot certify its preceding positions.
            failed = [i for i in range(4) if world[i] != attempt[i]]
            for reported in failed:
                random_events += 1
                if any(world[i] != attempt[i] for i in range(reported)):
                    unsafe_events += 1
                    unsafe_probability += Fraction(1, failed_pairs * len(failed))
    assert sum(counts.values()) == failed_pairs
    return dict(
        scope="CPU finite-environment feasibility preview, not model behavior, a GPU manifest, a working method, or a novelty finding.",
        assumptions="Four roles and four slots; a hidden bijection with uniform prior. A full proposed bijection is checked in role order and stops at the first mismatch. No changes to the world during checking.",
        first_error=dict(enumerated_world_proposal_pairs=failed_pairs,
                         pairs_by_zero_based_failure_position=dict(counts),
                         posterior_supports_by_position=supports,
                         error_only_lossy_pairs=lossy,
                         full_and_typed_support_equal_on_all_pairs=True),
        random_error=dict(enumerated_world_proposal_report_events=random_events,
                          unsafe_first_error_interpretation_events=unsafe_events,
                          unsafe_probability_under_uniform_pairs_and_uniform_failed_position=str(unsafe_probability),
                          note="Event counts are not uniformly weighted probabilities. With a random reporter, even the full-history posterior is generally nonuniform because report likelihood depends on the number of failed positions. No random-reporter sufficiency claim is made."),
        independent_spot_check=dict(
            mechanism="Choose one role uniformly before checking, independent of the world; test only that role. Here consider the observed failed checks.",
            failed_events=random_events, posterior_support_after_failed_check=18,
            full_and_error_only_support_equal=True,
            unsafe_first_error_interpretation_events=unsafe_events,
            unsafe_probability_conditional_on_failure=str(Fraction(unsafe_events, random_events)),
            note="Unlike the random-failed-position reporter, these failed events are equally weighted under uniform world, proposal, and independently chosen role. Earlier roles were not checked and cannot be certified."),
        example=example,
        limits="There are only three first-failure-position classes up to relabeling. The 552 enumerated pairs are not 552 independent research cases or an experimental sample. Valid-prefix reuse and lossy abstraction are known; this calculation only exposes a reporting-policy dependence that a proposed model experiment would have to respect. No GPU requests were created.")


if __name__ == "__main__":
    result = preview()
    output = ROOT / "outputs/generation-diagnostics-20261005/feedback_evidence_preview"
    output.mkdir(parents=True, exist_ok=True)
    (output / "sufficiency_preview.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf8")
    print(json.dumps({k: v for k, v in result.items() if k != "example"}, ensure_ascii=False))
