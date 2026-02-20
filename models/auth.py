#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Auth request / response schemas."""
from pydantic import BaseModel, Field


class AuthRequest(BaseModel):
    token: str = Field(..., description="A valid user token for authentication")
