"""Bounded, resumable mechanism-first A100 experiment. No new source sampling."""
from __future__ import annotations

import argparse
import dataclasses
import json
import os
import random
import signal
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from selective_context.diagnostic_data import prepare, read_jsonl, paired_effect, score_margin, expression_measurement


def save(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    tmp.replace(path)


def append(path, obj):
    with Path(path).open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False)+"\n")
        f.flush()
        os.fsync(f.fileno())


class BudgetExceeded(Exception):
    pass


class Budget:
    def __init__(self, path, hours):
        self.path, self.limit = Path(path), hours*3600
        prior = json.loads(self.path.read_text()) if self.path.exists() else {}
        self.spent = prior.get("gpu_seconds", 0)
        if prior.get("active"):
            # Conservatively account for at most one lost heartbeat after a crash.
            self.spent += 30
        self.started = self.last = time.monotonic()
        self.check(force=True)
        if hasattr(signal, "SIGALRM"):
            signal.signal(signal.SIGALRM, self._alarm)
            signal.setitimer(signal.ITIMER_REAL, max(.001, self.limit-self.spent))

    def _alarm(self, *_):
        raise BudgetExceeded("24-hour GPU budget exhausted")

    def check(self, force=False):
        now = time.monotonic()
        elapsed = self.spent+now-self.started
        if force or now-self.last >= 30 or elapsed >= self.limit:
            save(self.path, dict(gpu_seconds=elapsed, limit_seconds=self.limit, active=True))
            self.last = now
        if elapsed >= self.limit:
            raise BudgetExceeded("GPU budget exhausted")

    def close(self):
        if hasattr(signal, "SIGALRM"):
            signal.setitimer(signal.ITIMER_REAL, 0)
        save(self.path, dict(gpu_seconds=self.spent+time.monotonic()-self.started,
                             limit_seconds=self.limit, active=False))


class Experiment:
    def __init__(self, backend, manifest, output, budget):
        self.backend, self.manifest, self.output, self.budget = backend, manifest, output, budget
        self.path = output / "diagnostics.jsonl"
        self.rows = read_jsonl(self.path)
        self.done = {(r["phase"], r["id"], r["condition"], r["suffix"]): r for r in self.rows}
        self.questions = {q["id"]: q for q in manifest["questions"]}
        self.annotations = json.loads((output/"probes.json").read_text()) if (output/"probes.json").exists() else {}
        for qid, probes in self.annotations.items():
            if qid not in self.questions or "correct" not in self.questions[qid]["suffixes"]:
                raise ValueError("Annotated probe has no corresponding correct continuation")
            tokens=self.questions[qid]["suffixes"]["correct"]["tokens"]
            for probe in probes:
                index=probe["index"]
                if not 0 <= index < min(512,len(tokens)) or probe["preferred"] != tokens[index]:
                    raise ValueError("Annotated probe does not match its fixed continuation")
                if (not 0 <= probe["alternative"] < self.backend.model.config.vocab_size
                        or probe["alternative"] == probe["preferred"]):
                    raise ValueError("Invalid probe alternative")
                if probe.get("semantic") and not probe.get("reason"):
                    raise ValueError("Semantic probe requires a reviewed validity explanation")

    def prefill(self, q):
        return self.backend.prefill(q["request"]["input_ids"])

    def measure(self, phase, ids, conditions, *, window=128, collect=False, annotated=False):
        for qid in ids:
            q = self.questions[qid]
            todo = [(name, spec, suffix) for name, spec in conditions for suffix in q["suffixes"]
                    if (phase, qid, name, suffix) not in self.done]
            if not todo:
                continue
            pre = self.prefill(q)
            for name, spec, suffix in todo:
                self.budget.check()
                started = time.monotonic()
                tokens = q["suffixes"][suffix]["tokens"][:window]
                probes = q["probes"] if suffix == "correct" else []
                if annotated and suffix == "correct":
                    probes = self.annotations.get(qid, [])
                out = self.backend.teacher_force(pre, tokens, q["request"]["draft_token_span"], spec,
                                                 collect=collect, probes=probes)
                row = dict(phase=phase, id=qid, condition=name, suffix=suffix,
                           mode=spec.mode, heads=spec.heads, strength=spec.strength,
                           source=q["suffixes"][suffix]["source"],
                           gpu_seconds=time.monotonic()-started,
                           margin=score_margin(out), **out)
                append(self.path, row)
                self.rows.append(row)
                self.done[phase, qid, name, suffix] = row
                self.budget.check(force=True)
                print(f"{phase} {qid} {name} {suffix} nll={row['nll']:.4f} margin={row['margin']}", flush=True)
            del pre

    def utility(self, phase, condition, metric):
        rows = [dict(r, negative_nll=-r["nll"]) for r in self.rows
                if r["phase"] == phase and r["suffix"] == "correct"]
        return paired_effect(rows, "FULL", condition, field=metric)

    def summary(self, status, **kwargs):
        save(self.output/"summary.json", dict(status=status, **kwargs))
        lines = ["# Mechanism experiment", "", f"Status: {status}", "",
                 "Only paired question-level results are interpreted. Historical outcomes were already observed.",
                 "Lexical token preference and fixed-continuation NLL are diagnostic proxies, not proof of reasoning correctness.",
                 "VALUE_ZERO separates local value content from MASK's joint access/renormalization effect.",
                 "Head localization alone does not establish novelty beyond prior false-induction-head ablations.", "",
                 "```json", json.dumps(kwargs, ensure_ascii=False, indent=2), "```"]
        (self.output/"report.md").write_text("\n".join(lines)+"\n", encoding="utf-8")

    def accept(self):
        from selective_context.diagnostics import Intervention
        import torch
        checks = []
        for qid in self.manifest["discovery"][:2]:
            q = self.questions[qid]
            suffix = q["suffixes"].get("correct") or q["suffixes"].get("wrong")
            if suffix is None:
                checks.append(dict(id=qid, status="missing_continuation"))
                continue
            tokens, span = suffix["tokens"][:32], q["request"]["draft_token_span"]
            pre = self.prefill(q)
            cache_length = pre[1].get_seq_length()
            full = self.backend.teacher_force(pre, tokens, span, collect=True, capture=True)
            masked = self.backend.teacher_force(pre, tokens, span, Intervention("MASK"), collect=True, capture=True)
            # Reuse prefill, reverse branch order, and then test explicit identity.
            reverse_mask = self.backend.teacher_force(pre, tokens, span, Intervention("MASK"))
            reverse_full = self.backend.teacher_force(pre, tokens, span)
            identity = self.backend.teacher_force(pre, tokens, span, Intervention("VALUE_ZERO", ()))
            assert pre[1].get_seq_length() == cache_length, "Prefill cache mutated by branch"
            assert full["log_probs"][0] == masked["log_probs"][0], "First-token distribution changed"
            torch.testing.assert_close(torch.tensor(full["log_probs"]), torch.tensor(reverse_full["log_probs"]), rtol=0, atol=1e-5)
            torch.testing.assert_close(torch.tensor(masked["log_probs"]), torch.tensor(reverse_mask["log_probs"]), rtol=0, atol=1e-5)
            torch.testing.assert_close(torch.tensor(full["log_probs"]), torch.tensor(identity["log_probs"]), rtol=0, atol=1e-5)
            error = max(m["reconstruction_relative_error"] for m in full["retrieval"])
            assert error < .02, "Contribution reconstruction failed"
            assert max(max(m["mass"]) for m in full["retrieval"]) > 0, "Draft span is never accessed"
            assert max(max(m["applied_mass"]) for m in masked["retrieval"]) == 0, "Masked edges remain visible"
            checks.append(dict(id=qid, status="passed", reconstruction_relative_error=error,
                               first_token_logp=full["log_probs"][0]))
            del pre, full, masked
        assert checks and all(x["status"] == "passed" for x in checks), "Acceptance sample missing"
        save(self.output/"acceptance.json", dict(passed=True, checks=checks))

    def run(self):
        from selective_context.diagnostics import Intervention
        discovery, validation = self.manifest["discovery"], self.manifest["validation"]
        if not (self.output/"acceptance.json").exists():
            self.accept()
        base = [("FULL", Intervention()), ("VALUE_ZERO", Intervention("VALUE_ZERO")),
                ("MASK", Intervention("MASK"))]
        self.measure("screen", discovery, base, collect=True)
        # A probe at t=0 cannot be influenced by any decode intervention.
        informative = any(q["probes"] and q["probes"][0]["index"] > 0
                          for q in self.manifest["questions"] if q["id"] in discovery)
        metric = "margin" if informative else "negative_nll"
        ve, me = [self.utility("screen", c, metric) for c in ("VALUE_ZERO", "MASK")]
        phase = "screen"
        if not any(e["mean"] is not None and e["mean"] > 0 for e in (ve, me)):
            reviewed = [qid for qid in discovery if self.annotations.get(qid)]
            if not reviewed:
                self.summary("stopped_no_early_signal", value=ve, mask=me,
                             next="Only a reviewed construction-decision probe may be appended; no new generation.")
                return
            self.measure("construction", reviewed, base, window=512, annotated=True)
            phase, metric = "construction", "margin"
            ve, me = [self.utility(phase, c, metric) for c in ("VALUE_ZERO", "MASK")]
            if not any(e["mean"] is not None and e["mean"] > 0 for e in (ve, me)):
                self.summary("stopped_no_construction_signal", value=ve, mask=me)
                return
            discovery = reviewed
        mode = "VALUE_ZERO" if ve["mean"] is not None and ve["mean"] > 0 else "MASK"
        save(self.output/"screen_summary.json",dict(phase=phase,metric=metric,value=ve,mask=me,
                                                   selected_branch=mode,
                                                   interpretation="Exploratory proxy; full behavioural validation is still required."))
        groups = [list(range(len(self.backend.layers)*i//4, len(self.backend.layers)*(i+1)//4)) for i in range(4)]
        group_specs = [(f"GROUP_{i}", Intervention(mode, tuple((l,h) for l in layers
                                                              for h in range(self.backend.n_heads))))
                       for i,layers in enumerate(groups)]
        self.measure("groups", discovery, [("FULL", Intervention())]+group_specs,
                     window=512 if phase == "construction" else 128, annotated=phase == "construction")
        group_effects = {name:self.utility("groups", name, metric) for name,_ in group_specs}
        best = max(group_effects, key=lambda k: group_effects[k]["mean"] if group_effects[k]["mean"] is not None else -float("inf"))
        if group_effects[best]["mean"] is None or group_effects[best]["mean"] <= 0:
            self.summary("stopped_no_local_group", value=ve, mask=me, groups=group_effects)
            return
        layers = groups[int(best.split("_")[-1])]
        # Cheap retrieval proxy shortlists at most 8 heads; it is not a causal claim.
        importance = {}
        for r in self.rows:
            if r["phase"] == "screen" and r["condition"] == "FULL":
                for m in r["retrieval"]:
                    if m["layer"] in layers:
                        for h,(a,n) in enumerate(zip(m["mass"],m["value_norm"])):
                            importance.setdefault((m["layer"],h), []).append(a*n)
        shortlist = sorted(importance, key=lambda h: (-statistics.mean(importance[h]), h))[:8]
        if not shortlist:
            self.summary("stopped_no_head_shortlist")
            return
        singles = [(f"HEAD_{l}_{h}", Intervention(mode, ((l,h),))) for l,h in shortlist]
        self.measure("heads", discovery, [("FULL", Intervention())]+singles,
                     window=512 if phase == "construction" else 128, annotated=phase == "construction")
        ranking = sorted(singles, key=lambda x: -(self.utility("heads", x[0], metric)["mean"] or 0))
        positive = [spec.heads[0] for name,spec in ranking
                    if (self.utility("heads", name, metric)["mean"] or 0) > 0]
        if not positive:
            self.summary("stopped_no_causal_heads", groups=group_effects)
            return
        unions = [(f"UNION_{k}", Intervention(mode, tuple(positive[:k]))) for k in range(1,len(positive)+1)]
        self.measure("unions", discovery, [("FULL", Intervention())]+unions,
                     window=512 if phase == "construction" else 128, annotated=phase == "construction")
        name, spec = max(unions, key=lambda x: self.utility("unions", x[0], metric)["mean"] or -float("inf"))
        candidate = dict(mode=spec.mode, heads=[list(h) for h in spec.heads], strength=1.,
                         metric=metric, discovery=discovery,
                         group=layers, shortlist=[list(h) for h in shortlist],
                         caveat="Shortlist is based on retrieval norm/mass; untested heads may also be causal.")
        frozen = self.output/"candidate.json"
        if frozen.exists():
            assert json.loads(frozen.read_text()) == candidate, "Frozen candidate cannot change on resume"
        else:
            save(frozen,candidate)
        if mode == "VALUE_ZERO":
            self.patch(discovery, spec)
        else:
            self.measure("redistribution", discovery, [("FULL",Intervention()),
                         ("MASK",spec), ("VALUE_ZERO",Intervention("VALUE_ZERO",spec.heads))])
        rng = random.Random(20261005)
        pool = [(l,h) for l in layers for h in range(self.backend.n_heads) if (l,h) not in spec.heads]
        control = Intervention(mode,tuple(rng.sample(pool,len(spec.heads))))
        self.measure("validation",validation,[("FULL",Intervention()),("MASK",Intervention("MASK")),
                                               ("CANDIDATE",spec),("CONTROL",control)],
                     window=512 if phase == "construction" else 128, annotated=phase == "construction")
        ce, re = [self.utility("validation", c, metric) for c in ("CANDIDATE","CONTROL")]
        save(self.output/"validation.json",dict(candidate=ce,control=re,control_heads=control.heads))
        if ce["mean"] is None or re["mean"] is None or ce["mean"] <= 0 or ce["mean"] <= re["mean"]:
            self.summary("stopped_validation_failed",candidate=candidate,effect=ce,control=re)
            return
        self.bridge(validation[:4],spec)
        first=self.behaviour(validation[:4])
        if first["candidate_correct"] > first["full_correct"] and first["candidate_reuse"] < first["full_reuse"]:
            self.bridge(validation[4:8],spec)
        self.summary("completed",candidate=candidate,effect=ce,control=re,
                     first_bridge=first,behaviour=self.behaviour(validation[:8]))

    def patch(self, ids, spec):
        from selective_context.diagnostics import Intervention
        for qid in ids:
            q=self.questions[qid]
            if "correct" not in q["suffixes"]:
                continue
            keys=[("patch",qid,n,"correct") for n in ("R2_FROM_R3","R3_FROM_R2")]
            if all(k in self.done for k in keys):
                continue
            pre=self.prefill(q)
            tokens=q["suffixes"]["correct"]["tokens"][:128]
            span=q["request"]["draft_token_span"]
            full=self.backend.teacher_force(pre,tokens,span,capture=True)
            masked=self.backend.teacher_force(pre,tokens,span,Intervention("MASK"),capture=True)
            # Reverse donor experiment uses MASK globally, then overwrites selected outputs.
            for name, donor, base_mode in (("R2_FROM_R3",masked,"FULL"),("R3_FROM_R2",full,"MASK")):
                key=("patch",qid,name,"correct")
                if key in self.done:
                    continue
                if base_mode == "FULL":
                    out=self.backend.teacher_force(pre,tokens,span,Intervention("PATCH",spec.heads),
                                                  donor=donor["outputs"],probes=q["probes"])
                else:
                    # Composite mask+patch is explicit, not silently approximated.
                    out=self.backend.teacher_force(pre,tokens,span,Intervention("PATCH_MASK",spec.heads),
                                                  donor=donor["outputs"],probes=q["probes"])
                row=dict(phase="patch",id=qid,condition=name,suffix="correct",margin=score_margin(out),**out)
                append(self.path,row); self.rows.append(row); self.done[key]=row
            del pre,full,masked

    def bridge(self,ids,spec,conditions=None):
        from selective_context.diagnostics import Intervention
        from selective_context.schema import SelectiveContextRequest
        from selective_context.tasks import score_record,extract_math_box
        from selective_context.official_compat import make_official_record
        from selective_context.phase0.thinking_pilot import extract_final_draft
        path=self.output/"behaviour.jsonl"
        done={(r["id"],r["seed"],r["condition"]) for r in read_jsonl(path)}
        for qid in ids:
            q=self.questions[qid]
            pre=None
            for seed in q["seeds"]:
                for name,intervention in (conditions if conditions is not None else
                        (("FULL",Intervention()),("MASK",Intervention("MASK")),("CANDIDATE",spec))):
                    if (qid,seed,name) in done:
                        continue
                    started=time.monotonic()
                    if pre is None:
                        pre=self.prefill(q)
                    request=dataclasses.replace(SelectiveContextRequest.from_dict(q["request"]),sample_seed=seed)
                    result=self.backend.generate_diagnostic(pre,request,intervention,
                                                           max_new_tokens=q["max_new_tokens"],**self.manifest["sampling"])
                    final,status=extract_final_draft(result.text,q["prompt"],self.backend.tokenizer.eos_token)
                    original=result.text
                    result.text=final
                    official=score_record(make_official_record(problem_id=qid,problem=q["problem"],answer=q["answer"],
                        prompt=q["prompt"],request=request,generations=[result],model_config_alias="Qwen3_8B_Thinking"))
                    g=official["init_response_generations"][0]
                    lo,hi=request.draft_token_span
                    old=extract_math_box(self.backend.tokenizer.decode(request.input_ids[lo:hi]))
                    normalize=lambda s:"".join((s or "").replace("\\left","").replace("\\right","").split())
                    row=dict(id=qid,seed=seed,condition=name,correct=g.get("correctness") is True,
                             score_status=g.get("correctness"),finish_reason=result.finish_reason,
                             extracted_answer=g.get("extracted_answer"),thinking_status=status,
                             old_expression=old,reuse=bool(old and g.get("extracted_answer") and
                                                          normalize(old)==normalize(g["extracted_answer"])),
                             text=original,generated_token_ids=result.generated_token_ids,
                             mode=intervention.mode,heads=intervention.heads,query_window=intervention.query_window,
                             model=self.manifest["model"],sampling=self.manifest["sampling"],
                             source=q.get("source"),gpu_seconds=time.monotonic()-started)
                    append(path,row); done.add((qid,seed,name)); self.budget.check(force=True)
                    print(f"bridge {qid} {seed} {name} correct={row['correct']} finish={row['finish_reason']}",flush=True)
            del pre

    def behaviour(self,ids):
        rows=[r for r in read_jsonl(self.output/"behaviour.jsonl") if r["id"] in ids]
        stats={}
        for condition in ("FULL","MASK","CANDIDATE"):
            rs=[r for r in rows if r["condition"]==condition]
            stats[condition]=dict(n=len(rs),correct=sum(r["correct"] for r in rs),reuse=sum(r["reuse"] for r in rs),
                                  eos=sum(r["finish_reason"]=="eos" for r in rs),
                                  length=sum(r["finish_reason"]=="length" for r in rs),
                                  unresolved=sum(r["score_status"] is None for r in rs))
        index={(r["id"],r["seed"],r["condition"]):r for r in rows}
        transitions=[(r["correct"],index[q,s,"CANDIDATE"]["correct"]) for (q,s,c),r in index.items()
                     if c=="FULL" and (q,s,"CANDIDATE") in index]
        return dict(conditions=stats,full_correct=stats["FULL"]["correct"],candidate_correct=stats["CANDIDATE"]["correct"],
                    full_reuse=stats["FULL"]["reuse"],candidate_reuse=stats["CANDIDATE"]["reuse"],
                    recovered=sum(not a and b for a,b in transitions),harmed=sum(a and not b for a,b in transitions))


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",type=Path,default=ROOT/"outputs/generation-diagnostics-20261005")
    parser.add_argument("--prepare",action="store_true")
    parser.add_argument("--resume",action="store_true")
    parser.add_argument("--status",action="store_true",help="Read persisted progress without using the GPU")
    args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    manifest_path=args.output/"manifest.json"
    if not manifest_path.exists():
        manifest=prepare(ROOT,expression_measurement)
        save(manifest_path,manifest)
    else:
        manifest=json.loads(manifest_path.read_text(encoding="utf-8"))
    if args.status:
        from collections import Counter
        counts=Counter()
        results=args.output/"diagnostics.jsonl"
        if results.exists():
            with results.open(encoding="utf-8") as handle:
                for line in handle:
                    if line.strip(): counts[json.loads(line)["phase"]] += 1
        status=dict(phase_requests=dict(counts),behaviour_requests=len(read_jsonl(args.output/"behaviour.jsonl")))
        semantic=read_jsonl(args.output/"semantic_diagnostics.jsonl")
        if semantic:
            status["current_protocol"]="semantic_rejection"
            status["last_completed_semantic_request"]={k:semantic[-1][k] for k in ("phase","id","condition")}
            status["semantic_phase_requests"]={phase:sum(r["phase"]==phase for r in semantic)
                                               for phase in sorted({r["phase"] for r in semantic})}
        status["semantic_behaviour_requests"]=len(read_jsonl(args.output/"semantic_behaviour"/"behaviour.jsonl"))
        for name in ("budget","candidate","summary","failure","semantic_summary","semantic_failure","semantic_candidate"):
            path=args.output/f"{name}.json"
            if path.exists(): status[name]=json.loads(path.read_text(encoding="utf-8"))
        print(json.dumps(status,ensure_ascii=False,indent=2))
        return
    if args.prepare:
        print(json.dumps(dict(discovery=manifest["discovery"],validation=manifest["validation"],
                              missing={q["id"]:q["missing"] for q in manifest["questions"] if q["missing"]}),indent=2))
        return
    if (args.output/"budget.json").exists() and not args.resume:
        parser.error("Existing experiment requires --resume")
    import torch
    from transformers import AutoModelForCausalLM,AutoTokenizer
    from selective_context.diagnostics import DiagnosticBackend
    if not torch.cuda.is_available() or "A100" not in torch.cuda.get_device_name(0) or torch.cuda.device_count()!=1:
        raise RuntimeError("Experiment requires exactly one visible A100")
    budget=Budget(args.output/"budget.json",manifest["gpu_hours"])
    experiment=None
    try:
        acceptance=args.output/"acceptance.json"
        if not acceptance.exists():
            import subprocess
            subprocess.run([sys.executable,"-m","pytest","-q","tests/selective_context/test_diagnostics.py"],
                           cwd=ROOT,check=True)
            budget.check(force=True)
        tokenizer=AutoTokenizer.from_pretrained(manifest["model"],local_files_only=True)
        model=AutoModelForCausalLM.from_pretrained(manifest["model"],local_files_only=True,
                    torch_dtype=torch.bfloat16,attn_implementation="sdpa",device_map="cuda:0")
        backend=DiagnosticBackend(model,tokenizer,budget.check)
        experiment=Experiment(backend,manifest,args.output,budget)
        experiment.run()
    except BudgetExceeded:
        if experiment:
            experiment.summary("budget_exhausted",completed_requests=len(experiment.rows),
                               behaviour=experiment.behaviour(manifest["validation"][:8]))
        else:
            save(args.output/"summary.json",dict(status="budget_exhausted_during_loading"))
    except Exception as exc:
        save(args.output/"failure.json",dict(type=type(exc).__name__,message=str(exc)))
        raise
    finally:
        budget.close()


if __name__=="__main__":
    main()
