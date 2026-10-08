# -*- coding: utf-8 -*-
"""
青芽表情包 v4 抠图模块：chroma key 透明背景

适用输入：VideoGen 输出的"薄荷蓝背景" MP4（蓝绿背景）
目标：240×240 透明背景 GIF，主体干净、边缘柔和
"""
import imageio.v3 as iio
from PIL import Image
import numpy as np
from typing import List, Tuple

# 薄荷蓝背景（参考视频色调）
BG_TARGET = (188, 220, 215)  # 薄荷蓝主色
BG_TOLERANCE = 65             # 颜色容差
EDGE_FEATHER_PX = 2           # 边缘羽化像素


def chroma_key_to_transparent(img: Image.Image,
                              bg_target: Tuple[int, int, int] = BG_TARGET,
                              tolerance: int = BG_TOLERANCE) -> Image.Image:
    """
    将指定背景色像素转为透明。
    实现：
    1. RGB → 计算每个像素到 bg_target 的欧式距离
    2. 距离 < tolerance 的 → 完全透明
    3. 距离稍远的 → 半透明（feather）
    4. 其余 → 完全不透明
    """
    if img.mode != "RGB":
        img = img.convert("RGB")
    arr = np.array(img, dtype=np.int32)
    h, w, _ = arr.shape
    # 距离
    diff = arr - np.array(bg_target, dtype=np.int32)
    dist = np.sqrt((diff.astype(np.float64) ** 2).sum(axis=2))  # (h, w)

    # alpha 通道：dist 越大越不透明
    feather = EDGE_FEATHER_PX * 4  # 羽化范围（颜色距离单位）
    alpha = np.clip((dist - tolerance) / feather * 255, 0, 255).astype(np.uint8)

    # 合成 RGBA（RGB 用 uint8）
    rgba = np.dstack([arr.astype(np.uint8), alpha])
    return Image.fromarray(rgba, mode="RGBA")


def extract_frames_to_transparent_rgba(
    mp4_path: str,
    target_count: int = 14,
    bg_target: Tuple[int, int, int] = BG_TARGET,
    tolerance: int = BG_TOLERANCE,
    crop_bottom_pct: float = 0.06,
) -> List[Image.Image]:
    """
    从视频抽帧 + chroma key 透明化 + 裁底部去水印。
    返回 list of PIL RGBA images (size = SOURCE_SIZE)。
    """
    frames = list(iio.imiter(mp4_path))
    n = len(frames)
    if n == 0:
        return []

    # 均匀抽帧
    if n >= target_count:
        indices = [round(i * (n - 1) / (target_count - 1)) for i in range(target_count)]
    else:
        indices = list(range(n))

    pil_frames = []
    for idx in indices:
        arr = frames[idx]
        img = Image.fromarray(arr).convert("RGB")
        # 1. 裁底部去水印
        w, h = img.size
        crop_h = int(h * crop_bottom_pct)
        if crop_h > 0:
            img = img.crop((0, 0, w, h - crop_h))
        # 2. chroma key 透明化
        rgba = chroma_key_to_transparent(img, bg_target, tolerance)
        pil_frames.append(rgba)
    return pil_frames


def save_transparent_gif(pil_frames: List[Image.Image], out_path: str,
                          duration_ms: int = 100, size: int = 240):
    """保存透明背景 GIF（v3：alpha 二值化后 PIL 自动分配透明索引）"""
    out_frames = []
    for f in pil_frames:
        small = f.resize((size, size), Image.LANCZOS)
        # alpha 通道二值化（<128 → 0，否则 255）
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
    # 测试：用现有的 QY_01_zaoan.gif（白底）做一次 chroma key 测试
    # 注意：白色不是薄荷蓝，所以这次只是验证算法
    from PIL import Image
    test_gif = r"C:\Users\XIAOMI\Desktop\青芽\WKBD\QINGYABUD\outputs\emojis_v1\qy_01_zaoan.gif"
    g = Image.open(test_gif)
    g.seek(7)
    rgb = g.convert("RGB")
    rgba = chroma_key_to_transparent(rgb, bg_target=(255, 255, 255), tolerance=30)
    rgba.save("test_chroma.png")
    print("saved chroma test")