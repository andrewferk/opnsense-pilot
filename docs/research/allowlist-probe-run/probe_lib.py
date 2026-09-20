"""Shared helpers for the allowlist probe run (wayfinder ticket #13).

Credentials are read from the probe directory outside the repo and are never printed.
Run scripts with:  uv run --with 'httpx[http2]' python <script>
"""
import os

import httpx

PROBE = os.path.expanduser("~/.local/share/opnsense-pilot-probe")


def creds():
    out = {}
    with open(os.path.join(PROBE, "credentials.env")) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                out[k] = v
    return out


def client(role, http2=False, **kw):
    """role: 'admin' | 'readonly' | 'none'. Never follows redirects."""
    c = creds()
    http1 = kw.pop("http1", True)
    auth = None
    if role != "none":
        tag = role.upper()
        auth = (c[f"PROBE_{tag}_API_KEY"], c[f"PROBE_{tag}_API_SECRET"])
    return httpx.Client(
        base_url=c["PROBE_URL"], auth=auth, verify=False, http2=http2,
        http1=http1,
        follow_redirects=False, timeout=kw.pop("timeout", 120), **kw,
    )
