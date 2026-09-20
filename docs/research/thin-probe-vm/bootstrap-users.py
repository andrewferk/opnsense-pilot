#!/usr/bin/env python3
"""One-off bootstrap for the probe VM (wayfinder ticket #12).

Logs in to the web GUI with a session, then uses the session + CSRF token against the
MVC user API (actions checked in opnsense/core at tag 26.7.4, Auth/Api/UserController.php)
to: rotate root's password, create an admin API user and a least-privilege API user, and
mint an API key for each. Writes everything to credentials.env (mode 0600), outside any repo.

Usage: bootstrap-users.py [--dry-run]     (dry run: log in and list users only)
"""
import http.cookiejar
import json
import os
import re
import secrets
import ssl
import sys
import urllib.parse
import urllib.request

BASE = "https://127.0.0.1:10443"
PROBE = os.path.expanduser("~/.local/share/opnsense-pilot-probe")
CRED = os.path.join(PROBE, "credentials.env")
OLD_ROOT_PW = os.environ.get("PROBE_ROOT_PW", "opnsense")

LIMITED_PRIVS = ["page-system-login-logout", "page-system-status", "user-config-readonly"]

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE  # self-signed throwaway; pinned by loopback forward
jar = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(
    urllib.request.HTTPSHandler(context=ctx), urllib.request.HTTPCookieProcessor(jar)
)


def fetch(path, data=None, headers=None):
    req = urllib.request.Request(BASE + path, data=data, headers=headers or {})
    with opener.open(req, timeout=120) as r:
        return r.read().decode("utf-8", "replace")


def login():
    page = fetch("/")
    m = re.search(r'<input type="hidden" name="([^"]+)" value="([^"]+)"', page)
    form = {m.group(1): m.group(2), "usernamefld": "root", "passwordfld": OLD_ROOT_PW, "login": "1"}
    fetch("/", urllib.parse.urlencode(form).encode())
    page = fetch("/ui/auth/user")
    m = re.search(r'setRequestHeader\(\s*"X-CSRFToken",\s*"([^"]+)"', page)
    if not m:
        sys.exit("login failed or CSRF token not found")
    return m.group(1)


def api(token, path, payload=None):
    headers = {"X-CSRFToken": token}
    data = None
    if payload is not None:
        data = json.dumps(payload).encode()
        headers["Content-Type"] = "application/json"
    return json.loads(fetch("/api/" + path, data, headers))


def main():
    token = login()
    users = api(token, "auth/user/search")
    print("users:", [(u["name"], u["uuid"]) for u in users["rows"]])
    if "--dry-run" in sys.argv:
        return
    if os.path.exists(CRED):
        sys.exit(f"{CRED} already exists; refusing to overwrite")

    out = {}
    for name, privs in (("pilot-admin", ["page-all"]), ("pilot-readonly", LIMITED_PRIVS)):
        pw = secrets.token_urlsafe(24)
        r = api(token, "auth/user/add", {"user": {
            "name": name, "password": pw, "scrambled_password": "0",
            "descr": f"OPNsense Pilot probe ({name})", "priv": ",".join(privs),
        }})
        print("add", name, r)
        if r.get("result") != "saved":
            sys.exit(f"could not create {name}")
        k = api(token, f"auth/user/add_api_key/{name}", {})
        if k.get("result") != "ok":
            sys.exit(f"could not create key for {name}: {k}")
        tag = name.split("-")[1].upper()
        out[f"PROBE_{tag}_USER"] = name
        out[f"PROBE_{tag}_PASSWORD"] = pw
        out[f"PROBE_{tag}_API_KEY"] = k["key"]
        out[f"PROBE_{tag}_API_SECRET"] = k["secret"]

    root_uuid = next(u["uuid"] for u in users["rows"] if u["name"] == "root")
    root_pw = secrets.token_urlsafe(24)
    r = api(token, f"auth/user/set/{root_uuid}", {"user": {"password": root_pw}})
    print("root password:", r)
    out["PROBE_ROOT_PASSWORD"] = root_pw if r.get("result") == "saved" else OLD_ROOT_PW

    fd = os.open(CRED, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write("# OPNsense Pilot probe VM credentials. Throwaway lab only. Never commit.\n")
        f.write(f"PROBE_URL={BASE}\n")
        for k, v in out.items():
            f.write(f"{k}={v}\n")
    print("wrote", CRED)


if __name__ == "__main__":
    main()
