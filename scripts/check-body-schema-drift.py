#!/usr/bin/env python3
"""check-body-schema-drift.py — diff request/response/parameter schemas.

Compares two OpenAPI 3 documents on the operations they share (matched by
path + method) and emits a delta line for each (operation, kind) where the
resolved schema differs.

Usage:
    check-body-schema-drift.py <wrapper.json> <live.json>

Intended to be invoked by check-spec-drift.sh after the path/method-level
inventory diff. Stdlib-only.

Exit codes:
    0  no body-schema drift
    1  drift detected
    2  usage / read error
"""

from __future__ import annotations

import json
import sys
from typing import Any

METHODS = ("get", "post", "put", "patch", "delete")


def load(path: str) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def resolve_ref(doc: dict[str, Any], ref: str, seen: frozenset[str]) -> Any:
    """Resolve a local $ref like '#/components/schemas/Foo'.

    Cycles are broken by returning a sentinel so repeated visits compare equal.
    """
    if not ref.startswith("#/"):
        return {"$unresolved-ref": ref}
    if ref in seen:
        return {"$cycle": ref}
    parts = ref[2:].split("/")
    node: Any = doc
    for p in parts:
        if not isinstance(node, dict) or p not in node:
            return {"$unresolved-ref": ref}
        node = node[p]
    return _normalize(doc, node, seen | {ref})


def _normalize(doc: dict[str, Any], node: Any, seen: frozenset[str]) -> Any:
    """Recursively expand $ref and return a comparable structure."""
    if isinstance(node, dict):
        if "$ref" in node and isinstance(node["$ref"], str):
            return resolve_ref(doc, node["$ref"], seen)
        return {k: _normalize(doc, v, seen) for k, v in node.items()}
    if isinstance(node, list):
        return [_normalize(doc, v, seen) for v in node]
    return node


def normalize(doc: dict[str, Any], node: Any) -> Any:
    return _normalize(doc, node, frozenset())


def stable(node: Any) -> str:
    return json.dumps(node, sort_keys=True, separators=(",", ":"))


def schema_summary(a: Any, b: Any) -> str:
    """Best-effort short summary of how schema `a` differs from schema `b`.

    Reports added/removed required, added/removed top-level properties, and
    root type changes. Falls back to 'schema body changed' if none of those
    cleanly apply.
    """
    if not isinstance(a, dict) or not isinstance(b, dict):
        return "schema body changed (non-object root)"
    bits: list[str] = []

    a_req = set(a.get("required", []) or [])
    b_req = set(b.get("required", []) or [])
    if a_req != b_req:
        added = sorted(b_req - a_req)
        removed = sorted(a_req - b_req)
        if added:
            bits.append(f"added required: {', '.join(added)}")
        if removed:
            bits.append(f"removed required: {', '.join(removed)}")

    a_props = set((a.get("properties") or {}).keys())
    b_props = set((b.get("properties") or {}).keys())
    if a_props != b_props:
        added = sorted(b_props - a_props)
        removed = sorted(a_props - b_props)
        if added:
            bits.append(f"added properties: {', '.join(added)}")
        if removed:
            bits.append(f"removed properties: {', '.join(removed)}")

    a_type = a.get("type")
    b_type = b.get("type")
    if a_type != b_type:
        bits.append(f"type change: {a_type} -> {b_type}")

    if not bits:
        bits.append("schema body changed (deep diff)")

    return "; ".join(bits)


def request_bodies(doc: dict[str, Any], op: dict[str, Any]) -> dict[str, Any]:
    """Return {content_type: normalized_schema} for an operation's requestBody."""
    rb = op.get("requestBody")
    if not rb:
        return {}
    rb = normalize(doc, rb)
    if not isinstance(rb, dict):
        return {}
    out: dict[str, Any] = {}
    for ct, media in (rb.get("content") or {}).items():
        if isinstance(media, dict) and "schema" in media:
            out[ct] = media["schema"]
    return out


def parameters(doc: dict[str, Any], op: dict[str, Any]) -> dict[tuple[str, str], Any]:
    """Return {(in, name): normalized_param} for an operation's parameters."""
    params = op.get("parameters") or []
    out: dict[tuple[str, str], Any] = {}
    for p in params:
        norm = normalize(doc, p)
        if not isinstance(norm, dict):
            continue
        key = (norm.get("in", "?"), norm.get("name", "?"))
        out[key] = norm
    return out


def responses(doc: dict[str, Any], op: dict[str, Any]) -> dict[tuple[str, str], Any]:
    """Return {(status, content_type): normalized_schema} for response bodies."""
    resps = op.get("responses") or {}
    out: dict[tuple[str, str], Any] = {}
    for status, body in resps.items():
        norm = normalize(doc, body)
        if not isinstance(norm, dict):
            continue
        for ct, media in (norm.get("content") or {}).items():
            if isinstance(media, dict) and "schema" in media:
                out[(status, ct)] = media["schema"]
    return out


def operations(doc: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    """Return {(path, METHOD): operation_object}."""
    out: dict[tuple[str, str], dict[str, Any]] = {}
    for path, item in (doc.get("paths") or {}).items():
        if not isinstance(item, dict):
            continue
        for method, op in item.items():
            if method.lower() in METHODS and isinstance(op, dict):
                out[(path, method.upper())] = op
    return out


def diff_op(
    wrapper_doc: dict[str, Any],
    live_doc: dict[str, Any],
    path: str,
    method: str,
    wrapper_op: dict[str, Any],
    live_op: dict[str, Any],
) -> list[str]:
    deltas: list[str] = []

    # requestBody
    a_rb = request_bodies(wrapper_doc, wrapper_op)
    b_rb = request_bodies(live_doc, live_op)
    for ct in sorted(set(a_rb) | set(b_rb)):
        a = a_rb.get(ct)
        b = b_rb.get(ct)
        if a is None and b is not None:
            deltas.append(f"requestBody[{ct}]: added in live")
        elif a is not None and b is None:
            deltas.append(f"requestBody[{ct}]: removed in live")
        elif stable(a) != stable(b):
            deltas.append(f"requestBody[{ct}]: {schema_summary(a, b)}")

    # parameters
    a_p = parameters(wrapper_doc, wrapper_op)
    b_p = parameters(live_doc, live_op)
    for key in sorted(set(a_p) | set(b_p)):
        a = a_p.get(key)
        b = b_p.get(key)
        loc, name = key
        if a is None and b is not None:
            req = " (required)" if isinstance(b, dict) and b.get("required") else ""
            deltas.append(f"parameter[{loc}:{name}]: added in live{req}")
        elif a is not None and b is None:
            deltas.append(f"parameter[{loc}:{name}]: removed in live")
        elif stable(a) != stable(b):
            # parameters-level diff: focus on required-flag flip + schema delta
            sub: list[str] = []
            a_req = bool(isinstance(a, dict) and a.get("required"))
            b_req = bool(isinstance(b, dict) and b.get("required"))
            if a_req != b_req:
                sub.append(f"required {a_req} -> {b_req}")
            a_schema = a.get("schema") if isinstance(a, dict) else None
            b_schema = b.get("schema") if isinstance(b, dict) else None
            if stable(a_schema) != stable(b_schema):
                sub.append(f"schema: {schema_summary(a_schema or {}, b_schema or {})}")
            if not sub:
                sub.append("parameter body changed")
            deltas.append(f"parameter[{loc}:{name}]: {'; '.join(sub)}")

    # responses
    a_r = responses(wrapper_doc, wrapper_op)
    b_r = responses(live_doc, live_op)
    for key in sorted(set(a_r) | set(b_r)):
        a = a_r.get(key)
        b = b_r.get(key)
        status, ct = key
        if a is None and b is not None:
            deltas.append(f"response[{status}:{ct}]: added in live")
        elif a is not None and b is None:
            deltas.append(f"response[{status}:{ct}]: removed in live")
        elif stable(a) != stable(b):
            deltas.append(f"response[{status}:{ct}]: {schema_summary(a, b)}")

    return deltas


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        sys.stderr.write("usage: check-body-schema-drift.py <wrapper.json> <live.json>\n")
        return 2
    try:
        wrapper_doc = load(argv[1])
        live_doc = load(argv[2])
    except (OSError, json.JSONDecodeError) as exc:
        sys.stderr.write(f"ERROR: {exc}\n")
        return 2

    wrapper_ops = operations(wrapper_doc)
    live_ops = operations(live_doc)
    common = sorted(set(wrapper_ops) & set(live_ops))

    drifted: list[tuple[str, str, list[str]]] = []
    for path, method in common:
        deltas = diff_op(
            wrapper_doc,
            live_doc,
            path,
            method,
            wrapper_ops[(path, method)],
            live_ops[(path, method)],
        )
        if deltas:
            drifted.append((path, method, deltas))

    if not drifted:
        print(f"No body-schema drift across {len(common)} shared operations.")
        return 0

    total = sum(len(d) for _, _, d in drifted)
    print(f"{len(drifted)} operations with body-schema drift ({total} deltas):")
    for path, method, deltas in drifted:
        for d in deltas:
            print(f"  {path}\t{method}\t{d}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
