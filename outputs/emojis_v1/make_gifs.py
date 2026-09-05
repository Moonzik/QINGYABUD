#!/usr/bin/env python3
"""青芽表情包 GIF 合成器
- 把白底 PNG 抠成透明
- 缩放到 240x240
- 生成 12 帧循环呼吸动效
- 输出透明背景 GIF（符合微信表情包规范）
"""
import os
import glob
from PIL import Image

INPUT_DIR = r"C:\Users\XIAOMI\Desktop\青芽\WKBD\QINGYABUD\outputs\emojis_v1"
OUT_DIR = INPUT_DIR

SCALE = 240           # 微信表情包规范尺寸
N_FRAMES = 12         # 帧数
DURATION = 120        # 每帧 120ms，1.44s 循环
INNER_PADDING = 0.94  # 主体占画布 94%，留 3% 边距呼吸

# 不同表情可配不同动效
MODE_MAP = {
    "01_zaoan": "sway",          # 挥手 → 左右摇摆
    "02_wanan": "breathe_slow",  # 睡觉 → 缓慢呼吸
    "03_zaine": "breathe",       # 在呢 → 呼吸
    "04_jiayou": "float",        # 加油 → 上下浮动
    "05_weiqu": "breathe",       # 委屈 → 轻微呼吸
    "06_emo": "breathe_slow",    # emo → 缓慢呼吸
    "07_kaixin": "bounce",       # 开心 → 轻快弹跳
    "08_baobao": "breathe",      # 抱抱 → 呼吸
    "09_bixin": "bounce",        # 比心 → 轻跳
    "10_cengceng": "sway",       # 蹭蹭 → 左右蹭
    "11_qinqin": "breathe",      # 亲亲 → 呼吸
    "12_tietie": "breathe",      # 贴贴 → 呼吸
    "13_shoudao": "float",       # 收到 → 上下点头
    "14_xiexie": "breathe",      # 谢谢 → 呼吸
    "15_bukeqi": "sway",         # 不客气 → 摇摆
    "16_meiguanxi": "sway",      # 没关系 → 摇摆
    "17_sikao": "float",         # 思考 → 上下浮
    "18_aiya": "bounce",         # 哎呀 → 弹跳
    "19_ele": "breathe",         # 饿了 → 呼吸
    "20_xiangni": "breathe",     # 想你啦 → 呼吸
    "21_duilian_wink": "breathe",       # 怼脸wink → 呼吸
    "22_duilian_qinqin": "breathe",     # 怼脸亲亲 → 呼吸
    "23_duilian_haixiu": "breathe_slow",# 怼脸害羞 → 缓慢呼吸
    "24_duilian_miyankxiao": "bounce",  # 怼脸眯眼笑 → 弹跳
}


def make_white_transparent(img: Image.Image, threshold: int = 220) -> Image.Image:
    """把白色/近白色背景 mask 成完全透明（含边缘反锯齿白边修复）"""
    img = img.convert("RGBA")
    px = img.load()
    w, h = img.size
    changed = 0
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            # 更严格：所有通道 ≥ threshold 且彼此接近 → 视为白
            mn = min(r, g, b)
            mx = max(r, g, b)
            if r >= threshold and g >= threshold and b >= threshold and (mx - mn) <= 8:
                px[x, y] = (r, g, b, 0)
                changed += 1
            elif a < 10:
                px[x, y] = (r, g, b, 0)
                changed += 1
    # 边缘羽化：把"半透明+近白"的像素 alpha 减半（去白边）
    px = img.load()
    w, h = img.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a > 0 and a < 200:
                mn = min(r, g, b)
                mx = max(r, g, b)
                if mx >= 200 and (mx - mn) <= 25:
                    # 边缘疑似白边 → 压低 alpha
                    px[x, y] = (r, g, b, max(0, a - 80))
    return img


def render_frame(base: Image.Image, i: int, mode: str, scale: int) -> Image.Image:
    """生成单帧。base 已经透明化、缩放到 INNER_PADDING 之内"""
    n = 12
    t = i / n  # 0~1
    frame = Image.new("RGBA", (scale, scale), (0, 0, 0, 0))
    bw, bh = base.size

    if mode == "breathe":
        # 0.97 ~ 1.0 之间柔和呼吸
        factor = 0.97 + 0.03 * (1 - abs(0.5 - t) * 2)
        tw = int(bw * factor); th = int(bh * factor)
        tmp = base.resize((tw, th), Image.LANCZOS)
        frame.paste(tmp, ((scale - tw) // 2, (scale - th) // 2), tmp)
    elif mode == "breathe_slow":
        # 0.95 ~ 1.0 较慢呼吸
        factor = 0.95 + 0.05 * (1 - abs(0.5 - t) * 2)
        tw = int(bw * factor); th = int(bh * factor)
        tmp = base.resize((tw, th), Image.LANCZOS)
        frame.paste(tmp, ((scale - tw) // 2, (scale - th) // 2), tmp)
    elif mode == "float":
        # 上下浮动 ±6px
        offset = int(6 * (1 - abs(0.5 - t) * 2) * (1 if t < 0.5 else -1))
        frame.paste(base, ((scale - bw) // 2, (scale - bh) // 2 + offset), base)
    elif mode == "sway":
        # 左右摇摆 ±5px
        offset = int(5 * (1 - abs(0.5 - t) * 2) * (1 if t < 0.5 else -1))
        frame.paste(base, ((scale - bw) // 2 + offset, (scale - bh) // 2), base)
    elif mode == "bounce":
        # 轻快弹跳（缩放+位移）
        factor = 1.0 + 0.04 * (1 - abs(0.5 - t) * 2) * (1 if t < 0.5 else -1)
        tw = int(bw * factor); th = int(bh * factor)
        tmp = base.resize((tw, th), Image.LANCZOS)
        frame.paste(tmp, ((scale - tw) // 2, (scale - th) // 2), tmp)
    else:
        frame.paste(base, ((scale - bw) // 2, (scale - bh) // 2), base)
    return frame


def to_gif(in_path: str, out_path: str, mode: str = "breathe") -> tuple:
    base = Image.open(in_path)
    base = make_white_transparent(base)

    # 缩放到 240 之内
    inner = int(SCALE * INNER_PADDING)
    base.thumbnail((inner, inner), Image.LANCZOS)

    # 生成 12 帧
    raw_frames = [render_frame(base, i, mode, SCALE) for i in range(N_FRAMES)]

    # 转 P 模式并设置透明索引
    pal_frames = []
    for f in raw_frames:
        # 用 quantize 把 RGBA 转 P，保留 alpha
        p = f.convert("RGBA").convert("P", palette=Image.ADAPTIVE, colors=255)
        # 把透明区域（alpha=0）映射到索引 255
        # 因为 quantize 后 palette 最末索引通常是 255，且通常用作"其他/透明"
        # 我们手工确保：扫描 alpha=0 像素，把它们都设为索引 255
        alpha = f.split()[-1]  # alpha 通道
        mask = alpha.point(lambda v: 255 if v < 10 else 0)  # 透明 → 255
        # 把 mask 应用到 P 模式上
        # 实际上 quantize 不会保留 alpha，我们手工处理：
        # 获取 P 图像，调色板
        p_data = p.load()
        a_data = alpha.load()
        for y in range(p.size[1]):
            for x in range(p.size[0]):
                if a_data[x, y] < 10:
                    p_data[x, y] = 255
        p.info["transparency"] = 255
        pal_frames.append(p)

    pal_frames[0].save(
        out_path,
        save_all=True,
        append_images=pal_frames[1:],
        duration=DURATION,
        loop=0,
        transparency=255,
        disposal=2,
        optimize=True,
    )

    size_kb = os.path.getsize(out_path) / 1024
    return (out_path, size_kb)


def main():
    pngs = sorted(glob.glob(os.path.join(INPUT_DIR, "qy_*.png")))
    print(f"Found {len(pngs)} PNGs\n")
    results = []
    for png in pngs:
        name = os.path.basename(png).replace(".png", "")
        mode = MODE_MAP.get(name, "breathe")
        out = os.path.join(OUT_DIR, name + ".gif")
        try:
            path, kb = to_gif(png, out, mode)
            results.append((name, mode, f"{kb:.1f}KB"))
            print(f"[OK] {name:30s} mode={mode:14s} {kb:6.1f} KB")
        except Exception as e:
            print(f"[FAIL] {name}: {e}")
    print(f"\nDone. {len(results)}/{len(pngs)} GIFs generated.")


if __name__ == "__main__":
    main()