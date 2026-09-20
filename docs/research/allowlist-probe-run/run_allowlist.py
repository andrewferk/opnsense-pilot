"""Run every allowlist entry as one role and record what came back.

  run_allowlist.py --role admin|readonly|none --label NAME [--fixtures]

Writes results/NAME.json (one row per entry) and, with --fixtures, sanitized bodies
under fixtures/NAME/. Secrets are redacted by key name and by the seed marker.
"""
import argparse
import hashlib
import json
import os
import re
import time

from allowlist import ALLOWLIST, NEVER_SAVE, request_kwargs
from probe_lib import client

HERE = os.path.dirname(os.path.abspath(__file__))
SECRET_KEY = re.compile(r"(privkey|psk|passw|secret|apikey|api_key|shared_key|tls_key|^key$)", re.I)


def shape(v, prefix="", out=None):
    """Sorted set of key paths; list elements collapse to []; option dicts collapse to {opt}."""
    out = set() if out is None else out
    if isinstance(v, dict):
        if v and all(isinstance(x, dict) and "selected" in x for x in v.values()):
            out.add(prefix + "{opt}")
        else:
            for k, x in v.items():
                shape(x, f"{prefix}.{k}" if prefix else k, out)
    elif isinstance(v, list):
        for x in v[:50]:
            shape(x, prefix + "[]", out)
        if not v:
            out.add(prefix + "[]")
    else:
        out.add(prefix)
    return out


def secrets_present(v, path="", out=None):
    out = [] if out is None else out
    if isinstance(v, dict):
        for k, x in v.items():
            p = f"{path}.{k}" if path else k
            if SECRET_KEY.search(k) and isinstance(x, str) and x:
                out.append(p)
            secrets_present(x, p, out)
    elif isinstance(v, list):
        for x in v:
            secrets_present(x, path + "[]", out)
    return sorted(set(out))


def sanitize(v, key=""):
    if isinstance(v, dict):
        return {k: sanitize(x, k) for k, x in v.items()}
    if isinstance(v, list):
        kept = [sanitize(x, key) for x in v[:3]]
        if len(v) > 3:
            kept.append(f"<{len(v) - 3} more rows truncated>")
        return kept
    if isinstance(v, str):
        if v and SECRET_KEY.search(key):
            return "<REDACTED>"
        if "SEEDSECRET" in v:
            return "<REDACTED-SEED-MARKER>"
        if len(v) > 300:
            return v[:120] + f"<truncated, {len(v)} chars>"
    return v


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--role", required=True)
    ap.add_argument("--label", required=True)
    ap.add_argument("--fixtures", action="store_true")
    ap.add_argument("--only", default="")
    a = ap.parse_args()
    only = set(a.only.split(",")) if a.only else None
    fixdir = os.path.join(HERE, "fixtures", a.label)
    if a.fixtures:
        os.makedirs(fixdir, exist_ok=True)
    os.makedirs(os.path.join(HERE, "results"), exist_ok=True)
    rows = []
    with client(a.role) as c:
        for eid, method, path in ALLOWLIST:
            if only and eid not in only:
                continue
            t0 = time.time()
            try:
                r = c.request(method, path, **request_kwargs(eid))
            except Exception as e:  # transport failure is a finding, not a crash
                rows.append({"id": eid, "method": method, "path": path, "error": repr(e)[:300], "t_start": t0})
                print(eid, "ERROR", repr(e)[:120])
                continue
            dt = time.time() - t0
            ctype = r.headers.get("content-type", "")
            row = {"id": eid, "method": method, "path": path, "status": r.status_code, "content_type": ctype,
                   "bytes": len(r.content), "seconds": round(dt, 3), "t_start": round(t0, 3),
                   "http_version": r.http_version, "location": r.headers.get("location"),
                   "transfer_encoding": r.headers.get("transfer-encoding"),
                   "marker_leak": "SEEDSECRET" in r.text if eid not in NEVER_SAVE else None}
            body = None
            if "json" in ctype:
                try:
                    body = r.json()
                except Exception:
                    row["json_error"] = True
            if body is not None:
                sh = sorted(shape(body))
                row["shape_sha"] = hashlib.sha256("\n".join(sh).encode()).hexdigest()[:12]
                row["top_keys"] = sorted(body) if isinstance(body, dict) else f"list[{len(body)}]"
                if isinstance(body, dict) and isinstance(body.get("rows"), list):
                    row["rows"] = len(body["rows"])
                    row["total"] = body.get("total")
                    row["rowCount"] = body.get("rowCount")
                row["secret_fields_nonempty"] = secrets_present(body)
                if r.status_code != 200:
                    row["body"] = sanitize(body)
                if a.fixtures and eid not in NEVER_SAVE:
                    with open(os.path.join(fixdir, f"{eid}.json"), "w") as f:
                        json.dump({"request": {"method": method, "path": path, **request_kwargs(eid)},
                                   "status": r.status_code, "shape": sh, "body": sanitize(body)}, f, indent=1, sort_keys=True)
            else:
                row["text_head"] = None if eid in NEVER_SAVE else sanitize(r.text[:200])
            rows.append(row)
            print(eid, r.status_code, row["bytes"], f"{dt:.2f}s", row.get("rows", ""), row.get("secret_fields_nonempty") or "")
    with open(os.path.join(HERE, "results", a.label + ".json"), "w") as f:
        json.dump(rows, f, indent=1)


if __name__ == "__main__":
    main()
