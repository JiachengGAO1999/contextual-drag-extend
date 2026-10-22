"""CPU-only SQLite evidence-scope audit; only disposable in-memory databases."""
from __future__ import annotations

import itertools
import json
import re
import sqlite3
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAMES = ("alpha", "beta", "gamma", "delta")


def run_query(connection, query):
    try:
        connection.execute(query)
        return None
    except sqlite3.Error as exc:
        return str(exc)


def audit():
    worlds = list(itertools.combinations(NAMES, 2))
    records = []
    for schema in worlds:
        connection = sqlite3.connect(":memory:")
        try:
            connection.execute("CREATE TABLE resources (" + ",".join(c + " INTEGER" for c in schema) + ")")
            for order in itertools.permutations(NAMES):
                query = "SELECT " + ", ".join(order) + " FROM resources"
                error = run_query(connection, query)
                reported = error.removeprefix("no such column: ") if error else None
                expected = next(c for c in order if c not in schema)
                records.append(dict(schema=list(schema), order=list(order), query=query,
                                    error=error, reported=reported, expected=expected,
                                    matches_select_list_order=reported == expected))
        finally:
            connection.close()
    observation = {(tuple(r["schema"]), tuple(r["order"])): r["error"] for r in records}
    equivalent = lossy = 0
    for r in records:
        if r["reported"] not in NAMES:
            continue
        k = r["order"].index(r["reported"])
        # Full support is computed from actual SQLite observations on all
        # six schemas, independently of the proposed textual-prefix summary.
        full = [list(w) for w in worlds if observation[w, tuple(r["order"])] == r["error"]]
        typed = [list(w) for w in worlds if all(c in w for c in r["order"][:k])
                 and r["reported"] not in w]
        error_only = [list(w) for w in worlds if r["reported"] not in w]
        r.update(first_failure_position=k, full_schema_support=full,
                 typed_schema_support=typed, error_only_schema_support=error_only)
        equivalent += full == typed
        lossy += full != error_only

    connection = sqlite3.connect(":memory:")
    probes = []
    try:
        connection.execute("CREATE TABLE resources (alpha INTEGER,beta INTEGER)")
        queries = [
            "SELECT alpha,beta,gamma,delta FROM resources",
            "SELECT gamma FROM resources WHERE delta>0",
            "SELECT alpha FROM resources WHERE gamma>0 ORDER BY delta",
            "SELECT alpha FROM resources JOIN missing_table ON gamma>0",
            "SELECT gamma FROM resources JOIN missing_table ON delta>0",
            "SELECT alpha FROM resources WHERE gamma>0 LIMIT delta",
            "SELECT gamma FROM resources WHERE alpha>0 LIMIT delta",
            "SELECT gamma FROM resources WHERE EXISTS (SELECT delta FROM resources)",
            "SELECT alpha FROM resources LIMIT alpha",
            "SELECT alpha FROM resources",
            "SELECT alpha AS omega FROM resources ORDER BY omega",
            "SELECT alpha AS omega FROM resources LIMIT omega",
        ]
        for query in queries:
            error = run_query(connection, query)
            reported = error.removeprefix("no such column: ") if error and error.startswith("no such column: ") else None
            previous_missing = []
            if reported in NAMES:
                before = query[:query.index(reported)]
                previous_missing = [c for c in NAMES if c not in ("alpha", "beta")
                                    and re.search(r"\b" + c + r"\b", before)]
            probes.append(dict(schema=["alpha", "beta"], query=query, error=error,
                               reported_column=reported,
                               reported_name_present_in_table=reported in ("alpha", "beta") if reported else None,
                               missing_column_references_textually_before_reported=previous_missing))
    finally:
        connection.close()
    return dict(sqlite_version=sqlite3.sqlite_version,
        scope="Actual local SQLite execution, CPU only, all databases in memory. No model outputs, GPU manifest or novelty claim.",
        restricted_class="One table, a simple SELECT list of four candidate names, exactly two columns present, no additional clauses. Six schemas times 24 list orders; highly symmetric, not 144 independent research cases.",
        restricted_summary=dict(queries=len(records),
            order_mismatches=sum(not r["matches_select_list_order"] for r in records),
            failure_positions=dict(Counter(r.get("first_failure_position") for r in records)),
            actual_full_support_equals_typed_support=equivalent,
            error_only_lossy_records=lossy),
        restricted_records=records, clause_order_probes=probes,
        interpretation="The checked SELECT-list class supports the limited prefix-membership inference in this SQLite version. Counterexamples with other clauses prohibit generalizing it to textual prefixes of arbitrary SQL, let alone arbitrary reasoning. A 'no such column' error in LIMIT can name a column that really exists in the table; visibility at one use site is not global absence. Name resolution does not certify runtime behavior or semantic correctness. An error-only summary may lose evidence, while an unjustified prefix certificate may invent evidence.")


if __name__ == "__main__":
    result = audit()
    output = ROOT / "outputs/generation-diagnostics-20261005/feedback_evidence_preview/sqlite_semantics.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf8")
    print(json.dumps({k: v for k, v in result.items() if k != "restricted_records"}, ensure_ascii=False))
