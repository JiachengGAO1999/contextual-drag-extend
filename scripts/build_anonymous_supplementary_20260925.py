"""Build a clean review artifact from an explicit allowlist (never zip the repo)."""
from pathlib import Path
import json
import sys
import hashlib
import re
import shutil
import zipfile
import ast

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'supplementary'
EVIDENCE = ROOT / 'runs/iclr2027_evidence_20260925_completed/evidence.json'

def read(path):
    return json.loads(path.read_text(encoding='utf-8'))

def write(rel, data):
    path = OUT / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    if not isinstance(data, str):
        data = json.dumps(data, indent=2, ensure_ascii=False) + '\n'
    path.write_text(data, encoding='utf-8')

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def copy(rel):
    write(rel, (ROOT/rel).read_text(encoding='utf-8'))

def slim_record(raw):
    keys = ['id','problem','answer','init_response_prompt','generated_token_ids','final_response','thinking_status','stratum','benchmark','task']
    result = {k:raw[k] for k in keys if k in raw}
    generations = []
    for gen in raw['init_response_generations']:
        g = {k:gen[k] for k in ['response_id','generated_response','finish_reason','correctness','extracted_answer','scorer_version','first_generated_token_id','generated_token_count'] if k in gen}
        meta = gen['selective_context_metadata']
        req = meta.get('request') or raw.get('init_response_generations_metadata',{}).get('intervention')
        g['selective_context_metadata'] = {k:meta[k] for k in ['backend','access_mode','decode_layout','logical_kv_blocking','physical_kv_eviction','eos_token_ids','stop_token_id','cache_type','sampling_rng'] if k in meta}
        g['selective_context_metadata']['request'] = req
        result['init_response_generations_metadata'] = {'intervention': req}
        generations.append(g)
    result['init_response_generations'] = generations
    return result

if sys.argv[1] == 'inspect':
    for key, entry in read(EVIDENCE)['inputs'].items():
        path = ROOT / entry['path'].replace('\\', '/')
        raw = json.loads(path.open(encoding='utf-8').readline())
        gen = raw['init_response_generations'][0]
        meta = gen['selective_context_metadata']
        print(key, path.stat().st_size, 'raw:', list(raw), 'gen:', list(gen), 'meta:', list(meta))
        request = meta.get('request') or raw.get('init_response_generations_metadata', {}).get('intervention')
        print('request keys:', list(request))
        config = path.parent / 'config.json'
        if config.exists():
            obj = read(config)
            print('config keys:', list(obj))
            print('versions:', {k:v for k,v in obj.items() if any(x in k for x in ['torch','transformers','vllm','python','backend','temperature','top_','max_','seed','dtype'])})
    print('control analysis candidates:', [str(p.relative_to(ROOT)) for p in (ROOT/'runs').glob('*correct*')])
elif sys.argv[1] == 'inspect2':
    for name, start, end in [('LICENSE',0,100), ('scripts/analyze_game24_correct_specificity_20260922.py',140,265), ('scripts/plot_iclr2027_access_effects_20260925.py',0,100), ('selective_context/schema.py',0,125)]:
        print(name)
        print('\n'.join((ROOT/name).read_text(encoding='utf-8').splitlines()[start:end]).encode('ascii',errors='backslashreplace').decode())
    for p in (ROOT/'requirements').glob('*'):
        print(p.name)
        for line in p.read_text(encoding='utf-8').splitlines():
            if any(line.startswith(x) for x in ('torch=', 'transformers=', 'vllm=', 'math-verify=', 'sympy=')):
                print(line)
elif sys.argv[1] == 'inspect3':
    for p in (ROOT/'utils/verifiable_evaluation/math_eval/utils').glob('*.py'):
        print(p.name, [x for x in p.read_text(encoding='utf-8').splitlines() if x.startswith(('from ', 'import '))])
    print('license tail:', (ROOT/'LICENSE').read_text()[-900:])
    for rel in ['runs/game24_correct_draft_specificity_20260922_raw/manifest.json','runs/game24_correct_draft_specificity_20260922_raw/completion.json','runs/game24_correct_draft_specificity_20260921/selected_correct_pairs.jsonl']:
        p=ROOT/rel
        obj=json.loads(p.open(encoding='utf-8').readline()) if p.suffix=='.jsonl' else read(p)
        print(rel, list(obj[0]) if isinstance(obj,list) else list(obj))
    for line in (ROOT/'scripts/analyze_game24_correct_specificity_20260922.py').read_text().splitlines()[208:232]:
        print(line)
elif sys.argv[1] == 'build':
    OUT.mkdir(exist_ok=True)
    for p in (ROOT/'selective_context').glob('*.py'):
        if p.name != 'testing.py':
            copy(p.relative_to(ROOT))
    for name in ['evaluation_utils.py','verification_utils.py','math_utils.py']:
        rel = 'utils/verifiable_evaluation/math_eval/utils/' + name
        s = (ROOT/rel).read_text(encoding='utf-8')
        if name == 'evaluation_utils.py' and s.count('embed') == 1:
            s = '# Review packaging: removed unused IPython debugger import.\n' + s.replace('from IPython import embed\n','')
        write(rel,s)
    for rel in ['utils/__init__.py','utils/verifiable_evaluation/__init__.py','utils/verifiable_evaluation/math_eval/__init__.py','utils/verifiable_evaluation/math_eval/utils/__init__.py']:
        write(rel, '"""Minimal review package initializer; optional dataset-loading imports omitted."""\n')
    for name in ['init_response_prompt_templates.json','1f_templates.json','prompted_error_signal_templates.json']:
        copy('prompt_templates/'+name)
    for name in ['build_iclr2027_evidence_20260925.py','analyze_continued_access_math_20260921.py','analyze_game24_correct_specificity_20260922.py','plot_iclr2027_access_effects_20260925.py','plot_iclr2027_question_recovery_20260925.py']:
        copy('scripts/'+name)
    copy('LICENSE')
    original = read(EVIDENCE)
    entries = {}
    total = 0
    for key, entry in original['inputs'].items():
        rel = entry['path'].replace('\\','/')
        source = ROOT/rel
        if sha(source) != entry['sha256']:
            raise RuntimeError('Frozen source hash mismatch: '+key)
        rows = [slim_record(json.loads(line)) for line in source.read_text(encoding='utf-8').splitlines() if line.strip()]
        total += len(rows)
        write(rel, ''.join(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n' for r in rows))
        entries[key] = {'path':rel,'source_sha256':sha(source),'packaged_sha256':sha(OUT/rel),'records':len(rows),'transform':'allowlisted scientific fields; request, prompt, tokens, responses, and scores preserved'}
        cfg = source.parent/'config.json'
        c = read(cfg) if cfg.exists() else {}
        allowed = ['task','questions','generations','temperature','top_p','top_k','context_size','context','batch_size','enable_thinking','prefix_caching','seeds','conditions','sampling','max_new_tokens','backend','eos_policy','condition_ids']
        selected={k:c[k] for k in allowed if k in c}
        selected['recorded_generation_backends']=sorted({r['init_response_generations'][0]['selective_context_metadata']['backend'] for r in rows})
        write('configs/'+key+'.json',selected)
    if total != 524:
        raise RuntimeError('Expected 524 scientific requests')
    write('evidence_manifest/source_records.json',{'scientific_requests':total,'inputs':entries,'note':'Original hashes identify the frozen sources. Packaged hashes cover the anonymized projections. No Git commit identifiers are included.'})
    expected = {k:v for k,v in original.items() if k != 'inputs'}
    write('evidence_manifest/expected_evidence.json',expected)
    control=read(ROOT/'runs/game24_correct_draft_specificity_20260922_analysis/analysis.json')
    write('evidence_manifest/expected_control.json',{k:v for k,v in control.items() if k not in ['audit','sources','inputs']})
    source_rel='runs/game24_correct_draft_specificity_20260921/selected_correct_pairs.jsonl'
    sources=[]
    for line in (ROOT/source_rel).read_text(encoding='utf-8').splitlines():
        if line.strip():
            row=json.loads(line)
            sources.append({k:v for k,v in row.items() if k in ['id','task','problem','answer','failed_traj','correct_traj','failed_sha256','correct_sha256','stratum','benchmark','correct_source_finish_reason','correct_source_correctness','correct_source_thinking_status','selection_rank']})
    write(source_rel,''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in sources))
    control_dir='runs/game24_correct_draft_specificity_20260922_raw/'
    manifest=[]
    for row in [json.loads(x) for x in (OUT/(control_dir+'results.jsonl')).read_text(encoding='utf-8').splitlines()]:
        req=row['init_response_generations'][0]['selective_context_metadata']['request']
        manifest.append({'id':row['id'],'condition':req['condition_id'],'seed':req['sample_seed'],'task':'game24'})
    write(control_dir+'manifest.json',manifest)
    write(control_dir+'completion.json',{'completed':len(manifest),'note':'Derived from included completed records; infrastructure timing omitted.'})
    (OUT/'texts/iclr-2027-style-files/iclr2027').mkdir(parents=True,exist_ok=True)
    write('requirements.txt','# CPU figure rendering only. Statistical reconstruction uses the Python standard library.\nmatplotlib==3.10.5\nnumpy==2.2.6\n')
    write('requirements-scoring.txt','math-verify==0.8.0\nsympy==1.14.0\nantlr4-python3-runtime==4.11.0\njoblib==1.5.1\nnumpy==2.2.6\ntqdm==4.67.1\n')
    write('requirements-qwen.txt','-r requirements-scoring.txt\ntorch==2.8.0\ntransformers==4.55.4\nvllm==0.11.0\n')
    write('configs/condition_names.json',{'R0':'Clean','R2':'Full','R3':'LateBlock','R4':'PathBlock','C_FULL':'Correct-history Full','C_LATE':'Correct-history LateBlock'})
    print('Prepared core code and',total,'anonymized experimental records.')
elif sys.argv[1] == 'metadata':
    import importlib.metadata
    import struct
    versions={k:importlib.metadata.version(k) for k in ['matplotlib','numpy']}
    versions['python']=sys.version.split()[0]
    png_reports={}
    for path in OUT.rglob('*.png'):
        data=path.read_bytes(); offset=8; fields=[]
        while offset<len(data):
            length=struct.unpack('>I',data[offset:offset+4])[0]
            kind=data[offset+4:offset+8]
            payload=data[offset+8:offset+8+length]
            if kind in (b'tEXt',b'iTXt',b'zTXt'):
                fields.append(payload.decode('latin1'))
            offset+=12+length
        png_reports[path.relative_to(OUT).as_posix()]=fields
    write('evidence_manifest/packaging_environment.json',{'cpu_reconstruction_environment':versions,'gpu_replay_run_during_packaging':False,'fresh_dependency_install_run':False,'png_text_metadata':png_reports,'pdf_metadata_review':'Both generated figure PDFs contain only generic Matplotlib creator/producer metadata and creation time; no Author field.'})
    write('requirements.txt','# Versions used for the artifact CPU figure reconstruction. Statistical reconstruction uses only the standard library.\n'+''.join(k+'=='+versions[k]+'\n' for k in ['matplotlib','numpy']))
    print(json.dumps(versions))
elif sys.argv[1] in ('scan','zip'):
    patterns={
        'known_identity':r'gaojc|phoen|huangrj|sjtu|sisu|上海交通|上海外国语',
        'machine_path':r'(?:[A-Z]:[\\/](?:Users|Learning)|/(?:home|data\d*|mnt|root)/[A-Za-z0-9_.-]+)',
        'email':r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b',
        'credential':r'\b(?:hf_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9_-]{20,}|gh[pousr]_[A-Za-z0-9]{20,})\b',
        'private_tracking_url':r'https?://(?:wandb\.ai|api\.wandb\.ai)/[^\s"<>]+',
    }
    files=[]; findings=[]
    for path in sorted(OUT.rglob('*')):
        if not path.is_file() or '__pycache__' in path.parts or path.suffix in ('.pyc','.pyo'):
            continue
        rel=path.relative_to(OUT).as_posix()
        if any(part.startswith('.') for part in Path(rel).parts):
            findings.append({'path':rel,'kind':'hidden_file'})
        files.append(path)
        if path.suffix not in ('.pdf','.png'):
            content=path.read_text(encoding='utf-8')
            for kind,pattern in patterns.items():
                matches=list(re.finditer(pattern,content,re.I))
                if matches:
                    findings.append({'path':rel,'kind':kind,'count':len(matches)})
    print(json.dumps({'files':len(files),'findings':findings},indent=2))
    if findings: raise SystemExit(1)
    if sys.argv[1]=='zip':
        report={'files_scanned':len(files),'findings':findings,'excluded':['.git','__pycache__','bytecode','editor state','shell history','unrelated runs'],
                'record_projection':'Scientific fields allowlisted; original records untouched.',
                'scan_scope':list(patterns),'note':'Automated content scan plus an explicit file allowlist; not a guarantee against every possible identity inference.'}
        write('evidence_manifest/anonymization_report.json',report)
        files=[p for p in sorted(OUT.rglob('*')) if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ('.pyc','.pyo') and p.name!='SHA256SUMS.txt']
        write('SHA256SUMS.txt',''.join(sha(p)+'  '+p.relative_to(OUT).as_posix()+'\n' for p in files))
        files.append(OUT/'SHA256SUMS.txt')
        archive=ROOT/'supplementary_code.zip'
        with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
            for path in files:
                info=zipfile.ZipInfo('supplementary/'+path.relative_to(OUT).as_posix(),date_time=(2026,1,1,0,0,0))
                info.compress_type=zipfile.ZIP_DEFLATED
                info.create_system=0
                info.external_attr=0
                z.writestr(info,path.read_bytes())
        with zipfile.ZipFile(archive) as z:
            assert z.testzip() is None
            assert len(z.namelist())==len(files)
            assert not any('/.git/' in name or '__pycache__' in name for name in z.namelist())
        print(json.dumps({'archive':archive.name,'bytes':archive.stat().st_size,'files':len(files),'sha256':sha(archive)}))
