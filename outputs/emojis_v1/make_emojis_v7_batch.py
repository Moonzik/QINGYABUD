"""青芽 v7 批量表情包生成（使用新形象底图）。
- 3 张源图（v7_base: 全身/怼脸/睡觉），裁掉右下角水印
- 画心形等道具 PNG
- 24 张表情 → 源图 + 动作 prompt + 后期叠加
"""
import os, json
from PIL import Image, ImageDraw

ROOT = r"C:\Users\XIAOMI\Desktop\青芽\WKBD\QINGYABUD\outputs\emojis_v1"
SRC_DIR = os.path.join(ROOT, "v7_base")
CANON_SRC = os.path.join(ROOT, "v7_src")
OUT_DIR = os.path.join(ROOT, "v7_gifs")
VIDEO_DIR = os.path.join(ROOT, "v7_videos")
ASSET_DIR = os.path.join(ROOT, "v7_assets")
os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(VIDEO_DIR, exist_ok=True)
os.makedirs(ASSET_DIR, exist_ok=True)
os.makedirs(CANON_SRC, exist_ok=True)

# 24 张表情配置：name → {src, motion, overlay, position, text, text_pos}
EMOJIS = [
    # 01-08 日常问候
    {"name": "01_zaoan",  "src": "base",    "motion": "Soft gentle blink, slow subtle head tilt up as if greeting the morning sun, ears slightly flick, body subtle breathing, very gentle calm rhythm.",
     "overlay": [("sunray", (700, 200))], "text": "hi", "text_pos": (820, 250)},
    {"name": "02_wanan",  "src": "sleep",   "motion": "Soft slow breathing while sleeping, eyes gently closed with peaceful smile, blanket slightly rises and falls, tiny sprouts sway faintly.",
     "overlay": [], "text": None, "text_pos": None},
    {"name": "03_zaine",  "src": "base",    "motion": "Slowly turns head from side to side looking around attentively, ears rotating to listen, calm attentive mood, gentle body breathing.",
     "overlay": [], "text": None, "text_pos": None},
    {"name": "04_jiayou", "src": "base",    "motion": "Lifts both front paws upward in a small encouraging gesture, slight body bounce, head bobs gently, eyes bright and determined, sprouts stand tall.",
     "overlay": [], "text": None, "text_pos": None},
    {"name": "05_weiqu",  "src": "closeup", "motion": "Ears droop downward slowly, eyes lower looking down sadly, head tilts down slightly, subtle sad healing expression, tears forming at corners.",
     "overlay": [("tear", (350, 480)), ("tear", (670, 480))], "text": None, "text_pos": None},
    {"name": "06_emo",    "src": "base",    "motion": "Head hangs low, eyes look up toward camera with sad yearning expression, ears flat, soft blue-gray tint shifts in, gentle body still.",
     "overlay": [], "text": None, "text_pos": None},
    {"name": "07_kaixin", "src": "base",    "motion": "Happy bouncy up-down body motion, ears perk up, tail wags, mouth opens in small smile, sprouts glow softly with gentle pink light, joyful rhythm.",
     "overlay": [], "text": None, "text_pos": None},
    {"name": "08_baobao", "src": "base",    "motion": "Reaches both front paws forward gently toward camera as if offering a hug, slow soft forward lean, kind healing expression, body subtle breathing.",
     "overlay": [("heart_small", (300, 350)), ("heart_small", (720, 350))], "text": None, "text_pos": None},
    # 09-16 互动
    {"name": "09_bixin",  "src": "closeup", "motion": "Tilt head slightly to one side, both front paws gently come up to form a small heart shape in front of chest, sprouts glow with soft pink light, healing smile.",
     "overlay": [("heart_big", (480, 380)), ("glow", (480, 130))], "text": None, "text_pos": None},
    {"name": "10_cengceng","src": "base",   "motion": "Slowly leans forward toward camera as if nuzzling, eyes close gently halfway, soft affectionate mood, ears relax.",
     "overlay": [], "text": None, "text_pos": None},
    {"name": "11_qinqin", "src": "closeup", "motion": "Slowly zooms closer toward camera as if giving a soft kiss, eyes close gently, several small heart shapes float up around face, healing mood.",
     "overlay": [("heart_small", (220, 250)), ("heart_small", (820, 280)), ("heart_small", (480, 180))], "text": None, "text_pos": None},
    {"name": "12_tietie", "src": "base",    "motion": "Tilts head to one side and presses cheek softly against an invisible friend, eyes half closed in contentment, gentle smile, soft healing rhythm.",
     "overlay": [], "text": None, "text_pos": None},
    {"name": "13_shoudao","src": "base",    "motion": "Quick small head nod as if saluting 'got it', ears perk forward briefly, then relax, confident calm expression.",
     "overlay": [], "text": "👌", "text_pos": (820, 220)},
    {"name": "14_xiexie", "src": "base",    "motion": "Small gentle bow, head lowers slightly forward, eyes close softly, then lifts back up with kind smile, healing grateful mood.",
     "overlay": [], "text": None, "text_pos": None},
    {"name": "15_bukeqi", "src": "base",    "motion": "Apologetic tilt of head to side, eyes look up with soft sorry expression, front paws slightly lift in small apologetic gesture.",
     "overlay": [], "text": None, "text_pos": None},
    {"name": "16_meiguanxi","src": "base", "motion": "Shakes head gently from side to side as if saying 'no worries', small kind smile, ears relaxed, body subtle breathing.",
     "overlay": [], "text": None, "text_pos": None},
    # 17-20 思考/情绪
    {"name": "17_sikao",  "src": "closeup", "motion": "Tilts head to one side in curious thinking pose, one ear rotates forward attentively, eyes look up thoughtfully, gentle pondering mood.",
     "overlay": [("qmark", (760, 280))], "text": None, "text_pos": None},
    {"name": "18_aiya",   "src": "closeup", "motion": "Small surprised expression, eyes widen briefly, ears flick up, slight startle, then relax back to calm.",
     "overlay": [("exclaim", (760, 240))], "text": None, "text_pos": None},
    {"name": "19_ele",    "src": "base",    "motion": "Tongue flicks out briefly licking lips, head tilts to side, eyes look around longingly as if hungry, soft whimper mood.",
     "overlay": [("drool", (700, 460))], "text": None, "text_pos": None},
    {"name": "20_xiangni","src": "base",    "motion": "Front paws reach up longingly toward camera, ears droop slightly, eyes look up with soft yearning, body gentle slow breathing.",
     "overlay": [("heart_small", (320, 280)), ("heart_small", (720, 280))], "text": None, "text_pos": None},
    # 21-24 对联系列特写
    {"name": "21_duilian_wink",      "src": "closeup", "motion": "Plays a slow wink, one eye gently closes then opens, slight mischievous smile, ear flicks, gentle cheek blush.",
     "overlay": [], "text": None, "text_pos": None},
    {"name": "22_duilian_qinqin",    "src": "closeup", "motion": "Brings both paws up to cheeks, cheeks puff slightly, eyes close softly as if blowing a gentle kiss, healing mood.",
     "overlay": [("heart_small", (220, 250)), ("heart_small", (820, 250))], "text": None, "text_pos": None},
    {"name": "23_duilian_haixiu",    "src": "closeup", "motion": "Shy smile, eyes look down then up, cheeks blush deeper pink, ears fold slightly back, gentle bashful mood.",
     "overlay": [], "text": None, "text_pos": None},
    {"name": "24_duilian_miyankxiao","src": "closeup","motion": "Eyes narrow into a squinty happy smile, mouth opens in small joyful grin, head tilts slightly, gentle happy rhythm.",
     "overlay": [], "text": None, "text_pos": None},
]

def crop_watermark(img, pct=0.10):
    """裁掉底部 pct 比例（去 AI 水印）"""
    w, h = img.size
    cut = int(h * pct)
    return img.crop((0, 0, w, h - cut))

# 准备源图：优先使用已经裁好的 v7_src，否则从 v7_base 重新裁
SOURCES = {
    "base":    os.path.join(SRC_DIR, "qy_base_raw.png"),
    "closeup": os.path.join(SRC_DIR, "qy_closeup_raw.png"),
    "sleep":   os.path.join(SRC_DIR, "qy_sleep_raw.png"),
}

for k, p in SOURCES.items():
    canon = os.path.join(CANON_SRC, f"qy_{k}.png")
    if os.path.exists(canon):
        print(f"src ready (existing): {canon}")
        continue
    if not os.path.exists(p):
        print(f"MISSING src: {p}")
        continue
    img = Image.open(p).convert("RGB")
    cropped = crop_watermark(img, pct=0.10)
    cropped.save(canon)
    print(f"src ready: {canon} ({cropped.size})")

# 生成心形等道具 PNG (1024x1024 透明)
def draw_heart(size=200, color=(255, 105, 180, 220)):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    s = size
    d.ellipse([s*0.10, s*0.15, s*0.55, s*0.60], fill=color)
    d.ellipse([s*0.45, s*0.15, s*0.90, s*0.60], fill=color)
    d.polygon([(s*0.10, s*0.50), (s*0.90, s*0.50), (s*0.50, s*0.92)], fill=color)
    return img

def draw_tear(size=120, color=(135, 206, 250, 220)):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse([size*0.30, size*0.20, size*0.70, size*0.65], fill=color)
    d.polygon([(size*0.30, size*0.55), (size*0.70, size*0.55), (size*0.50, size*0.92)], fill=color)
    return img

def draw_glow(size=300, color=(255, 182, 193, 90)):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse([0, 0, size, size], fill=color)
    return img

def draw_qmark(size=120):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    try:
        from PIL import ImageFont
        font = ImageFont.truetype("C:/Windows/Fonts/seguisb.ttf", int(size*0.7))
    except:
        font = None
    d.text((size*0.25, size*0.05), "?", fill=(255, 215, 0, 230), font=font)
    return img

def draw_exclaim(size=120):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    try:
        from PIL import ImageFont
        font = ImageFont.truetype("C:/Windows/Fonts/seguisb.ttf", int(size*0.7))
    except:
        font = None
    d.text((size*0.30, size*0.05), "!", fill=(255, 100, 100, 230), font=font)
    return img

def draw_drool(size=120, color=(180, 230, 255, 200)):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse([size*0.35, size*0.30, size*0.65, size*0.65], fill=color)
    d.polygon([(size*0.35, size*0.55), (size*0.65, size*0.55), (size*0.50, size*0.95)], fill=color)
    return img

def draw_sunray(size=300):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cx, cy = size*0.5, size*0.5
    rays = 12
    import math
    for i in range(rays):
        ang = i * (360 / rays)
        x1 = cx + math.cos(math.radians(ang)) * size*0.25
        y1 = cy + math.sin(math.radians(ang)) * size*0.25
        x2 = cx + math.cos(math.radians(ang)) * size*0.45
        y2 = cy + math.sin(math.radians(ang)) * size*0.45
        d.line([(x1, y1), (x2, y2)], fill=(255, 235, 150, 200), width=10)
    d.ellipse([size*0.35, size*0.35, size*0.65, size*0.65], fill=(255, 235, 150, 220))
    return img

ASSETS = {
    "heart_big":   draw_heart(280, (255, 105, 180, 230)),
    "heart_small": draw_heart(140, (255, 130, 180, 230)),
    "tear":        draw_tear(100, (135, 206, 250, 230)),
    "glow":        draw_glow(400, (255, 182, 193, 110)),
    "qmark":       draw_qmark(160),
    "exclaim":     draw_exclaim(160),
    "drool":       draw_drool(120),
    "sunray":      draw_sunray(280),
}
for n, a in ASSETS.items():
    a.save(os.path.join(ASSET_DIR, f"{n}.png"))
print("assets ready:", list(ASSETS.keys()))

# 保存配置
with open(os.path.join(ROOT, "v7_emojis.json"), "w", encoding="utf-8") as f:
    json.dump(EMOJIS, f, ensure_ascii=False, indent=2)
print(f"saved config: {len(EMOJIS)} emojis")
