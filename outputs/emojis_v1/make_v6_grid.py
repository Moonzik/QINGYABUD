"""v6 表情包总预览：
- 24 GIF 在微信聊天背景色上平铺
- 每张单独渲染预览帧
"""
import os
from PIL import Image, ImageDraw, ImageFont

ROOT = r"C:\Users\XIAOMI\Desktop\青芽\WKBD\QINGYABUD\outputs\emojis_v1"
GIF_DIR = os.path.join(ROOT, "v6_gifs")
OUT = os.path.join(ROOT, "v6_grid_preview.png")

CHAT_BG = (237, 237, 237)   # 微信聊天背景
CELL = 200                  # 每格尺寸
PAD = 10
COLS = 6
NAMES = [
    "01_zaoan", "02_wanan", "03_zaine", "04_jiayou", "05_weiqu", "06_emo",
    "07_kaixin", "08_baobao", "09_bixin", "10_cengceng", "11_qinqin", "12_tietie",
    "13_shoudao", "14_xiexie", "15_bukeqi", "16_meiguanxi", "17_sikao", "18_aiya",
    "19_ele", "20_xiangni", "21_duilian_wink", "22_duilian_qinqin", "23_duilian_haixiu", "24_duilian_miyankxiao",
]
LABELS = ["早安", "晚安", "在呢", "加油", "委屈", "emo",
          "开心", "抱抱", "比心", "蹭蹭", "亲亲", "贴贴",
          "收到", "谢谢", "抱歉", "没关系", "思考", "哎呀",
          "饿了", "想你", "wink", "亲亲", "害羞", "眯眼笑"]

def get_font(size):
    for path in ["C:/Windows/Fonts/msyhbd.ttc", "C:/Windows/Fonts/msyh.ttc"]:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()

rows = (len(NAMES) + COLS - 1) // COLS
W = COLS * (CELL + PAD) + PAD
H = rows * (CELL + 40 + PAD) + PAD + 60

canvas = Image.new("RGB", (W, H), CHAT_BG)
draw = ImageDraw.Draw(canvas)

# 顶部标题
title_font = get_font(28)
draw.text((PAD, 15), "青芽 BUD 微信表情包 v6（蹲坐版 · 透明背景 · 240×240）", fill=(60,60,60), font=title_font)

for i, (n, label) in enumerate(zip(NAMES, LABELS)):
    r = i // COLS
    c = i % COLS
    x = PAD + c * (CELL + PAD)
    y = 60 + r * (CELL + 40 + PAD)
    gif = os.path.join(GIF_DIR, f"qy_{n}.gif")
    if not os.path.exists(gif):
        continue
    # 取中间帧
    img = Image.open(gif)
    # 找到中间帧
    n_frames = getattr(img, 'n_frames', 1)
    img.seek(n_frames // 2)
    frame = img.convert("RGBA").resize((CELL, CELL), Image.LANCZOS)
    # 用 chat bg 渲染
    cell = Image.new("RGB", (CELL, CELL), CHAT_BG)
    cell.paste(frame, mask=frame.split()[3])
    canvas.paste(cell, (x, y))
    # 标签
    draw.text((x + 6, y + CELL + 4), f"{i+1:02d} {label}", fill=(80,80,80), font=get_font(18))

canvas.save(OUT)
print(f"saved: {OUT} ({canvas.size})")