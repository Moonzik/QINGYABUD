#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build slim publish site from outputs/_cloud into QINGYABUD/site/."""
import html
import json
import os
import shutil
import datetime

SRC = r"C:/Users/XIAOMI/Desktop/青芽/WKBD/QINGYABUD/outputs/_cloud"
DST = r"C:/Users/XIAOMI/Desktop/青芽/WKBD/QINGYABUD/site"

PINYIN_CN = {
    "jiayou": "加油", "meiguanxi": "没关系", "shoudao": "收到", "xiangni": "想你",
    "bukeqi": "不客气", "kaixin": "开心", "tietie": "贴贴", "baobao": "抱抱",
    "ele": "饿了", "cengceng": "蹭蹭", "zaine": "在呢", "emo": "emo",
    "xiexie": "谢谢", "bixin": "比心", "weiqu": "委屈", "haixiu": "害羞",
    "sikao": "思考", "wink": "眨眼", "aiya": "哎呀", "qinqin": "亲亲",
    "miyankxiao": "眯眼笑", "duilian": "对联", "zaoan": "早安", "wanan": "晚安",
}

SKIP_EXTS = {".zip", ".glb", ".py"}


def cn_label(fname):
    base = os.path.splitext(os.path.basename(fname))[0]
    for k, v in PINYIN_CN.items():
        if k in base:
            return v
    return base


def copy_dir(rel_src, rel_dst, skip=(), allow_glb=False):
    s = os.path.join(SRC, rel_src)
    d = os.path.join(DST, rel_dst)
    os.makedirs(d, exist_ok=True)
    n = 0
    for f in sorted(os.listdir(s)):
        p = os.path.join(s, f)
        if not os.path.isfile(p):
            continue
        ext = os.path.splitext(f)[1].lower()
        if ext in SKIP_EXTS and not (allow_glb and ext == ".glb"):
            continue
        if any(f.startswith(x) for x in skip):
            continue
        shutil.copy2(p, os.path.join(d, f))
        n += 1
    return n


def main():
    if os.path.isdir(DST):
        shutil.rmtree(DST)
    os.makedirs(DST, exist_ok=True)

    n_doc = copy_dir("docs", "docs")
    n_gif = copy_dir("emojis", "emojis")
    n_vid = copy_dir("videos", "videos")
    n_v1 = copy_dir("models/v1", "models/v1", allow_glb=True)  # v1 查看器依赖同目录 glb
    # v1 keeps glb (viewer needs it), only zip skipped by SKIP_EXTS
    n_v4 = copy_dir("models/v4", "models/v4", skip=("tex_",))

    gifs = sorted(f for f in os.listdir(DST + "/emojis") if f.endswith(".gif"))
    vids = sorted(f for f in os.listdir(DST + "/videos") if f.endswith(".mp4"))
    v1 = sorted(os.listdir(DST + "/models/v1"))
    v4 = sorted(os.listdir(DST + "/models/v4"))
    docs = sorted(os.listdir(DST + "/docs"))

    emoji_cards = "\n".join(
        '<figure class="card"><img loading="lazy" src="emojis/%s" alt="%s">'
        '<figcaption>%s</figcaption></figure>' % (html.escape(f), html.escape(cn_label(f)), html.escape(cn_label(f)))
        for f in gifs)
    def vid_label(f):
        base = os.path.splitext(f)[0]
        return " ".join(base.split("_")[:4])
    video_cards = "\n".join(
        '<figure class="card"><video loading="lazy" controls preload="metadata" src="videos/%s#t=0.5"></video>'
        '<figcaption>%s</figcaption></figure>'
        % (html.escape(f), html.escape(vid_label(f))) for f in vids)

    def model_cards(folder, files):
        cards = []
        for f in files:
            if f.endswith(".html"):
                label = f.replace(".html", "").replace("qingya_3d_", "").replace("_", " ")
                cards.append(
                    '<a class="model-card" href="%s/%s" target="_blank" rel="noopener">'
                    '<span class="model-title">%s</span>'
                    '<span class="model-desc">可在浏览器里旋转、拖拽查看</span>'
                    '<span class="model-go">打开 3D 查看器 ↗</span></a>' % (folder, html.escape(f), html.escape(label)))
            elif f.endswith((".png", ".jpg")):
                cards.append(
                    '<a class="model-card" href="%s/%s" target="_blank" rel="noopener">'
                    '<img class="model-thumb" loading="lazy" src="%s/%s" alt="%s">'
                    '<span class="model-title">%s</span></a>' % (
                        folder, html.escape(f), folder, html.escape(f), html.escape(f), html.escape(f)))
            else:
                cards.append(
                    '<a class="model-card" href="%s/%s" download>'
                    '<span class="model-title">%s</span>'
                    '<span class="model-go">下载 ↧</span></a>' % (folder, html.escape(f), html.escape(f)))
        return "\n".join(cards)

    doc_cards = "\n".join(
        '<a class="model-card" href="docs/%s" target="_blank" rel="noopener">'
        '<span class="model-title">%s</span><span class="model-go">打开 ↗</span></a>'
        % (html.escape(f), html.escape(f)) for f in docs)

    total = len(gifs) + len(vids) + len(v1) + len(v4) + len(docs)

    PAGE = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>青芽BUD · 成果云端总览</title>
<style>
  :root {{ --bg:#0f1419; --panel:#171e26; --card:#1f2933; --txt:#e8eef3; --muted:#8aa0b2; --accent:#7fd1a0; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:var(--bg); color:var(--txt); font-family:-apple-system,"PingFang SC","Microsoft YaHei",system-ui,sans-serif; }}
  header {{ padding:32px 24px 12px; }}
  h1 {{ margin:0 0 6px; font-size:26px; }}
  .sub {{ color:var(--muted); font-size:14px; }}
  main {{ padding:8px 24px 60px; }}
  h2 {{ margin:34px 0 14px; font-size:19px; border-left:4px solid var(--accent); padding-left:10px; }}
  .grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(150px,1fr)); gap:14px; }}
  .card {{ background:var(--card); border-radius:14px; overflow:hidden; margin:0; box-shadow:0 2px 10px rgba(0,0,0,.25); }}
  .card img, .card video {{ width:100%; height:150px; object-fit:cover; background:#0b0f13; display:block; }}
  .card figcaption {{ padding:8px 10px; font-size:13px; text-align:center; }}
  .model-grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(220px,1fr)); gap:14px; }}
  .model-card {{ background:var(--card); border-radius:14px; padding:14px; text-decoration:none; color:var(--txt);
    display:flex; flex-direction:column; gap:6px; box-shadow:0 2px 10px rgba(0,0,0,.25); transition:transform .12s; }}
  .model-card:hover {{ transform:translateY(-3px); }}
  .model-thumb {{ width:100%; height:150px; object-fit:contain; border-radius:10px; background:#0b0f13; }}
  .model-title {{ font-size:14px; font-weight:600; word-break:break-all; }}
  .model-desc {{ font-size:12px; color:var(--muted); }}
  .model-go {{ font-size:13px; color:var(--accent); margin-top:auto; }}
  footer {{ color:var(--muted); font-size:12px; padding:0 24px 40px; }}
</style>
</head>
<body>
<header>
  <h1>🌱 青芽BUD · 成果云端总览</h1>
  <div class="sub">正向行为引导电子疗愈宠物 IP · 共 {total} 个成品文件 · 更新于 {datetime.date.today().isoformat()}</div>
</header>
<main>
  <h2>表情包（{len(gifs)} 张 · 透明 GIF）</h2>
  <div class="grid">{emoji_cards}</div>

  <h2>3D 模型 · 当前版 v4（{len(v4)} 个文件）</h2>
  <div class="model-grid">{model_cards("models/v4", v4)}</div>

  <h2>3D 模型 · 首版 v1（{len(v1)} 个文件）</h2>
  <div class="model-grid">{model_cards("models/v1", v1)}</div>

  <h2>动态视频（{len(vids)} 段）</h2>
  <div class="grid">{video_cards}</div>

  <h2>文档</h2>
  <div class="model-grid">{doc_cards}</div>
</main>
<footer>本页为青芽BUD 项目产出物的云端索引。原始 .glb / .zip 大模型文件归档在 WorkBuddy 资料库。</footer>
</body>
</html>'''

    with open(os.path.join(DST, "index.html"), "w", encoding="utf-8") as f:
        f.write(PAGE)

    size = sum(os.path.getsize(os.path.join(r, x)) for r, _, fs in os.walk(DST) for x in fs)
    print(json.dumps({"doc": n_doc, "gif": n_gif, "video": n_vid, "v1": n_v1, "v4": n_v4,
                      "size_mb": round(size / 1048576, 1)}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
