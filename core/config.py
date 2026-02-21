#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Shared application configuration constants."""
import os

HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))
