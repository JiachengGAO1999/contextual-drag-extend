"""Persist this audit's single-assistant semantic decisions and verbatim anchors.

These are manually reviewed annotations, not an automatic semantic classifier.
The preparation/validation script checks every quote against the selected raw text.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/p1-review-phase2a-20261013"

# dataset, physical source line -> reviewed quote, interpretation, optional preference
MANUAL = {
    ("cross_question_behavior", 1): ("The draft's expression uses all four numbers once.", "输入已含合法求和式并暗示多运算更符合题意；输出重复该暗示。", "Let me go with the more complex one that uses multiple operations, as that might be what the problem expects."),
    ("cross_question_behavior", 14): ("Therefore, the draft's answer is wrong because it uses three 12s.", "明确正确否定旧式；思考段末选择合法式；最终重写旧式并错误验证。", None),
    ("cross_question_behavior", 19): ("The numbers used are 9, 6, 7, and 6.", "把6/6清点成一个6；未确认准确旧式非法判定。", None),
    ("cross_question_behavior", 32): ("So total numbers used: 12, 12, 9, 9.", "清点时遗漏12-9中的9；合法求和式也被认可。", None),
    ("cross_question_behavior", 50): ("They used 9, 5, 7, and another 7.", "把7/7清点成一个7；合法备选被认可。", None),
    ("cross_question_behavior", 55): ("In the draft's solution, numbers used are 12, 11, 6, 6. Each exactly once. Correct.", "把6*6两个操作数清点成一个6；一度选合法式，末尾又认可旧式。", None),
    ("candidate_adoption", 3): ("Numbers used: 6, 12, 9 (from 12-9), and 9 (from 9/9). So two 9s, which is allowed. So correct.", "把9/9清点成一个9；两式共同认可。", "Let me choose the first one, as it's the one in the draft."),
    ("candidate_adoption", 8): ("two 6s (in 6+6 and in the denominator 6-1)", "把6+6清点成一个6；合法式也被认可。", None),
    ("candidate_adoption", 16): ("in the draft's answer, the 10 is used twice, which is allowed since there are two 10s.", "旧式实际三个10；曾否定其他候选，不能算否定旧式。", None),
    ("candidate_adoption", 24): ("So numbers used: 6, 9, 5, 9. Yes, exactly once each.", "实际三个9；把合法替代式误称与非法旧式等价。", None),
    ("candidate_adoption", 97): ("3 once, 4 twice, 5 once.", "实际三个4；共同认可两式，选择草稿式。", None),
    ("candidate_adoption", 114): ("the numbers used are: 8 once, 9 once, 12 once in the denominator, and 12 once in the subtraction.", "遗漏12-8中的8；曾表示选合法简单式，末尾恢复旧式合法判定。", None),
    ("candidate_adoption", 126): ("Let's count the numbers: 11 appears twice, 4 once, 2 once. Correct.", "实际三个11；复杂度与沿用草稿理由可见，但非因果证明。", "Let's go with the first one that the draft had, since it's more complex and uses division and multiplication."),
    ("candidate_adoption", 161): ("So that's two 12s and two 10s. Each number is used once.", "合法式已在输入；实际三个12；选择更多运算。", "Let me choose the one that uses all operations, like the second option."),
    ("candidate_adoption", 163): ("A is used once, D is used twice (in D/D), B and C once each.", "准确局部重复诊断并说不能这样，随后用两张12牌为额外D辩护。", None),
    ("candidate_adoption", 184): ("In the expression 8*(4 + 1) - 4*4, the numbers used are 8, 4, 1, and another 4.", "正确指出另一候选8*(4-1)*(4/4)超用4，随后错误认可旧式；对象不同。", None),
    ("candidate_adoption", 189): ("4 (from the first 4 in 4+1), 1 (from the 4+1), and then another 4 (from the 4×4).", "遗漏4*4中的一个4；一度选择合法式后改回旧式，同时仍称旧式正确。", None),
    ("candidate_adoption", 190): ("Wait, but that uses C twice.", "准确注意旧式重复C，立刻改口；后来的明确invalid针对C*C+A*B。", None),
    ("candidate_adoption", 222): ("So the expression uses each card once.", "C实际两次、数字式11实际两次；未确认准确旧式非法判定。", None),
    ("candidate_adoption", 224): ("So that uses 10, 2, 4, 10. All numbers exactly once.", "把10/10清点成一个10；两式共同认可。", None),
}
EXTRA = {
    12: ("The original draft used three 6s instead of two.", "accurate_old_rejection_followed_by_legal_final"),
    162: ("So this expression is invalid because it uses three 12s.", "accurate_old_rejection_followed_by_legal_final"),
    78: ("But that uses 1 twice. Not allowed. So that's not possible.", "accurate_rejection_of_other_construction_not_old"),
    62: ("So the draft's solution is incorrect because it uses the number 5 twice.", "early_old_acceptance_then_accurate_rejection_and_legal_final"),
    87: ("The draft's answer uses four 6s, but the problem only allows three 6s and one 9.", "early_old_acceptance_then_accurate_rejection_and_legal_final"),
    108: ("So the draft's expression is wrong because it uses the 8 twice.", "early_old_acceptance_then_accurate_rejection_and_legal_final"),
}


def main():
    rows = json.loads((OUT / "selected_raw.json").read_text(encoding="utf8"))
    labels = json.loads((ROOT / "outputs/evidence-audit-phase1-20261013/early_stance_audit.json").read_text(encoding="utf8"))["labels"]
    labs = {(x["source_raw"], x["source_raw_line"]): x for x in labels}
    anns = []
    for r in rows:
        i, t = r["index"], r["raw"]["text"]
        cut, key = t.find("</think>"), (i["dataset"], i["line"])
        events = []
        ann = dict(uid=i["uid"], role=r["role"], legal_expression_explicitly_endorsed=True if r["role"] == "primary_support" else "not_exhaustively_labeled",
            old_rejection="none_confirmed_in_reviewed_judgment_passages", simultaneous_or_unretracted_coapproval="not_classified",
            final_exact_audit=i["exact_final"], provided_legal_detected=r["provided_legal_detected"],
            review_scope="All extracted count/rejection candidates, legal-expression contexts, terminal Thinking and final answer reviewed. Full raw text supplied; unobserved wording is not a population negative.", evidence=events)
        if r["role"] == "primary_support":
            quote, note, preference = MANUAL[key]
            assert quote in t, (key, quote)
            ann.update(notes=note, simultaneous_or_unretracted_coapproval="observed_at_some_point" if i["id"] != "651" else "not_for_old_and_legal_after_accurate_rejection", final_false_inventory_assertion=True)
            z = i["legal_mentions"][0]
            a, b = max(0, z["start"]-130), min(cut, z["end"]+720)
            events.append(dict(type="endorsed_legal_expression_context", quote=t[a:b], search_from=a))
            events.append(dict(type="old_count_or_legality_judgment", quote=quote))
            if preference:
                assert preference in t, (key, preference)
                events.append(dict(type="emitted_preference_not_causal_evidence", quote=preference))
            matches = list(re.finditer(r"[^\n]*(?:exactly once|used once|used twice)[^\n]*", t[cut:]))
            if matches:
                match = matches[-1]
                a, b = cut+max(0, match.start()-120), min(len(t), cut+match.end()+100)
                events.append(dict(type="final_revalidation_context", quote=t[a:b], search_from=a))
            if key == ("cross_question_behavior", 14):
                ann["old_rejection"] = "accurate_specific_old_illegality_repeated_and_not_retracted_before_think_end"
                events += [dict(type="accurate_old_count_diagnosis", quote="The draft's answer was incorrect because it used three 12s."),
                    dict(type="legal_final_intention_at_think_end", quote="So the boxed answer should be \\boxed{(12 \\times 3) - (12 \\times 1)}."),
                    dict(type="incorrect_final_inventory_validation", quote="All four numbers are used exactly once, and the operations used are valid.", search_from=cut)]
            if key == ("candidate_adoption", 163):
                ann["old_rejection"] = "accurate_local_old_symbol_violation_then_retracted"
                events += [dict(type="accurate_local_violation", quote="Wait, but D is used twice. That's not possible."),
                    dict(type="incorrect_reacceptance", quote="So the expression A × (D / D + B / C) uses all four numbers exactly once.")]
            if key == ("candidate_adoption", 190):
                ann["old_rejection"] = "true_old_duplicate_notice_immediately_retracted_no_committed_old_invalid_verdict"
                events.append(dict(type="other_candidate_rejection_not_old", quote="Wait, if I have C × C + A × B, that would use C twice (the same card), which is not allowed."))
        else:
            ann["notes"] = "Counterexample/control; exact terminal outcome checked, not a separate independent replication."
            if i["dataset"] == "candidate_adoption" and i["line"] in EXTRA:
                q, status = EXTRA[i["line"]]
                assert q in t, (key, q)
                events.append(dict(type=status, quote=q))
                ann["old_rejection"] = status
            lab = labs.get((i["source"], i["line"]))
            if lab and lab["early_adopt"]:
                events.append(dict(type="previous_early_endorsement_anchor_rechecked", quote=lab["anchor"]))
            if r["role"] == "history_counterexample" and i["line"] not in EXTRA:
                ann["notes"] += " 早期认可后最终选合法式；未确认后来准确判旧式非法。"
            if r["role"] == "paired_terminal_control" and i["id"] == "651":
                if i["condition"] == "CANDIDATE":
                    events.append(dict(type="accurate_old_rejection_success_counter", quote="Therefore, the draft's solution is wrong."))
                    ann["old_rejection"] = "accurate_old_rejection_and_legal_final"
                else:
                    events.append(dict(type="wrong_old_inventory_verification", quote="in the first expression, the (12 - 12) uses the second 12."))
                    ann["old_rejection"] = "none_confirmed_wrong_old_verification_observed"
            events.append(dict(type="terminal_thinking_and_final_transition", quote=t[max(0, cut-500):min(len(t), cut+250)], search_from=max(0, cut-500)))
        anns.append(ann)
    (OUT / "annotations.json").write_text(json.dumps(anns, ensure_ascii=False, indent=2)+"\n", encoding="utf8")
    print("Saved", len(anns), "manually reviewed annotations")


if __name__ == "__main__":
    main()
