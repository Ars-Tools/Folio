-- ==========================================================================
-- FOLIO — canonical schema  (SQLite)
-- Generated from app/models/*.py
-- Run: sqlite3 app.db < schema.sql
-- Or:  python -c "from app.core.db import init_db; init_db()"
-- ==========================================================================

PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

-- -------------------------------------------------------------------------
-- tokens — authentication credential registry
-- kind: user | node | service
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS tokens (
    id      TEXT PRIMARY KEY,
    name    TEXT NOT NULL,
    kind    TEXT NOT NULL DEFAULT 'user'
                CHECK (kind IN ('user', 'node', 'service')),
    "update" TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

-- -------------------------------------------------------------------------
-- providers — LLM provider connections
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS providers (
    id       TEXT PRIMARY KEY,
    name     TEXT NOT NULL,
    kind     TEXT NOT NULL,
    endpoint TEXT NOT NULL,
    apikey   TEXT NOT NULL,
    "update" TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

-- -------------------------------------------------------------------------
-- agents — AI agent definitions
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS agents (
    id           TEXT PRIMARY KEY,
    provider     TEXT NOT NULL REFERENCES providers(id),
    model        TEXT NOT NULL,
    name         TEXT NOT NULL,
    prompt       TEXT NOT NULL DEFAULT '',
    avatar       TEXT,
    capabilities TEXT NOT NULL DEFAULT '[]',
    diary        INTEGER NOT NULL DEFAULT 0,
    concurrency  INTEGER,
    "update"     TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

-- -------------------------------------------------------------------------
-- chats — conversation sessions between users and agents
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS chats (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    user     TEXT NOT NULL,
    agent    TEXT NOT NULL REFERENCES agents(id),
    messages TEXT NOT NULL DEFAULT '[]',
    "update" TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);
CREATE INDEX IF NOT EXISTS ix_chats_user  ON chats(user);
CREATE INDEX IF NOT EXISTS ix_chats_agent ON chats(agent);

-- -------------------------------------------------------------------------
-- approvals — pending tool-call approval requests
-- status: pending | approved | denied
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS approvals (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    agent    TEXT NOT NULL REFERENCES agents(id),
    request  TEXT NOT NULL,
    status   TEXT NOT NULL DEFAULT 'pending'
                 CHECK (status IN ('pending', 'approved', 'denied')),
    "update" TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

-- -------------------------------------------------------------------------
-- crons — scheduled tasks
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS crons (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    agent    TEXT NOT NULL REFERENCES agents(id),
    pattern  TEXT NOT NULL,
    message  TEXT NOT NULL,
    execute  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    "update" TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

-- -------------------------------------------------------------------------
-- journals — agent diary / log entries
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS journals (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    agent     TEXT NOT NULL REFERENCES agents(id),
    abstract  TEXT,
    body      TEXT NOT NULL,
    timestamp TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    "update"  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

-- -------------------------------------------------------------------------
-- skills — reusable prompt fragments
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS skills (
    id       TEXT PRIMARY KEY,
    body     TEXT NOT NULL,
    "update" TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

-- -------------------------------------------------------------------------
-- equips — many-to-many: which skills are equipped to which agents
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS equips (
    skill    TEXT NOT NULL REFERENCES skills(id),
    agent    TEXT NOT NULL REFERENCES agents(id),
    "update" TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    PRIMARY KEY (skill, agent)
);
