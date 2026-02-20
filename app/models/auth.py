#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Auth request / response schemas."""
from pydantic import BaseModel, Field


class AuthRequest(BaseModel):
    user: str = Field(..., description="The username for authentication")
    password: str = Field(..., description="The password for the user")
