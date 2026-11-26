#!/usr/bin/env python3
"""Minimal ERPNext/Frappe REST client.

Reads FRAPPE_URL, FRAPPE_API_KEY, FRAPPE_API_SECRET from the environment.
Never prints the internal URL. Errors go to stderr; JSON to stdout.
"""
import argparse
import json
import os
import sys

import requests


def base_url():
    url = os.environ.get("FRAPPE_URL", "").strip()
    if not url:
        sys.exit("FRAPPE_URL is not set")
    return url.rstrip("/")


def auth_headers():
    key = os.environ.get("FRAPPE_API_KEY", "").strip()
    secret = os.environ.get("FRAPPE_API_SECRET", "").strip()
    if not key or not secret:
        sys.exit("FRAPPE_API_KEY / FRAPPE_API_SECRET are not set")
    return {
        "Authorization": f"token {key}:{secret}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


def call(method, path, params=None, body=None, timeout=30):
    url = base_url() + path
    try:
        r = requests.request(
            method,
            url,
            headers=auth_headers(),
            params=params,
            json=body,
            timeout=timeout,
        )
    except requests.RequestException as e:
        sys.exit(f"request failed: {type(e).__name__}: {e}")
    try:
        data = r.json()
    except ValueError:
        data = {"raw": r.text}
    if r.status_code >= 400:
        print(
            json.dumps({"status": r.status_code, "error": data}, indent=2, ensure_ascii=False),
            file=sys.stderr,
        )
        sys.exit(1)
    return data


def jload(s):
    try:
        return json.loads(s)
    except json.JSONDecodeError as e:
        sys.exit(f"invalid JSON: {e}")


def fields_json(s):
    """Accept either a JSON array or a comma-separated field list."""
    s = s.strip()
    if s.startswith("["):
        return s
    return json.dumps([x.strip() for x in s.split(",") if x.strip()])


def main():
    p = argparse.ArgumentParser(description="ERPNext/Frappe REST client")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("ping")

    lp = sub.add_parser("list")
    lp.add_argument("doctype")
    lp.add_argument("--fields", default="name")
    lp.add_argument("--filters", default="[]")
    lp.add_argument("--limit", type=int, default=20)
    lp.add_argument("--start", type=int, default=0)
    lp.add_argument("--order-by", default=None)

    gp = sub.add_parser("get")
    gp.add_argument("doctype")
    gp.add_argument("name")

    cp = sub.add_parser("create")
    cp.add_argument("doctype")
    cp.add_argument("json")

    up = sub.add_parser("update")
    up.add_argument("doctype")
    up.add_argument("name")
    up.add_argument("json")

    dp = sub.add_parser("delete")
    dp.add_argument("doctype")
    dp.add_argument("name")

    sp = sub.add_parser("submit")
    sp.add_argument("doctype")
    sp.add_argument("name")

    xp = sub.add_parser("cancel")
    xp.add_argument("doctype")
    xp.add_argument("name")

    mp = sub.add_parser("method")
    mp.add_argument("path")
    mp.add_argument("json", nargs="?", default="{}")

    rp = sub.add_parser("report")
    rp.add_argument("report_name")
    rp.add_argument("filters", nargs="?", default="{}")

    a = p.parse_args()

    if a.cmd == "ping":
        out = call("GET", "/api/method/ping")
    elif a.cmd == "list":
        params = {
            "fields": fields_json(a.fields),
            "filters": a.filters,
            "limit_page_length": a.limit,
            "limit_start": a.start,
        }
        if a.order_by:
            params["order_by"] = a.order_by
        out = call("GET", f"/api/resource/{a.doctype}", params=params)
    elif a.cmd == "get":
        out = call("GET", f"/api/resource/{a.doctype}/{a.name}")
    elif a.cmd == "create":
        out = call("POST", f"/api/resource/{a.doctype}", body=jload(a.json))
    elif a.cmd == "update":
        out = call("PUT", f"/api/resource/{a.doctype}/{a.name}", body=jload(a.json))
    elif a.cmd == "delete":
        out = call("DELETE", f"/api/resource/{a.doctype}/{a.name}")
    elif a.cmd in ("submit", "cancel"):
        doc = call("GET", f"/api/resource/{a.doctype}/{a.name}")["data"]
        method = "frappe.client.submit" if a.cmd == "submit" else "frappe.client.cancel"
        out = call("POST", f"/api/method/{method}", body={"doc": doc})
    elif a.cmd == "method":
        out = call("POST", f"/api/method/{a.path}", body=jload(a.json))
    elif a.cmd == "report":
        out = call(
            "POST",
            "/api/method/frappe.desk.query_report.run",
            body={"report_name": a.report_name, "filters": jload(a.filters)},
        )

    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
