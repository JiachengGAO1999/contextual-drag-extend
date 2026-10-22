"""One-time, explicitly authorized cleanup of four gaojc pip HTTP caches only."""
import argparse
import datetime
import json
import os
from pathlib import Path
import re
import shutil
import socket
import stat
import subprocess

TARGETS = (
    '/data/gaojc/pip-cache/http-v2',
    '/data/gaojc/cache/pip/http-v2',
    '/data/gaojc/tmp/pip-cache/http-v2',
    '/home/gaojc/.cache/pip/http-v2',
)
PROJECT = Path('/data/gaojc/projects/contextual-drag-extend-game24-100q')
REPORT = PROJECT/'outputs/game24-100q-8b-20261015/pip_http_cleanup_20261016.json'


def inspect_target(name):
    p = Path(name)
    if name not in TARGETS or p.resolve(strict=True) != p or not p.is_dir():
        raise RuntimeError('Target must be an exact, non-symlink authorized HTTP cache')
    root_stat = p.lstat()
    if root_stat.st_uid != 1018:
        raise RuntimeError('Unexpected cache owner')
    files = allocated = 0
    for folder, dirs, names in os.walk(p, followlinks=False):
        for child in dirs:
            q = Path(folder)/child
            if q.is_symlink() or q.lstat().st_uid != 1018:
                raise RuntimeError('Unexpected cache directory owner or symlink')
        for child in names:
            q = Path(folder)/child
            s = q.lstat()
            if not stat.S_ISREG(s.st_mode) or s.st_uid != 1018 or s.st_nlink != 1:
                raise RuntimeError('Cache file is non-regular, shared or owned by another user')
            files += 1
            allocated += s.st_blocks*512
    return dict(path=name, files=files, allocated_bytes=allocated)


def save(report):
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    temp = REPORT.with_suffix('.json.tmp')
    with temp.open('w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
        f.write('\n')
        f.flush()
        os.fsync(f.fileno())
    os.replace(temp, REPORT)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    args = ap.parse_args()
    if socket.gethostname() != '10-7-130-17' or os.getuid() != 1018:
        raise RuntimeError('This one-time cleanup is limited to gaojc on the verified A800 host')
    processes = subprocess.check_output(['ps', '-u', 'gaojc', '-o', 'pid=,args='], text=True)
    for line in processes.splitlines():
        if re.search(r'(^|[ /\t])(pip|pip3|uv|mamba|micromamba|conda)([ \t]|$)', line):
            raise RuntimeError('A package tool is running; cache cleanup deferred')
    targets = [inspect_target(name) for name in TARGETS]
    report = dict(authorized_by='2026-10-16 user explicitly requested direct deletion without archiving download caches',
                  started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  mode='apply' if args.apply else 'inspect_only', targets=targets,
                  before_free_bytes={p: shutil.disk_usage(p).free for p in ('/', '/data')},
                  deleted=[], installation_packages_archived=False,
                  preserved=['pip wheels caches', 'installed environments', 'model checkpoints', 'research data and logs'])
    if not args.apply:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return
    if REPORT.exists():
        raise RuntimeError('A cleanup report already exists; this script is one-time')
    save(report)
    try:
        for item in targets:
            p = Path(item['path'])
            inspect_target(str(p))
            shutil.rmtree(p)
            p.mkdir(mode=0o755)
            report['deleted'].append(item)
            save(report)
        report.update(state='completed', after_free_bytes={p: shutil.disk_usage(p).free for p in ('/', '/data')},
                      finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
        save(report)
    except BaseException as exc:
        report.update(state='failed_or_partial', error=str(exc))
        save(report)
        raise
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
