"""Оценка качества описаний и выбор единого эффективного описания."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Mapping

from app.taxonomy import normalize_name, valid_ai_summary_sources


@dataclass(frozen=True)
class EffectiveDescription:
    effective_description: str | None
    effective_description_source: str | None
    description_quality: str


def assess_description(
    text: Any,
    name: Any,
    cfg: Mapping[str, Any],
    trusted: bool = False,
) -> str:
    """Возвращает причину отказа или код качества описания."""
    normalized = " ".join(str(text or "").split())
    if not normalized:
        return "empty"

    normalized_name = _comparison_text(name)
    comparison = _comparison_text(normalized)
    if normalized_name:
        candidate_words = comparison.split()
        name_words = normalized_name.split()
        if candidate_words[:len(name_words)] == name_words and len(candidate_words) - len(name_words) <= 2:
            return "same_as_name"

    if trusted:
        return "ok_manual"

    if any(
        re.search(pattern, normalize_name(normalized), flags=re.IGNORECASE)
        for pattern in cfg.get("placeholder_patterns", ())
    ):
        return "placeholder"
    if len(normalized) < cfg["min_chars"]:
        return "too_short"
    words = re.findall(r"\b[\w'-]+\b", normalized, flags=re.UNICODE)
    if len(words) < cfg["min_words"]:
        return "too_few_words"

    letters = [character for character in normalized if character.isalpha()]
    cyrillic_letters = [
        character for character in letters
        if "\u0400" <= character <= "\u04ff"
    ]
    ratio = len(cyrillic_letters) / len(letters) if letters else 0
    if ratio < cfg["min_cyrillic_ratio"]:
        return "not_russian"
    return "ok"


def pick_effective_description(
    candidates: Mapping[str, Any],
    name: Any,
    cfg: Mapping[str, Any],
) -> EffectiveDescription:
    """Выбирает первый качественный текст в нормативном порядке."""
    first_rejection: str | None = None
    history = candidates.get("history")
    short_description = candidates.get("short_description")
    ai_summary = candidates.get("ai_summary")

    for source, text in (("history", history), ("short_description", short_description)):
        if not str(text or "").strip():
            continue
        trusted = source == "short_description" and candidates.get("description_source") == "manual"
        quality = assess_description(text, name, cfg["description"], trusted=trusted)
        if quality in {"ok", "ok_manual"}:
            return EffectiveDescription(str(text).strip(), source, quality)
        if first_rejection is None:
            first_rejection = quality

    if str(ai_summary or "").strip():
        quality = assess_description(ai_summary, name, cfg["description"])
        if (
            cfg["description"].get("accept_ai_summary") is True
            and cfg["evidence"].get("trust_researched_ai_summary") is True
            and valid_ai_summary_sources(candidates.get("ai_summary_sources"))
            and quality == "ok"
        ):
            return EffectiveDescription(str(ai_summary).strip(), "ai_summary", "ok_ai_summary")
        if first_rejection is None:
            first_rejection = quality

    return EffectiveDescription(None, None, first_rejection or "empty")


def _comparison_text(value: Any) -> str:
    normalized = normalize_name(value)
    return " ".join(re.findall(r"[\w]+", normalized, flags=re.UNICODE))
