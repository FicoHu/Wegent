# SPDX-FileCopyrightText: 2025 Weibo, Inc.
#
# SPDX-License-Identifier: Apache-2.0

"""Helpers for persisting and restoring task-level skill selections."""

import json as json_lib
import logging
from collections.abc import Mapping, Sequence
from typing import Any

logger = logging.getLogger(__name__)

ADDITIONAL_SKILLS_LABEL = "additionalSkills"
ADDITIONAL_SKILL_REFS_LABEL = "additionalSkillRefs"


def _get_skill_field(skill: Any, field: str) -> Any:
    if isinstance(skill, Mapping):
        return skill.get(field)
    return getattr(skill, field, None)


def build_task_skill_labels(skills: Sequence[Any] | None) -> dict[str, str]:
    """Build task labels for user-selected skills."""
    if not skills:
        return {}

    skill_names: list[str] = []
    skill_refs: dict[str, dict[str, Any]] = {}

    for skill in skills:
        name = _get_skill_field(skill, "name")
        if not isinstance(name, str) or not name:
            continue

        if name not in skill_names:
            skill_names.append(name)

        skill_ref: dict[str, Any] = {
            "namespace": _get_skill_field(skill, "namespace") or "default",
            "is_public": bool(_get_skill_field(skill, "is_public")),
        }

        skill_id = _get_skill_field(skill, "skill_id")
        if skill_id is not None:
            skill_ref["skill_id"] = skill_id

        skill_refs[name] = skill_ref

    if not skill_names:
        return {}

    return {
        ADDITIONAL_SKILLS_LABEL: json_lib.dumps(skill_names),
        ADDITIONAL_SKILL_REFS_LABEL: json_lib.dumps(skill_refs),
    }


def parse_task_skill_labels(
    labels: Mapping[str, Any] | None,
) -> tuple[list[str], dict[str, dict[str, Any]]]:
    """Parse persisted task skill labels into names and precise refs."""
    if not labels:
        return [], {}

    return _parse_skill_names(labels.get(ADDITIONAL_SKILLS_LABEL)), _parse_skill_refs(
        labels.get(ADDITIONAL_SKILL_REFS_LABEL)
    )


def _parse_skill_names(raw_value: Any) -> list[str]:
    if not raw_value:
        return []

    try:
        parsed = json_lib.loads(raw_value)
    except (TypeError, json_lib.JSONDecodeError) as exc:
        logger.warning("[task_skill_labels] Failed to parse additionalSkills: %s", exc)
        return []

    if not isinstance(parsed, list):
        return []

    return [name for name in parsed if isinstance(name, str) and name]


def _parse_skill_refs(raw_value: Any) -> dict[str, dict[str, Any]]:
    if not raw_value:
        return {}

    try:
        parsed = json_lib.loads(raw_value)
    except (TypeError, json_lib.JSONDecodeError) as exc:
        logger.warning(
            "[task_skill_labels] Failed to parse additionalSkillRefs: %s", exc
        )
        return {}

    if not isinstance(parsed, dict):
        return {}

    result: dict[str, dict[str, Any]] = {}
    for name, raw_ref in parsed.items():
        if not isinstance(name, str) or not name or not isinstance(raw_ref, dict):
            continue

        skill_ref: dict[str, Any] = {
            "namespace": raw_ref.get("namespace") or "default",
            "is_public": bool(raw_ref.get("is_public")),
        }

        skill_id = raw_ref.get("skill_id")
        if skill_id is not None:
            skill_ref["skill_id"] = skill_id

        result[name] = skill_ref

    return result
