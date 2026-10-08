#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Create _cloud folder tree in library, then move misplaced nodes into it."""
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

CLOUD_TREE = {
    "_cloud": "_cloud 成品精选（云端发布包）",
    "_cloud/docs": "docs 文档",
    "_cloud/emojis": "emojis 表情包GIF",
    "_cloud/models": "models 三维模型",
    "_cloud/models/v1": "v1 首版模型",
    "_cloud/models/v4": "v4 绑定版模型",
    "_cloud/videos": "videos 动态视频",
}


def run(args, stdin_data=TOKEN):
    return subprocess.run(args, input=stdin_data, capture_output=True,
                          text=True, encoding="utf-8", errors="replace")


def create(title, parent):
    p = run([sys.executable, SKILL + "/manage/create_folder.py", "--token-stdin",
             "--title", title, "--space-id", SPACE, "--parent-id", parent])
    out = (p.stdout or "").strip()
    if out.startswith("KS_FOLDER_CREATE"):
        return out.split("\t")[1]
    print("  create failed:", title, out[:160], flush=True)
    return None


def main():
    folders = json.load(open(MAP, encoding="utf-8"))
    # level-wise create
    for rel in sorted(CLOUD_TREE, key=lambda s: s.count("/")):
        name = CLOUD_TREE[rel]
        parent = ROOT if "/" not in rel else folders[rel.rsplit("/", 1)[0]]
        nid = create(name, parent)
        if nid:
            folders[rel] = nid
            print("OK folder", rel, nid, flush=True)
    json.dump(folders, open(MAP, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    # list root children
    p = run([sys.executable, SKILL + "/space_api.py", "space.workspace.list-node",
             "--token-stdin", "--space-id", SPACE, "--parent-node-id", ROOT])
    out = (p.stdout or "").strip()
    nodes = json.loads(out)["data"]["nodes"]
    print("root children:", len(nodes), flush=True)
    by_title = {}
    for n in nodes:
        by_title.setdefault(n["title"], []).append(n["id"])

    log = json.load(open(LOG, encoding="utf-8"))
    cloud = [x for x in log if x["rel"].startswith("_cloud/") and x["ok"]]
    tasks = []
    unresolved = []
    for item in cloud:
        rel = item["rel"]
        base = os.path.basename(rel)
        target_rel = rel.rsplit("/", 1)[0]
        tgt = folders.get(target_rel)
        cands = by_title.get(base)
        if not tgt or not cands:
            unresolved.append(rel)
            continue
        nid = cands.pop(0)
        by_title[base] = cands
        tasks.append((nid, tgt, rel))
    print("to move:", len(tasks), "unresolved:", len(unresolved), flush=True)
    if unresolved:
        print(json.dumps(unresolved, ensure_ascii=False, indent=1), flush=True)

    def do(t):
        nid, tgt, rel = t
        for _ in range(2):
            p = run([sys.executable, SKILL + "/space_api.py", "space.workspace.move-node",
                     "--token-stdin", "--node-id", nid, "--target-parent-id", tgt])
            o = (p.stdout or "").strip()
            if '"data"' in o and '"error"' not in o.split("\n")[0][:40]:
                return True
        print("  move failed:", rel, o[:120], flush=True)
        return False

    with ThreadPoolExecutor(max_workers=6) as ex:
        res = list(ex.map(do, tasks))
    print("moved ok:", sum(1 for r in res if r), "/", len(tasks), flush=True)


if __name__ == "__main__":
    main()
