"""Verify and unpack the existing A100 packages into a project-local A800 overlay."""
import hashlib
import importlib.metadata
import json
from pathlib import Path, PurePosixPath
import shutil
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT/"outputs/game24-replication-qwen3-8b-heldout82-20261019"
RUNTIME = BASE/"runtime"


def main():
    archive = RUNTIME/"runtime.tar.gz"
    manifest = json.loads((RUNTIME/"runtime_manifest.json").read_text())
    assert hashlib.sha256(archive.read_bytes()).hexdigest()==manifest["archive_sha256"]
    assert shutil.disk_usage(RUNTIME).free > sum(r["bytes"] for r in manifest["files"])+2*1024**3
    expected = {r["path"]: r for r in manifest["files"]}
    with tarfile.open(archive,"r:gz") as tar:
        members = tar.getmembers()
        assert {m.name for m in members}==set(expected)
        for member in members:
            parts = PurePosixPath(member.name)
            assert not parts.is_absolute() and ".." not in parts.parts and member.isfile()
            destination = RUNTIME/member.name
            assert destination.resolve().is_relative_to(RUNTIME.resolve())
            if destination.exists():
                assert hashlib.sha256(destination.read_bytes()).hexdigest()==expected[member.name]["sha256"]
                continue
            destination.parent.mkdir(parents=True,exist_ok=True)
            with tar.extractfile(member) as source, destination.open("xb") as output:
                shutil.copyfileobj(source,output)
            assert hashlib.sha256(destination.read_bytes()).hexdigest()==expected[member.name]["sha256"]
    model = RUNTIME/"model"
    model.mkdir(exist_ok=True)
    shared = Path("/data/gaojc/shared/models/Qwen3-8B")
    index = "model.safetensors.index.json"
    assert (shared/index).read_bytes()==(RUNTIME/"model_metadata"/index).read_bytes(), "Checkpoint index drift"
    for source in (RUNTIME/"model_metadata").iterdir():
        target = model/source.name
        if target.exists(): assert target.read_bytes()==source.read_bytes()
        else: target.write_bytes(source.read_bytes())
    weights = sorted(set(json.loads((model/index).read_text())["weight_map"].values()))
    for name in weights:
        assert (shared/name).is_file()
        target = model/name
        if target.is_symlink(): assert target.resolve()==(shared/name).resolve()
        else: target.symlink_to(shared/name)
    profile = dict(host="sjtu-a800",gpu_index=4,gpu_uuid="GPU-9d164491-5abf-96eb-3d3f-e08e77deb8f7",
        python=str(ROOT/".venv/bin/python"),overlay=str(RUNTIME/"overlay"),reference=str(RUNTIME/"reference"),
        model=str(model),expected_versions={"vllm":"0.11.0","torch":"2.8.0","transformers":"4.55.4",
        "tokenizers":"0.21.4","xformers":"0.0.32.post1","xgrammar":"0.1.25"},
        sampler="PyTorch-native; VLLM_USE_FLASHINFER_SAMPLER=0 as in development fallback",
        package_archive_sha256=manifest["archive_sha256"],package_files_verified=len(expected),
        source_model_config_sha256=hashlib.sha256((model/"config.json").read_bytes()).hexdigest(),
        local_weight_files=[dict(path=str(shared/name),bytes=(shared/name).stat().st_size) for name in weights],
        boundary="A800 hardware differs from development A100. Exact model metadata/index and all migrated package hashes verified; weight bytes not fully hashed. No shared package/model file modified.")
    target = BASE/"runtime_profile.json"
    assert not target.exists() or json.loads(target.read_text())==profile
    target.write_text(json.dumps(profile,indent=2)+"\n")
    sys.path.insert(0,str(RUNTIME/"overlay"))
    for name,version in profile["expected_versions"].items():
        assert importlib.metadata.version(name)==version,(name,importlib.metadata.version(name))
    from packaging.requirements import Requirement
    discrepancies = []
    for text in importlib.metadata.requires("vllm"):
        req = Requirement(text)
        if req.marker and not req.marker.evaluate(): continue
        try:
            version = importlib.metadata.version(req.name)
            if req.specifier and not req.specifier.contains(version,prereleases=True):
                discrepancies.append(dict(requirement=text,installed=version))
        except importlib.metadata.PackageNotFoundError:
            discrepancies.append(dict(requirement=text,installed=None))
    report = dict(verified_package_files=len(expected),requirements_discrepancies=discrepancies,
        available_gib=shutil.disk_usage(BASE).free/1024**3,profile=profile)
    (BASE/"runtime_staging.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(dict(verified_package_files=len(expected),requirements_discrepancies=discrepancies,
                         available_gib=report["available_gib"])))
    if discrepancies: raise RuntimeError("Resolve pinned runtime requirements before GPU launch")


if __name__=="__main__": main()
