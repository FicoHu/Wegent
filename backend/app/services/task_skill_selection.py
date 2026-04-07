# SPDX-FileCopyrightText: 2025 Weibo, Inc.
#
# SPDX-License-Identifier: Apache-2.0

"""Helpers for persisting and reading task-scoped requested skill selections."""

import json as json_lib
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

REQUESTED_SKILL_REFS_LABEL = "requestedSkillRefs"
ADDITIONAL_SKILLS_LABEL = "additionalSkills"


def normalize_requested_skill_refs(
    skills: Optional[List[Any]],
) -> List[Dict[str, Any]]:
    """Normalize task-scoped requested skills to serializable dicts."""
    normalized_by_name: Dict[str, Dict[str, Any]] = {}

    for skill in skills or []:
        if isinstance(skill, BaseModel):
            skill_id = getattr(skill, "skill_id", None)
            name = getattr(skill, "name", None)
            namespace = getattr(skill, "namespace", "default")
            is_public = bool(getattr(skill, "is_public", False))
        else:
            skill_id = skill.get("skill_id") if isinstance(skill, dict) else None
            name = skill.get("name") if isinstance(skill, dict) else None
            namespace = (
                skill.get("namespace", "default")
                if isinstance(skill, dict)
                else "default"
            )
            is_public = (
                bool(skill.get("is_public", False))
                if isinstance(skill, dict)
                else False
            )

        if not isinstance(name, str) or not name:
            continue

        normalized_skill = {
            "name": name,
            "namespace": namespace or "default",
            "is_public": is_public,
        }
        if isinstance(skill_id, int):
            normalized_skill["skill_id"] = skill_id
        if name in normalized_by_name:
            del normalized_by_name[name]
        normalized_by_name[name] = normalized_skill

    return list(normalized_by_name.values())


def build_task_skill_labels(skills: Optional[List[Any]]) -> Dict[str, str]:
    """Build task metadata labels for requested skills."""
    normalized = normalize_requested_skill_refs(skills)
    if not normalized:
        return {}

    return {
        ADDITIONAL_SKILLS_LABEL: json_lib.dumps(
            [skill["name"] for skill in normalized]
        ),
        REQUESTED_SKILL_REFS_LABEL: json_lib.dumps(normalized),
    }


def parse_requested_skill_refs_from_labels(
    labels: Optional[Dict[str, str]],
) -> List[Dict[str, Any]]:
    """Read task-scoped requested skill refs from labels."""
    if not labels:
        return []

    raw = labels.get(REQUESTED_SKILL_REFS_LABEL)
    if not raw:
        return []

    try:
        parsed = json_lib.loads(raw)
    except json_lib.JSONDecodeError:
        return []

    if not isinstance(parsed, list):
        return []

    return normalize_requested_skill_refs(parsed)


def parse_additional_skill_names_from_labels(
    labels: Optional[Dict[str, str]],
) -> List[str]:
    """Read legacy name-only additional skills from labels."""
    if not labels:
        return []

    raw = labels.get(ADDITIONAL_SKILLS_LABEL)
    if not raw:
        return []

    try:
        parsed = json_lib.loads(raw)
    except json_lib.JSONDecodeError:
        return []

    if not isinstance(parsed, list):
        return []

    return [skill for skill in parsed if isinstance(skill, str) and skill]


def format_requested_skill_refs_for_log(
    skills: Optional[List[Any]],
) -> List[str]:
    """Render skill refs to stable compact strings for logs."""
    formatted_refs: List[str] = []

    for skill in normalize_requested_skill_refs(skills):
        skill_id = skill.get("skill_id")
        skill_id_display = str(skill_id) if isinstance(skill_id, int) else "?"
        formatted_refs.append(
            f"{skill['name']}@{skill['namespace']}#{skill_id_display}"
        )

    return formatted_refs


def format_skill_ref_map_for_log(
    skill_refs: Optional[Dict[str, Dict[str, Any]]],
) -> List[str]:
    """Render resolved skill ref maps to stable compact strings for logs."""
    if not skill_refs:
        return []

    formatted_refs: List[str] = []
    for skill_name in sorted(skill_refs):
        ref_meta = skill_refs[skill_name] or {}
        namespace = ref_meta.get("namespace") or "default"
        skill_id = ref_meta.get("skill_id")
        skill_id_display = str(skill_id) if isinstance(skill_id, int) else "?"
        formatted_refs.append(f"{skill_name}@{namespace}#{skill_id_display}")

    return formatted_refs
