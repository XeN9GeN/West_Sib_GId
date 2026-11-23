"""Загрузка и применение правил таксономии без обращения к базе данных."""

from __future__ import annotations

from dataclasses import dataclass
import ipaddress
from pathlib import Path
import re
import unicodedata
from typing import Any, Mapping
from urllib.parse import urlsplit

import yaml


TAXONOMY_PATH = Path(__file__).resolve().parents[1] / "config" / "taxonomy.yaml"
LEGACY_TYPE1_VALUES = frozenset({"human", "nature"})
LEGACY_TYPE2_VALUES = frozenset({
    "museum",
    "monument",
    "architecture",
    "theater",
    "temple",
    "lake",
    "river",
    "reserve",
    "forest",
    "historic_nature",
})
_ROOT_KEYS = {
    "version",
    "settings",
    "object_classes",
    "exclusion_reasons",
    "exclude_rules",
    "categories",
}
_CATEGORY_KEYS = {"id", "label", "subcategories"}
_SUBCATEGORY_KEYS = {
    "id",
    "label",
    "match_order",
    "must_precede",
    "legacy_type1",
    "legacy_type2",
    "default_class",
    "significance",
    "significance_kind",
    "base_priority",
    "match",
    "marker",
    "trust_ai_summary_as_evidence",
}
_MATCH_KEYS = {"tags", "name_regex", "name_not_regex"}
_SHAPE_VALUES = {"pin", "circle", "star"}


@dataclass(frozen=True)
class Classification:
    category: str | None
    subcategory: str | None
    object_class: str
    decision: str
    exclusion_reason: str | None
    size_priority: float
    legacy_type1: str | None
    legacy_type2: str | None
    evidence: tuple[dict[str, str], ...]
    taxonomy_version: str


def normalize_name(value: Any) -> str:
    """Нормализует название для сопоставления по правилам YAML."""
    if value is None:
        return ""
    normalized = unicodedata.normalize("NFKC", str(value)).casefold().replace("ё", "е")
    return " ".join(normalized.split())


def load_taxonomy(path: str | Path | None = None) -> dict[str, Any]:
    """Загружает YAML безопасным загрузчиком и валидирует всю схему."""
    taxonomy_path = Path(path) if path is not None else TAXONOMY_PATH
    with taxonomy_path.open("r", encoding="utf-8") as source:
        taxonomy = yaml.safe_load(source)
    validate_taxonomy(taxonomy)
    return taxonomy


def validate_taxonomy(taxonomy: Any) -> None:
    """Проверяет структуру, типы, ссылки и порядок правил YAML."""
    _require_mapping(taxonomy, "корень")
    _check_keys(taxonomy, _ROOT_KEYS, "корень")
    _require_keys(taxonomy, _ROOT_KEYS, "корень")
    _require_nonempty_string(taxonomy["version"], "version")

    settings = taxonomy["settings"]
    _require_mapping(settings, "settings")
    _check_keys(
        settings,
        {"railway_radius_meters", "description", "evidence", "zoom", "demo"},
        "settings",
    )
    _require_keys(
        settings,
        {"railway_radius_meters", "description", "evidence", "zoom", "demo"},
        "settings",
    )
    if type(settings["railway_radius_meters"]) is not int or settings["railway_radius_meters"] <= 0:
        raise ValueError("settings.railway_radius_meters должен быть положительным целым")

    description = settings["description"]
    _require_mapping(description, "settings.description")
    _check_keys(
        description,
        {"min_chars", "min_words", "min_cyrillic_ratio", "placeholder_patterns", "accept_ai_summary"},
        "settings.description",
    )
    _require_keys(
        description,
        {"min_chars", "min_words", "min_cyrillic_ratio", "placeholder_patterns", "accept_ai_summary"},
        "settings.description",
    )
    for key in ("min_chars", "min_words"):
        if type(description[key]) is not int or description[key] < 0:
            raise ValueError(f"settings.description.{key} должен быть неотрицательным целым")
    ratio = description["min_cyrillic_ratio"]
    if type(ratio) not in (int, float) or not 0 <= ratio <= 1:
        raise ValueError("settings.description.min_cyrillic_ratio должен быть от 0 до 1")
    if type(description["accept_ai_summary"]) is not bool:
        raise ValueError("settings.description.accept_ai_summary должен быть boolean")
    _validate_regex_list(description["placeholder_patterns"], "placeholder_patterns")

    evidence_settings = settings["evidence"]
    _require_mapping(evidence_settings, "settings.evidence")
    _check_keys(
        evidence_settings,
        {
            "min_strong",
            "min_weak",
            "historic_year_cutoff",
            "trust_researched_ai_summary",
            "heritage_status_values",
            "heritage_registry_tags",
            "mkrf_registry",
        },
        "settings.evidence",
    )
    _require_keys(
        evidence_settings,
        {
            "min_strong",
            "min_weak",
            "historic_year_cutoff",
            "trust_researched_ai_summary",
            "heritage_status_values",
            "heritage_registry_tags",
            "mkrf_registry",
        },
        "settings.evidence",
    )
    for key in ("min_strong", "min_weak", "historic_year_cutoff"):
        minimum = 1 if key in {"min_strong", "min_weak"} else 0
        if type(evidence_settings[key]) is not int or evidence_settings[key] < minimum:
            raise ValueError(f"settings.evidence.{key} должен быть неотрицательным целым")
    if type(evidence_settings["trust_researched_ai_summary"]) is not bool:
        raise ValueError("trust_researched_ai_summary должен быть boolean")
    _validate_string_list(evidence_settings["heritage_status_values"], "heritage_status_values")
    _validate_string_list(evidence_settings["heritage_registry_tags"], "heritage_registry_tags")
    mkrf = evidence_settings["mkrf_registry"]
    _require_mapping(mkrf, "settings.evidence.mkrf_registry")
    _check_keys(mkrf, {"tags", "only_categories"}, "settings.evidence.mkrf_registry")
    _require_keys(mkrf, {"tags", "only_categories"}, "settings.evidence.mkrf_registry")
    _validate_string_list(mkrf["tags"], "mkrf_registry.tags")
    _validate_string_list(mkrf["only_categories"], "mkrf_registry.only_categories")

    _validate_zoom(settings["zoom"])
    demo = settings["demo"]
    _require_mapping(demo, "settings.demo")
    _check_keys(demo, {"hide_duplicates", "priority_cap"}, "settings.demo")
    _require_keys(demo, {"hide_duplicates", "priority_cap"}, "settings.demo")
    if type(demo["hide_duplicates"]) is not bool:
        raise ValueError("settings.demo.hide_duplicates должен быть boolean")
    if demo["priority_cap"] is not None and (
        type(demo["priority_cap"]) not in (int, float) or demo["priority_cap"] < 0
    ):
        raise ValueError("settings.demo.priority_cap должен быть неотрицательным числом или null")

    object_classes = taxonomy["object_classes"]
    _validate_string_list(object_classes, "object_classes")
    if set(object_classes) != {"heritage", "tourism", "both", "unclassified"}:
        raise ValueError("object_classes должен содержать heritage, tourism, both, unclassified")

    reasons = taxonomy["exclusion_reasons"]
    _require_mapping(reasons, "exclusion_reasons")
    if not reasons:
        raise ValueError("exclusion_reasons не должен быть пустым")
    for reason_id, label in reasons.items():
        _require_nonempty_string(reason_id, "exclusion_reasons.id")
        _require_nonempty_string(label, f"exclusion_reasons.{reason_id}")

    rules = taxonomy["exclude_rules"]
    _require_list(rules, "exclude_rules")
    rule_ids: set[str] = set()
    for index, rule in enumerate(rules):
        context = f"exclude_rules[{index}]"
        _require_mapping(rule, context)
        _check_keys(rule, {"id", "match", "reason", "overridable", "unless"}, context)
        _require_keys(rule, {"id", "match", "reason", "overridable"}, context)
        _require_nonempty_string(rule["id"], f"{context}.id")
        if rule["id"] in rule_ids:
            raise ValueError(f"Повтор id правила исключения: {rule['id']}")
        rule_ids.add(rule["id"])
        if rule["reason"] not in reasons:
            raise ValueError(f"Неизвестная причина исключения: {rule['reason']}")
        if type(rule["overridable"]) is not bool:
            raise ValueError(f"{context}.overridable должен быть boolean")
        _validate_match(rule["match"], f"{context}.match")
        if "unless" in rule:
            _validate_string_list(rule["unless"], f"{context}.unless")

    categories = taxonomy["categories"]
    _require_list(categories, "categories")
    category_ids: set[str] = set()
    subcategory_ids: set[str] = set()
    subcategories: list[dict[str, Any]] = []
    match_orders: set[int] = set()
    for category_index, category in enumerate(categories):
        context = f"categories[{category_index}]"
        _require_mapping(category, context)
        _check_keys(category, _CATEGORY_KEYS, context)
        _require_keys(category, _CATEGORY_KEYS, context)
        _require_nonempty_string(category["id"], f"{context}.id")
        _require_nonempty_string(category["label"], f"{context}.label")
        if category["id"] in category_ids:
            raise ValueError(f"Повтор id категории: {category['id']}")
        category_ids.add(category["id"])
        _require_list(category["subcategories"], f"{context}.subcategories")

        for subcategory_index, subcategory in enumerate(category["subcategories"]):
            subcontext = f"{context}.subcategories[{subcategory_index}]"
            _require_mapping(subcategory, subcontext)
            _check_keys(subcategory, _SUBCATEGORY_KEYS, subcontext)
            required_subcategory_keys = _SUBCATEGORY_KEYS - {
                "must_precede",
                "trust_ai_summary_as_evidence",
            }
            _require_keys(subcategory, required_subcategory_keys, subcontext)
            _require_nonempty_string(subcategory["id"], f"{subcontext}.id")
            _require_nonempty_string(subcategory["label"], f"{subcontext}.label")
            if subcategory["id"] in subcategory_ids:
                raise ValueError(f"Повтор id подкатегории: {subcategory['id']}")
            subcategory_ids.add(subcategory["id"])
            order = subcategory["match_order"]
            if type(order) is not int or order < 0:
                raise ValueError(f"{subcontext}.match_order должен быть неотрицательным целым")
            if order in match_orders:
                raise ValueError(f"Повтор match_order: {order}")
            match_orders.add(order)
            if "must_precede" in subcategory:
                _validate_string_list(subcategory["must_precede"], f"{subcontext}.must_precede")
            if subcategory["legacy_type1"] not in LEGACY_TYPE1_VALUES:
                raise ValueError(f"Недопустимый legacy_type1 у {subcategory['id']}")
            if subcategory["legacy_type2"] not in LEGACY_TYPE2_VALUES:
                raise ValueError(f"Недопустимый legacy_type2 у {subcategory['id']}")
            if subcategory["default_class"] not in object_classes:
                raise ValueError(f"Недопустимый default_class у {subcategory['id']}")
            if subcategory["significance"] not in {"include", "review", "require"}:
                raise ValueError(f"Недопустимый significance у {subcategory['id']}")
            if subcategory["significance_kind"] not in {"cultural", "tourism"}:
                raise ValueError(f"Недопустимый significance_kind у {subcategory['id']}")
            _require_number(subcategory["base_priority"], f"{subcontext}.base_priority", minimum=0)
            if "trust_ai_summary_as_evidence" in subcategory and type(
                subcategory["trust_ai_summary_as_evidence"]
            ) is not bool:
                raise ValueError("trust_ai_summary_as_evidence должен быть boolean")
            _validate_match(subcategory["match"], f"{subcontext}.match")
            _validate_marker(subcategory["marker"], f"{subcontext}.marker")
            subcategories.append(subcategory)

    if not categories or not subcategories:
        raise ValueError("categories и subcategories не должны быть пустыми")
    required_reasons = {
        "unsupported_object_type",
        "pending_review",
        "insufficient_cultural_significance",
        "insufficient_tourism_value",
    }
    required_reasons.update(rule["reason"] for rule in rules)
    missing_reasons = required_reasons - set(reasons)
    if missing_reasons:
        raise ValueError(
            "Причины классификатора отсутствуют в exclusion_reasons: "
            + ", ".join(sorted(missing_reasons))
        )
    _validate_precedence(subcategories)
    for category_id in mkrf["only_categories"]:
        if category_id not in category_ids:
            raise ValueError(f"Неизвестная категория в mkrf_registry.only_categories: {category_id}")


def classify(facts: Mapping[str, Any], taxonomy: Mapping[str, Any] | None = None) -> Classification:
    """Классифицирует факты; имя используется только для выбора подкатегории."""
    if not isinstance(facts, Mapping):
        raise TypeError("facts должен быть отображением")
    config = taxonomy if taxonomy is not None else load_taxonomy()
    if taxonomy is not None:
        validate_taxonomy(config)

    tags = facts.get("tags") or {}
    if not isinstance(tags, Mapping):
        raise TypeError("facts.tags должен быть отображением")
    normalized_facts = dict(facts)
    normalized_facts["tags"] = tags
    normalized_facts["name"] = facts.get("name") or tags.get("name:ru") or tags.get("name") or ""
    name = normalize_name(normalized_facts["name"])
    version = str(config["version"])

    for rule in config["exclude_rules"]:
        if _matches_exclusion(rule, normalized_facts, name, config):
            return _excluded(
                config,
                reason=rule["reason"],
                rule_id=rule["id"],
                version=version,
            )

    ordered_subcategories = sorted(
        (
            (category["id"], subcategory)
            for category in config["categories"]
            for subcategory in category["subcategories"]
        ),
        key=lambda item: item[1]["match_order"],
    )
    selected: tuple[str, dict[str, Any]] | None = None
    for category_id, subcategory in ordered_subcategories:
        if _matches(subcategory["match"], normalized_facts, name):
            selected = category_id, subcategory
            break
    if selected is None:
        return _excluded(config, "unsupported_object_type", "unsupported_object_type", version)

    category_id, subcategory = selected
    evidence = _collect_evidence(normalized_facts, config, category_id, subcategory)
    strong_count = sum(item["source"] == "strong" for item in evidence)
    weak_count = sum(item["source"] == "weak" for item in evidence)
    thresholds = config["settings"]["evidence"]
    significant = strong_count >= thresholds["min_strong"] or weak_count >= thresholds["min_weak"]
    object_class = _resolve_object_class(
        subcategory["default_class"],
        normalized_facts,
        bool(evidence and any(item["rule"] == "heritage_status" for item in evidence)),
        category_id,
        subcategory["id"],
    )

    reason = None
    if not significant:
        if subcategory["significance"] in {"include", "review"}:
            decision = "pending_review"
            reason = "pending_review"
        else:
            decision = "excluded"
            reason = (
                "insufficient_tourism_value"
                if subcategory["significance_kind"] == "tourism"
                else "insufficient_cultural_significance"
            )
    else:
        decision = "include"

    priority = float(subcategory["base_priority"])
    priority += 0.5 if any(item["rule"] == "wikipedia_article" for item in evidence) else 0
    priority += 0.5 if any(item["rule"] == "heritage_status" for item in evidence) else 0
    if facts.get("quality_description") in {"ok", "ok_ai_summary", "ok_manual"}:
        priority += 0.3
    if facts.get("wikidata_id"):
        priority += 0.2
    priority = min(priority, 5.0)

    return Classification(
        category=category_id,
        subcategory=subcategory["id"],
        object_class=object_class,
        decision=decision,
        exclusion_reason=reason,
        size_priority=priority,
        legacy_type1=subcategory["legacy_type1"],
        legacy_type2=subcategory["legacy_type2"],
        evidence=tuple(evidence),
        taxonomy_version=version,
    )


def _excluded(
    taxonomy: Mapping[str, Any],
    reason: str,
    rule_id: str,
    version: str,
) -> Classification:
    if reason not in taxonomy["exclusion_reasons"]:
        raise ValueError(f"Причина отсутствует в реестре taxonomy: {reason}")
    return Classification(
        category=None,
        subcategory=None,
        object_class="unclassified",
        decision="excluded",
        exclusion_reason=reason,
        size_priority=0.0,
        legacy_type1=None,
        legacy_type2=None,
        evidence=({"rule": rule_id, "fact": reason, "source": "taxonomy"},),
        taxonomy_version=version,
    )


def _matches_exclusion(
    rule: Mapping[str, Any],
    facts: Mapping[str, Any],
    name: str,
    taxonomy: Mapping[str, Any],
) -> bool:
    if rule["id"] == "unnamed_or_broken":
        return not name and not facts.get("wikidata_id")
    if not _matches(rule["match"], facts, name):
        return False
    for condition in rule.get("unless", ()):
        if condition == "heritage_status" and _has_heritage_status(
            facts,
            taxonomy["settings"]["evidence"],
        ):
            return False
        if condition == "wikipedia" and facts.get("wikipedia_article_verified"):
            return False
        if condition == "wikidata" and facts.get("wikidata_id"):
            return False
    return True


def _matches(clauses: Any, facts: Mapping[str, Any], name: str) -> bool:
    tags = facts["tags"]
    for clause in clauses:
        if not isinstance(clause, Mapping):
            continue
        if any(not _tag_condition_matches(condition, tags) for condition in clause.get("tags", ())):
            continue
        if "name_regex" in clause and not re.search(
            clause["name_regex"],
            name,
            flags=re.IGNORECASE,
        ):
            continue
        if "name_not_regex" in clause and re.search(
            clause["name_not_regex"],
            name,
            flags=re.IGNORECASE,
        ):
            continue
        return True
    return False


def _tag_condition_matches(condition: str, tags: Mapping[str, Any]) -> bool:
    negate = condition.startswith("!")
    expression = condition[1:] if negate else condition
    key, separator, value_expression = expression.partition("=")
    keys = key.split("|")
    if separator:
        values = value_expression.split("|")
        result = any(
            str(tags.get(tag_key, "")).casefold() in {item.casefold() for item in values}
            for tag_key in keys
        )
    else:
        result = any(tag_key in tags and tags[tag_key] not in (None, "") for tag_key in keys)
    return not result if negate else result


def _collect_evidence(
    facts: Mapping[str, Any],
    taxonomy: Mapping[str, Any],
    category_id: str,
    subcategory: Mapping[str, Any],
) -> list[dict[str, str]]:
    tags = facts["tags"]
    evidence_settings = taxonomy["settings"]["evidence"]
    evidence: list[dict[str, str]] = []
    if _has_heritage_status(facts, evidence_settings):
        evidence.append({
            "rule": "heritage_status",
            "fact": "confirmed_heritage_status",
            "source": "strong",
        })

    if (
        evidence_settings["trust_researched_ai_summary"]
        and subcategory.get("trust_ai_summary_as_evidence", False)
        and facts.get("ai_summary_significance_verified") is True
        and facts.get("ai_summary")
        and valid_ai_summary_sources(facts.get("ai_summary_sources"))
    ):
        evidence.append({
            "rule": "researched_ai_summary",
            "fact": "verified_ai_summary",
            "source": "strong",
        })
    if facts.get("wikidata_heritage_status") is True:
        evidence.append({
            "rule": "heritage_status",
            "fact": "wikidata_p1435",
            "source": "strong",
        })
    if facts.get("wikipedia_article_verified"):
        evidence.append({
            "rule": "wikipedia_article",
            "fact": "dedicated_wikipedia_article",
            "source": "weak",
        })
    if facts.get("wikivoyage_verified"):
        evidence.append({
            "rule": "wikivoyage",
            "fact": "dedicated_wikivoyage_article",
            "source": "weak",
        })
    if tags.get("subject:wikidata") or tags.get("memorial:subject"):
        evidence.append({
            "rule": "subject_wikidata",
            "fact": "subject_reference",
            "source": "weak",
        })
    if _is_historically_old(tags.get("start_date"), evidence_settings["historic_year_cutoff"]):
        evidence.append({
            "rule": "historic_age",
            "fact": "start_date_before_cutoff",
            "source": "weak",
        })
    inscription = str(tags.get("inscription", "")).strip()
    if len(inscription) > 80 and not re.search(
        r"инвентарн|охранн|техническ|служебн|номер документа",
        normalize_name(inscription),
    ):
        evidence.append({
            "rule": "long_inscription",
            "fact": "inscription_over_80_chars",
            "source": "weak",
        })
    if tags.get("website") or tags.get("contact:website"):
        evidence.append({
            "rule": "official_website",
            "fact": "object_website",
            "source": "weak",
        })
    mkrf = evidence_settings["mkrf_registry"]
    if category_id in mkrf["only_categories"] and any(tags.get(key) for key in mkrf["tags"]):
        evidence.append({
            "rule": "mkrf_registry",
            "fact": "cultural_institution_registry_reference",
            "source": "weak",
        })
    return evidence


def _has_heritage_status(facts: Mapping[str, Any], evidence_settings: Mapping[str, Any]) -> bool:
    tags = facts.get("tags") or {}
    allowed_values = evidence_settings.get("heritage_status_values", ())
    allowed_registry_tags = evidence_settings.get("heritage_registry_tags", ())
    heritage_value = str(tags.get("heritage", "")).casefold()
    return (
        heritage_value in {str(value).casefold() for value in allowed_values}
        or any(tags.get(key) for key in allowed_registry_tags)
    )


def valid_ai_summary_sources(sources: Any) -> bool:
    if not isinstance(sources, list) or not sources:
        return False
    expected_keys = {"url", "title", "publisher", "accessed_at"}
    for source in sources:
        if not isinstance(source, Mapping) or set(source) != expected_keys:
            return False
        if not all(isinstance(source[key], str) and source[key].strip() for key in expected_keys):
            return False
        if not _is_valid_https_url(source["url"].strip()):
            return False
    return True


def _is_valid_https_url(value: str) -> bool:
    if re.search(r"\s|[\x00-\x1f]", value):
        return False
    try:
        parsed = urlsplit(value)
        if (
            parsed.scheme.lower() != "https"
            or not parsed.netloc
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
        ):
            return False
        parsed.port
        hostname = parsed.hostname
        if ":" in hostname:
            ipaddress.IPv6Address(hostname)
        else:
            encoded = hostname.encode("idna").decode("ascii")
            labels = encoded.split(".")
            if any(
                not re.fullmatch(r"[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?", label)
                for label in labels
            ):
                return False
    except (UnicodeError, ValueError):
        return False
    return True


def _is_historically_old(value: Any, cutoff: int) -> bool:
    if not value:
        return False
    match = re.match(r"^\s*(\d{4})", str(value))
    return bool(match and int(match.group(1)) <= cutoff)


def _resolve_object_class(
    default_class: str,
    facts: Mapping[str, Any],
    protected: bool,
    category_id: str,
    subcategory_id: str,
) -> str:
    tourism_tag = bool((facts.get("tags") or {}).get("tourism"))
    tags = facts.get("tags") or {}
    if protected:
        if default_class == "tourism":
            return "both"
        if default_class == "unclassified":
            return "heritage"
    if category_id == "religious_heritage" and not protected:
        return "unclassified"
    if (
        subcategory_id == "monuments_memorials"
        and tags.get("heritage")
        and not tags.get("historic")
        and not tags.get("memorial")
    ):
        return "unclassified"
    if tourism_tag and default_class == "heritage":
        return "both"
    return default_class


def _validate_zoom(zoom: Any) -> None:
    _require_mapping(zoom, "settings.zoom")
    _check_keys(zoom, {"description_required_from_zoom", "priority_tiers"}, "settings.zoom")
    _require_keys(zoom, {"description_required_from_zoom", "priority_tiers"}, "settings.zoom")
    if type(zoom["description_required_from_zoom"]) is not int:
        raise ValueError("description_required_from_zoom должен быть целым")
    _require_list(zoom["priority_tiers"], "settings.zoom.priority_tiers")
    previous_max = -1
    for index, tier in enumerate(zoom["priority_tiers"]):
        context = f"settings.zoom.priority_tiers[{index}]"
        _require_mapping(tier, context)
        _check_keys(tier, {"max_zoom", "min_priority"}, context)
        _require_keys(tier, {"max_zoom", "min_priority"}, context)
        max_zoom = tier["max_zoom"]
        if type(max_zoom) is not int or max_zoom <= previous_max:
            raise ValueError("max_zoom должен возрастать")
        _require_number(tier["min_priority"], f"{context}.min_priority", minimum=0)
        previous_max = max_zoom


def _validate_match(clauses: Any, context: str) -> None:
    _require_list(clauses, context)
    if not clauses:
        raise ValueError(f"{context} не должен быть пустым")
    for index, clause in enumerate(clauses):
        clause_context = f"{context}[{index}]"
        _require_mapping(clause, clause_context)
        _check_keys(clause, _MATCH_KEYS, clause_context)
        if not clause:
            raise ValueError(f"{clause_context} не должен быть пустым")
        if "tags" in clause:
            _validate_string_list(clause["tags"], f"{clause_context}.tags")
            for condition in clause["tags"]:
                if not condition or condition in {"!", "="}:
                    raise ValueError(f"Некорректное условие тега: {condition!r}")
        for key in ("name_regex", "name_not_regex"):
            if key in clause:
                _require_nonempty_string(clause[key], f"{clause_context}.{key}")
                try:
                    re.compile(clause[key], flags=re.IGNORECASE)
                except re.error as error:
                    raise ValueError(f"Некорректный {key}: {clause[key]}") from error
                if key == "name_regex":
                    _validate_short_tokens(clause[key], clause_context)


def _validate_short_tokens(pattern: str, context: str) -> None:
    tokens_requiring_left_and_right = {
        "жд",
        "цдт",
        "т-34",
        "бмп",
        "бтр",
        "су-25",
        "ис-3",
        "зис-2",
        "бм-13",
        "п36",
    }
    tokens_requiring_left = {"фд", "эр"}
    for token in tokens_requiring_left_and_right | tokens_requiring_left:
        for match in re.finditer(token, pattern, flags=re.IGNORECASE):
            before = pattern[:match.start()]
            after = pattern[match.end():]
            left_bounded = before.endswith(r"(?<!\w)") or before.endswith(r"\b") or (
                not before and pattern.startswith("^")
            )
            right_bounded = (
                token in tokens_requiring_left
                or after.startswith(r"(?!\w)")
                or after.startswith(r"\b")
            )
            if not left_bounded or not right_bounded:
                raise ValueError(
                    f"{context}: короткий токен {token!r} требует границ слова"
                )


def _validate_precedence(
    subcategories: list[dict[str, Any]],
) -> None:
    by_id = {subcategory["id"]: subcategory for subcategory in subcategories}
    for subcategory in subcategories:
        for target_id in subcategory.get("must_precede", ()):
            if target_id not in by_id:
                raise ValueError(
                    f"Неизвестная подкатегория в must_precede: {target_id}"
                )
            if subcategory["match_order"] >= by_id[target_id]["match_order"]:
                raise ValueError(
                    f"Порядок match_order нарушен: {subcategory['id']} должна быть "
                    f"раньше {target_id}"
                )


def _validate_marker(marker: Any, context: str) -> None:
    _require_mapping(marker, f"{context}.marker")
    _check_keys(marker, {"color", "icon", "shape"}, f"{context}.marker")
    _require_keys(marker, {"color", "icon", "shape"}, f"{context}.marker")
    if not isinstance(marker["color"], str) or not re.fullmatch(r"#[0-9a-fA-F]{6}", marker["color"]):
        raise ValueError(f"{context}.marker.color должен быть HEX-цветом")
    _require_nonempty_string(marker["icon"], f"{context}.marker.icon")
    if marker["shape"] not in _SHAPE_VALUES:
        raise ValueError(f"{context}.marker.shape должен быть pin, circle или star")


def _validate_regex_list(values: Any, context: str) -> None:
    _validate_string_list(values, context)
    for pattern in values:
        try:
            re.compile(pattern, flags=re.IGNORECASE)
        except re.error as error:
            raise ValueError(f"Некорректный регулярный шаблон в {context}: {pattern}") from error


def _validate_string_list(values: Any, context: str) -> None:
    _require_list(values, context)
    for index, value in enumerate(values):
        _require_nonempty_string(value, f"{context}[{index}]")


def _require_mapping(value: Any, context: str) -> None:
    if not isinstance(value, Mapping):
        raise ValueError(f"{context} должен быть объектом")


def _require_list(value: Any, context: str) -> None:
    if not isinstance(value, list):
        raise ValueError(f"{context} должен быть списком")


def _check_keys(value: Mapping[str, Any], allowed: set[str], context: str) -> None:
    unknown = set(value) - allowed
    if unknown:
        raise ValueError(f"Неизвестные ключи в {context}: {', '.join(sorted(unknown))}")


def _require_keys(value: Mapping[str, Any], required: set[str], context: str) -> None:
    missing = required - set(value)
    if missing:
        raise ValueError(f"Отсутствуют ключи в {context}: {', '.join(sorted(missing))}")


def _require_nonempty_string(value: Any, context: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{context} должен быть непустой строкой")


def _require_number(value: Any, context: str, minimum: float) -> None:
    if type(value) not in (int, float) or value < minimum:
        raise ValueError(f"{context} должен быть числом не меньше {minimum}")
