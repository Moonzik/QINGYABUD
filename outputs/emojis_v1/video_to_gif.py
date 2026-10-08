# -*- coding: utf-8 -*-
"""
青芽视频→GIF 转换 pipeline v3

输入：VideoGen 输出的 MP4（白底，右下角有视频由 AI 生成 水印）
输出：240×240 微信规格 GIF（白底或透明 + 顶部字幕 + 水印去除）

步骤：
1. imageio 抽帧
2. 自动检测水印（右下角区域扫描 AI 文本亮度规律）
3. 有水印则裁底部区域 + 用 PIL 高仿白底重绘
4. 缩放到 240×240
5. 加字幕层（圆角白底+黑色微软雅黑+绿描边）
6. 抽帧（24fps→降采样到 14 帧）
7. 保存 GIF（≤500KB）

依赖：imageio + imageio-ffmpeg + Pillow
"""
import os
import math
import imageio.v3 as iio
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from typing import List, Tuple, Optional


# ============================================================
# 配置
# ============================================================

EMOJI_SIZE = 240
TARGET_FRAMES = 14            # 循环 GIF 帧数（14 帧 * 100ms ≈ 1.4s）
FRAME_DURATION_MS = 100       # 每帧 ms
WATERMARK_BOTTOM_CROP_PCT = 0.07  # 裁掉底部多少百分比（如水印存在）
WHITE = (255, 255, 255)
FONT_PATH = r"C:/Windows/Fonts/msyh.ttc"

# 中文字体（用于 subtitle 水印位置检测的参考字体）
try:
    FONT_TITLE = ImageFont.truetype(FONT_PATH, 28)
    FONT_WM_DETECT = ImageFont.truetype(FONT_PATH, 12)  # 视频水印大约 12pt
except Exception:
    FONT_TITLE = ImageFont.load_default()
    FONT_WM_DETECT = ImageFont.load_default()


# ============================================================
# 水印检测
# ============================================================

def detect_watermark_bbox(img: Image.Image, search_box=None) -> Optional[Tuple[int, int, int, int]]:
    """
    自动检测右下角水印位置。
    简单实现：扫描右下 1/5 区域，找最深灰区域（认为是水印文字）。
    返回 (x0, y0, x1, y1) bbox 或 None。
    """
    w, h = img.size
    if search_box is None:
        # 只扫描右下 1/5
        x0 = int(w * 0.6)
        y0 = int(h * 0.78)
        crop = img.crop((x0, y0, w, h)).convert("RGB")
    else:
        x0, y0, x1, y1 = search_box
        crop = img.crop(search_box).convert("RGB")
        w, h = (x1 - x0, y1 - y0)
    pw, ph = crop.size
    # 找深色文字像素（亮度 < 150）
    px = crop.load()
    dark_pixels = []
    for y in range(ph):
        for x in range(pw):
            r, g, b = px[x, y]
            if r < 150 and g < 150 and b < 150:
                dark_pixels.append((x, y))
    if len(dark_pixels) < 30:  # 文字像素太少 → 没水印
        return None
    # 取 bbox
    xs = [p[0] for p in dark_pixels]
    ys = [p[1] for p in dark_pixels]
    bx0 = min(xs)
    by0 = min(ys)
    bx1 = max(xs) + 1
    by1 = max(ys) + 1
    # 转回原图坐标系
    return (x0 + bx0, y0 + by0, x0 + bx1, y0 + by1)


def remove_watermark_simple(img: Image.Image, crop_bottom_pct: float = 0.06) -> Image.Image:
    """
    v3 升级：直接裁掉底部 crop_bottom_pct 区域（水印必然在这部分），
    然后用白底重绘边缘。比检测+白方块覆盖更干净。
    """
    w, h = img.size
    crop_h = int(h * crop_bottom_pct)
    if crop_h <= 0:
        return img
    # 裁掉底部
    out = img.crop((0, 0, w, h - crop_h)).copy()
    # 底部填白
    canvas = Image.new("RGB", (w, h), WHITE)
    canvas.paste(out, (0, 0))
    return canvas


# ============================================================
# 字幕层
# ============================================================

def make_caption_layer(text: str, width: int = 240, height: int = 240,
                       font_size: int = 22,
                       anchor: str = "bottom-left",
                       offset_xy: tuple = (10, -10)) -> Image.Image:
    """
    创建 RGBA 字幕层（v3 升级：去掉气泡框，直接文字 + 灵活位置）
    anchor: top-left/top-right/bottom-left/bottom-right/top-center/bottom-center
    """
    layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    if not text:
        return layer
    d = ImageDraw.Draw(layer)
    font = ImageFont.truetype(FONT_PATH, font_size)
    try:
        bbox = d.textbbox((0, 0), text, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        off_x = -bbox[0]
        off_y = -bbox[1]
    except AttributeError:
        tw, th = d.textsize(text, font=font)
        off_x, off_y = 0, 0
    pad = 4
    ox, oy = offset_xy
    if anchor == "top-left":
        x = pad + ox
        y = pad + oy
    elif anchor == "top-right":
        x = width - tw - pad + ox
        y = pad + oy
    elif anchor == "bottom-right":
        x = width - tw - pad + ox
        y = height - th - pad + oy
    elif anchor == "top-center":
        x = (width - tw) // 2 + ox
        y = pad + oy
    else:  # bottom-left default
        x = pad + ox
        y = height - th - pad + oy
    # 浅绿色描边（轻微光晕）
    for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
        d.text((x + dx + off_x, y + dy + off_y), text, font=font, fill=(180, 225, 190, 220))
    # 深绿主色字
    d.text((x + off_x, y + off_y), text, font=font, fill=(30, 70, 45, 255))
    return layer


# ============================================================
# 抽帧 + 水印处理
# ============================================================

def extract_clean_frames(mp4_path: str, target_count: int = TARGET_FRAMES) -> List[Image.Image]:
    """
    从视频抽帧，处理水印，缩放到目标尺寸（再加字幕前）。
    返回 list of PIL RGB images (size = SOURCE_SIZE)。
    """
    frames = list(iio.imiter(mp4_path))
    n = len(frames)
    if n == 0:
        return []

    # 均匀抽帧到 target_count
    if n >= target_count:
        indices = [round(i * (n - 1) / (target_count - 1)) for i in range(target_count)]
    else:
        # 视频太短：补帧
        indices = list(range(n))
    pil_frames = []
    for idx in indices:
        arr = frames[idx]
        img = Image.fromarray(arr)
        # 去水印
        img = remove_watermark_simple(img)
        pil_frames.append(img)
    return pil_frames


# ============================================================
# GIF 合成
# ============================================================

def make_gif_from_video(
    mp4_path: str,
    out_gif: str,
    caption: str = "",
    size: int = EMOJI_SIZE,
    frames: int = TARGET_FRAMES,
    duration_ms: int = FRAME_DURATION_MS,
    caption_anchor: str = "bottom-left",
    caption_font_size: int = 22,
    transparent_bg: bool = False,
) -> Tuple[str, int]:
    """
    主入口：MP4 → GIF（裁底部去水印+字幕+缩放）
    caption_anchor / caption_font_size 控制字幕位置和字号
    """
    pil_frames = extract_clean_frames(mp4_path, target_count=frames)
    if not pil_frames:
        return out_gif, 0

    # 字幕层（v3：全画面尺寸、灵活位置，无气泡框）
    cap_layer = make_caption_layer(
        caption, width=size, height=size,
        font_size=caption_font_size,
        anchor=caption_anchor,
    )

    out_frames = []
    for img in pil_frames:
        small = img.resize((size, size), Image.LANCZOS)
        rgba = small.convert("RGBA")
        if caption:
            rgba.alpha_composite(cap_layer)
        rgb = Image.new("RGB", (size, size), WHITE)
        rgb.paste(rgba, mask=rgba.split()[3])
        out_frames.append(rgb)

    out_frames[0].save(
        out_gif,
        save_all=True,
        append_images=out_frames[1:],
        duration=duration_ms,
        loop=0,
        optimize=True,
        disposal=2,
    )
    kb = os.path.getsize(out_gif) // 1024
    return out_gif, kb


# ============================================================
# 测试入口
# ============================================================

if __name__ == "__main__":
    test_video = r"C:\Users\XIAOMI\Desktop\青芽\WKBD\QINGYABUD\outputs\emojis_v1\videos_test\国风3D_Q版灵植小兽青芽_巴掌大小圆滚滚幼态体型_白绿渐变_2026-09-05T11-32-16.mp4"
    out = r"C:\Users\XIAOMI\Desktop\青芽\WKBD\QINGYABUD\outputs\emojis_v1\videos_test\test_pipeline.gif"
    path, kb = make_gif_from_video(test_video, out, caption="嗨呀~")
    print(f"OK: {path}, {kb} KB")
