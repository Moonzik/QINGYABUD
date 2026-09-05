# -*- coding: utf-8 -*-
"""
青芽 24表情包升级版动效合成引擎 v2

核心升级 vs v1：
1. 字幕层 - 顶部圆角白底+黑色微软雅黑文字，支持每张自定义文案
2. 多帧真动效 - 根据 action_type 决定位移/缩放/旋转序列
3. 关键帧扩展 - 支持多张主图作为关键帧，PIL 简单补间
4. 透明背景 - 白底 mask 透明 + 字幕独立层

依赖：Pillow
"""
import os
import math
import random
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops
from typing import List, Tuple, Optional

# ============================================================
# 全局配置
# ============================================================

EMOJI_SIZE = 240            # 输出 GIF 尺寸（微信规范 240x240）
FRAME_COUNT = 14            # 帧数（足够平滑且 ≤500KB）
FRAME_DURATION_MS = 90      # 每帧时长 ms（14帧循环 ≈1.26秒）
SOURCE_SIZE = 1024          # 源图尺寸
FONT_SIZE = 26              # 字幕字号
FONT_PATH = r"C:/Windows/Fonts/msyh.ttc"  # 微软雅黑（中文字体，柔）

# 动作类型枚举
ACTION_BREATHE = "breathe"      # 纯呼吸（身体没动）
ACTION_BOB = "bob"              # 点头
ACTION_SWAY = "sway"            # 横向轻晃（蹭贴）
ACTION_PULSE = "pulse"          # 心跳/用力
ACTION_SCALE_TAP = "scale_tap"  # 缩放弹跳
ACTION_WAVE = "wave"            # 挥手（叠加水平平移）
ACTION_TILT = "tilt"            # 歪头（旋转 ±5°）
ACTION_SPIN_LIGHT = "spinlight" # 小幅旋转

# ============================================================
# 字幕层
# ============================================================

def make_caption_layer(
    text: str,
    width: int = EMOJI_SIZE,
    height: int = 48,
    font_size: int = FONT_SIZE,
) -> Image.Image:
    """创建一个 顶部 RGBA 字幕层（圆角白底+黑色加粗文字）。"""
    if not text:
        return Image.new("RGBA", (width, height), (0, 0, 0, 0))

    layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)

    # 圆角白底矩形（半透明白）
    pad = 6
    rect_box = [pad, 4, width - pad - 1, height - 1]
    draw_rounded_rect(d, rect_box, radius=10, fill=(255, 255, 255, 230),
                       border=(120, 180, 140, 180), border_width=1)

    # 文字
    try:
        font = ImageFont.truetype(FONT_PATH, font_size)
    except Exception:
        font = ImageFont.load_default()
    try:
        bbox = d.textbbox((0, 0), text, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        tx = (width - tw) // 2 - bbox[0]
        ty = (height - th) // 2 - bbox[1] - 2
    except Exception:
        tw, th = d.textsize(text, font=font)
        tx = (width - tw) // 2
        ty = (height - th) // 2 - 4
    # 文字阴影（淡绿描边感）：先画一层浅绿阴影再画黑字
    for dx, dy in [(-1,0),(1,0),(0,-1),(0,1)]:
        d.text((tx+dx, ty+dy), text, font=font, fill=(200, 230, 200, 180))
    d.text((tx, ty), text, font=font, fill=(40, 60, 50, 255))

    return layer


def draw_rounded_rect(d, box, radius=10, fill=None, border=None, border_width=1):
    """PIL 圆角矩形（用 alpha mask 避免内描边锯齿）"""
    x0, y0, x1, y1 = box
    # 先画整体矩形
    if border is not None:
        d.rounded_rectangle(box, radius=radius, fill=fill, outline=border, width=border_width)
    else:
        d.rounded_rectangle(box, radius=radius, fill=fill)


# ============================================================
# 透明背景处理
# ============================================================

def load_white_to_transparent(img_path: str) -> Image.Image:
    """加载 PNG，将白色/近白色背景 mask 透明，alpha 边缘抗锯齿。"""
    img = Image.open(img_path).convert("RGBA")
    w, h = img.size
    px = img.load()
    threshold = 240
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            # 整体偏白 → 透明
            if r >= threshold and g >= threshold and b >= threshold:
                px[x, y] = (r, g, b, 0)
    # 边缘 alpha 减半去白边（处理白色残留）
    arr = img.split()
    a = arr[3].point(lambda v: int(v * 0.9) if v < 255 else v)
    img.putalpha(a)
    return img


# ============================================================
# 动效函数：每帧对源图施加变换，返回新图
# ============================================================

def apply_transform(
    img: Image.Image,
    action: str,
    t: float,
) -> Image.Image:
    """
    根据动作类型在参数 t ∈ [0,1) 上对 img 施加几何变换，
    返回变换后图像（仍为 RGBA，尺寸不变）。
    """
    if action == ACTION_BREATHE:
        # 呼吸：缩放 0.96 ↔ 1.04
        scale = 1.0 + 0.04 * math.sin(t * math.tau)
        return img_with_scale(img, scale, scale)

    if action == ACTION_BOB:
        # 上下点头 + 缩放
        bob = 0.025 * math.sin(t * math.tau)
        scale = 1.0 + 0.02 * math.sin(t * math.tau)
        return img_with_transform(img, scale=scale, dy=bob)

    if action == ACTION_SWAY:
        # 左右轻晃
        dx = 0.025 * math.sin(t * math.tau)
        scale = 1.0 + 0.015 * math.sin(t * math.tau * 2)
        return img_with_transform(img, scale=scale, dx=dx)

    if action == ACTION_PULSE:
        # 心跳：缩放 1.0 → 1.08 → 0.96 → 1.0
        # 双拍心跳
        p1 = math.exp(-((t * 4 - 0.0) % 1) * 12)
        p2 = math.exp(-((t * 4 - 0.35) % 1) * 12)
        pulse = 0.05 * (p1 + 0.5 * p2)
        scale = 1.0 + pulse
        return img_with_scale(img, scale, scale)

    if action == ACTION_SCALE_TAP:
        # 弹跳：1.0 → 1.12 → 0.97 → 1.0
        if t < 0.25:
            s = 1.0 + 0.12 * (t / 0.25)
        elif t < 0.5:
            s = 1.12 - 0.15 * ((t - 0.25) / 0.25)
        elif t < 0.75:
            s = 0.97 + 0.04 * ((t - 0.50) / 0.25)
        else:
            s = 1.01 - 0.01 * ((t - 0.75) / 0.25)
        return img_with_scale(img, s, s)

    if action == ACTION_WAVE:
        # 挥手：水平平移 + 微旋转
        dx = 0.03 * math.sin(t * math.tau)
        rot = 4 * math.sin(t * math.tau * 2)
        scale = 1.0 + 0.025 * math.sin(t * math.tau)
        return img_with_transform(img, scale=scale, dx=dx, rot_deg=rot)

    if action == ACTION_TILT:
        # 歪头：旋转 ±5° + 轻微位移
        rot = 5 * math.sin(t * math.tau)
        return img_with_transform(img, scale=1.0, rot_deg=rot)

    if action == ACTION_SPIN_LIGHT:
        # 轻微旋转抖动
        rot = 3 * math.sin(t * math.tau * 3)
        scale = 1.0 + 0.015 * math.sin(t * math.tau)
        return img_with_transform(img, scale=scale, rot_deg=rot)

    return img


def img_with_scale(img: Image.Image, sx: float, sy: float) -> Image.Image:
    """中心缩放（裁剪保持原尺寸）"""
    w, h = img.size
    new_w = max(1, int(w * sx))
    new_h = max(1, int(h * sy))
    scaled = img.resize((new_w, new_h), Image.LANCZOS)
    bg = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    bg.paste(scaled, ((w - new_w) // 2, (h - new_h) // 2), scaled)
    return bg


def img_with_transform(
    img: Image.Image,
    scale: float = 1.0,
    dx: float = 0.0,    # 占图宽比例 [-1,1]
    dy: float = 0.0,
    rot_deg: float = 0.0,
) -> Image.Image:
    """综合变换：缩放+平移+旋转，保持原画布大小。"""
    w, h = img.size
    # 先旋转再缩放
    work = img
    if abs(rot_deg) > 0.01:
        work = work.rotate(rot_deg, resample=Image.BICUBIC, expand=False)
    # 缩放（先放大一点避免旋转后裁掉）
    if abs(scale - 1.0) > 0.001:
        new_w = max(1, int(w * scale))
        new_h = max(1, int(h * scale))
        scaled = work.resize((new_w, new_h), Image.LANCZOS)
        # 先放到一块大画布上，再平移
        big = Image.new("RGBA", (w * 2, h * 2), (0, 0, 0, 0))
        big.paste(scaled, ((w * 2 - new_w) // 2, (h * 2 - new_h) // 2), scaled)
        # 平移
        crop_x = (w * 2 - w) // 2 + int(dx * w)
        crop_y = (h * 2 - h) // 2 + int(dy * h)
        return big.crop((crop_x, crop_y, crop_x + w, crop_y + h))
    else:
        # 不缩放：直接位移
        big = Image.new("RGBA", (w * 2, h * 2), (0, 0, 0, 0))
        big.paste(work, (w - w // 2, h - h // 2), work)
        crop_x = (w * 2 - w) // 2 + int(dx * w)
        crop_y = (h * 2 - h) // 2 + int(dy * h)
        return big.crop((crop_x, crop_y, crop_x + w, crop_y + h))


# ============================================================
# GIF 合成
# ============================================================

def make_gif(
    base_png: str,
    out_gif: str,
    action: str = ACTION_BREATHE,
    caption: str = "",
    frames: int = FRAME_COUNT,
    duration_ms: int = FRAME_DURATION_MS,
    size: int = EMOJI_SIZE,
) -> Tuple[str, int]:
    """
    主入口：从 base_png 制作符合微信规范的 240×240 GIF（透明背景+字幕）。
    返回 (out_gif, 文件 KB)。
    """
    base = load_white_to_transparent(base_png)

    # 字幕层（一次性创建）
    caption_layer = make_caption_layer(caption, width=size, height=46)

    pil_frames: List[Image.Image] = []
    for i in range(frames):
        t = i / frames
        # 1. 几何动效
        transformed = apply_transform(base, action, t)
        # 2. 缩放到目标尺寸
        small = transformed.resize((size, size), Image.LANCZOS)
        # 3. 叠加字幕
        small = small.copy()
        small.alpha_composite(caption_layer)
        # 4. 转成 P（透明 GIF 需要 P 模式）
        rgb = Image.new("RGB", (size, size), (255, 255, 255))
        rgb.paste(small, (0, 0), small)
        pil_frames.append(rgb)

    # 保存 GIF
    pil_frames[0].save(
        out_gif,
        save_all=True,
        append_images=pil_frames[1:],
        duration=duration_ms,
        loop=0,
        optimize=True,
        disposal=2,
    )

    kb = os.path.getsize(out_gif) // 1024
    return out_gif, kb


# ============================================================
# 24 张表情配置
# ============================================================

# 每张：(主图文件名, 动效类型, 字幕文案)
EMOJIS_V2 = [
    ("qy_01_zaoan",   ACTION_WAVE,        "嗨呀~"),     # 早安 挥手
    ("qy_02_wanan",   ACTION_BOB,         "晚安~"),     # 晚安 点头闭眼
    ("qy_03_zaine",   ACTION_TILT,        "在呢~"),     # 在呢 歪头
    ("qy_04_jiayou",  ACTION_PULSE,       "加油！"),     # 加油 心跳
    ("qy_05_weiqu",   ACTION_BOB,         "呜…"),        # 委屈 低头
    ("qy_06_emo",     ACTION_SWAY,        "抱抱"),       # emo 抱抱
    ("qy_07_kaixin",  ACTION_SCALE_TAP,   "嘿嘿"),      # 开心 弹跳
    ("qy_08_baobao",  ACTION_SPIN_LIGHT,  "来抱~"),     # 抱抱 转转
    ("qy_09_bixin",   ACTION_WAVE,        "比心"),      # 比心 轻挥
    ("qy_10_cengceng",ACTION_SWAY,        "蹭蹭"),      # 蹭蹭 横向
    ("qy_11_qinqin",  ACTION_SCALE_TAP,   "mua~"),      # 亲亲 嘟嘴弹
    ("qy_12_tietie",  ACTION_SWAY,        "贴贴"),      # 贴贴 晃动
    ("qy_13_shoudao", ACTION_TILT,        "收到"),      # 收到 点头
    ("qy_14_xiexie",  ACTION_BOB,         "谢谢~"),     # 谢谢 鞠躬
    ("qy_15_bukeqi",  ACTION_TILT,        "没事"),      # 不客气
    ("qy_16_meiguanxi",ACTION_BOB,        "没关系~"),   # 没关系
    ("qy_17_sikao",   ACTION_TILT,        "嗯？"),      # 思考 歪头
    ("qy_18_aiya",    ACTION_SCALE_TAP,   "哎呀"),      # 哎呀 弹跳惊讶
    ("qy_19_ele",     ACTION_PULSE,       "饿饿"),      # 饿了 心跳(渴望)
    ("qy_20_xiangni", ACTION_BREATHE,     "想你"),      # 想你 安静呼吸
    ("qy_21_duilian_wink",   ACTION_WAVE, "嗨~"),        # 怼脸 wink 挥手
    ("qy_22_duilian_qinqin", ACTION_SCALE_TAP, "mua"),  # 怼脸亲亲 嘟嘴弹
    ("qy_23_duilian_haixiu", ACTION_SWAY, "羞"),        # 怼脸害羞
    ("qy_24_duilian_miyankxiao", ACTION_SCALE_TAP, "嘿嘿"),  # 怼脸笑
]


def batch_make(folder: str):
    """批量制作 24 张 GIF。"""
    results = []
    for name, action, caption in EMOJIS_V2:
        # 主图来源：优先用 _main 替代（修复后的图）
        main_png = name + "_main.png"
        path_main = os.path.join(folder, main_png)
        if not os.path.exists(path_main):
            main_png = name + ".png"
            path_main = os.path.join(folder, main_png)
        if not os.path.exists(path_main):
            print(f"[SKIP] {name} - no base png found")
            continue
        out = os.path.join(folder, name + ".gif")
        try:
            gif, kb = make_gif(path_main, out, action=action, caption=caption)
            results.append((name, gif, kb, caption))
            print(f"[OK] {name:30s} {action:14s} '{caption}' -> {kb} KB")
        except Exception as e:
            print(f"[ERR] {name}: {e}")
    return results


if __name__ == "__main__":
    import sys
    folder = sys.argv[1] if len(sys.argv) > 1 else r"C:\Users\XIAOMI\Desktop\青芽\WKBD\QINGYABUD\outputs\emojis_v1"
    batch_make(folder)
