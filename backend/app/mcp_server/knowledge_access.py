# SPDX-FileCopyrightText: 2026 Weibo, Inc.
#
# SPDX-License-Identifier: Apache-2.0

"""Shared helpers for knowledge MCP authentication and user lookup."""

from typing import Optional

from sqlalchemy.orm import Session

from app.mcp_server.auth import TaskTokenInfo
from app.models.user import User


def get_user_from_token(db: Session, token_info: TaskTokenInfo) -> Optional[User]:
    """Load the authenticated user from MCP task token information."""
    return db.query(User).filter(User.id == token_info.user_id).first()
