#!/usr/bin/env python3
"""二次确认机制"""

import json
import os
import time
import hashlib
from typing import Optional

NONCE_DIR = "/tmp/quantclaw/nonces"
DEFAULT_TTL = 300


def _key(*parts: str) -> str:
    raw = ":".join(str(p) if p is not None else "" for p in parts)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def check(*nonce_parts: str) -> str:
    """返回 "none" / "expired" / "confirmed" """
    path = os.path.join(NONCE_DIR, _key(*nonce_parts))
    if not os.path.exists(path):
        return "none"
    try:
        with open(path) as f:
            data = json.load(f)
        if time.time() - data.get("created_at", 0) > data.get("ttl", DEFAULT_TTL):
            os.remove(path)
            return "expired"
        return "confirmed"
    except Exception:
        return "none"


def create(*nonce_parts: str, ttl: int = DEFAULT_TTL) -> None:
    os.makedirs(NONCE_DIR, exist_ok=True)
    agent_id = nonce_parts[0] if nonce_parts else ""
    # 同一 agent 同时只保留一个 nonce 凭证，防止旧 nonce 被意外复用
    if agent_id:
        _clear_agent_nonces(agent_id)
    with open(os.path.join(NONCE_DIR, _key(*nonce_parts)), "w") as f:
        json.dump({"created_at": time.time(), "ttl": ttl, "agent_id": agent_id}, f)


def clear(*nonce_parts: str) -> None:
    path = os.path.join(NONCE_DIR, _key(*nonce_parts))
    if os.path.exists(path):
        os.remove(path)


def reject(agent_id: str) -> int:
    """用户拒绝确认时调用，清除该 agent 所有 nonce 凭证"""
    if not agent_id:
        return 0
    return _clear_agent_nonces(agent_id)


def _clear_agent_nonces(agent_id: str) -> int:
    """清除同一 agent 的所有 nonce，确保同一 agent 同时只保留一个凭证"""
    if not os.path.isdir(NONCE_DIR) or not agent_id:
        return 0
    cleaned = 0
    for fname in os.listdir(NONCE_DIR):
        path = os.path.join(NONCE_DIR, fname)
        if not os.path.isfile(path):
            continue
        try:
            with open(path) as f:
                data = json.load(f)
            if data.get("agent_id") == agent_id:
                os.remove(path)
                cleaned += 1
        except Exception:
            pass
    return cleaned


def sweep_expired() -> int:
    if not os.path.isdir(NONCE_DIR):
        return 0
    now = time.time()
    cleaned = 0
    for fname in os.listdir(NONCE_DIR):
        path = os.path.join(NONCE_DIR, fname)
        if not os.path.isfile(path):
            continue
        try:
            with open(path) as f:
                data = json.load(f)
            if now - data.get("created_at", 0) > data.get("ttl", DEFAULT_TTL):
                os.remove(path)
                cleaned += 1
        except Exception:
            os.remove(path)
            cleaned += 1
    return cleaned