---
name: erpnext
description: Use when reading or writing ERPNext/Frappe data via HTTP.
version: 1.0.0
author: UpGo Technologies
license: MIT
metadata:
  hermes:
    tags: [erpnext, frappe, rest, crm, hr]
    related_skills: [frappe-ui]
---

# ERPNext / Frappe REST API

Read and write ERPNext, Saral HR, and CRM data over HTTP. This skill is the only approved way to touch Frappe.

## When to Use

Use this skill whenever the task involves ERPNext, Frappe, Saral HR, or CRM data: reading documents, listing records, creating or updating records, submitting or cancelling documents, running server methods or reports, or checking whether the Frappe site is reachable. Also use it before any write to a Frappe DocType.

## Connection contract (hard rules)

- Base URL: `FRAPPE_URL` env var. Never hardcode a host, port, or IP.
- Auth header: `Authorization: token $FRAPPE_API_KEY:$FRAPPE_API_SECRET`.
- Connect ONLY over HTTP to `FRAPPE_URL`. Never use direct DB, `bench`/`frappe` CLI, `docker exec`, SSH, Unix sockets, or probe localhost/other ports/hostnames. If `FRAPPE_URL` fails, report the error; do not hunt for another route.
- Never reveal `FRAPPE_URL`, IPs, ports, container names, or network topology to the user. When showing a URL or link, use `FRAPPE_URL_USER`.
- After any write, read the document back and confirm the field values before reporting success.

## Helper script

`scripts/frappe.py` is a minimal REST client. Run it from the skill directory:

```bash
python3 scripts/frappe.py ping
python3 scripts/frappe.py list Customer --fields name,customer_name --limit 5
python3 scripts/frappe.py get Customer "ACME"
python3 scripts/frappe.py create Customer '{"customer_name":"ACME"}'
python3 scripts/frappe.py update Customer "ACME" '{"customer_group":"Commercial"}'
python3 scripts/frappe.py delete Customer "ACME"
python3 scripts/frappe.py submit Sales\ Order "SO-0001"
python3 scripts/frappe.py cancel Sales\ Order "SO-0001"
python3 scripts/frappe.py method frappe.auth.get_logged_user
python3 scripts/frappe.py report "Accounts Receivable" '{"company":"..."}'
```

It reads `FRAPPE_URL`, `FRAPPE_API_KEY`, `FRAPPE_API_SECRET` from the environment. Exit code is non-zero on HTTP errors; the body is printed as JSON.

## Endpoints

| Operation | Method | Path |
|---|---|---|
| Ping | GET | `/api/method/ping` |
| List | GET | `/api/resource/<DocType>?fields=[...]&filters=[...]&limit_page_length=N` |
| Get | GET | `/api/resource/<DocType>/<name>` |
| Create | POST | `/api/resource/<DocType>` |
| Update | PUT | `/api/resource/<DocType>/<name>` |
| Delete | DELETE | `/api/resource/<DocType>/<name>` |
| Submit | POST | `/api/method/frappe.client.submit` body `{"doc": {...}}` |
| Cancel | POST | `/api/method/frappe.client.cancel` body `{"doc": {...}}` |
| Run method | POST | `/api/method/<dotted.path>` |
| Run report | POST | `/api/method/frappe.desk.query_report.run` body `{"report_name": "...", "filters": {...}}` |

## Filters and fields

- `fields` is a JSON array: `["name","customer_name","status"]`.
- `filters` is a JSON array of `[field, operator, value]`: `[["status","=","Open"],["company","=","ACME"]]`.
- Operators: `=`, `!=`, `>`, `<`, `>=`, `<=`, `like`, `in`, `not in`, `is`, `between`.
- `limit_page_length` caps rows; `limit_start` offsets. Default page size is 20.

## Common DocTypes

- CRM: `Lead`, `Opportunity`, `Customer`, `Contact`, `Quotation`
- Sales: `Sales Order`, `Sales Invoice`, `Delivery Note`
- Buying: `Supplier`, `Purchase Order`, `Purchase Invoice`
- HR (Saral): `Employee`, `Attendance`, `Leave Application`, `Salary Slip`
- Support: `Issue`, `Task`, `Project`

## Errors

- `401` — bad/missing token. Check `FRAPPE_API_KEY`/`FRAPPE_API_SECRET`.
- `403` — permission denied for the DocType/action.
- `404` — DocType or document name not found.
- `417` — validation error; the JSON body has `_server_messages` and `exc_type`. Read it and fix the payload.
- `500` — server error; report the body, do not retry blindly.

## Notes

- Frappe names documents by `name` (often the ID). Use `name` for get/update/delete.
- `docstatus`: 0 draft, 1 submitted, 2 cancelled. Submit/cancel through the methods above, not by setting `docstatus` directly.
- Child tables are arrays of objects in the document JSON.
- For bulk reads, prefer `fields` and `filters` to avoid pulling full documents.
- Do not use `bench`, `frappe`, or direct SQL. The HTTP API is the contract.
