# -*- coding: utf-8 -*-
"""
青芽 v4 抠图模块：GrabCut + 自适应前景检测

对"主体 + 白底"做智能前景分割。
算法：先用"中心矩形"假设主体居中，让 GrabCut 自动迭代出前景蒙版。
再叠加"边缘保留"滤镜软化 alpha。
"""
import numpy as np
import cv2
from PIL import Image
from typing import List, Tuple


def grabcut_foreground(img_pil: Image.Image,
                       iter_count: int = 3,
                       margin_pct: float = 0.05,
                       prev_mask: np.ndarray = None) -> Tuple[Image.Image, np.ndarray]:
    """
    用 GrabCut 把"主体+背景"图抠出主体，返回 (RGBA, mask)。

    prev_mask: 上一帧的 mask（uint8, 0/2=背景, 1/3=前景）。如果提供，
              用 GC_INIT_WITH_MASK 模式继续优化（主体跟踪更稳）。
    """
    img = np.array(img_pil.convert("RGB"))
    h, w = img.shape[:2]

    bgdModel = np.zeros((1, 65), np.float64)
    fgdModel = np.zeros((1, 65), np.float64)

    if prev_mask is not None and prev_mask.shape == (h, w):
        mask = prev_mask.copy()
        try:
            cv2.grabCut(img, mask, None, bgdModel, fgdModel, iter_count, cv2.GC_INIT_WITH_MASK)
        except Exception as e:
            print(f"GrabCut-with-mask error: {e}, fallback to rect mode")
            mask = np.zeros((h, w), np.uint8)
            mx = int(w * margin_pct)
            my = int(h * margin_pct)
            rect = (mx, my, w - 2 * mx, h - 2 * my)
            cv2.grabCut(img, mask, rect, bgdModel, fgdModel, iter_count, cv2.GC_INIT_WITH_RECT)
    else:
        mask = np.zeros((h, w), np.uint8)
        mx = int(w * margin_pct)
        my = int(h * margin_pct)
        rect = (mx, my, w - 2 * mx, h - 2 * my)
        try:
            cv2.grabCut(img, mask, rect, bgdModel, fgdModel, iter_count, cv2.GC_INIT_WITH_RECT)
        except Exception as e:
            print(f"GrabCut error: {e}, fallback to white->transparent")
            return _fallback_white_to_transparent(img_pil), np.zeros((h, w), np.uint8)

    # 蒙版 → alpha
    alpha = np.where((mask == 1) | (mask == 3), 255, 0).astype(np.uint8)
    alpha = cv2.GaussianBlur(alpha, (3, 3), 0)

    rgba = np.dstack([img, alpha])
    return Image.fromarray(rgba, mode="RGBA"), mask


def _fallback_white_to_transparent(img_pil: Image.Image) -> Image.Image:
    """兜底方案：白底→透明（之前 v1 的逻辑）"""
    arr = np.array(img_pil.convert("RGB"), dtype=np.int32)
    h, w = arr.shape[:2]
    diff = arr - np.array([255, 255, 255], dtype=np.int32)
    dist = np.sqrt((diff.astype(np.float64) ** 2).sum(axis=2))
    feather = 30
    tolerance = 235
    alpha = np.clip((dist - tolerance) / feather * 255, 0, 255).astype(np.uint8)
    rgba = np.dstack([arr.astype(np.uint8), alpha])
    return Image.fromarray(rgba, mode="RGBA")


def extract_frames_grabcut(
    mp4_path: str,
    target_count: int = 14,
    crop_bottom_pct: float = 0.07,
    margin_pct: float = 0.05,
) -> List[Image.Image]:
    """
    抽帧 + GrabCut 抠图 + 裁底部水印。
    用前一帧 mask 引导下一帧（主体跟踪），保证动作后仍稳定抠图。
    """
    import imageio.v3 as iio
    frames = list(iio.imiter(mp4_path))
    n = len(frames)
    if n == 0:
        return []

    if n >= target_count:
        indices = [round(i * (n - 1) / (target_count - 1)) for i in range(target_count)]
    else:
        indices = list(range(n))

    pil_frames = []
    prev_mask = None
    for idx in indices:
        img = Image.fromarray(frames[idx]).convert("RGB")
        w, h = img.size
        crop_h = int(h * crop_bottom_pct)
        if crop_h > 0:
            img = img.crop((0, 0, w, h - crop_h))
        rgba, prev_mask = grabcut_foreground(
            img, iter_count=3, margin_pct=margin_pct, prev_mask=prev_mask,
        )
        pil_frames.append(rgba)
    return pil_frames


def save_transparent_gif_v2(pil_frames: List[Image.Image], out_path: str,
                             duration_ms: int = 110, size: int = 240) -> int:
    """保存透明 GIF（v4 方案：alpha 二值化 → 0 索引透明）"""
    out_frames = []
    for f in pil_frames:
        small = f.resize((size, size), Image.LANCZOS)
        # alpha 二值化
        r, g, b, a = small.split()
        a_bin = a.point(lambda v: 0 if v < 128 else 255)
        rgba = Image.merge("RGBA", (r, g, b, a_bin))
        out_frames.append(rgba)

    out_frames[0].save(
        out_path,
        save_all=True,
        append_images=out_frames[1:],
        duration=duration_ms,
        loop=0,
        optimize=True,
        disposal=2,
        transparency=0,
    )

    import os
    kb = os.path.getsize(out_path) // 1024
    return kb


if __name__ == "__main__":
    # 测试：用 v4 视频（白底+主体居中）跑 GrabCut
    import sys
    sys.path.insert(0, ".")
    frames = extract_frames_grabcut(
        "videos_v4/demo_zaoan_v4.mp4",
        target_count=14,
        crop_bottom_pct=0.07,
    )
    print(f"{len(frames)} frames")
    # 保存中间帧预览
    from PIL import Image as PImage
    for i in [0, 4, 8, 12]:
        f = frames[i]
        bg = PImage.new("RGB", f.size, (240, 237, 230))
        bg.paste(f, mask=f.split()[3])
        bg.save(f"videos_v4/grabcut_frame_{i:02d}.png")

    # 4 帧拼图
    imgs = [PImage.open(f"videos_v4/grabcut_frame_{i:02d}.png").convert("RGB") for i in [0, 4, 8, 12]]
    W = 240
    canvas = PImage.new("RGB", (W * 4 + 50, W + 50), "white")
    for j, im in enumerate(imgs):
        canvas.paste(im, (j * (W + 10) + 5, 5))
    canvas.save("videos_v4/grabcut_4frames.png")

    # 保存透明 GIF
    kb = save_transparent_gif_v2(frames, "videos_v4/demo_zaoan_grabcut.gif", duration_ms=110, size=240)
    print(f"GrabCut GIF: {kb} KB")