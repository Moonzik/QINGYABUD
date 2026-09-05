#!/usr/bin/env python3
"""生成 24 表情上架预览大图（6列×4行网格）"""
import os
from PIL import Image, ImageDraw, ImageFont

DIR = r"C:\Users\XIAOMI\Desktop\青芽\WKBD\QINGYABUD\outputs\emojis_v1"
OUT = os.path.join(DIR, "emojis_preview_grid.png")

# 24 表情清单（编号、文件名、中文名）
ITEMS = [
    (1, "zaoan",       "早安"),
    (2, "wanan",       "晚安"),
    (3, "zaine",       "在呢"),
    (4, "jiayou",      "加油"),
    (5, "weiqu",       "委屈"),
    (6, "emo",         "emo抱抱"),
    (7, "kaixin",      "开心"),
    (8, "baobao",      "抱抱"),
    (9, "bixin",       "比心"),
    (10, "cengceng",   "蹭蹭"),
    (11, "qinqin",     "亲亲"),
    (12, "tietie",     "贴贴"),
    (13, "shoudao",    "收到"),
    (14, "xiexie",     "谢谢"),
    (15, "bukeqi",     "不客气"),
    (16, "meiguanxi",  "没关系"),
    (17, "sikao",      "思考"),
    (18, "aiya",       "哎呀"),
    (19, "ele",        "饿了"),
    (20, "xiangni",    "想你啦"),
    (21, "duilian_wink",      "怼脸wink"),
    (22, "duilian_qinqin",    "怼脸亲亲"),
    (23, "duilian_haixiu",    "怼脸害羞"),
    (24, "duilian_miyankxiao","怼脸眯眼笑"),
]

CELL = 240          # 每格主图尺寸
LABEL_H = 50        # 标签区高度
PAD = 24            # 网格内间距
MARGIN = 48         # 外边距
TITLE_H = 140       # 标题区高度

COLS = 6
ROWS = 4
GRID_W = MARGIN*2 + COLS*CELL + (COLS-1)*PAD
GRID_H = TITLE_H + ROWS*(CELL+LABEL_H) + (ROWS-1)*PAD + MARGIN

# 浅薄荷绿背景
BG = (244, 250, 244)
TITLE = (60, 90, 60)
LABEL = (60, 90, 60)
SUB = (140, 170, 140)
GRID_LINE = (220, 235, 220)

canvas = Image.new("RGBA", (GRID_W, GRID_H), BG + (255,))
draw = ImageDraw.Draw(canvas)

# 尝试加载中文字体（用 system 字体）
def load_font(size, bold=False):
    candidates = [
        r"C:\Windows\Fonts\msyh.ttc",          # 微软雅黑
        r"C:\Windows\Fonts\msyh.ttf",
        r"C:\Windows\Fonts\simhei.ttf",        # 黑体
        r"C:\Windows\Fonts\simsun.ttc",        # 宋体
        r"C:\Users\XIAOMI\.workbuddy\binaries\fonts",
    ]
    for c in candidates:
        if os.path.exists(c):
            try:
                return ImageFont.truetype(c, size)
            except Exception:
                pass
    return ImageFont.load_default()

f_title = load_font(46, bold=True)
f_sub = load_font(24)
f_label = load_font(22)
f_num = load_font(20, bold=True)

# 标题
title_text = "青芽 BUD · 24 表情包 · 微信表情包上架预览"
sub_text = "Qingya IP · WeChat Sticker Pack · V1.0 · 2026.09.05"
draw.text((MARGIN, 36), title_text, font=f_title, fill=TITLE)
draw.text((MARGIN, 100), sub_text, font=f_sub, fill=SUB)

# 标题区底部细线
draw.line([(MARGIN, TITLE_H+10), (GRID_W-MARGIN, TITLE_H+10)], fill=GRID_LINE, width=2)

# 24 表情网格
for idx, (num, key, cn) in enumerate(ITEMS):
    row = idx // COLS
    col = idx % COLS
    x = MARGIN + col * (CELL + PAD)
    y = TITLE_H + row * (CELL + LABEL_H + PAD)

    # 背景圆角卡片
    card = Image.new("RGBA", (CELL, CELL + LABEL_H), (255, 255, 255, 255))
    # 轻微圆角（用抗锯齿mask）—— 直接画矩形
    draw.rectangle([x-4, y-4, x+CELL+4, y+CELL+LABEL_H+4], outline=GRID_LINE, width=2)

    # 表情图（用 GIF 第一帧）
    src = os.path.join(DIR, f"qy_{num:02d}_{key}.gif")
    if os.path.exists(src):
        g = Image.open(src)
        g.seek(0)
        first = g.convert("RGBA")
        # 已经 240x240 直接贴
        canvas.paste(first, (x, y), first)

    # 表情编号 + 中文名
    num_text = f"{num:02d}"
    draw.text((x+10, y+CELL+12), num_text, font=f_num, fill=SUB)
    # 计算中文标签宽度，右对齐
    bbox = draw.textbbox((0, 0), cn, font=f_label)
    tw = bbox[2] - bbox[0]
    draw.text((x+CELL - tw - 10, y+CELL+14), cn, font=f_label, fill=LABEL)

canvas.convert("RGB").save(OUT, optimize=True)
print(f"Saved {OUT}  {os.path.getsize(OUT)/1024:.1f} KB  size={canvas.size}")