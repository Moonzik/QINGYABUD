"""v7 表情包 GIF 生成（先跑 3 张验证新形象）：
- rembg 抠图 (u2netp)
- 叠加道具 + 字幕
- 240×240 透明 GIF（magenta 占位 + ADAPTIVE 共享调色板 + 容差映射）
复用 v6 已验证的透明方案。
"""
import os, json, gc
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import imageio.v3 as iio
from rembg import remove, new_session

ROOT = r"C:\Users\XIAOMI\Desktop\青芽\WKBD\QINGYABUD\outputs\emojis_v1"
VID_DIR = os.path.join(ROOT, "v7_videos")
SRC_DIR = os.path.join(ROOT, "v7_src")
ASSET_DIR = os.path.join(ROOT, "v7_assets")
OUT_DIR = os.path.join(ROOT, "v7_gifs")
os.makedirs(OUT_DIR, exist_ok=True)

# 本次先跑的 3 张：视频文件名 → emoji 名
VIDEO_TO_NAME = {
    "The_camera_and_framing_stay_pe_2026-10-08T17-21-53.mp4": "01_zaoan",
    "The_camera_and_framing_stay_pe_2026-10-08T17-30-07.mp4": "02_wanan",
    "Full_body_of_the_character_sta_2026-10-08T17-14-57.mp4": "09_bixin",
}
# 用户要求：不要文字/符号挡脸 → 关闭所有 overlay 道具与字幕，只保留角色本身
USE_OVERLAY = False

# 读完整配置（含 overlay / text）
with open(os.path.join(ROOT, "v7_emojis.json"), encoding="utf-8") as f:
    EMOJIS = {e["name"]: e for e in json.load(f)}

print("Loading rembg u2netp model...")
sess = new_session("u2netp")

ASSETS = {}
for fname in os.listdir(ASSET_DIR):
    if fname.endswith(".png"):
        ASSETS[fname[:-4]] = Image.open(os.path.join(ASSET_DIR, fname)).convert("RGBA")

def get_font(size):
    for path in ["C:/Windows/Fonts/msyhbd.ttc", "C:/Windows/Fonts/msyh.ttc", "C:/Windows/Fonts/simhei.ttf"]:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()

def composite_overlay(base_rgba, overlay_asset, pos):
    if overlay_asset is None:
        return base_rgba
    out = base_rgba.copy()
    asset = overlay_asset.copy()
    bx, by = pos
    aw, ah = asset.size
    bw, bh = out.size
    if bx < 0 or by < 0 or bx+aw > bw or by+ah > bh:
        x0 = max(0, -bx); y0 = max(0, -by)
        x1 = min(aw, bw-bx); y1 = min(ah, bh-by)
        if x0 >= x1 or y0 >= y1:
            return out
        asset = asset.crop((x0, y0, x1, y1))
        bx, by = max(0, bx), max(0, by)
    tmp = Image.new("RGBA", out.size, (0,0,0,0))
    tmp.paste(asset, (bx, by), asset)
    out = Image.alpha_composite(out, tmp)
    return out

def add_text(rgba, text, pos, font_size=48, color=(255,255,255,250), stroke_color=(60,60,60,255), stroke_width=3):
    if not text:
        return rgba
    out = rgba.copy()
    draw = ImageDraw.Draw(out)
    font = get_font(font_size)
    x, y = pos
    for dx in range(-stroke_width, stroke_width+1):
        for dy in range(-stroke_width, stroke_width+1):
            if dx*dx + dy*dy <= stroke_width*stroke_width:
                draw.text((x+dx, y+dy), text, font=font, fill=stroke_color)
    draw.text((x, y), text, font=font, fill=color)
    return out

N_FRAMES = 12
DURATION_MS = 110
SIZE = 320
BG_PLACEHOLDER = np.array([255, 0, 255], dtype=np.uint8)
BG_TOLERANCE = 24
results_summary = []

for idx, (vf, name) in enumerate(sorted(VIDEO_TO_NAME.items())):
    video_path = os.path.join(VID_DIR, vf)
    cfg = EMOJIS.get(name, {})
    out_gif = os.path.join(OUT_DIR, f"qy_{name}.gif")
    print(f"\n[{idx+1}/3] {name}", flush=True)
    if not os.path.exists(video_path):
        print(f"  ✗ missing video")
        continue

    raw_frames = None
    for attempt in range(3):
        try:
            raw_frames = list(iio.imiter(video_path))
            break
        except Exception as e:
            print(f"  retry {attempt+1}/3: {e}")
            import time; time.sleep(1)
    if raw_frames is None:
        print(f"  ✗ ffmpeg failed on {vf}")
        continue
    n = len(raw_frames)
    crop_h = int(raw_frames[0].shape[0] * 0.08)
    indices = [round(i * (n-1) / (N_FRAMES-1)) for i in range(N_FRAMES)]

    rgba_frames = []
    for fi, fidx in enumerate(indices):
        raw = raw_frames[fidx]
        h = raw.shape[0]
        if crop_h > 0:
            raw = raw[:h-crop_h, :, :]
        pil = Image.fromarray(raw).convert("RGB")
        rgba = remove(pil, session=sess)  # 原图分辨率抠图
        arr = np.array(rgba)  # RGBA
        a = arr[:, :, 3]
        rgb = arr[:, :, :3]
        # 紫光雾清理：视频模型偶尔残留的紫色辉光（角色本身无紫色，半透明紫像素视为光雾置透明）
        purple_haze = (rgb[:, :, 0] > 110) & (rgb[:, :, 2] > 110) & (rgb[:, :, 1] < rgb[:, :, 0] * 0.7) & (a < 200)
        a[purple_haze] = 0
        # GIF 仅 1-bit 透明：把 alpha 做硬阈值（≥128 实 / 否则透），避免品红占位色与主体在半透明
        # 边缘混合出 salmon 紫边。硬边对 240px 表情包完全可接受。
        a = np.where(a >= 128, 255, 0).astype(np.uint8)
        rgba = Image.fromarray(arr)
        rgba.putalpha(Image.fromarray(a))
        rgba_frames.append(rgba)
        del raw, pil
        gc.collect()

    overlays = cfg.get("overlay", []) if USE_OVERLAY else []
    text = cfg.get("text") if USE_OVERLAY else None
    text_pos = cfg.get("text_pos")
    W, H = rgba_frames[0].size
    sx, sy = W / 1024.0, H / 922.0

    # --- 统一取景框：所有帧主体包围盒取并集 ---
    # 目的：整段 GIF 用同一个裁切框，主体位置/大小恒定，消除逐帧"忽闪"抖动
    ux0, uy0, ux1, uy1 = W, H, 0, 0
    for f in rgba_frames:
        am = f.split()[3].point(lambda v: 255 if v > 8 else 0)
        b = am.getbbox()
        if b:
            ux0 = min(ux0, b[0]); uy0 = min(uy0, b[1])
            ux1 = max(ux1, b[2]); uy1 = max(uy1, b[3])
    pad = int(max(ux1 - ux0, uy1 - uy0) * 0.04)
    bx0, by0 = max(0, ux0 - pad), max(0, uy0 - pad)
    bx1, by1 = min(W, ux1 + pad), min(H, uy1 + pad)
    bw, bh = bx1 - bx0, by1 - by0
    print(f"  union bbox=({bx0},{by0},{bx1},{by1}) {bw}x{bh} / frame {W}x{H}")

    # contain 完整放入画布并居中（不裁切主体）
    MARGIN = 0.04
    scale = min(SIZE / bw, SIZE / bh) * (1 - 2 * MARGIN)
    nw, nh = max(1, int(bw * scale)), max(1, int(bh * scale))
    ox, oy = (SIZE - nw) // 2, (SIZE - nh) // 2
    print(f"  fit -> {nw}x{nh} at ({ox},{oy})")

    out_frames = []
    ucx, ucy = (bx0 + bx1) / 2.0, (by0 + by1) / 2.0
    max_shift = int(SIZE * 0.07)
    for f in rgba_frames:
        composed = f
        for asset_name, pos in overlays:
            asset = ASSETS.get(asset_name)
            if asset is None:
                continue
            aw, ah = asset.size
            composed = composite_overlay(
                composed,
                asset.resize((max(1, int(aw * sx)), max(1, int(ah * sy))), Image.LANCZOS),
                (int(pos[0] * sx), int(pos[1] * sy)),
            )
        if text:
            if text_pos:
                tp = (int(text_pos[0] * sx), int(text_pos[1] * sy))
            else:
                tp = (W - int(120 * sx), H - int(70 * sy))
            composed = add_text(composed, text, tp, font_size=int(W * 0.05))
        # 逐帧居中微调：按该帧主体中心向统一框中心小幅平移（固定缩放不变大小，限制幅度防跳）
        am = f.split()[3].point(lambda v: 255 if v > 8 else 0)
        b = am.getbbox()
        if b:
            fcx, fcy = (b[0] + b[2]) / 2.0, (b[1] + b[3]) / 2.0
            dx = int(np.clip((ucx - fcx) * scale, -max_shift, max_shift))
            dy = int(np.clip((ucy - fcy) * scale, -max_shift, max_shift))
        else:
            dx = dy = 0
        sub = composed.crop((bx0, by0, bx1, by1)).resize((nw, nh), Image.LANCZOS)
        canvas = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
        canvas.paste(sub, (ox + dx, oy + dy), sub)
        out_frames.append(canvas)

    # 透明 GIF：第一帧生成共享 ADAPTIVE 调色板 → 所有帧量化到该 palette → 占位色附近像素映射 bg_idx
    first_small = out_frames[0].resize((SIZE, SIZE), Image.LANCZOS)
    first_bg = Image.new("RGB", first_small.size, tuple(BG_PLACEHOLDER.tolist()))
    first_bg.paste(first_small, mask=first_small.split()[3])
    first_p = first_bg.convert("P", palette=Image.ADAPTIVE, colors=255)
    shared_pal = first_p.getpalette()
    pal_arr = np.array(shared_pal, dtype=np.uint8).reshape(-1, 3)
    diffs = np.abs(pal_arr.astype(np.int16) - BG_PLACEHOLDER.astype(np.int16)).sum(axis=1)
    bg_idx = int(np.argmin(diffs))
    print(f"  bg_idx={bg_idx}")

    p_frames = []
    for f in out_frames:
        small = f.resize((SIZE, SIZE), Image.LANCZOS)
        bg = Image.new("RGB", small.size, tuple(BG_PLACEHOLDER.tolist()))
        bg.paste(small, mask=small.split()[3])
        p_img = bg.quantize(colors=255, palette=first_p)
        arr = np.array(p_img)
        pix_colors = pal_arr[arr]
        dist = np.abs(pix_colors.astype(np.int16) - BG_PLACEHOLDER.astype(np.int16)).sum(axis=2)
        # 兜底：把品红+主体混合出的 salmon 紫边（偏紫像素）也映射为透明，杜绝紫边残留
        salmon = (pix_colors[:, :, 0] > 120) & (pix_colors[:, :, 2] > 120) & (pix_colors[:, :, 1] < pix_colors[:, :, 0] * 0.7)
        arr[(dist < BG_TOLERANCE*3) | salmon] = bg_idx
        new_img = Image.fromarray(arr, mode="P")
        new_img.putpalette(shared_pal)
        p_frames.append(new_img)

    p_frames[0].save(
        out_gif, save_all=True, append_images=p_frames[1:],
        duration=DURATION_MS, loop=0, optimize=True, disposal=2, transparency=bg_idx,
    )
    kb = os.path.getsize(out_gif) // 1024
    results_summary.append((name, kb, out_gif))
    print(f"  ✓ {kb} KB")

print("\n=== Summary ===")
for name, kb, p in results_summary:
    print(f"  {name}: {kb} KB")
print(f"Total: {len(results_summary)} GIFs")
