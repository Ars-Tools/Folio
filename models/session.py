#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Runtime session / sender types (non-table Pydantic models)."""
from enum import Enum
from pydantic import BaseModel, Field


class Category(str, Enum):
    unknown = "unknown"
    system = "system"
    agent = "agent"
    user = "user"


class Sender(BaseModel):
    id: str = Field(description="The unique identifier for the sender")
    name: str = Field(description="The name of the sender")
    category: Category = Field(description="The category of the sender")


class Session(BaseModel):
    id: str = Field(description="The unique identifier for the session")
    sender: Sender = Field(description="The sender associated with this session")
