# SPDX-FileCopyrightText: 2025 Weibo, Inc.
#
# SPDX-License-Identifier: Apache-2.0

from executor.agents.claude_code.prompt_enrichment import inject_kb_meta_prompt


class TestInjectKbMetaPrompt:
    def test_local_mode_injects_kb_meta_for_string_prompt(self):
        prompt = "Save this file to the selected knowledge base."
        kb_meta_prompt = (
            "Available Knowledge Bases:\n"
            "- KB Name: 222, KB ID: 1408\n"
            "Current Request Target KB:\n"
            "- Use KB Name: 222, KB ID: 1408 as the target knowledge base."
        )

        result = inject_kb_meta_prompt(prompt, kb_meta_prompt, executor_mode="local")

        assert result.startswith("<knowledge_base_context>\n")
        assert "KB Name: 222, KB ID: 1408" in result
        assert result.endswith(prompt)

    def test_non_local_mode_does_not_inject_kb_meta(self):
        prompt = "Save this file to the selected knowledge base."
        kb_meta_prompt = "Available Knowledge Bases:\n- KB Name: 222, KB ID: 1408"

        result = inject_kb_meta_prompt(prompt, kb_meta_prompt, executor_mode="docker")

        assert result == prompt

    def test_local_mode_injects_kb_meta_for_content_block_prompt(self):
        prompt = [{"type": "input_text", "text": "Save this file."}]
        kb_meta_prompt = "Available Knowledge Bases:\n- KB Name: 222, KB ID: 1408"

        result = inject_kb_meta_prompt(prompt, kb_meta_prompt, executor_mode="local")

        assert result[0]["type"] == "input_text"
        assert result[0]["text"].startswith("<knowledge_base_context>\n")
        assert "KB Name: 222, KB ID: 1408" in result[0]["text"]
        assert result[0]["text"].endswith("Save this file.")
