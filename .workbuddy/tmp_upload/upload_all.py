#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch upload outputs/ to WorkBuddy library with mirrored folder tree."""
import json
import os
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor

SKILL = r"C:/wb/WorkBuddy/resources/app.asar.unpacked/resources/plugins/workbuddy-builtin/skills/library"
SRC = r"C:/Users/XIAOMI/Desktop/青芽/WKBD/QINGYABUD/outputs"
SPACE = "V61O49UfiLeIRb03IEDOmE"

TOKEN = os.environ.get("WB_TOKEN", "").strip()
if not TOKEN:
    print("need WB_TOKEN")
    sys.exit(1)

FOLDERS = json.load(open(sys.argv[1], encoding="utf-8"))
LOG = sys.argv[2]
WORKERS = int(sys.argv[3]) if len(sys.argv) > 3 else 6
ONLY = sys.argv[4] if len(sys.argv) > 4 else None  # optional substring filter

DRIVE_MAX = 100 * 1024 * 1024
PAGE_MAX = 50 * 1024 * 1024

lock = threading.Lock()
results = []
done = {"n": 0}
total = {"n": 0}


def collect():
    items = []
    for root, dirs, files in os.walk(SRC):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        rel_dir = os.path.relpath(root, SRC).replace("\\", "/")
        if rel_dir == ".":
            rel_dir = "."
        for fn in files:
            if fn.endswith(".pyc"):
                continue
            full = os.path.join(root, fn)
            if not os.path.isfile(full):
                continue
            items.append((rel_dir, fn, full))
    return items


def run(cmd, stdin_data):
    return subprocess.run(cmd, input=stdin_data, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")


def upload_drive(path, parent, tries=3):
    for attempt in range(tries):
        p = run([sys.executable, SKILL + "/drive/upload_drive_file.py", "--token-stdin",
                 path, "--space-id", SPACE, "--parent-id", parent], TOKEN)
        out = (p.stdout or "").strip()
        if out.startswith("KS_DRIVE_UPLOAD_OK"):
            try:
                j = json.loads(out.split("\t", 1)[1])
            except Exception:
                j = {}
            return True, j.get("url", ""), j.get("node_block_id", "")
        time.sleep(2 * (attempt + 1))
    return False, out[:220], ""


def upload_page(path, parent, tries=3):
    for attempt in range(tries):
        p = run([sys.executable, SKILL + "/page/import_html.py", "--token-stdin",
                 path, "--space-id", SPACE, "--parent-id", parent], TOKEN)
        out = (p.stdout or "").strip()
        if out.startswith("KS_IMPORT_OK"):
            try:
                j = json.loads(out.split("\t", 1)[1])
            except Exception:
                j = {}
            return True, j.get("url", ""), j.get("node_block_id", "")
        time.sleep(2 * (attempt + 1))
    return False, out[:220], ""


def job(item):
    rel_dir, fn, full = item
    size = os.path.getsize(full)
    ext = os.path.splitext(fn)[1].lower()
    parent = FOLDERS.get(rel_dir, FOLDERS["."])
    rel_path = fn if rel_dir == "." else rel_dir + "/" + fn
    if ext in (".html", ".htm", ".zip"):
        if size > PAGE_MAX:
            with lock:
                results.append({"rel": rel_path, "ok": False, "err": "TOO_BIG_PAGE>50MiB", "url": ""})
            return
        ok, url_or_err, nid = upload_page(full, parent)
        kind = "page"
    else:
        if size > DRIVE_MAX:
            with lock:
                results.append({"rel": rel_path, "ok": False, "err": "TOO_BIG_DRIVE>100MiB", "url": ""})
            return
        ok, url_or_err, nid = upload_drive(full, parent)
        kind = "drive"

    with lock:
        done["n"] += 1
        results.append({"rel": rel_path, "ok": ok, "kind": kind, "size": size,
                        "url": url_or_err if ok else "", "err": "" if ok else url_or_err,
                        "node": nid})
        if not ok or done["n"] % 20 == 0:
            print("[%d/%d] %s %s" % (done["n"], total["n"], "OK " if ok else "FAIL", rel_path),
                  flush=True)
        json.dump(results, open(LOG, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def main():
    items = collect()
    if ONLY:
        items = [i for i in items if ONLY in (i[0] + "/" + i[1])]
    global results
    if os.path.exists(LOG) and os.path.getsize(LOG) > 2:
        try:
            prev = json.load(open(LOG, encoding="utf-8"))
        except Exception:
            prev = []
        done_set = {r["rel"] for r in prev if r.get("ok")}
        results = [r for r in prev if r.get("ok")]
        items = [i for i in items
                 if (i[1] if i[0] == "." else i[0] + "/" + i[1]) not in done_set]
        print("resume: skip %d already ok" % len(done_set), flush=True)
    total["n"] = len(items)
    print("total files:", total["n"], flush=True)
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        list(ex.map(job, items))
    json.dump(results, open(LOG, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    ok = sum(1 for r in results if r["ok"])
    print("DONE ok=%d fail=%d" % (ok, len(results) - ok), flush=True)
    for r in results:
        if not r["ok"]:
            print("FAILED:", r["rel"], r.get("err", "")[:160], flush=True)


if __name__ == "__main__":
    main()
