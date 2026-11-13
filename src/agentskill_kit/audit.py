"""Check the skills that are already installed on this machine."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .lint import LintResult, lint_skill
from .scan import ScanResult, exceeds, scan_skill
from .skillfile import discover_skills


@dataclass
class AuditEntry:
    location: str
    path: Path
    lint: LintResult
    scan: ScanResult

    def to_dict(self) -> Dict[str, Any]:
        return {"location": self.location, "path": str(self.path), "name": self.lint.skill,
                "lint_errors": len(self.lint.errors), "lint_warnings": len(self.lint.warnings),
                "verdict": self.scan.verdict, "safety": self.scan.safety,
                "findings": [f.to_dict() for f in self.scan.findings],
                "issues": [i.to_dict() for i in self.lint.issues if i.severity != "info"]}


@dataclass
class AuditReport:
    entries: List[AuditEntry] = field(default_factory=list)
    scanned_locations: List[str] = field(default_factory=list)

    def failing(self, fail_on: str) -> List[AuditEntry]:
        return [e for e in self.entries if exceeds(e.scan, fail_on)]

    def to_dict(self) -> Dict[str, Any]:
        return {"locations": self.scanned_locations, "skills": [e.to_dict() for e in self.entries]}


def default_locations(cwd: Optional[Path] = None, home: Optional[Path] = None) -> List[Tuple[str, Path]]:
    """Folders where agents keep skills, for the current project and for the user."""
    cwd = Path(cwd) if cwd else Path.cwd()
    home = Path(home) if home else Path.home()
    cands = [
        ("project claude", cwd / ".claude" / "skills"),
        ("project hermes", cwd / ".hermes" / "skills"),
        ("project bundle", cwd / ".agent-skills"),
        ("user claude", home / ".claude" / "skills"),
        ("user hermes", home / ".hermes" / "skills"),
    ]
    out: List[Tuple[str, Path]] = []
    seen = set()
    for label, path in cands:
        if path.is_dir():
            key = str(path.resolve())
            if key not in seen:
                seen.add(key)
                out.append((label, path))
    return out


def run_audit(locations: List[Tuple[str, Path]]) -> AuditReport:
    report = AuditReport(scanned_locations=[str(p) for _, p in locations])
    seen = set()
    for label, root in locations:
        for d in discover_skills(root):
            key = str(d.resolve())
            if key in seen:
                continue
            seen.add(key)
            report.entries.append(AuditEntry(label, d, lint_skill(d), scan_skill(d)))
    return report
