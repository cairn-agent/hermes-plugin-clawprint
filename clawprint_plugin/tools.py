"""Model-facing operations. Neither operation performs network I/O."""

from __future__ import annotations

import hashlib
import json
import time
from typing import Any

PREVIEW_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "content": {"type": "string"},
        "tags": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["title", "content"],
    "additionalProperties": False,
}

VERIFY_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "content": {"type": "string"},
        "tags": {"type": "array", "items": {"type": "string"}},
        "expected_hash": {"type": "string"},
    },
    "required": ["title", "content", "expected_hash"],
    "additionalProperties": False,
}


def _normalise_text(value: str) -> str:
    return value.replace("\r\n", "\n").replace("\r", "\n")


def canonical_payload(args: dict[str, Any]) -> dict[str, Any]:
    title = _normalise_text(str(args.get("title", "")).strip())
    content = _normalise_text(str(args.get("content", "")))
    tags = args.get("tags", [])
    if not title or not content.strip():
        raise ValueError("title and non-empty content are required")
    if not isinstance(tags, list) or not all(isinstance(tag, str) and tag.strip() for tag in tags):
        raise ValueError("tags must be an array of non-empty strings")
    return {"content": content, "tags": [tag.strip() for tag in tags], "title": title}


def payload_hash(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _put(state: Any, key: str, value: dict[str, Any]) -> None:
    if hasattr(state, "set"):
        state.set(key, value)
    else:
        state[key] = value


def preview(args: dict[str, Any], *, state: Any, ttl_seconds: int = 600, now: float | None = None) -> dict[str, Any]:
    """Create a local pending proposal. This function must remain network-free."""
    if ttl_seconds <= 0:
        raise ValueError("publish_ttl_seconds must be positive")
    payload = canonical_payload(args)
    digest = payload_hash(payload)
    created = time.time() if now is None else now
    _put(state, "proposal:" + digest, {"payload": payload, "expires_at": created + ttl_seconds, "consumed": False})
    return {
        "preview": True,
        "proposal_hash": digest,
        "expires_at": created + ttl_seconds,
        "payload": payload,
        "network_performed": False,
        "publish_instruction": f"Ask the human to run /clawprint publish {digest} --confirm",
        "proof_boundary": "A later receipt may support matching-byte checks; it does not prove authorship or truth.",
    }


def verify_record(args: dict[str, Any]) -> dict[str, Any]:
    """Locally compare an expected proposal hash. It does not validate an OTS proof."""
    actual = payload_hash(canonical_payload(args))
    expected = args["expected_hash"]
    return {
        "matches": actual == expected,
        "actual_hash": actual,
        "expected_hash": expected,
        "network_performed": False,
        "ots_verified": False,
        "boundary": "This only compares the canonical payload hash. Supply a complete .ots proof to an OpenTimestamps verifier for Bitcoin-attestation validation.",
    }
