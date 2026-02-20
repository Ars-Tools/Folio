#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""User model — replaces hardcoded credentials."""
from datetime import datetime, timezone
from typing import Optional
from sqlmodel import SQLModel, Field
import hashlib


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True, index=True)
    password_hash: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @staticmethod
    def hash_password(password: str) -> str:
        """Simple SHA-256 hash. Replace with bcrypt for production."""
        return hashlib.sha256(password.encode()).hexdigest()

    def verify_password(self, password: str) -> bool:
        return self.password_hash == self.hash_password(password)
