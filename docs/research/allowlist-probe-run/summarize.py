"""Build results/capability-table.md from the three result sets, plus a few fixture facts."""
import collections
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))


def load(label):
    return {r["id"]: r for r in json.load(open(os.path.join(HERE, "results", label + ".json")))}


adm, mini, wide = load("admin"), load("readonly-minimal"), load("readonly-wide")
lines = ["| # | Call | admin | limited, minimal privs | limited, least-privilege set | bytes | s | rows | same shape as admin | non-empty secret fields |",
         "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
for eid, a in adm.items():
    w, m = wide[eid], mini[eid]
    same = "n/a" if w.get("status") != 200 or "shape_sha" not in a else ("yes" if a.get("shape_sha") == w.get("shape_sha") else "NO")
    lines.append(f"| {eid} | `{a['method']} {a['path']}` | {a['status']} | {m['status']} | {w['status']} | {a['bytes']} | "
                 f"{w.get('seconds', '')} | {a.get('rows', '')} | {same} | {', '.join(a.get('secret_fields_nonempty') or []).replace('90e10f06-368c-4194-a553-e26c2f2977da', '<uuid>')} |")
open(os.path.join(HERE, "results", "capability-table.md"), "w").write("\n".join(lines) + "\n")
print("\n".join(lines))

f1 = json.load(open(os.path.join(HERE, "fixtures", "readonly-wide", "F1.json")))
print("\nF1 row keys:", [k for k in f1["shape"] if k.startswith("rows[].")][:80])
print("marker leaks:", [(k, v.get("marker_leak")) for k, v in wide.items() if v.get("marker_leak")])
tot = collections.Counter(v.get("status") for v in wide.values())
print("wide statuses:", dict(tot), "| total seconds:", round(sum(v.get("seconds", 0) for v in wide.values()), 1))
