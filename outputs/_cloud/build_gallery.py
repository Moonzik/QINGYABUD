# -*- coding: utf-8 -*-
"""
扫描 outputs/_cloud/ 下的成品，生成一个可浏览的成果总览画廊 index.html。
分类：表情包 GIF / 3D 模型 / 视频 / 文档。
"""
import os, html, datetime

ROOT = os.path.dirname(os.path.abspath(__file__))  # outputs/_cloud

# 拼音 -> 中文 标注（用于表情包更友好的说明）
PINYIN_CN = {
    "jiayou": "加油", "meiguanxi": "没关系", "shoudao": "收到", "xiangni": "想你",
    "bukeqi": "不客气", "kaixin": "开心", "tietie": "贴贴", "baobao": "抱抱",
    "ele": "饿了", "cengceng": "蹭蹭", "zaine": "在呢", "emo": "emo",
    "xiexie": "谢谢", "bixin": "比心", "weiqu": "委屈", "haixiu": "害羞",
    "sikao": "思考", "wink": "眨眼", "aiya": "哎呀", "qinqin": "亲亲",
    "miyankxiao": "眯眼笑", "duilian": "对联",
}

def cn_label(fname):
    base = os.path.splitext(os.path.basename(fname))[0]
    # 去掉 qy_ 前缀和序号
    parts = base.split("_")
    tail = parts[-1] if parts else base
    if tail in PINYIN_CN:
        return PINYIN_CN[tail]
    # 尝试组合
    for k, v in PINYIN_CN.items():
        if k in base:
            return v
    return base

def card_img(src, cap, cls=""):
    return f'''<figure class="card {cls}">
      <img loading="lazy" src="{html.escape(src)}" alt="{html.escape(cap)}">
      <figcaption>{html.escape(cap)}</figcaption>
    </figure>'''

def card_video(src, cap):
    return f'''<figure class="card">
      <video loading="lazy" controls preload="metadata" src="{html.escape(src)}#t=0.5"></video>
      <figcaption>{html.escape(cap)}</figcaption>
    </figure>'''

def card_link(href, label, desc=""):
    return f'''<a class="model-card" href="{html.escape(href)}" target="_blank" rel="noopener">
      <span class="model-title">{html.escape(label)}</span>
      <span class="model-desc">{html.escape(desc)}</span>
      <span class="model-go">打开 ↗</span>
    </a>'''

def list_files(folder, exts):
    folder = os.path.join(ROOT, folder)
    if not os.path.isdir(folder):
        return []
    out = []
    for f in sorted(os.listdir(folder)):
        if any(f.lower().endswith(e) for e in exts):
            out.append(os.path.join(folder, f))
    return out

# ---- 表情包 ----
gifs = list_files("emojis", [".gif"])
emoji_cards = "\n".join(card_img("emojis/" + os.path.basename(p), cn_label(p)) for p in gifs)

# ---- 视频 ----
def video_label(fname):
    base = os.path.splitext(os.path.basename(fname))[0]
    base = base.split("_2026")[0]          # 去掉时间戳
    return base.replace("_", " ").strip()

videos = list_files("videos", [".mp4"])
video_cards = "\n".join(card_video("videos/" + os.path.basename(p), video_label(p)) for p in videos)

# ---- 3D 模型 ----
# v4 当前版：优先展示 html 查看器 + 预览图；glb 作为下载
def model_section(title, folder):
    htmls = list_files(folder, [".html"])
    pngs = list_files(folder, [".png"])
    glbs = list_files(folder, [".glb"])
    zips = list_files(folder, [".zip"])
    cards = []
    # 查看器卡片（预览图 -> html）
    for h in htmls:
        name = os.path.basename(h)
        # 找同名或含关键词的预览图
        thumb = ""
        for p in pngs:
            pb = os.path.basename(p)
            if pb.split(".")[0] in name or name.split(".")[0] in pb:
                thumb = "models/" + os.path.relpath(p, os.path.join(ROOT, "models")).replace("\\", "/")
                break
        label = name.replace(".html", "").replace("qingya_3d_", "").replace("_", " ").strip()
        inner = f'<span class="model-title">{html.escape(label)}</span>'
        if thumb:
            inner = f'<img class="model-thumb" loading="lazy" src="{html.escape(thumb)}" alt="{html.escape(label)}">{inner}'
        cards.append(f'''<a class="model-card" href="models/{os.path.relpath(h, os.path.join(ROOT,"models")).replace(chr(92),"/")}" target="_blank" rel="noopener">
      {inner}
      <span class="model-go">打开 3D 查看器 ↗</span>
    </a>''')
    # glb 下载（若无对应查看器）
    used_glb = False
    for g in glbs:
        gb = os.path.basename(g)
        # 若已有同名 html 查看器则跳过（避免重复）
        if any(gb.replace(".glb", "") in os.path.basename(h) for h in htmls):
            continue
        label = gb.replace(".glb", "").replace("qingya_3d_", "").replace("_", " ").strip()
        cards.append(f'''<a class="model-card" href="models/{os.path.relpath(g, os.path.join(ROOT,"models")).replace(chr(92),"/")}" download>
      <span class="model-title">{html.escape(label)}</span>
      <span class="model-desc">.glb 模型文件</span>
      <span class="model-go">下载 ↧</span>
    </a>''')
    if zips:
        for z in zips:
            zb = os.path.basename(z)
            label = zb.replace(".zip", "").replace("qingya_3d_", "").replace("_", " ").strip()
            cards.append(f'''<a class="model-card" href="models/{os.path.relpath(z, os.path.join(ROOT,"models")).replace(chr(92),"/")}" download>
      <span class="model-title">{html.escape(label)}</span>
      <span class="model-desc">.zip 打包</span>
      <span class="model-go">下载 ↧</span>
    </a>''')
    return f'<h2>{html.escape(title)}</h2><div class="model-grid">{"".join(cards)}</div>'

models_html = model_section("3D 模型 · 当前版 v4", "models/v4") + model_section("3D 模型 · 首版", "models/v1")

# ---- 文档 ----
docs = list_files("docs", [".docx", ".pdf", ".md"])
doc_cards = "\n".join(card_link("docs/" + os.path.basename(p), os.path.basename(p),
                                "点击下载 / 查看") for p in docs)

total_files = len(gifs) + len(videos) + len(list_files("models", [".html",".glb",".zip"])) + len(docs)

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
  .card figcaption {{ padding:8px 10px; font-size:13px; color:var(--txt); text-align:center; }}
  .model-grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(220px,1fr)); gap:14px; }}
  .model-card {{ background:var(--card); border-radius:14px; padding:16px; text-decoration:none; color:var(--txt);
    display:flex; flex-direction:column; gap:6px; box-shadow:0 2px 10px rgba(0,0,0,.25); transition:transform .12s; }}
  .model-card:hover {{ transform:translateY(-3px); }}
  .model-thumb {{ width:100%; height:130px; object-fit:cover; border-radius:10px; background:#0b0f13; }}
  .model-title {{ font-size:15px; font-weight:600; }}
  .model-desc {{ font-size:12px; color:var(--muted); }}
  .model-go {{ font-size:13px; color:var(--accent); margin-top:auto; }}
  footer {{ color:var(--muted); font-size:12px; padding:0 24px 40px; }}
</style>
</head>
<body>
<header>
  <h1>🌱 青芽BUD · 成果云端总览</h1>
  <div class="sub">正向行为引导电子疗愈宠物 IP · 共 {total_files} 个成品文件 · 生成于 {datetime.date.today().isoformat()}</div>
</header>
<main>
  <h2>表情包（{len(gifs)} 张 · 透明 GIF）</h2>
  <div class="grid">{emoji_cards}</div>

  {models_html}

  <h2>动态视频（{len(videos)} 段 · 表情包动态源）</h2>
  <div class="grid">{video_cards}</div>

  <h2>文档</h2>
  <div class="model-grid">{doc_cards}</div>
</main>
<footer>本页为青芽BUD 项目产出物的云端索引，所有资源均托管于 WorkBuddy 云端。</footer>
</body>
</html>'''

out = os.path.join(ROOT, "index.html")
with open(out, "w", encoding="utf-8") as f:
    f.write(PAGE)
print("generated:", out, "bytes:", len(PAGE))
print("gifs:", len(gifs), "videos:", len(videos), "docs:", len(docs))
