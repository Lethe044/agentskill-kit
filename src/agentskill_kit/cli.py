"""Command line interface for agentskill-kit (``askit``)."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from . import __version__, i18n, ui
from .config import (CONFIG_KEYS, DEFAULT_REGISTRY, DEFAULT_THRESHOLD, RAW_BASE, config_path, get_setting,
                     load_config, load_dotenv, set_setting)
from .i18n import t
from .skillfile import SkillError, discover_skills, load_skill, slugify

EXPORT_TARGET_CHOICES = None  # filled lazily to keep import time low


class CliError(Exception):
    pass


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _rel(path: Any) -> str:
    try:
        return os.path.relpath(str(path))
    except ValueError:
        return str(path)


def _collect(paths: Sequence[str]) -> List[Path]:
    """Resolve CLI path arguments to skill directories."""
    targets = list(paths)
    if not targets:
        targets = ["skills"] if Path("skills").is_dir() else ["."]
    found: List[Path] = []
    for p in targets:
        base = Path(p)
        if not base.exists():
            raise CliError("not found: %s" % p)
        for d in discover_skills(base):
            if d not in found:
                found.append(d)
    if not found:
        raise CliError(t("no_skills", path=", ".join(targets)))
    return found


def _threshold(args: Any) -> float:
    val = getattr(args, "threshold", None)
    if val is None:
        val = get_setting("threshold", DEFAULT_THRESHOLD)
    try:
        return float(val)
    except (TypeError, ValueError):
        return DEFAULT_THRESHOLD


def _add_llm_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--provider", help="ollama, groq, gemini, openrouter, openai, anthropic, custom or mock")
    p.add_argument("--model", help="model name (defaults depend on the provider)")
    p.add_argument("--base-url", dest="base_url", help="override the API base URL")


def _llm(args: Any):
    from .providers import ProviderError, resolve_provider
    try:
        return resolve_provider(args.provider, args.model, args.base_url)
    except ProviderError as exc:
        raise CliError(str(exc))


def _emit_json(data: Any) -> None:
    print(json.dumps(data, indent=2, ensure_ascii=False))


# ---------------------------------------------------------------------------
# commands
# ---------------------------------------------------------------------------

def cmd_init(args) -> int:
    from .scaffold import create_skill
    tags = [x.strip() for x in (args.tags or "").split(",") if x.strip()]
    try:
        dest = create_skill(args.name, Path(args.dir), args.description or "", args.script, args.author or "",
                            tags, args.force)
    except FileExistsError as exc:
        print(ui.fail(t("exists", path=_rel(exc.args[0]))))
        return 1
    print(ui.ok(t("created", path=_rel(dest))))
    print("   edit %s, then run: askit lint %s" % (_rel(dest / "SKILL.md"), _rel(dest)))
    return 0


def cmd_lint(args) -> int:
    from .lint import format_github, lint_skill
    skills = _collect(args.paths)
    results = [lint_skill(p) for p in skills]
    if args.format == "json":
        _emit_json([r.to_dict() for r in results])
    elif args.format == "github":
        for r in results:
            for line in format_github(r):
                print(line)
    else:
        print(ui.heading(t("lint_title")))
        for r in results:
            tone = "green" if not r.errors else "red"
            print("%s  %s" % (_rel(r.path), ui.paint("%s %d/100" % (t("score"), r.score), tone)))
            if not r.issues:
                print("  " + ui.ok(t("no_issues")))
            for i in r.issues:
                mark = {"error": ui.paint("error", "red", "bold"), "warning": ui.paint("warn ", "yellow"),
                        "info": ui.paint("info ", "gray")}[i.severity]
                loc = ":%d" % i.line if i.line else ""
                print("  %s %s %s%s  %s" % (mark, i.code, i.file, loc, i.message))
                if i.hint and i.severity != "info":
                    print("        " + ui.paint(i.hint, "dim"))
    errors = sum(len(r.errors) for r in results)
    warnings = sum(len(r.warnings) for r in results)
    if args.format == "text":
        print(t("summary_lint", n=len(results), e=errors, w=warnings))
    return 1 if errors or (args.strict and warnings) else 0


def cmd_scan(args) -> int:
    from .scan import exceeds, scan_skill
    skills = _collect(args.paths)
    results = [scan_skill(p) for p in skills]
    if args.format == "json":
        _emit_json([r.to_dict() for r in results])
    else:
        print(ui.heading(t("scan_title")))
        for r in results:
            tone = {"clean": "green", "review": "yellow", "risky": "red"}[r.verdict]
            print("%s  %s" % (_rel(r.path), ui.paint("%s, safety %d/100" % (r.verdict, r.safety), tone)))
            if not r.findings:
                print("  " + ui.ok(t("no_findings")))
            for f in r.findings:
                sev = {"high": ui.paint("high  ", "red", "bold"), "medium": ui.paint("medium", "yellow"),
                       "low": ui.paint("low   ", "gray")}[f.severity]
                loc = ":%d" % f.line if f.line else ""
                print("  %s %s %s%s  %s" % (sev, f.rule, f.file, loc, f.message))
                if f.snippet:
                    print("        " + ui.paint(ui.truncate(f.snippet, 90), "dim"))
        print(t("summary_scan", n=len(results), h=sum(r.count("high") for r in results),
                m=sum(r.count("medium") for r in results), l=sum(r.count("low") for r in results)))
    return 1 if any(exceeds(r, args.fail_on) for r in results) else 0


def cmd_test(args) -> int:
    from .runner import run_skill_tests
    skills = _collect(args.paths)
    reports = [run_skill_tests(p, timeout=args.timeout, allow_unsafe=args.allow_unsafe) for p in skills]
    if args.format == "json":
        _emit_json([r.to_dict() for r in reports])
    else:
        print(ui.heading(t("test_title")))
        for p, r in zip(skills, reports):
            if r.refused:
                print("%s  %s" % (_rel(p), ui.paint("refused", "red")))
                print("  " + ui.fail(r.refused))
                continue
            if not r.has_tests:
                print("%s  %s" % (_rel(p), ui.paint(t("no_tests"), "gray")))
                continue
            tone = "green" if r.passed == r.total else "red"
            print("%s  %s" % (_rel(p), ui.paint("%d/%d" % (r.passed, r.total), tone)))
            for c in r.cases:
                line = "%s [%s]" % (c.name, c.kind)
                print("  " + (ui.ok(line) if c.passed else ui.fail("%s: %s" % (line, c.detail))))
        tested = [r for r in reports if r.has_tests]
        print(t("summary_test", p=sum(r.passed for r in tested), t=sum(r.total for r in tested), n=len(tested)))
    bad = any(r.refused or (r.has_tests and r.passed < r.total) for r in reports)
    return 1 if bad else 0


def cmd_score(args) -> int:
    from .publish import check_gate
    from .scoring import evaluate_skill
    skills = _collect(args.paths)
    thr = _threshold(args)
    qualities = [evaluate_skill(p, run_tests=not args.no_tests) for p in skills]
    if args.format == "json":
        _emit_json([q.to_dict() for q in qualities])
    else:
        rows = []
        for p, q in zip(skills, qualities):
            tests = ("%d/%d" % (q.tests.passed, q.tests.total)) if q.tests and q.tests.has_tests else "-"
            reasons = check_gate(q, thr)
            rows.append((_rel(p), "%.2f" % q.score, q.grade, str(len(q.lint.errors)) + "/" + str(len(q.lint.warnings)),
                         str(q.scan.safety) if q.scan else "-", tests,
                         ui.paint("pass", "green") if not reasons else ui.paint("fail", "red")))
        print(ui.table(rows, ["skill", "score", "grade", "lint e/w", "safety", "tests", "gate"]))
        print(t("threshold_note", threshold=thr))
    return 1 if any(check_gate(q, thr) for q in qualities) else 0


def cmd_forge(args) -> int:
    from .forge import ForgeError, forge
    task = args.task or ""
    context = ""
    if args.from_file:
        fp = Path(args.from_file)
        if not fp.is_file():
            raise CliError("not found: %s" % args.from_file)
        context = fp.read_text(encoding="utf-8", errors="replace")
        if not task:
            task = "Turn the source material into a reusable skill."
    if not task.strip():
        raise CliError("give a task: askit forge --task \"summarize meeting notes into action items\"")
    llm = _llm(args)
    print(ui.info(t("forge_start", provider=llm.name, model=llm.model)))
    if not llm.is_free:
        print(ui.warn("this provider is paid; usage is billed to your account"))
    out = args.out or get_setting("output_dir") or "skills"
    thr = _threshold(args)
    rounds = args.rounds or int(get_setting("max_rounds", 3))
    try:
        res = forge(task, llm, out, thr, rounds, args.force, args.dry_run, context, args.name or "",
                    not args.no_check, log=lambda m: print(ui.info(m)))
    except ForgeError as exc:
        raise CliError(str(exc))
    q = res.quality
    if q:
        print("%s: score %.2f (%s) after %d round(s)" % (res.name, q.score, q.grade, res.rounds))
    if res.written:
        if not res.accepted:
            print(ui.warn(t("forge_below", score="%.2f" % (q.score if q else 0), threshold=thr)))
        print(ui.ok(t("forge_done", path=_rel(res.path), score="%.2f" % (q.score if q else 0))))
        print("   next: askit test %s   askit export %s --target claude" % (_rel(res.path), _rel(res.path)))
        return 0
    if res.accepted and args.dry_run:
        print(ui.ok("dry run: skill would be written to %s" % _rel(Path(out) / res.name)))
        if args.show:
            for path, content in res.files.items():
                print("\n--- %s ---\n%s" % (path, content))
        return 0
    print(ui.fail(t("forge_rejected", score="%.2f" % (q.score if q else 0), threshold=thr)))
    return 1


def cmd_eval(args) -> int:
    from .evalrun import run_evals
    skills = _collect([args.path])
    llm = _llm(args)
    rc = 0
    for p in skills:
        rep = run_evals(p, llm, args.baseline, args.limit)
        if not rep.has_evals:
            print("%s  %s" % (_rel(p), ui.paint("no evals/evals.json", "gray")))
            continue
        base = rep.baseline_passed
        extra = "" if base is None else "  without skill: %d/%d" % (base, len(rep.cases))
        print("%s  %d/%d with skill%s" % (_rel(p), rep.passed, len(rep.cases), extra))
        for c in rep.cases:
            line = c.name + ("" if c.baseline_passed is None else "  (baseline %s)" % ("pass" if c.baseline_passed else "fail"))
            print("  " + (ui.ok(line) if c.passed else ui.fail("%s: %s" % (line, c.detail))))
        if rep.passed < len(rep.cases):
            rc = 1
    return rc


def cmd_mine(args) -> int:
    from . import mine
    files = [Path(f) for f in args.file] if args.file else None
    if args.stdin:
        cmds = mine.parse_history(sys.stdin.read())
    else:
        if not files and not mine.default_history_files():
            raise CliError("no shell history found. Pass one with --file, or pipe it with --stdin")
        cmds = mine.read_history(files)
    cands = mine.find_candidates(cmds, args.min_count, args.max_len, args.limit)
    if args.format == "json":
        _emit_json([{"name": c.name, "kind": c.kind, "count": c.count, "steps": c.template,
                     "examples": c.examples, "score": round(c.score, 2)} for c in cands])
        return 0
    print(ui.info("read %d commands" % len(cmds)))
    if not cands:
        print(t("mine_none"))
        return 0
    print(t("mine_found", n=len(cands)))
    for i, c in enumerate(cands, 1):
        print("\n%s  %s  (%dx)" % (ui.paint("#%d" % i, "bold"), ui.paint(c.name, "cyan"), c.count))
        for step in c.template:
            print("     " + step)
    if args.draft or args.forge:
        n = args.draft or args.forge
        if not 1 <= n <= len(cands):
            raise CliError("pick a number between 1 and %d" % len(cands))
        cand = cands[n - 1]
        out = Path(args.out or "skills")
        if args.draft:
            files_map = mine.draft_skill_files(cand)
            dest = out / slugify(cand.name)
            if dest.exists() and not args.force:
                raise CliError(t("exists", path=_rel(dest)))
            dest.mkdir(parents=True, exist_ok=True)
            (dest / "SKILL.md").write_text(files_map["SKILL.md"], encoding="utf-8")
            print("\n" + ui.ok(t("created", path=_rel(dest))))
        else:
            from .forge import ForgeError, forge
            llm = _llm(args)
            task = ("Create a skill that automates this recurring workflow found in shell history (%d times). "
                    "Steps with placeholders:\n%s\nExample runs:\n%s" % (
                        cand.count, "\n".join(cand.template), "\n".join(cand.examples)))
            try:
                res = forge(task, llm, out, _threshold(args), 3, args.force, False, "", cand.name,
                            True, log=lambda m: print(ui.info(m)))
            except ForgeError as exc:
                raise CliError(str(exc))
            print(ui.ok(t("forge_done", path=_rel(res.path), score="%.2f" % res.quality.score)) if res.written
                  else ui.fail(t("forge_rejected", score="%.2f" % (res.quality.score if res.quality else 0),
                                 threshold=_threshold(args))))
    else:
        print("\nWrite one as a skill:  askit mine --draft 1     (no model needed)")
        print("Or let a model refine:  askit mine --forge 1")
    return 0


def cmd_export(args) -> int:
    from .export import ExportError, TARGETS, export_skill
    skills = _collect([args.path])
    targets = list(TARGETS) if args.target == "all" else [args.target]
    if args.global_ and args.target == "all":
        targets = [n for n, tg in TARGETS.items() if tg.global_]
    base = Path(args.dest) if args.dest else None
    for sk in skills:
        name = load_skill(sk).name
        for tg in targets:
            try:
                actions = export_skill(sk, tg, base, args.global_, args.dry_run)
            except ExportError as exc:
                raise CliError(str(exc))
            print(ui.ok(t("exported", name=name, target=tg)) + ("  (dry run)" if args.dry_run else ""))
            for a in actions:
                print("     " + a)
    return 0


def cmd_pack(args) -> int:
    from .publish import pack
    for sk in _collect([args.path]):
        print(ui.ok(t("packed", path=_rel(pack(sk, args.out)))))
    return 0


def cmd_publish(args) -> int:
    from .publish import PublishError, check_gate, pack, pr_commands, publish_to_registry, run_pr
    from .scoring import evaluate_skill
    skills = _collect([args.path])
    thr = _threshold(args)
    rc = 0
    for sk in skills:
        name = load_skill(sk).name
        q = evaluate_skill(sk)
        reasons = check_gate(q, thr)
        print("%s: score %.2f (%s)" % (name, q.score, q.grade))
        if reasons and not args.force:
            print(ui.fail(t("gate_failed", reason="; ".join(reasons))))
            rc = 1
            continue
        if args.registry_dir:
            try:
                info = publish_to_registry(sk, args.registry_dir, thr, args.force, args.dry_run)
            except PublishError as exc:
                raise CliError(str(exc))
            for step in info["steps"]:
                print("   " + step)
            if args.open_pr and not args.dry_run:
                ok_, msg = run_pr(name, args.registry_dir)
                print(ui.ok(msg) if ok_ else ui.fail(msg))
                rc = rc or (0 if ok_ else 1)
            else:
                print("\nOpen a pull request from the registry checkout:")
                for c in pr_commands(name):
                    print("   " + c)
        else:
            archive = pack(sk, args.out)
            print(ui.ok(t("published", name=name)))
            print(ui.ok(t("packed", path=_rel(archive))))
            print("\nShare it:")
            print("  - Push the folder to a GitHub repo, then others run: askit install github:OWNER/REPO/%s" % _rel(sk).replace("\\", "/"))
            print("  - Or add it to the community registry: fork https://github.com/Lethe044/agentskill-kit,")
            print("    then run: askit publish %s --registry-dir PATH_TO_YOUR_FORK" % _rel(sk))
    return rc


def _registry_source(args) -> str:
    return getattr(args, "registry", None) or get_setting("registry") or DEFAULT_REGISTRY


def cmd_search(args) -> int:
    from . import registry
    try:
        index = registry.load_index(_registry_source(args))
    except SkillError as exc:
        raise CliError(str(exc))
    hits = registry.search(index, " ".join(args.query), args.tag or "", args.limit)
    if args.format == "json":
        _emit_json(hits)
        return 0
    if not hits:
        print(t("no_results"))
        return 1
    rows = [(s["name"], "%s %.2f" % (s.get("grade", "?"), s.get("score", 0)),
             "yes" if s.get("tested") else "no", ui.truncate(s.get("description", ""), 70)) for s in hits]
    print(ui.table(rows, ["name", "quality", "tested", "description"]))
    print("\ninstall: askit install %s" % hits[0]["name"])
    return 0


def cmd_install(args) -> int:
    from .install import InstallError, install
    base = Path(args.dest) if args.dest else None
    try:
        res = install(args.source, args.target, base, args.global_, args.registry, args.force, args.dry_run)
    except InstallError as exc:
        raise CliError(str(exc))
    print(ui.ok(t("installed", name=res["name"], target=args.target)) + ("  (dry run)" if args.dry_run else ""))
    for a in res["actions"]:
        print("     " + a)
    for n in res["notes"]:
        print(ui.warn(n))
    return 0


def cmd_uninstall(args) -> int:
    from .install import InstallError, uninstall
    base = Path(args.dest) if args.dest else None
    try:
        done = uninstall(args.name, args.target, base, args.global_)
    except InstallError as exc:
        raise CliError(str(exc))
    if not done:
        print(ui.warn("%s was not found for target %s" % (args.name, args.target)))
        return 1
    print(ui.ok(t("uninstalled", name=args.name)))
    for d in done:
        print("     " + d)
    return 0


def cmd_list(args) -> int:
    if args.installed:
        from .install import load_ledger
        rows = [(e["name"], e.get("version", ""), e["target"], "global" if e.get("global") else "project",
                 ui.truncate(e.get("source", ""), 50)) for e in load_ledger()["installed"]]
        if not rows:
            print("nothing installed through askit yet")
            return 0
        print(ui.table(rows, ["name", "version", "target", "scope", "source"]))
        return 0
    rows = []
    for p in _collect(args.paths):
        sk = load_skill(p)
        rows.append((sk.name, sk.version, _rel(p), ui.truncate(sk.description, 60)))
    print(ui.table(rows, ["name", "version", "path", "description"]))
    return 0


def cmd_registry(args) -> int:
    from . import registry
    from .site import write_site
    roots = args.roots or (["skills"] if Path("skills").is_dir() else ["."])
    for r in roots:
        if not Path(r).exists():
            raise CliError("not found: %s" % r)
    base = Path(args.base).resolve() if getattr(args, "base", None) else Path.cwd()
    if args.reg_cmd == "build":
        index = registry.build_index(roots, base_url=args.base_url, include_body=not args.no_body,
                                     relative_to=base, run_tests=not args.no_tests)
        out = Path(args.out)
        if args.check:
            if registry.index_is_current(index, out):
                print(ui.ok("%s is up to date (%d skills)" % (_rel(out), index["count"])))
                return 0
            print(ui.fail("%s is out of date. Run: askit registry build" % _rel(out)))
            return 1
        registry.write_index(index, out)
        print(ui.ok("wrote %s (%d skills)" % (_rel(out), index["count"])))
        return 0
    index = registry.build_index(roots, base_url=args.base_url, include_body=True, relative_to=base,
                                 run_tests=not args.no_tests)
    page = write_site(index, args.out, args.title)
    print(ui.ok("wrote %s (%d skills)" % (_rel(page), index["count"])))
    return 0


def cmd_serve(args) -> int:
    from .server import default_roots, serve
    roots = [Path(p) for p in args.paths] if args.paths else default_roots()
    if not roots:
        raise CliError("no skills folders found. Pass one: askit serve ./skills")
    serve(roots, args.host, args.port, args.open, lambda url: print(ui.ok(t("serving", url=url))))
    return 0


def cmd_providers(args) -> int:
    from .providers import PROVIDERS, ProviderError, provider_status, resolve_provider
    if args.models:
        try:
            llm = resolve_provider(args.provider, None, None)
            for m in llm.list_models():
                print(m)
        except (ProviderError, OSError) as exc:
            raise CliError(str(exc))
        return 0
    rows = []
    for r in provider_status():
        cost = "free" if r["free"] else "paid"
        setup = ("set " + r["key_env"]) if r["key_env"] and r["state"] == "no key" else ""
        rows.append((r["name"], cost, r["state"], r["model"] or "(auto)", setup))
    print(ui.table(rows, ["provider", "cost", "status", "default model", "setup"]))
    print("\nFree options: ollama (local), groq, gemini, openrouter. Paid keys are optional.")
    print("Pick one with --provider NAME or: askit config set provider NAME")
    for name in ("groq", "gemini", "openrouter"):
        spec = PROVIDERS[name]
        print("  %-10s key: %s" % (name, spec.signup))
    return 0


def cmd_config(args) -> int:
    if args.action == "show":
        cfg = load_config()
        print("file: %s" % config_path())
        for k, desc in CONFIG_KEYS.items():
            print("  %-11s %-18s %s" % (k, cfg.get(k, "(not set)"), ui.paint(desc, "dim")))
        return 0
    if args.action == "path":
        print(config_path())
        return 0
    if not args.key or args.key not in CONFIG_KEYS:
        raise CliError("choose a key: " + ", ".join(CONFIG_KEYS))
    if args.action == "get":
        print(get_setting(args.key, ""))
    elif args.action == "set":
        if args.value is None:
            raise CliError("usage: askit config set KEY VALUE")
        value: Any = args.value
        if args.key in ("threshold",):
            value = float(value)
        if args.key in ("max_rounds",):
            value = int(value)
        set_setting(args.key, value)
        print(ui.ok("%s = %s" % (args.key, value)))
    else:
        set_setting(args.key, None)
        print(ui.ok("%s removed" % args.key))
    return 0


def cmd_doctor(args) -> int:
    from . import mine
    from .providers import provider_status
    print(ui.heading(t("doctor_title")))
    problems = 0

    def row(good: bool, msg: str, bad_is_problem: bool = True) -> None:
        nonlocal problems
        print("  " + (ui.ok(msg) if good else (ui.fail(msg) if bad_is_problem else ui.warn(msg))))
        if not good and bad_is_problem:
            problems += 1

    row(sys.version_info >= (3, 9), "Python %s" % sys.version.split()[0])
    row(shutil.which("git") is not None, "git %s" % ("found" if shutil.which("git") else "not found"), False)
    row(shutil.which("gh") is not None, "GitHub CLI %s (only needed for publish --open-pr)" % (
        "found" if shutil.which("gh") else "not found"), False)
    try:
        from .config import home_dir
        h = home_dir()
        row(os.access(h, os.W_OK), "data directory %s" % h)
    except OSError as exc:
        row(False, "data directory: %s" % exc)
    usable = [r for r in provider_status() if r["state"] in ("key found", "running", "configured")
              or r["state"].startswith("running")]
    row(bool(usable), "LLM providers ready: %s" % (", ".join(r["name"] for r in usable) or "none (try: askit providers)"), False)
    hist = mine.default_history_files()
    row(bool(hist), "shell history files: %d found" % len(hist), False)
    if args.online:
        from . import registry
        src = _registry_source(args)
        try:
            idx = registry.load_index(src)
            row(True, "registry reachable (%d skills)" % idx.get("count", len(idx.get("skills", []))))
        except SkillError as exc:
            row(False, str(exc))
    print("\nagentskill-kit %s" % __version__)
    return 1 if problems else 0


# ---------------------------------------------------------------------------
# parser
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    from .export import TARGETS

    p = argparse.ArgumentParser(
        prog="askit", description="Create, lint, scan, test, share and export agent skills.",
        epilog="Docs: https://github.com/Lethe044/agentskill-kit")
    p.add_argument("--version", action="version", version="agentskill-kit %s" % __version__)
    p.add_argument("--lang", choices=["en", "tr"], help="interface language")
    p.add_argument("--no-color", action="store_true", help="disable coloured output")
    sub = p.add_subparsers(dest="command", metavar="COMMAND")

    def add(name: str, func, help_: str) -> argparse.ArgumentParser:
        sp = sub.add_parser(name, help=help_, description=help_)
        sp.set_defaults(func=func)
        return sp

    sp = add("init", cmd_init, "create a new skill from a template")
    sp.add_argument("name")
    sp.add_argument("--dir", default="skills", help="parent directory (default: skills)")
    sp.add_argument("--description", "-d")
    sp.add_argument("--script", action="store_true", help="include a Python script and tests")
    sp.add_argument("--author")
    sp.add_argument("--tags", help="comma separated tags")
    sp.add_argument("--force", action="store_true")

    sp = add("lint", cmd_lint, "check SKILL.md structure (offline, no model)")
    sp.add_argument("paths", nargs="*")
    sp.add_argument("--strict", action="store_true", help="treat warnings as errors")
    sp.add_argument("--format", choices=["text", "json", "github"], default="text")

    sp = add("scan", cmd_scan, "scan skills for security red flags")
    sp.add_argument("paths", nargs="*")
    sp.add_argument("--fail-on", choices=["high", "medium", "low", "never"], default="high")
    sp.add_argument("--format", choices=["text", "json"], default="text")

    sp = add("test", cmd_test, "run the tests that ship with a skill")
    sp.add_argument("paths", nargs="*")
    sp.add_argument("--timeout", type=float, default=20.0, help="seconds per case")
    sp.add_argument("--allow-unsafe", action="store_true", help="run code even if the scanner flags it")
    sp.add_argument("--format", choices=["text", "json"], default="text")

    sp = add("score", cmd_score, "combine lint, scan and tests into a quality score")
    sp.add_argument("paths", nargs="*")
    sp.add_argument("--threshold", type=float)
    sp.add_argument("--no-tests", action="store_true")
    sp.add_argument("--format", choices=["text", "json"], default="text")

    sp = add("forge", cmd_forge, "generate a tested skill from a task description")
    sp.add_argument("--task", "-t", help="what the skill should do")
    sp.add_argument("--from-file", help="notes, transcript or runbook to learn from")
    sp.add_argument("--name", help="preferred skill name")
    sp.add_argument("--out", help="output folder (default: skills)")
    sp.add_argument("--threshold", type=float, help="minimum score to accept (default 0.8)")
    sp.add_argument("--rounds", type=int, help="maximum refinement rounds (default 3)")
    sp.add_argument("--force", action="store_true", help="write the best attempt even if it misses the threshold")
    sp.add_argument("--dry-run", action="store_true")
    sp.add_argument("--show", action="store_true", help="print the files on a dry run")
    sp.add_argument("--no-check", action="store_true", help="skip the duplicate check")
    _add_llm_args(sp)

    sp = add("eval", cmd_eval, "check how well a model follows a skill (evals/evals.json)")
    sp.add_argument("path")
    sp.add_argument("--baseline", action="store_true", help="also run without the skill for comparison")
    sp.add_argument("--limit", type=int, default=0)
    _add_llm_args(sp)

    sp = add("mine", cmd_mine, "find repeated workflows in shell history")
    sp.add_argument("--file", action="append", help="history file (repeatable)")
    sp.add_argument("--stdin", action="store_true", help="read history from standard input")
    sp.add_argument("--min-count", type=int, default=3)
    sp.add_argument("--max-len", type=int, default=4)
    sp.add_argument("--limit", type=int, default=10)
    sp.add_argument("--draft", type=int, metavar="N", help="write candidate N as a skill (no model)")
    sp.add_argument("--forge", type=int, metavar="N", help="refine candidate N with a model")
    sp.add_argument("--out", help="output folder (default: skills)")
    sp.add_argument("--force", action="store_true")
    sp.add_argument("--threshold", type=float)
    sp.add_argument("--format", choices=["text", "json"], default="text")
    _add_llm_args(sp)

    sp = add("export", cmd_export, "convert and install a skill for another agent")
    sp.add_argument("path")
    sp.add_argument("--target", "-T", default="claude", choices=list(TARGETS) + ["all"])
    sp.add_argument("--dest", help="project folder (default: current directory)")
    sp.add_argument("--global", dest="global_", action="store_true", help="install in your home directory")
    sp.add_argument("--dry-run", action="store_true")

    sp = add("pack", cmd_pack, "bundle a skill into a zip with checksums")
    sp.add_argument("path")
    sp.add_argument("--out", default="dist")

    sp = add("publish", cmd_publish, "check a skill against the quality gate and prepare it for sharing")
    sp.add_argument("path")
    sp.add_argument("--registry-dir", help="path to a checkout of a registry repository")
    sp.add_argument("--open-pr", action="store_true", help="create the pull request with git and gh")
    sp.add_argument("--threshold", type=float)
    sp.add_argument("--force", action="store_true")
    sp.add_argument("--dry-run", action="store_true")
    sp.add_argument("--out", default="dist")

    sp = add("search", cmd_search, "search the skill registry")
    sp.add_argument("query", nargs="*")
    sp.add_argument("--tag")
    sp.add_argument("--limit", type=int, default=15)
    sp.add_argument("--registry", help="registry index URL or file")
    sp.add_argument("--format", choices=["text", "json"], default="text")

    sp = add("install", cmd_install, "install a skill from the registry, GitHub or a folder")
    sp.add_argument("source", help="registry name, ./folder or github:owner/repo/path[@ref]")
    sp.add_argument("--target", "-T", default="claude", choices=list(TARGETS))
    sp.add_argument("--dest", help="project folder (default: current directory)")
    sp.add_argument("--global", dest="global_", action="store_true")
    sp.add_argument("--registry", help="registry index URL or file")
    sp.add_argument("--force", action="store_true", help="install even if lint or scan fail")
    sp.add_argument("--dry-run", action="store_true")

    sp = add("uninstall", cmd_uninstall, "remove an installed skill")
    sp.add_argument("name")
    sp.add_argument("--target", "-T", default="claude", choices=list(TARGETS))
    sp.add_argument("--dest")
    sp.add_argument("--global", dest="global_", action="store_true")

    sp = add("list", cmd_list, "list local skills or what askit installed")
    sp.add_argument("paths", nargs="*")
    sp.add_argument("--installed", action="store_true")

    sp = add("registry", cmd_registry, "build a registry index or a static website")
    rsub = sp.add_subparsers(dest="reg_cmd", metavar="build|site", required=True)
    rb = rsub.add_parser("build", help="write registry/index.json")
    rb.add_argument("roots", nargs="*")
    rb.add_argument("--out", default="registry/index.json")
    rb.add_argument("--base-url", default=RAW_BASE)
    rb.add_argument("--base", help="folder the skill paths are relative to (default: current directory)")
    rb.add_argument("--check", action="store_true", help="exit 1 if the index is out of date")
    rb.add_argument("--no-body", action="store_true")
    rb.add_argument("--no-tests", action="store_true", help="skip running tests while scoring")
    rs = rsub.add_parser("site", help="write a searchable static website")
    rs.add_argument("roots", nargs="*")
    rs.add_argument("--out", default="site")
    rs.add_argument("--title", default="agentskill-kit skill registry")
    rs.add_argument("--base-url", default=RAW_BASE)
    rs.add_argument("--base")
    rs.add_argument("--no-tests", action="store_true")
    sp.set_defaults(func=cmd_registry)

    sp = add("serve", cmd_serve, "browse local skills in your browser")
    sp.add_argument("paths", nargs="*")
    sp.add_argument("--host", default="127.0.0.1")
    sp.add_argument("--port", type=int, default=8765)
    sp.add_argument("--open", action="store_true", help="open the browser")

    sp = add("providers", cmd_providers, "show LLM providers and what is ready")
    sp.add_argument("--models", action="store_true", help="list models of --provider")
    sp.add_argument("--provider")

    sp = add("config", cmd_config, "show or change default settings")
    sp.add_argument("action", choices=["show", "get", "set", "unset", "path"])
    sp.add_argument("key", nargs="?")
    sp.add_argument("value", nargs="?")

    sp = add("doctor", cmd_doctor, "check your environment")
    sp.add_argument("--online", action="store_true", help="also check the registry")
    sp.add_argument("--registry")
    return p


def main(argv: Optional[Sequence[str]] = None) -> int:
    ui.setup_stdio()
    load_dotenv()
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.no_color:
        ui.set_no_color(True)
    i18n.set_lang(args.lang or get_setting("lang") or i18n.detect_lang())
    if not getattr(args, "command", None):
        parser.print_help()
        return 0
    try:
        return int(args.func(args) or 0)
    except CliError as exc:
        print(ui.fail(str(exc)), file=sys.stderr)
        return 1
    except SkillError as exc:
        print(ui.fail(str(exc)), file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("", file=sys.stderr)
        return 130
    except BrokenPipeError:
        return 0


if __name__ == "__main__":
    sys.exit(main())
