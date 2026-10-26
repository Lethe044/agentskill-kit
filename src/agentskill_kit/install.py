"""Install skills from a registry, a GitHub repository or a local folder.

Every download is verified against the checksums in the registry index (when
there is one) and is linted and scanned before it is placed anywhere.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import tempfile
import urllib.parse
import urllib.request
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from . import registry
from .config import DEFAULT_REGISTRY, get_setting, ledger_path
from .export import ExportError, export_skill, remove_skill
from .lint import lint_skill
from .scan import scan_skill
from .skillfile import SkillError, load_skill


class InstallError(Exception):
    pass


def _safe_rel(rel: str) -> bool:
    p = Path(rel)
    return bool(rel) and not p.is_absolute() and ".." not in p.parts and not re.match(r"^[A-Za-z]:", rel)


def load_ledger() -> Dict[str, Any]:
    p = ledger_path()
    if not p.exists():
        return {"installed": []}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        data.setdefault("installed", [])
        return data
    except (OSError, ValueError):
        return {"installed": []}


def save_ledger(data: Dict[str, Any]) -> None:
    ledger_path().write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _github_get(url: str) -> Any:
    headers = {"User-Agent": registry.USER_AGENT, "Accept": "application/vnd.github+json"}
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def parse_github_ref(spec: str) -> Tuple[str, str, str, str]:
    """github:owner/repo/path/to/skill@ref -> (owner, repo, path, ref)."""
    body = spec[len("github:"):] if spec.startswith("github:") else spec
    body = re.sub(r"^https?://github\.com/", "", body)
    ref = ""
    if "@" in body:
        body, ref = body.rsplit("@", 1)
    m = re.match(r"^([\w.-]+)/([\w.-]+)(?:/(?:tree/[^/]+/)?(.*))?$", body)
    if not m:
        raise InstallError("expected github:owner/repo[/path][@ref], got %r" % spec)
    return m.group(1), m.group(2), (m.group(3) or "").strip("/"), ref


def _download_github(spec: str, dest: Path) -> str:
    owner, repo, path, ref = parse_github_ref(spec)
    api = "https://api.github.com/repos/%s/%s/contents/%s" % (owner, repo, urllib.parse.quote(path))
    if ref:
        api += "?ref=" + urllib.parse.quote(ref)

    def walk(url: str, target: Path, depth: int = 0) -> None:
        if depth > 5:
            return
        data = _github_get(url)
        if isinstance(data, dict):
            data = [data]
        for item in data:
            name = item.get("name", "")
            if not _safe_rel(name):
                continue
            if item.get("type") == "dir":
                walk(item["url"], target / name, depth + 1)
            elif item.get("type") == "file" and item.get("download_url"):
                if item.get("size", 0) > 2_000_000:
                    continue
                target.mkdir(parents=True, exist_ok=True)
                (target / name).write_bytes(registry.fetch_bytes(item["download_url"]))

    walk(api, dest)
    return "github:%s/%s/%s" % (owner, repo, path)


def _download_registry(entry: Dict[str, Any], index: Dict[str, Any], source: str, dest: Path) -> None:
    base = index.get("base_url") or ""
    is_remote = bool(re.match(r"^[a-z][a-z0-9+.-]*://", source, re.I))
    local_root = None if is_remote else Path(source).expanduser().resolve().parent.parent
    for f in entry.get("files", []):
        rel = f["path"]
        if not _safe_rel(rel) or not _safe_rel(entry["path"]):
            raise InstallError("registry lists an unsafe file path: %s" % rel)
        candidate = (local_root / entry["path"] / rel) if local_root else None
        if candidate is not None and candidate.is_file():
            data = candidate.read_bytes()
        elif base.startswith("http"):
            data = registry.fetch_bytes(base.rstrip("/") + "/" + entry["path"].strip("/") + "/" + rel)
        else:
            raise InstallError("cannot locate %s (registry has no usable base_url)" % rel)
        digest = hashlib.sha256(data).hexdigest()
        if f.get("sha256") and digest != f["sha256"]:
            raise InstallError("checksum mismatch for %s (expected %s, got %s)" % (rel, f["sha256"][:12], digest[:12]))
        out = dest / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(data)


def vet(path: Path) -> Tuple[List[str], List[str]]:
    """Return (blocking_reasons, warnings) for a downloaded skill."""
    blocking: List[str] = []
    notes: List[str] = []
    lint = lint_skill(path)
    if lint.errors:
        blocking.append("lint errors: " + "; ".join("[%s] %s" % (i.code, i.message) for i in lint.errors[:3]))
    scan = scan_skill(path)
    if scan.count("high"):
        blocking.append("security scan found %d high severity issue(s): %s" % (
            scan.count("high"), ", ".join(sorted({f.rule for f in scan.findings if f.severity == "high"}))))
    if scan.count("medium"):
        notes.append("%d medium severity finding(s); run: askit scan %s" % (scan.count("medium"), path.name))
    return blocking, notes


def install(source: str, target: str = "claude", base: Optional[Path] = None, global_: bool = False,
            registry_url: Optional[str] = None, force: bool = False, dry_run: bool = False) -> Dict[str, Any]:
    """Install a skill. `source` is a registry name, a local path or github:owner/repo/path."""
    tmp = Path(tempfile.mkdtemp(prefix="askit-install-"))
    try:
        origin = ""
        version = ""
        if source.startswith("github:") or source.startswith("https://github.com/"):
            staged = tmp / "skill"
            origin = _download_github(source, staged)
            if not (staged / "SKILL.md").exists():
                subs = [d for d in staged.iterdir() if d.is_dir() and (d / "SKILL.md").exists()] if staged.exists() else []
                if len(subs) == 1:
                    staged = subs[0]
                else:
                    raise InstallError("no SKILL.md found at %s" % source)
        elif Path(source).expanduser().exists():
            src = Path(source).expanduser().resolve()
            staged = tmp / src.name
            shutil.copytree(src, staged, ignore=shutil.ignore_patterns("__pycache__", ".git", "*.pyc"))
            origin = "local:%s" % src
        else:
            reg = registry_url or get_setting("registry") or DEFAULT_REGISTRY
            index = registry.load_index(reg)
            entry = registry.find(index, source)
            if not entry:
                close = [s["name"] for s in registry.search(index, source, limit=3)]
                hint = (" Did you mean: %s?" % ", ".join(close)) if close else ""
                raise InstallError("skill %r not found in %s.%s" % (source, reg, hint))
            staged = tmp / entry["name"]
            _download_registry(entry, index, reg, staged)
            origin = "registry:%s" % reg
            version = entry.get("version", "")

        try:
            skill = load_skill(staged)
        except SkillError as exc:
            raise InstallError(str(exc))
        blocking, notes = vet(staged)
        if blocking and not force:
            raise InstallError("refusing to install %s: %s (use --force to override)" % (skill.name, " | ".join(blocking)))
        if blocking:
            notes.append("installed despite: " + " | ".join(blocking))
        actions = export_skill(staged, target, base, global_, dry_run=dry_run)
        if not dry_run:
            ledger = load_ledger()
            ledger["installed"] = [e for e in ledger["installed"]
                                   if not (e["name"] == skill.name and e["target"] == target and e.get("global") == global_
                                           and e.get("base") == str(base or Path.cwd()))]
            ledger["installed"].append({"name": skill.name, "version": version or skill.version, "source": origin,
                                        "target": target, "global": global_, "base": str(base or Path.cwd())})
            save_ledger(ledger)
        return {"name": skill.name, "version": version or skill.version, "target": target, "actions": actions,
                "notes": notes, "source": origin}
    except (ExportError, OSError, ValueError) as exc:
        raise InstallError(str(exc))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def uninstall(name: str, target: str = "claude", base: Optional[Path] = None, global_: bool = False) -> List[str]:
    try:
        done = remove_skill(name, target, base, global_)
    except ExportError as exc:
        raise InstallError(str(exc))
    ledger = load_ledger()
    ledger["installed"] = [e for e in ledger["installed"] if not (
        e["name"] == name and e["target"] == target and e.get("global") == global_)]
    save_ledger(ledger)
    return done
