# SPDX-FileCopyrightText: 2025 Weibo, Inc.
#
# SPDX-License-Identifier: Apache-2.0

import json

from app.services.task_skill_labels import (
    ADDITIONAL_SKILL_REFS_LABEL,
    ADDITIONAL_SKILLS_LABEL,
    build_task_skill_labels,
)


def test_build_task_skill_labels_preserves_exact_skill_refs():
    labels = build_task_skill_labels(
        [
            {
                "name": "exchange-calendar",
                "namespace": "invest-team",
                "is_public": False,
            }
        ]
    )

    assert json.loads(labels[ADDITIONAL_SKILLS_LABEL]) == ["exchange-calendar"]
    assert json.loads(labels[ADDITIONAL_SKILL_REFS_LABEL]) == {
        "exchange-calendar": {
            "namespace": "invest-team",
            "is_public": False,
        }
    }
