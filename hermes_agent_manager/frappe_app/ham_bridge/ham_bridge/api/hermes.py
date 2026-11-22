"""Frappe → Hermes WebSocket JSON-RPC helpers."""

from __future__ import annotations

import asyncio
import json
import urllib.request

import frappe


@frappe.whitelist()
def ping_gateway(agent_name: str) -> dict:
    """Fetch a ticket and wait for gateway.ready over WebSocket JSON-RPC."""
    agent = frappe.get_doc("Ham Agent", agent_name)
    secret = agent.get_password("bridge_secret")
    ticket = _fetch_ticket(agent.ticket_url, secret)
    ready = asyncio.run(_wait_for_ready(agent.ws_url, ticket))
    return {"ok": True, "gateway_ready": ready, "ticket_keys": sorted(ticket.keys())}


def _fetch_ticket(ticket_url: str, secret: str) -> dict:
    request = urllib.request.Request(
        ticket_url,
        headers={"X-Ham-Bridge-Secret": secret},
        method="GET",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode())


async def _wait_for_ready(ws_url: str, ticket: dict) -> bool:
    import websockets

    protocols = ticket.get("protocols") or ["hermes-gateway-v1"]
    url = ticket.get("url") or ws_url
    if "ticket" in ticket and "ticket=" not in url:
        separator = "&" if "?" in url else "?"
        url = f"{url}{separator}ticket={ticket['ticket']}"
    async with websockets.connect(url, subprotocols=protocols) as socket:
        while True:
            raw = await asyncio.wait_for(socket.recv(), timeout=30)
            frame = json.loads(raw)
            event = frame.get("params") or frame
            if frame.get("method") == "event" and event.get("type") == "gateway.ready":
                return True
            if event.get("type") == "gateway.ready":
                return True
