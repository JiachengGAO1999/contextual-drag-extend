"""CPU-only controlled materials and question-level analysis. No model sampling."""
from __future__ import annotations

import ast
import itertools
import random
import statistics
from collections import Counter
from fractions import Fraction

SEED = 20261010
CONDITIONS = ("FULL", "LATE_BLOCK", "REBUILD_BLOCKED")
CRITIQUE = ("The draft violates the rule that each supplied number must appear exactly once. "
            "I must not use that expression as the solution. I will seek a valid construction.\n")
STEMS = {
    "judgment": "My judgment of the draft's number use is:\n",
    "adoption": "I will use the following expression as my solution:\n",
}


def inspect_expression(expression):
    leaves = []

    def walk(node):
        if isinstance(node, ast.Constant) and type(node.value) is int and node.value > 0:
            leaves.append(node.value)
            return Fraction(node.value)
        if not isinstance(node, ast.BinOp):
            raise ValueError("Only positive integer leaves and four binary operations are allowed")
        a, b = walk(node.left), walk(node.right)
        if isinstance(node.op, ast.Add): return a + b
        if isinstance(node.op, ast.Sub): return a - b
        if isinstance(node.op, ast.Mult): return a * b
        if isinstance(node.op, ast.Div): return a / b
        raise ValueError("Unsupported operation")

    value = walk(ast.parse(expression, mode="eval").body)
    return dict(value=str(value), leaves=leaves, inventory=sorted(leaves))


def solve(numbers):
    """Deterministic first exact solution; failed value states are memoized."""
    failed = set()

    def search(items):
        if len(items) == 1:
            return items[0][1] if items[0][0] == 24 else None
        key = tuple(sorted(value for value, _ in items))
        if key in failed: return None
        for i, j in itertools.combinations(range(len(items)), 2):
            a, ea = items[i]; b, eb = items[j]
            rest = [item for k, item in enumerate(items) if k not in (i, j)]
            choices = [(a+b, f"({ea}+{eb})"), (a*b, f"({ea}*{eb})"),
                       (a-b, f"({ea}-{eb})"), (b-a, f"({eb}-{ea})")]
            if b: choices.append((a/b, f"({ea}/{eb})"))
            if a: choices.append((b/a, f"({eb}/{ea})"))
            visited = set()
            for value, expression in choices:
                if value in visited: continue
                visited.add(value)
                found = search(rest + [(value, expression)])
                if found is not None: return found
        failed.add(key)
        return None

    return search([(Fraction(x), str(x)) for x in numbers])


def wrong_routes(numbers):
    """Replace exactly one supplied occurrence with another supplied value."""
    inventories, routes = set(), []
    for omitted, duplicated in itertools.product(sorted(set(numbers)), repeat=2):
        if omitted == duplicated: continue
        inventory = list(numbers)
        inventory.remove(omitted); inventory.append(duplicated); inventory.sort()
        key = tuple(inventory)
        if key in inventories: continue
        inventories.add(key)
        expression = solve(inventory)
        if expression is not None:
            routes.append(dict(expression=expression, omitted=omitted, duplicated=duplicated,
                               **inspect_expression(expression)))
    return routes


def content(numbers, expression):
    from .prompting import DRAFT_BEGIN, DRAFT_END
    return (f"Use the numbers {', '.join(map(str, numbers))} exactly once each, with addition, "
            "subtraction, multiplication, division and parentheses, to make 24.\n\n"
            "A previous attempt was:\n" + DRAFT_BEGIN + expression +
            " = 24. This uses the supplied numbers exactly once." + DRAFT_END +
            "\n\nFeedback: The draft is invalid because it violates the number-use constraint. "
            "Produce a valid solution using each supplied number exactly once.\n")


def build_materials(tokenizer, exclusions, count=32):
    from .prompting import encode_prompt, render_chat_prompt
    pool = list(itertools.combinations_with_replacement(range(1, 14), 4))
    random.Random(SEED).shuffle(pool)
    excluded = {tuple(x) for x in exclusions}
    questions, skips = [], []
    for numbers in pool:
        if numbers in excluded: continue
        legal = solve(numbers)
        if legal is None:
            skips.append(dict(numbers=numbers, reason="no_exact_solution")); continue
        routes = wrong_routes(numbers)
        encoded_routes = []
        for route in routes:
            text = render_chat_prompt(tokenizer, content(numbers, route["expression"]), enable_thinking=True)
            encoded_routes.append((route, encode_prompt(tokenizer, text)))
        pair = None
        for (a, ea), (b, eb) in itertools.combinations(encoded_routes, 2):
            if (len(ea.input_ids) == len(eb.input_ids) and ea.draft_token_span == eb.draft_token_span
                    and ea.input_ids[:ea.draft_token_span[0]] == eb.input_ids[:eb.draft_token_span[0]]
                    and ea.input_ids[ea.draft_token_span[1]:] == eb.input_ids[eb.draft_token_span[1]:]):
                pair = [(a, ea), (b, eb)]; break
        if pair is None:
            skips.append(dict(numbers=numbers, reason="no_equal_position_wrong_route_pair")); continue
        q = dict(id="rr-" + "-".join(map(str, numbers)), numbers=list(numbers), legal=legal,
                 legal_measurement=inspect_expression(legal), histories={}, readouts={})
        for name, (route, encoded) in zip(("A", "B"), pair):
            critique_ids = tokenizer.encode(CRITIQUE, add_special_tokens=False)
            ids = encoded.input_ids + critique_ids
            if len(ids) > 2048: raise ValueError("Controlled prefix exceeds frozen limit")
            q["histories"][name] = dict(route=route, prompt=encoded.text, critique=CRITIQUE,
                input_ids=ids, prompt_length=len(encoded.input_ids), draft_token_span=list(encoded.draft_token_span),
                cutoff=len(ids)-1, boundary_spillover=encoded.boundary_spillover)
        for outcome, stem in STEMS.items():
            candidates = (dict(reject="Invalid: the supplied number inventory is not used exactly once.\n",
                               endorse="Valid: the supplied number inventory is used exactly once.\n")
                          if outcome == "judgment" else
                          {name: q["histories"][name]["route"]["expression"] + " = 24.\n" for name in ("A", "B")})
            if outcome == "adoption": candidates["legal"] = legal + " = 24.\n"
            q["readouts"][outcome] = dict(stem=stem, stem_ids=tokenizer.encode(stem, add_special_tokens=False),
                candidates={name: dict(text=text, ids=tokenizer.encode(text, add_special_tokens=False))
                            for name, text in candidates.items()})
        questions.append(q)
        if len(questions) == count: break
    return questions, skips


def interval(values, draws=5000):
    if not values: return dict(n=0, mean=None, ci=None, positive=0, negative=0)
    rng = random.Random(SEED)
    sampled = sorted(statistics.mean(rng.choices(values, k=len(values))) for _ in range(draws))
    return dict(n=len(values), mean=statistics.mean(values),
                ci=[sampled[int(.025*draws)], sampled[min(draws-1, int(.975*draws))]],
                positive=sum(x > 0 for x in values), negative=sum(x < 0 for x in values))


def audit_materials(tokenizer, questions, exclusions):
    excluded = {tuple(x) for x in exclusions}
    reviewed = []
    for q in questions:
        assert tuple(q["numbers"]) not in excluded
        legal = inspect_expression(q["legal"])
        assert legal["value"] == "24" and legal["inventory"] == q["numbers"]
        a, b = [q["histories"][h] for h in ("A", "B")]
        lo, hi = a["draft_token_span"]
        assert a["draft_token_span"] == b["draft_token_span"]
        assert a["input_ids"][:lo] == b["input_ids"][:lo] and a["input_ids"][hi:] == b["input_ids"][hi:]
        for hist in (a, b):
            route = inspect_expression(hist["route"]["expression"])
            assert route["value"] == "24" and len(route["leaves"]) == 4 and route["inventory"] != q["numbers"]
            assert hist["cutoff"] == len(hist["input_ids"])-1 and hi < hist["cutoff"]
            assert tokenizer.encode(hist["prompt"]+hist["critique"], add_special_tokens=False) == hist["input_ids"]
            for readout in q["readouts"].values():
                for candidate in readout["candidates"].values():
                    whole = hist["prompt"]+hist["critique"]+readout["stem"]+candidate["text"]
                    assert tokenizer.encode(whole, add_special_tokens=False) == (
                        hist["input_ids"]+readout["stem_ids"]+candidate["ids"])
        reviewed.append(dict(id=q["id"], exact_arithmetic=True, wrong_routes_have_four_leaves=True,
                             equal_AB_positions=True, segmented_tokenization_matches_whole_text=True))
    return dict(status="passed_cpu_material_audit", questions=len(reviewed), checks=reviewed, gpu_model_calls=0,
        review="Exact arithmetic and token boundaries verified; forced critique is not observed self-recognition.")


def analyse(questions, rows):
    indexed = {(r["id"], r["history"], r["condition"], r["outcome"]): r for r in rows}
    per_question, missing = [], []
    for q in questions:
        keys = list(itertools.product(("A", "B"), CONDITIONS, STEMS))
        absent = [k for k in keys if (q["id"], *k) not in indexed]
        if absent:
            missing.append(dict(id=q["id"], missing=absent)); continue
        result = dict(id=q["id"])
        for normalized in (False, True):
            suffix = "_per_token" if normalized else ""
            field = "mean_log_probability" if normalized else "log_probability"
            def lp(h, c, o, candidate):
                return indexed[q["id"], h, c, o]["scores"][candidate][field]
            for c in CONDITIONS:
                result[c+"_adoption"+suffix] = statistics.mean(
                    lp(h, c, "adoption", "legal") - lp(h, c, "adoption", h) for h in ("A", "B"))
                result[c+"_judgment"+suffix] = statistics.mean(
                    lp(h, c, "judgment", "reject") - lp(h, c, "judgment", "endorse") for h in ("A", "B"))
                result[c+"_identity"+suffix] = .5 * (
                    lp("A", c, "adoption", "A") - lp("A", c, "adoption", "B")
                    - lp("B", c, "adoption", "A") + lp("B", c, "adoption", "B"))
            for outcome in ("adoption", "judgment", "identity"):
                result["rebuild_minus_late_"+outcome+suffix] = (
                    result["REBUILD_BLOCKED_"+outcome+suffix] - result["LATE_BLOCK_"+outcome+suffix])
            result["late_minus_full_adoption"+suffix] = result["LATE_BLOCK_adoption"+suffix] - result["FULL_adoption"+suffix]
        per_question.append(result)
    fields = [k for k in per_question[0] if k != "id"] if per_question else []
    return dict(status="completed" if not missing else "incomplete", completed_questions=len(per_question),
        planned_questions=len(questions), completed_score_units=len(indexed), planned_score_units=len(questions)*12,
        per_question=per_question, missing=missing,
        effects={k: interval([q[k] for q in per_question]) for k in fields},
        interpretation=["A question, not a history or token, is the statistical unit.",
            "Positive primary rebuild-minus-late adoption means increased legal-versus-old continuation preference.",
            "REBUILD identity zero is guaranteed by matched text outside blocked D; it is an acceptance property, not a discovery.",
            "Judgment measures post-feedback verdict maintenance, not naturally occurring error recognition.",
            "Candidate scores are not free-generation accuracy or evidence of functional equivalence."])
