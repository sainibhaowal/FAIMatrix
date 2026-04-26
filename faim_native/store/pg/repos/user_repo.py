"""FAIM-Native: User Repository.

Handles formal user registration and lookup in the identity registry.
"""

from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from store.pg.models_auth import UserModel

logger = logging.getLogger(__name__)


class UserRepository:
    """Repository for managing the formal user registry."""

    def __init__(self, session: Session):
        self.session = session

    def get_by_email(self, email: str) -> Optional[UserModel]:
        """Look up a user by their verified email address."""
        return (
            self.session.query(UserModel)
            .filter(UserModel.email == email.lower().strip())
            .first()
        )

    def get_by_id(self, user_id: UUID) -> Optional[UserModel]:
        """Look up a user by their deterministic UUID."""
        return self.session.query(UserModel).filter(UserModel.id == user_id).first()

    def create_user(
        self, user_id: UUID, email: str, full_name: Optional[str] = None
    ) -> UserModel:
        """Create a new formal user record."""
        user = UserModel(id=user_id, email=email.lower().strip(), full_name=full_name)
        self.session.add(user)
        try:
            self.session.commit()
            logger.info(f"👤 Formalized registration for user: {email}")
            return user
        except Exception as e:
            self.session.rollback()
            logger.error(f"Failed to create user record: {e}")
            raise

    def update_profile(self, user_id: UUID, full_name: str) -> Optional[UserModel]:
        """Update a user's display name."""
        user = self.get_by_id(user_id)
        if user:
            user.full_name = full_name
            self.session.commit()
            return user
        return None
