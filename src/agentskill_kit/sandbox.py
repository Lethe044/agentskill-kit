"""Run untrusted skill scripts in a throwaway working directory.

This limits accidents (runaway loops, huge output, stray writes, leaked API
keys in the environment). It is not a security boundary: a hostile script can
still do anything the current user can. The scanner refuses obviously
dangerous code before it is run, and you should use containers for real
isolation when testing skills you do not trust.
"""

from __future__ import annotations

import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterator, List, Optional

MAX_OUTPUT = 20_000
_PASS_ENV = ("PATH", "SYSTEMROOT", "SystemRoot", "COMSPEC", "PATHEXT", "LANG", "LC_ALL", "TZ")


@dataclass
class RunResult:
    exit_code: int
    stdout: str
    stderr: str
    timed_out: bool = False
    duration: float = 0.0
    error: str = ""


def clean_env(workdir: Path, extra: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    env = {k: os.environ[k] for k in _PASS_ENV if k in os.environ}
    env.update({
        "HOME": str(workdir), "USERPROFILE": str(workdir),
        "TEMP": str(workdir), "TMP": str(workdir), "TMPDIR": str(workdir),
        "PYTHONIOENCODING": "utf-8", "PYTHONDONTWRITEBYTECODE": "1", "PYTHONUTF8": "1",
        "NO_COLOR": "1",
    })
    if extra:
        env.update(extra)
    return env


def _limit_resources(timeout: float, mem_mb: int):
    def apply() -> None:
        try:
            import resource
            os.setsid()
            resource.setrlimit(resource.RLIMIT_CPU, (int(timeout) + 2, int(timeout) + 2))
            resource.setrlimit(resource.RLIMIT_FSIZE, (50 * 1024 * 1024, 50 * 1024 * 1024))
            resource.setrlimit(resource.RLIMIT_NOFILE, (256, 256))
            if sys.platform.startswith("linux"):
                limit = mem_mb * 1024 * 1024
                resource.setrlimit(resource.RLIMIT_AS, (limit, limit))
        except Exception:
            pass
    return apply


def _trim(text: str) -> str:
    return text if len(text) <= MAX_OUTPUT else text[:MAX_OUTPUT] + "\n...[output truncated]"


def run_python(args: List[str], cwd: Path, stdin: str = "", timeout: float = 20.0,
               extra_env: Optional[Dict[str, str]] = None, mem_mb: int = 768) -> RunResult:
    """Run `python <args>` inside cwd with a clean environment."""
    cmd = [sys.executable, "-B"] + list(args)
    start = time.time()
    kwargs: Dict[str, object] = {}
    if os.name == "nt":
        kwargs["creationflags"] = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    else:
        kwargs["preexec_fn"] = _limit_resources(timeout, mem_mb)
    try:
        proc = subprocess.Popen(
            cmd, cwd=str(cwd), env=clean_env(cwd, extra_env), stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kwargs)  # type: ignore[arg-type]
    except OSError as exc:
        return RunResult(-1, "", "", error=str(exc))
    try:
        out, err = proc.communicate(stdin.encode("utf-8"), timeout=timeout)
        timed_out = False
    except subprocess.TimeoutExpired:
        timed_out = True
        try:
            if os.name == "nt":
                proc.kill()
            else:
                os.killpg(proc.pid, signal.SIGKILL)
        except Exception:
            proc.kill()
        out, err = proc.communicate()
    return RunResult(
        exit_code=-1 if timed_out else proc.returncode,
        stdout=_trim(out.decode("utf-8", errors="replace")),
        stderr=_trim(err.decode("utf-8", errors="replace")),
        timed_out=timed_out, duration=time.time() - start)


@contextmanager
def scratch_copy(skill_dir: Path) -> Iterator[Path]:
    """Copy a skill into a temp directory so tests never touch the original."""
    tmp = Path(tempfile.mkdtemp(prefix="askit-"))
    target = tmp / skill_dir.name
    try:
        shutil.copytree(skill_dir, target, ignore=shutil.ignore_patterns("__pycache__", ".git", "*.pyc"))
        yield target
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
