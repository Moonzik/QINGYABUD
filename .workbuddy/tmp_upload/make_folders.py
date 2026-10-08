#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Create mirrored folder tree in WorkBuddy library and write mapping to JSON."""
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

SKILL = r"C:/wb/WorkBuddy/resources/app.asar.unpacked/resources/plugins/workbuddy-builtin/skills/library"
TOKEN = sys.argv[1]
SPACE = "V61O49UfiLeIRb03IEDOmE"
ROOT = "MVvZHan1mHaUFXhb7CxSZ6"
OUT = sys.argv[2]

# relative local dir -> display name
TREE = {
    "emojis_v1": "emojis_v1 表情包素材",
    "emojis_v1/qp_test": "qp_test",
    "emojis_v1/v6_assets": "v6_assets 第6版素材图",
    "emojis_v1/v6_base": "v6_base 第6版底图",
    "emojis_v1/v6_gifs": "v6_gifs 成品GIF",
    "emojis_v1/v6_src": "v6_src 第6版源文件",
    "emojis_v1/v6_videos": "v6_videos 成品视频",
    "emojis_v1/videos": "videos 视频初版",
    "emojis_v1/videos_test": "videos_test 视频测试",
    "emojis_v1/videos_v4": "videos_v4 视频第四版",
    "emojis_v1/videos_v5": "videos_v5 视频第五版",
    "v2": "v2 三维模型",
    "v3": "v3 三维模型",
    "v4": "v4 绑定版最终三维模型",
    "v4/lib": "lib 前端依赖库",
}


def create(title, parent):
    p = subprocess.run(
        [sys.executable, SKILL + "/manage/create_folder.py", "--token-stdin",
         "--title", title, "--space-id", SPACE, "--parent-id", parent],
        input=TOKEN, capture_output=True, text=True, encoding="utf-8")
    out = (p.stdout or "").strip()
    if not out.startswith("KS_FOLDER_CREATE"):
        return {"title": title, "error": out or (p.stderr or "")[:200]}
    parts = out.split("\t")
    return {"title": title, "id": parts[1], "url": parts[3] if len(parts) > 3 else ""}


def main():
    mapping = {}
    errors = []
    # level 1
    l1 = {k: v for k, v in TREE.items() if "/" not in k}
    l2 = {k: v for k, v in TREE.items() if "/" in k}

    with ThreadPoolExecutor(max_workers=6) as ex:
        res = list(ex.map(lambda kv: create(kv[1], ROOT), l1.items()))
    for (rel, _), r in zip(l1.items(), res):
        if "id" in r:
            mapping[rel] = r["id"]
            print("OK  ", rel, r["id"])
        else:
            errors.append((rel, r))
            print("FAIL", rel, r)

    tasks = []
    for rel, name in l2.items():
        parent_rel = rel.rsplit("/", 1)[0]
        pid = mapping.get(parent_rel)
        if not pid:
            errors.append((rel, "parent missing"))
            continue
        tasks.append((rel, name, pid))
    with ThreadPoolExecutor(max_workers=6) as ex:
        res = list(ex.map(lambda t: create(t[1], t[2]), tasks))
    for (rel, _, _), r in zip(tasks, res):
        if "id" in r:
            mapping[rel] = r["id"]
            print("OK  ", rel, r["id"])
        else:
            errors.append((rel, r))
            print("FAIL", rel, r)

    mapping["."] = ROOT
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)
    print("ERRORS:", len(errors))
    if errors:
        print(json.dumps(errors, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
