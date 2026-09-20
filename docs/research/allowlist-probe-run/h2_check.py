"""Does httpx really get HTTP/2 from the box, and do large responses survive it? Also cross-check with curl."""
import ssl
import subprocess
import tempfile

import h2
import httpx

from probe_lib import creds

c0 = creds()
print("httpx", httpx.__version__, "h2", h2.__version__, "openssl", ssl.OPENSSL_VERSION)
auth = (c0["PROBE_ADMIN_API_KEY"], c0["PROBE_ADMIN_API_SECRET"])
BIG = "/api/firewall/alias/search_item"
SMALL = "/api/diagnostics/system/system_time"
for label, kw in [("verify=False http2", dict(verify=False, http2=True)),
                  ("explicit ctx http2", None),
                  ("h2 only", dict(verify=False, http2=True, http1=False))]:
    if kw is None:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        kw = dict(verify=ctx, http2=True)
    for path in (SMALL, BIG):
        try:
            with httpx.Client(base_url=c0["PROBE_URL"], auth=auth, timeout=60, **kw) as c:
                r = c.get(path)
                ext = r.extensions.get("network_stream")
                alpn = ext.get_extra_info("ssl_object").selected_alpn_protocol() if ext else None
                print(label, path, r.http_version, r.status_code, len(r.content), "alpn=", alpn)
        except Exception as e:
            print(label, path, "ERROR", repr(e)[:160])

# curl with the same credentials, passed via a 0600 config file so they never reach argv or stdout
with tempfile.NamedTemporaryFile("w", suffix=".curlrc") as f:
    f.write(f'user = "{auth[0]}:{auth[1]}"\n')
    f.flush()
    for flag in ("--http1.1", "--http2"):
        for path in (SMALL, BIG):
            p = subprocess.run(["curl", "-sk", flag, "-K", f.name, "-o", "/dev/null", "-w",
                                "%{http_version} %{http_code} %{size_download} %{errormsg}", c0["PROBE_URL"] + path],
                               capture_output=True, text=True)
            print("curl", flag, path, p.stdout.strip(), "rc=", p.returncode)
