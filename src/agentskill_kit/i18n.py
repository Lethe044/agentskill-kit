"""Interface strings. Rule messages and docs stay in English; the CLI chrome is translated."""

from __future__ import annotations

import locale
import os
from typing import Dict

_LANG = "en"

STRINGS: Dict[str, Dict[str, str]] = {
    "en": {
        "no_skills": "No skills found in {path}",
        "lint_title": "Lint",
        "scan_title": "Security scan",
        "test_title": "Tests",
        "score": "score",
        "no_issues": "no issues",
        "no_findings": "no findings",
        "summary_lint": "{n} skill(s) checked: {e} error(s), {w} warning(s)",
        "summary_scan": "{n} skill(s) scanned: {h} high, {m} medium, {l} low",
        "summary_test": "{p}/{t} test case(s) passed across {n} skill(s)",
        "no_tests": "no tests (instruction-only skill)",
        "created": "Created {path}",
        "exists": "{path} already exists (use --force to overwrite)",
        "forge_start": "Forging a skill with {provider} ({model})",
        "forge_round": "Round {n}/{total}",
        "forge_done": "Skill written to {path} (score {score})",
        "forge_below": "Best score {score} is below the threshold {threshold}; saved anyway because of --force",
        "forge_rejected": "Best score {score} is below the threshold {threshold}; nothing written (lower --threshold or use --force)",
        "exported": "Exported {name} to {target}",
        "installed": "Installed {name} ({target})",
        "uninstalled": "Removed {name}",
        "packed": "Packed {path}",
        "no_results": "No matching skills",
        "mine_none": "No repeated workflows found (try --min-count 2)",
        "mine_found": "Found {n} repeated workflow(s)",
        "serving": "Serving on {url} (Ctrl+C to stop)",
        "doctor_title": "Environment check",
        "gate_failed": "Gate failed: {reason}",
        "published": "Ready to publish {name}",
        "provider_missing": "No LLM provider is configured. See: askit providers",
        "threshold_note": "Quality gate: {threshold}",
    },
    "tr": {
        "no_skills": "{path} içinde skill bulunamadı",
        "lint_title": "Lint",
        "scan_title": "Güvenlik taraması",
        "test_title": "Testler",
        "score": "puan",
        "no_issues": "sorun yok",
        "no_findings": "bulgu yok",
        "summary_lint": "{n} skill kontrol edildi: {e} hata, {w} uyarı",
        "summary_scan": "{n} skill tarandı: {h} yüksek, {m} orta, {l} düşük",
        "summary_test": "{n} skill içinde {p}/{t} test senaryosu başarılı",
        "no_tests": "test yok (yalnızca talimat içeren skill)",
        "created": "{path} oluşturuldu",
        "exists": "{path} zaten var (üzerine yazmak için --force kullanın)",
        "forge_start": "{provider} ({model}) ile skill üretiliyor",
        "forge_round": "Tur {n}/{total}",
        "forge_done": "Skill {path} konumuna yazıldı (puan {score})",
        "forge_below": "En iyi puan {score}, eşik {threshold} altında; --force nedeniyle yine de kaydedildi",
        "forge_rejected": "En iyi puan {score}, eşik {threshold} altında; hiçbir şey yazılmadı (--threshold değerini düşürün veya --force kullanın)",
        "exported": "{name}, {target} hedefine aktarıldı",
        "installed": "{name} kuruldu ({target})",
        "uninstalled": "{name} kaldırıldı",
        "packed": "{path} paketlendi",
        "no_results": "Eşleşen skill yok",
        "mine_none": "Tekrar eden iş akışı bulunamadı (--min-count 2 deneyin)",
        "mine_found": "{n} tekrar eden iş akışı bulundu",
        "serving": "{url} adresinde çalışıyor (durdurmak için Ctrl+C)",
        "doctor_title": "Ortam kontrolü",
        "gate_failed": "Kapı geçilemedi: {reason}",
        "published": "{name} yayına hazır",
        "provider_missing": "Yapılandırılmış bir LLM sağlayıcı yok. Bkz: askit providers",
        "threshold_note": "Kalite eşiği: {threshold}",
    },
}


def set_lang(lang: str) -> None:
    global _LANG
    lang = (lang or "en").lower()[:2]
    _LANG = lang if lang in STRINGS else "en"


def get_lang() -> str:
    return _LANG


def detect_lang() -> str:
    env = os.environ.get("ASKIT_LANG")
    if env:
        return env.lower()[:2]
    try:
        loc = locale.getlocale()[0] or os.environ.get("LANG", "")
    except Exception:
        loc = os.environ.get("LANG", "")
    return "tr" if str(loc).lower().startswith("tr") else "en"


def t(key: str, **kwargs) -> str:
    text = STRINGS.get(_LANG, {}).get(key) or STRINGS["en"].get(key) or key
    try:
        return text.format(**kwargs)
    except (KeyError, IndexError):
        return text
