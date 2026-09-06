"""Hermes plugin entry point for consent-first Clawprint handoffs."""

from clawprint_plugin.tools import PREVIEW_SCHEMA, VERIFY_SCHEMA, preview, verify_record
from clawprint_plugin.commands import handle_command


def register(ctx):
    """Register two read/local tools and one human-only slash command."""
    ttl = ctx.get_config("publish_ttl_seconds", default=600)
    api_url = ctx.get_config("api_url", default="https://clawprint.org")
    ctx.register_tool(
        name="clawprint_preview",
        toolset="clawprint",
        schema=PREVIEW_SCHEMA,
        handler=lambda args, **kwargs: preview(args, state=ctx.state, ttl_seconds=ttl),
    )
    ctx.register_tool(
        name="clawprint_verify_record",
        toolset="clawprint",
        schema=VERIFY_SCHEMA,
        handler=lambda args, **kwargs: verify_record(args),
    )
    ctx.register_command(
        "clawprint",
        lambda raw: handle_command(raw, state=ctx.state, api_url=api_url),
        description="Show or publish a reviewed, hash-bound Clawprint proposal",
    )
