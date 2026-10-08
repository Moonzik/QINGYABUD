#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Move misplaced _cloud nodes from library root into the _cloud folder tree."""
import collections
import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

SKILL = r"C:/wb/WorkBuddy/resources/app.asar.unpacked/resources/plugins/workbuddy-builtin/skills/library"
TOKEN = os.environ.get("WB_TOKEN", "").strip()
SPACE = "V61O49UfiLeIRb03IEDOmE"
ROOT = "MVvZHan1mHaUFXhb7CxSZ6"
LOG = r"C:/Users/XIAOMI/Desktop/青芽/WKBD/QINGYABUD/.workbuddy/tmp_upload/upload_log.json"
MAP = r"C:/Users/XIAOMI/Desktop/青芽/WKBD/QINGYABUD/.workbuddy/tmp_upload/folder_map.json"


def api(*args):
    p = subprocess.run([sys.executable, SKILL + "/space_api.py"] + list(args) +
                       ["--token-stdin"], input=TOKEN, capture_output=True,
                       text=True, encoding="utf-8", errors="replace")
    return (p.stdout or "").strip()


def node_name(n):
    if n.get("kind") == "web":
        return n["title"] + ".html"
    return n["title"] + ("." + n["ext"] if n.get("ext") else "")


def main():
    folders = json.load(open(MAP, encoding="utf-8"))
    nodes = json.loads(api("space.workspace.list-node", "--space-id", SPACE,
                           "--parent-node-id", ROOT))["data"]["nodes"]
    files = [n for n in nodes if n.get("kind") != "folder"]
    files.sort(key=lambda n: n.get("createdAt", 0))
    pool = collections.defaultdict(list)
    for n in files:
        pool[node_name(n)].append(n["id"])

    log = json.load(open(LOG, encoding="utf-8"))
    root_loose = [x for x in log if "/" not in x["rel"] and x["ok"]]
    cloud = [x for x in log if x["rel"].startswith("_cloud/") and x["ok"]]

    tasks = []
    unresolved = []
    # assign root loose files first (they were uploaded first -> earliest)
    for x in root_loose:
        p = pool.get(x["rel"])
        if p:
            p.pop(0)
    for x in cloud:
        rel = x["rel"]
        base = os.path.basename(rel)
        tgt = folders.get(rel.rsplit("/", 1)[0])
        p = pool.get(base)
        if not tgt or not p:
            unresolved.append(rel)
            continue
        tasks.append((p.pop(0), tgt, rel))

    print("to move:", len(tasks), "unresolved:", len(unresolved), flush=True)
    for r in unresolved:
        print("  UNRESOLVED", r, flush=True)
    # report leftovers
    left = {k: v for k, v in pool.items() if v}
    print("leftover candidates:", sum(len(v) for v in left.values()), flush=True)
    for k, v in list(left.items())[:10]:
        print("  LEFT", k, len(v), flush=True)

    def do(t):
        nid, tgt, rel = t
        for _ in range(2):
            out = api("space.workspace.move-node", "--node-id", nid,
                      "--target-parent-id", tgt)
            first = out.split("\n")[0][:60]
            if '"error"' not in first:
                return True, rel
        return False, rel + " :: " + out[:140]

    with ThreadPoolExecutor(max_workers=6) as ex:
        res = list(ex.map(do, tasks))
    bad = [r for ok, r in res if not ok]
    print("moved ok:", len(res) - len(bad), "/", len(res), flush=True)
    for b in bad[:20]:
        print("  FAIL", b, flush=True)


if __name__ == "__main__":
    main()
