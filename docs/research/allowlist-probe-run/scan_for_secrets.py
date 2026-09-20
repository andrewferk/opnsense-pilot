"""Fail if any credential value, API key id, seed secret marker, or private-key-looking field value is in this directory."""
import os
import re
import sys

from probe_lib import creds

HERE = os.path.dirname(os.path.abspath(__file__))
needles = {k: v for k, v in creds().items() if k != "PROBE_URL" and not k.endswith("_USER") and len(v) > 8}
bad = 0
for root, _, files in os.walk(HERE):
    for name in files:
        p = os.path.join(root, name)
        text = open(p, errors="replace").read()
        hits = [k for k, v in needles.items() if v in text]
        if "SEEDSECRET" in text and not name.endswith(".py"):
            hits.append("SEEDSECRET marker")
        if re.search(r'"(privkey|psk|password|ddns_domain_key_secret)": "(?!<REDACTED|")[^"]+"', text):
            hits.append("unredacted secret field")
        if not name.endswith(".py") and re.search(r"user_apitoken|using api key [A-Za-z0-9+/]{20}", text):
            hits.append("api key id in log/config excerpt")
        if hits:
            bad += 1
            print(os.path.relpath(p, HERE), "->", hits)
print("files with findings:", bad)
sys.exit(1 if bad else 0)
