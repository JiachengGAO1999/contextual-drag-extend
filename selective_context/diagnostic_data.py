"""Outcome-independent question split and reuse of completed continuations."""
from __future__ import annotations

import json
import random
import statistics
import ast
import re
from collections import Counter
from fractions import Fraction
from pathlib import Path

SOURCES = (
    "outputs/game24-dual-anchor-validation-20260918/results.jsonl",
    "runs/game24_batch02_validation_20260921_raw/results.jsonl",
    "runs/game24_batch03_validation_20260925_raw/results.jsonl",
)


def expression_measurement(expression, numbers):
    """Same narrow exact-arithmetic audit as the completed Game24 audit.

    Kept self-contained because the server's historical audit script is older.
    It is not a replacement for the official behavioural scorer.
    """
    def group(text, start):
        while start < len(text) and text[start].isspace():
            start += 1
        if start >= len(text) or text[start] != "{":
            raise ValueError("Expected LaTeX group")
        depth, end = 1, start+1
        while end < len(text) and depth:
            depth += (text[end] == "{") - (text[end] == "}")
            end += 1
        if depth:
            raise ValueError("Unclosed LaTeX group")
        return text[start+1:end-1], end
    try:
        text = expression.split("=",1)[0]
        for pattern, fraction in ((r"\\boxed\s*",False),(r"\\(?:d?frac)\s*",True)):
            while True:
                match = re.search(pattern,text)
                if not match:
                    break
                first,end = group(text,match.end())
                if fraction:
                    second,end = group(text,end)
                    replacement = f"(({first})/({second}))"
                else:
                    replacement = f"({first})"
                text = text[:match.start()]+replacement+text[end:]
        for old,new in (("\\left",""),("\\right",""),("\\times","*"),("\\cdot","*"),
                        ("\\div","/"),("×","*"),("÷","/"),("{","("),("}",")")):
            text = text.replace(old,new)
        operands = Counter()
        def visit(node):
            if isinstance(node,ast.Constant) and isinstance(node.value,int) and not isinstance(node.value,bool):
                operands[node.value] += 1
                return Fraction(node.value)
            if isinstance(node,ast.UnaryOp) and isinstance(node.op,(ast.UAdd,ast.USub)):
                value = visit(node.operand)
                return value if isinstance(node.op,ast.UAdd) else -value
            if isinstance(node,ast.BinOp) and isinstance(node.op,(ast.Add,ast.Sub,ast.Mult,ast.Div)):
                left,right = visit(node.left),visit(node.right)
                if isinstance(node.op,ast.Add): return left+right
                if isinstance(node.op,ast.Sub): return left-right
                if isinstance(node.op,ast.Mult): return left*right
                return left/right
            raise ValueError("Unsupported arithmetic")
        value = visit(ast.parse(text.strip(),mode="eval").body)
        return dict(evaluation_status="ok",exact_game24=value==24 and operands==Counter(numbers))
    except (SyntaxError,ValueError,ZeroDivisionError):
        return dict(evaluation_status="unparsed",exact_game24=False)


def read_jsonl(path):
    if not Path(path).exists():
        return []
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def request_of(row):
    return (row["init_response_generations"][0].get("selective_context_metadata", {}).get("request")
            or row["init_response_generations_metadata"]["intervention"])


def first_difference(preferred, alternative, limit=128):
    # Only the shared-prefix first difference is a valid same-prefix comparison.
    for i, (a, b) in enumerate(zip(preferred[:limit], alternative[:limit])):
        if a != b:
            return [dict(index=i, preferred=a, alternative=b, semantic=False,
                         label="source-conditioned token preference; not a verified reasoning decision")]
    return []


def prepare(root, measure):
    records = []
    for source in SOURCES:
        path = root / source
        if not path.exists():
            raise FileNotFoundError(path)
        records.extend((source, line, row) for line, row in enumerate(read_jsonl(path), 1))
    ids = sorted({str(row["id"]) for _, _, row in records}, key=int)
    if len(ids) != 23:
        raise ValueError("Expected the completed 23-question pool")
    random.Random(20261005).shuffle(ids)
    questions = []
    for qid in ids:
        rows = sorted([x for x in records if str(x[2]["id"]) == qid],
                      key=lambda x: (request_of(x[2])["sample_seed"], x[0], x[1]))
        r2 = [x for x in rows if request_of(x[2])["condition_id"] == "R2"]
        if len(r2) != 2:
            raise ValueError("Expected two paired R2 seeds per question")
        request = request_of(r2[0][2])
        if any(request_of(x[2])["input_ids"] != request["input_ids"] for x in r2):
            raise ValueError("Different frozen drafts across paired seeds")
        suffixes, missing = {}, []
        for name, condition, correct in (("correct", "R0", True), ("wrong", "R2", False)):
            for source, line, row in rows:
                g = row["init_response_generations"][0]
                if request_of(row)["condition_id"] != condition or g.get("correctness") is not correct:
                    continue
                expression = g.get("extracted_answer")
                m = measure(expression or "", row["answer"])
                # Scalar 24 requires a separate manual substantive-error judgement.
                if (g.get("finish_reason") != "eos" or not row.get("generated_token_ids")
                        or m["evaluation_status"] != "ok" or m["exact_game24"] != correct
                        or (not correct and str(expression).strip() == "24")):
                    continue
                suffixes[name] = dict(tokens=row["generated_token_ids"][:512], source=source,
                                      line=line, seed=request_of(row)["sample_seed"], expression=expression)
                break
            if name not in suffixes:
                missing.append(name)
        probes = [] if missing else first_difference(suffixes["correct"]["tokens"], suffixes["wrong"]["tokens"])
        questions.append(dict(id=qid, split="discovery" if qid in ids[:8] else "validation",
                              problem=r2[0][2]["problem"], answer=r2[0][2]["answer"],
                              prompt=r2[0][2]["init_response_prompt"], request=request,
                              seeds=[request_of(x[2])["sample_seed"] for x in r2],
                              source=r2[0][0], source_line=r2[0][1], suffixes=suffixes,
                              missing=missing, probes=probes,
                              max_new_tokens=32768-len(request["input_ids"])))
    return dict(seed=20261005, discovery=ids[:8], validation=ids[8:],
                model="/data2/huangrj/models/qwen3-8b", dtype="bfloat16",
                sampling=dict(temperature=.6, top_p=.95, top_k=20),
                context=32768, gpu_hours=24, questions=questions,
                limitations=["Historical behavioural outcomes have already been observed.",
                             "Unreviewed token probes measure lexical preference, not reasoning correctness.",
                             "Missing continuations are not replaced; scalar-24 failures require manual review."])


def score_margin(result):
    values = [p["margin"] for p in result["probes"]]
    return statistics.mean(values) if values else None


def paired_effect(rows, before, after, *, field="margin", draws=5000):
    index = {(r["id"], r["condition"]): r for r in rows}
    values = {}
    for qid, condition in index:
        if condition != before or (qid, after) not in index:
            continue
        a, b = index[qid, before].get(field), index[qid, after].get(field)
        if a is not None and b is not None:
            values[qid] = b-a
    if not values:
        return dict(n=0, mean=None, ci=None, by_question={})
    items = list(values.values())
    rng = random.Random(20261005)
    samples = sorted(statistics.mean(rng.choices(items, k=len(items))) for _ in range(draws))
    return dict(n=len(items), mean=statistics.mean(items),
                ci=[samples[int(draws*.025)], samples[int(draws*.975)]], by_question=values)
