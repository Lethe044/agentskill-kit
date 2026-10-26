"""Heuristic security scanner for skills.

Skills are instructions that an agent follows, often with shell access, so a
malicious or careless skill can do real damage. This scanner looks for common
red flags: prompt injection phrasing, hidden unicode, dangerous shell
patterns, embedded secrets and signs of credential exfiltration. It is a
heuristic filter, not a guarantee. Review skills from sources you do not trust.

Silence a deliberate match by adding ``askit-ignore`` (optionally followed by
rule ids, e.g. ``askit-ignore: SC103``) on the same line.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Pattern

from .skillfile import SkillError, iter_skill_files

SEVERITY_WEIGHT = {"high": 40, "medium": 15, "low": 3}
SEVERITY_RANK = {"high": 3, "medium": 2, "low": 1}
MAX_FILE_BYTES = 2_000_000
BINARY_SUFFIXES = {".exe", ".dll", ".so", ".dylib", ".bin", ".jar", ".msi", ".dmg", ".app",
                   ".class", ".o", ".a", ".whl", ".pyd"}
CODE_SUFFIXES = {".py", ".js", ".ts", ".mjs", ".cjs", ".sh", ".bash", ".zsh", ".ps1", ".rb", ".pl",
                 ".php", ".bat", ".cmd"}


@dataclass
class Rule:
    id: str
    severity: str
    title: str
    pattern: Pattern[str]
    code_only: bool = False
    accept: Optional[Callable[[str], bool]] = None


def _r(pattern: str, flags: int = re.I) -> Pattern[str]:
    return re.compile(pattern, flags)


def _is_placeholder(text: str) -> bool:
    low = text.lower()
    return any(w in low for w in ("example", "your", "xxxx", "changeme", "placeholder", "dummy",
                                  "sample", "<", "redacted", "0000", "1234", "abcd"))


def _public_ip(text: str) -> bool:
    m = re.search(r"(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})", text)
    if not m:
        return False
    a, b = int(m.group(1)), int(m.group(2))
    if a in (0, 10, 127) or (a == 192 and b == 168) or (a == 172 and 16 <= b <= 31) or (a == 169 and b == 254):
        return False
    return True


SECRET_PATTERNS: List[Pattern[str]] = [
    _r(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b", 0),
    _r(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b", 0),
    _r(r"\bgithub_pat_[A-Za-z0-9_]{50,}\b", 0),
    _r(r"\bsk-ant-[A-Za-z0-9_-]{20,}", 0),
    _r(r"\bsk-or-v1-[A-Za-z0-9]{20,}", 0),
    _r(r"\bsk-proj-[A-Za-z0-9_-]{20,}", 0),
    _r(r"\bsk-[A-Za-z0-9]{32,}\b", 0),
    _r(r"\bgsk_[A-Za-z0-9]{40,}\b", 0),
    _r(r"\bAIza[0-9A-Za-z_-]{35}\b", 0),
    _r(r"\bxox[abprs]-[A-Za-z0-9-]{10,}", 0),
    _r(r"\bnpm_[A-Za-z0-9]{36}\b", 0),
    _r(r"\bpypi-AgEIcHlwaS5vcmc[A-Za-z0-9_-]{20,}", 0),
]

RULES: List[Rule] = [
    # Prompt injection and hidden instructions
    Rule("SC001", "high", "Instruction override phrasing",
         _r(r"\bignore\s+(?:all\s+|any\s+|the\s+)*(?:previous|prior|above|earlier|preceding)\s+"
            r"(?:instructions?|prompts?|rules|messages|directions)")),
    Rule("SC002", "high", "Attempt to discard system rules",
         _r(r"\bdisregard\s+(?:all\s+|any\s+)*(?:your|the|previous|prior)\s+(?:system\s+)?"
            r"(?:prompt|instructions?|rules|guidelines)")),
    Rule("SC003", "high", "Instruction to hide actions from the user",
         _r(r"\b(?:do\s+not|don't|never)\s+(?:tell|inform|mention|reveal|show|notify)\s+(?:this\s+)?(?:to\s+)?the\s+user\b"
            r"|\bwithout\s+(?:telling|informing|notifying|alerting)\s+the\s+user\b"
            r"|\bhide\s+(?:this|it)\s+from\s+the\s+user\b")),
    Rule("SC004", "medium", "Jailbreak style phrasing",
         _r(r"\b(?:developer\s+mode|jailbreak(?:ed)?|do\s+anything\s+now|you\s+are\s+now\s+(?:in\s+)?"
            r"(?:a\s+|an\s+)?(?:unrestricted|unfiltered|dan)\b)")),
    Rule("SC005", "medium", "Asks the agent to reveal its hidden prompt",
         _r(r"\b(?:reveal|print|output|repeat|leak|dump)\s+(?:your|the)\s+(?:system\s+prompt|"
            r"hidden\s+instructions|initial\s+instructions)")),
    Rule("SC006", "high", "Invisible or bidirectional unicode characters",
         re.compile("[\u200b-\u200f\u202a-\u202e\u2060-\u2064\u2066-\u2069\U000e0000-\U000e007f]")),
    Rule("SC007", "medium", "Instruction hidden inside an HTML comment",
         _r(r"<!--(?:(?!-->).){0,400}?\b(?:ignore|you\s+must|always\s+run|execute|exfiltrate|send\s+the)\b"
            r"(?:(?!-->).){0,400}?-->", re.I | re.S)),
    # Dangerous commands
    Rule("SC101", "high", "Downloads and pipes straight into a shell",
         _r(r"\b(?:curl|wget)\b[^\n|;]*\|\s*(?:sudo\s+)?(?:ba|z|da|k)?sh\b"
            r"|\b(?:iwr|irm|invoke-webrequest|invoke-restmethod)\b[^\n|]*\|\s*(?:iex|invoke-expression)\b")),
    Rule("SC102", "high", "Recursive delete of a broad path",
         _r(r"\brm\s+-(?:[a-z]*r[a-z]*f|[a-z]*f[a-z]*r)[a-z]*\s+(?:--no-preserve-root\s+)?"
            r"(?:/|~|\$HOME|\$\{HOME\}|\*)(?:\s|$|/)")),
    Rule("SC103", "medium", "Uses sudo or elevated privileges",
         _r(r"(?:^|[;&|(`$]|\b(?:run|then|and|exec)\b)[ \t]*sudo[ \t]+[a-z-]", re.I | re.M)),
    Rule("SC104", "medium", "World-writable permissions", _r(r"\bchmod\s+(?:-R\s+)?(?:777|a\+rwx|0777)\b")),
    Rule("SC105", "high", "Decodes and runs obfuscated payload",
         _r(r"\bbase64\s+(?:-d|--decode)\b[^\n|]*\|\s*(?:ba|z)?sh\b"
            r"|\b(?:powershell|pwsh)\b[^\n]*\s-e(?:nc|ncodedcommand)?\s+[A-Za-z0-9+/=]{20,}")),
    Rule("SC106", "high", "Reverse shell pattern",
         _r(r"/dev/tcp/|\bnc(?:at)?\s+(?:-[a-z]*e|-c)\b|\bbash\s+-i\s*>&|\bmkfifo\b[^\n]*\bnc\b")),
    Rule("SC107", "medium", "Dynamic code execution (eval/exec)",
         _r(r"\b(?:eval|exec)\s*\("), code_only=True),
    Rule("SC108", "low", "Shell execution from code",
         _r(r"\bos\.system\s*\(|\bshell\s*=\s*True\b|\bchild_process\.exec\s*\("), code_only=True),
    Rule("SC109", "high", "Destructive disk or fork bomb command",
         _r(r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;\s*:|\bdd\s+if=\S+\s+of=/dev/(?:sd|nvme|disk|hd)|\bmkfs\.\w+\s+/dev/")),
    Rule("SC110", "low", "Force push or hard reset",
         _r(r"\bgit\s+push\s+(?:[^\n]*\s)?(?:-f|--force)\b|\bgit\s+reset\s+--hard\b")),
    Rule("SC111", "medium", "Installs a package from an arbitrary URL",
         _r(r"\bpip3?\s+install\s+(?:-[A-Za-z-]+\s+)*(?:https?://|git\+)")),
    # Secrets
    Rule("SC201", "high", "AWS access key", SECRET_PATTERNS[0]),
    Rule("SC202", "high", "GitHub token", _r(SECRET_PATTERNS[1].pattern + "|" + SECRET_PATTERNS[2].pattern, 0)),
    Rule("SC203", "high", "LLM or cloud API key",
         _r("|".join(p.pattern for p in SECRET_PATTERNS[3:9]), 0)),
    Rule("SC204", "high", "Slack, npm or PyPI token", _r("|".join(p.pattern for p in SECRET_PATTERNS[9:]), 0)),
    Rule("SC205", "high", "Private key material",
         _r(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP )?PRIVATE KEY-----", 0)),
    Rule("SC206", "medium", "Hardcoded credential assignment",
         _r(r"\b(?:api[_-]?key|secret|token|passwd|password)\b[\"']?\s*[:=]\s*[\"'][A-Za-z0-9/+_\-]{16,}[\"']"),
         accept=lambda s: not _is_placeholder(s)),
    # Credential access and exfiltration
    Rule("SC301", "medium", "Reads credential files or keys",
         _r(r"(?:~|\$HOME|%USERPROFILE%|/home/\w+)[/\\]\.(?:ssh|aws|gnupg|kube|docker[/\\]config\.json)\b"
            r"|/etc/(?:shadow|sudoers)\b|\bid_rsa\b|\.netrc\b|\bcredentials\.json\b")),
    Rule("SC302", "low", "Sends data over the network",
         _r(r"\brequests\.(?:post|put|patch)\s*\(|\burllib\.request\.urlopen\s*\(|\bhttp\.client\.\w+\s*\("
            r"|\bcurl\b[^\n]*\s(?:-d|--data\S*|-F|-T|--upload-file)\b|\bfetch\s*\(\s*[\"'`]https?://"
            r"|\bsocket\.socket\s*\("), code_only=True),
    Rule("SC303", "medium", "Suspicious host (raw IP, shortener or request catcher)",
         _r(r"https?://(?:\d{1,3}\.){3}\d{1,3}\b|\b(?:bit\.ly|tinyurl\.com|t\.co|goo\.gl|is\.gd)/"
            r"|\b(?:pastebin\.com|webhook\.site|requestbin\.\w+|ngrok\.(?:io|app|dev)|interact\.sh|"
            r"burpcollaborator\.net|discord(?:app)?\.com/api/webhooks)\b"),
         accept=lambda s: _public_ip(s) if re.match(r"https?://\d", s) else True),
    Rule("SC401", "medium", "Persistence mechanism (shell rc, cron, ssh keys)",
         _r(r"\bauthorized_keys\b|\bcrontab\s+-|\blaunchctl\s+load\b|\bsystemctl\s+enable\b"
            r"|>>\s*~?/?\.(?:bashrc|zshrc|profile|bash_profile)\b|\bschtasks\s+/create\b")),
]

RULES_BY_ID = {r.id: r for r in RULES}
IGNORE_RE = re.compile(r"askit-ignore(?::\s*([A-Z0-9, ]+))?")


@dataclass
class Finding:
    rule: str
    severity: str
    message: str
    file: str
    line: int
    snippet: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {"rule": self.rule, "severity": self.severity, "message": self.message,
                "file": self.file, "line": self.line, "snippet": self.snippet}


@dataclass
class ScanResult:
    skill: str
    path: str
    findings: List[Finding] = field(default_factory=list)
    files_scanned: int = 0

    def count(self, severity: str) -> int:
        return sum(1 for f in self.findings if f.severity == severity)

    @property
    def risk(self) -> int:
        return min(100, sum(SEVERITY_WEIGHT[f.severity] for f in self.findings))

    @property
    def safety(self) -> int:
        return 100 - self.risk

    @property
    def verdict(self) -> str:
        if self.count("high"):
            return "risky"
        if self.count("medium"):
            return "review"
        return "clean"

    def worst(self) -> str:
        for sev in ("high", "medium", "low"):
            if self.count(sev):
                return sev
        return "none"

    def to_dict(self) -> Dict[str, Any]:
        return {"skill": self.skill, "path": self.path, "verdict": self.verdict, "safety": self.safety,
                "high": self.count("high"), "medium": self.count("medium"), "low": self.count("low"),
                "files_scanned": self.files_scanned, "findings": [f.to_dict() for f in self.findings]}


def _ignored(line_text: str, rule_id: str) -> bool:
    m = IGNORE_RE.search(line_text)
    if not m:
        return False
    ids = m.group(1)
    if not ids:
        return True
    return rule_id in {p.strip() for p in ids.split(",")}


def scan_text(text: str, filename: str = "SKILL.md") -> List[Finding]:
    suffix = Path(filename).suffix.lower()
    is_code = suffix in CODE_SUFFIXES
    lines = text.split("\n")
    findings: List[Finding] = []
    for rule in RULES:
        if rule.code_only and not is_code:
            continue
        for m in rule.pattern.finditer(text):
            matched = m.group(0)
            if rule.accept and not rule.accept(matched):
                continue
            line_no = text.count("\n", 0, m.start()) + 1
            line_text = lines[line_no - 1] if line_no - 1 < len(lines) else ""
            if _ignored(line_text, rule.id):
                continue
            snippet = line_text.strip()
            if rule.id == "SC006":
                snippet = "U+%04X" % ord(matched[0])
            elif rule.id.startswith("SC2") and len(matched) > 8:
                snippet = matched[:4] + "..." + matched[-2:]
            if any(f.rule == rule.id and f.line == line_no for f in findings):
                continue
            findings.append(Finding(rule.id, rule.severity, rule.title, filename, line_no, snippet[:120]))
    # Reading credentials and sending data in the same file is a stronger signal.
    ids = {f.rule for f in findings}
    if "SC301" in ids and "SC302" in ids:
        first = next(f for f in findings if f.rule == "SC301")
        findings.append(Finding("SC310", "high", "Reads credentials and sends data over the network",
                                filename, first.line, first.snippet))
    return findings


def scan_skill(target: Any) -> ScanResult:
    base = Path(target)
    if base.is_file():
        base = base.parent
    if not base.is_dir():
        raise SkillError("not found: %s" % target)
    res = ScanResult(skill=base.name, path=str(base))
    for rel in iter_skill_files(base):
        full = base / rel
        name = rel.as_posix()
        if full.suffix.lower() in BINARY_SUFFIXES:
            res.findings.append(Finding("SC601", "medium", "Compiled or binary file bundled in skill", name, 0))
            continue
        try:
            size = full.stat().st_size
        except OSError:
            continue
        if size > MAX_FILE_BYTES:
            res.findings.append(Finding("SC602", "low", "Very large file (not scanned)", name, 0))
            continue
        try:
            data = full.read_bytes()
        except OSError:
            continue
        if b"\x00" in data[:4096]:
            continue
        text = data.decode("utf-8", errors="replace")
        res.files_scanned += 1
        res.findings.extend(scan_text(text, name))
    res.findings.sort(key=lambda f: (-SEVERITY_RANK[f.severity], f.file, f.line))
    return res


def exceeds(result: ScanResult, fail_on: str) -> bool:
    """True when the scan has a finding at or above the given severity."""
    if fail_on == "never":
        return False
    rank = SEVERITY_RANK.get(fail_on, 3)
    return any(SEVERITY_RANK[f.severity] >= rank for f in result.findings)


def redact(text: str) -> str:
    """Mask secrets in free text (used when showing shell history)."""
    out = text
    for pat in SECRET_PATTERNS:
        out = pat.sub("<redacted>", out)
    out = re.sub(r"(?i)(--?(?:password|passwd|pass|token|secret|api[-_]?key|key)(?:=|\s+))(\S+)", r"\1<redacted>", out)
    out = re.sub(r"\b([A-Z][A-Z0-9_]*(?:KEY|TOKEN|SECRET|PASSWORD|PASSWD)[A-Z0-9_]*)=(\S+)", r"\1=<redacted>", out)
    out = re.sub(r"(\bmysql(?:dump|admin)?\b[^\n]*?\s-p)(\S+)", r"\1<redacted>", out)
    out = re.sub(r"(?i)(authorization:\s*(?:bearer|basic|token)\s+)\S+", r"\1<redacted>", out)
    out = re.sub(r"(://[^/\s:@]+:)[^@\s/]+(@)", r"\1<redacted>\2", out)
    return out
