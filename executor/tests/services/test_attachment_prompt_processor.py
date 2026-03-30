# SPDX-FileCopyrightText: 2025 Weibo, Inc.
#
# SPDX-License-Identifier: Apache-2.0

from executor.services.attachment_prompt_processor import AttachmentPromptProcessor


class TestAttachmentPromptProcessor:
    def test_rewrites_backend_sandbox_path_to_local_path_in_text_blocks(self):
        """Backend-injected sandbox paths should be rewritten for local executor."""
        prompt = [
            {
                "type": "input_text",
                "text": (
                    "[Attachment: xxx.md | ID: 274 | File Path(already in sandbox): "
                    "/home/user/1233:executor:attachments/1642/xxx.md]"
                ),
            },
            {"type": "input_text", "text": "upload this file"},
        ]

        processed = AttachmentPromptProcessor.process_prompt(
            prompt=prompt,
            success_attachments=[
                {
                    "id": 274,
                    "original_filename": "xxx.md",
                    "local_path": "/Users/test/.wegent-executor/workspace/1233/1233:executor:attachments/1642/xxx.md",
                }
            ],
            failed_attachments=[],
            task_id=1233,
            subtask_id=1642,
        )

        assert (
            "Local File Path: "
            "/Users/test/.wegent-executor/workspace/1233/1233:executor:attachments/1642/xxx.md"
            in processed[0]["text"]
        )
        assert (
            "/home/user/1233:executor:attachments/1642/xxx.md"
            not in processed[0]["text"]
        )
