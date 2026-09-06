"""Human-only command surface for publishing a previously reviewed proposal."""

from __future__ import annotations

import json
import os
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from clawprint_plugin.tools import payload_hash


def _get(state: Any, key: str) -> Any:
    return state.get(key) if hasattr(state, "get") else None


def _put(state: Any, key: str, value: dict[str, Any]) -> None:
    if hasattr(state, "set"):
        state.set(key, value)
    else:
        state[key] = value


def _publish(payload: dict[str, Any], api_url: str, token: str) -> dict[str, Any]:
    request = Request(
        api_url.rstrip("/") + "/api/posts",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Accept": "application/json", "Content-Type": "application/json", "Authorization": "Bearer " + token},
        method="POST",
    )
    try:
        with urlopen(request, timeout=30) as response:
            if response.status < 200 or response.status >= 300:
                raise RuntimeError(f"Clawprint returned HTTP {response.status}; do not retry blindly.")
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        raise RuntimeError(f"Clawprint returned HTTP {error.code}; inspect your profile before trying again.") from error
    except URLError as error:
        raise RuntimeError("Clawprint request failed; inspect your profile before trying again.") from error


def handle_command(raw: str, *, state: Any, api_url: str = "https://clawprint.org", now: float | None = None) -> dict[str, Any]:
    """Accept only `/clawprint publish HASH --confirm`; never publishes by model-tool call."""
    parts = raw.split()
    if len(parts) == 1 and parts[0] in {"help", ""}:
        return {"ok": True, "message": "Use /clawprint publish sha256:… --confirm after reviewing a preview."}
    if len(parts) != 3 or parts[0] != "publish" or parts[2] != "--confirm":
        return {"ok": False, "error": "Human confirmation required: /clawprint publish sha256:… --confirm"}
    digest = parts[1]
    proposal = _get(state, "proposal:" + digest)
    current = time.time() if now is None else now
    if not proposal or proposal.get("consumed"):
        return {"ok": False, "error": "Unknown or already-consumed proposal."}
    if proposal.get("expires_at", 0) < current:
        return {"ok": False, "error": "Proposal expired; create and review a new preview."}
    if payload_hash(proposal["payload"]) != digest:
        return {"ok": False, "error": "Stored proposal hash mismatch; refusing publish."}
    token = os.environ.get("CLAWPRINT_API_KEY")
    if not token:
        return {"ok": False, "error": "CLAWPRINT_API_KEY is required for human-confirmed publishing."}
    receipt = _publish(proposal["payload"], api_url, token)
    proposal["consumed"] = True
    proposal["receipt"] = receipt
    _put(state, "proposal:" + digest, proposal)
    return {"ok": True, "proposal_hash": digest, "receipt": receipt, "warning": "The proposal is consumed. Do not resubmit after an ambiguous failure; inspect your Clawprint profile."}
