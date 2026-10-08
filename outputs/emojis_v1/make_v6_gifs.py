"""v6 表情包 GIF 批量生成：
- rembg 抠图 (u2netp 小模型)
- 叠加心形/泪滴/问号/感叹号/口水/光晕/阳光
- 加字幕（无气泡框，右下角或指定位置）
- 240×240 透明 GIF
"""
import os, json, gc
from PIL import Image, ImageDraw, ImageFont
import imageio.v3 as iio
from rembg import remove, new_session

ROOT = r"C:\Users\XIAOMI\Desktop\青芽\WKBD\QINGYABUD\outputs\emojis_v1"
VID_DIR = os.path.join(ROOT, "v6_videos")
SRC_DIR = os.path.join(ROOT, "v6_src")
ASSET_DIR = os.path.join(ROOT, "v6_assets")
OUT_DIR = os.path.join(ROOT, "v6_gifs")
os.makedirs(OUT_DIR, exist_ok=True)

# 视频文件 → emoji 名映射（按 prompt 顺序匹配）
VIDEO_TO_NAME = {
    "Soft_gentle_blink__slow_subtle_2026-09-05T14-00-00.mp4": "01_zaoan",
    "Soft_slow_breathing_while_slee_2026-09-05T13-59-49.mp4": "02_wanan",
    "Slowly_turns_head_from_side_to_2026-09-05T14-03-10.mp4": "03_zaine",
    "Lifts_both_front_paws_upward_i_2026-09-05T14-00-05.mp4": "04_jiayou",
    "Ears_droop_downward_slowly__ey_2026-09-05T14-03-51.mp4": "05_weiqu",
    "Head_hangs_low__eyes_look_up_t_2026-09-05T14-03-15.mp4": "06_emo",
    "Happy_bouncy_up_down_body_moti_2026-09-05T13-59-49.mp4": "07_kaixin",
    "Reaches_both_front_paws_forwar_2026-09-05T14-03-16.mp4": "08_baobao",
    "Tilt_head_slightly_to_one_side_2026-09-05T14-00-00.mp4": "09_bixin",
    "Slowly_leans_forward_toward_ca_2026-09-05T14-03-16.mp4": "10_cengceng",
    "Slowly_leans_closer_toward_cam_2026-09-05T14-00-47.mp4": "11_qinqin",
    "Tilts_head_to_one_side_and_pre_2026-09-05T14-03-26.mp4": "12_tietie",
    "Quick_small_head_nod_as_if_sal_2026-09-05T14-46-48.mp4": "13_shoudao",
    "Small_gentle_bow__head_lowers__2026-09-05T14-48-54.mp4": "14_xiexie",
    "Apologetic_tilt_of_head_to_sid_2026-09-05T14-49-59.mp4": "15_bukeqi",
    "Shakes_head_gently_from_side_t_2026-09-05T14-52-08.mp4": "16_meiguanxi",
    "Tilts_head_to_one_side_in_curi_2026-09-05T14-53-35.mp4": "17_sikao",
    "Small_surprised_expression__ey_2026-09-05T14-55-17.mp4": "18_aiya",
    "Tongue_flicks_out_briefly_lick_2026-09-05T14-56-33.mp4": "19_ele",
    "Front_paws_reach_up_longingly__2026-09-05T14-57-38.mp4": "20_xiangni",
    "Plays_a_slow_wink__one_eye_gen_2026-09-05T14-58-43.mp4": "21_duilian_wink",
    "Brings_both_paws_up_to_cheeks__2026-09-05T15-00-38.mp4": "22_duilian_qinqin",
    "Shy_smile__eyes_look_down_then_2026-09-05T15-01-53.mp4": "23_duilian_haixiu",
    "Eyes_narrow_into_a_squinty_hap_2026-09-05T15-02-55.mp4": "24_duilian_miyankxiao",
}

# 读取配置
with open(os.path.join(ROOT, "v6_emojis.json"), encoding="utf-8") as f:
    EMOJIS = {e["name"]: e for e in json.load(f)}

# 加载 rembg 模型（u2netp，小）
print("Loading rembg u2netp model...")
sess = new_session("u2netp")

# 加载道具
ASSETS = {}
for fname in os.listdir(ASSET_DIR):
    if fname.endswith(".png"):
        ASSETS[fname[:-4]] = Image.open(os.path.join(ASSET_DIR, fname)).convert("RGBA")

# 加载字体（黑体 / 微软雅黑）
def get_font(size):
    for path in [
        "C:/Windows/Fonts/msyhbd.ttc",
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/simhei.ttf",
    ]:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()

def composite_overlay(base_rgba, overlay_asset, pos):
    """在 base_rgba 上叠加 asset（pos 为左上角）"""
    if overlay_asset is None:
        return base_rgba
    out = base_rgba.copy()
    asset = overlay_asset.copy()
    # 若 asset 超出 base 边界，裁掉
    bx, by = pos
    aw, ah = asset.size
    bw, bh = out.size
    if bx < 0 or by < 0 or bx+aw > bw or by+ah > bh:
        # 裁 asset 到可见区域
        x0 = max(0, -bx)
        y0 = max(0, -by)
        x1 = min(aw, bw-bx)
        y1 = min(ah, bh-by)
        if x0 >= x1 or y0 >= y1:
            return out
        asset = asset.crop((x0, y0, x1, y1))
        bx, by = max(0, bx), max(0, by)
    tmp = Image.new("RGBA", out.size, (0,0,0,0))
    tmp.paste(asset, (bx, by), asset)
    out = Image.alpha_composite(out, tmp)
    return out

def add_text(rgba, text, pos, font_size=48, color=(255,255,255,250), stroke_color=(60,60,60,255), stroke_width=3):
    """加字幕（白字+深色描边，无气泡框）"""
    if not text:
        return rgba
    out = rgba.copy()
    draw = ImageDraw.Draw(out)
    font = get_font(font_size)
    x, y = pos
    # 描边
    for dx in range(-stroke_width, stroke_width+1):
        for dy in range(-stroke_width, stroke_width+1):
            if dx*dx + dy*dy <= stroke_width*stroke_width:
                draw.text((x+dx, y+dy), text, font=font, fill=stroke_color)
    # 主字
    draw.text((x, y), text, font=font, fill=color)
    return out

# 处理每个视频
N_FRAMES = 14
DURATION_MS = 110
SIZE = 240
results_summary = []

for idx, (vf, name) in enumerate(sorted(VIDEO_TO_NAME.items())):
    video_path = os.path.join(VID_DIR, vf)
    cfg = EMOJIS.get(name, {})
    out_gif = os.path.join(OUT_DIR, f"qy_{name}.gif")

    print(f"\n[{idx+1}/24] {name}", flush=True)
    if os.path.exists(out_gif):
        kb = os.path.getsize(out_gif) // 1024
        print(f"  ↻ already exists ({kb} KB), skip")
        results_summary.append((name, kb, out_gif))
        continue
    if not os.path.exists(video_path):
        print(f"  ✗ missing video")
        continue

    # 读视频帧（带 ffmpeg 重试）
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
    # 底部 8% 裁掉（水印 + 抖动边缘）
    crop_h = int(raw_frames[0].shape[0] * 0.08)
    # 均匀采样 14 帧
    indices = [round(i * (n-1) / (N_FRAMES-1)) for i in range(N_FRAMES)]

    rgba_frames = []
    for fi, fidx in enumerate(indices):
        raw = raw_frames[fidx]
        h = raw.shape[0]
        if crop_h > 0:
            raw = raw[:h-crop_h, :, :]
        pil = Image.fromarray(raw).convert("RGB")
        # rembg 在原图分辨率上做抠图（近景需要更高精度）
        rgba = remove(pil, session=sess)
        rgba_frames.append(rgba)
        del raw, pil
        gc.collect()

    # 叠道具 + 字幕
    overlays = cfg.get("overlay", [])
    text = cfg.get("text")
    text_pos = cfg.get("text_pos")

    out_frames = []
    for f in rgba_frames:
        composed = f
        for asset_name, pos in overlays:
            composed = composite_overlay(composed, ASSETS.get(asset_name), pos)
        # 默认字幕位置：右下角
        if text:
            tw, th = 100, 50
            if text_pos:
                # 归一化到原图尺寸 (1024)
                # 我们的源图是 1024×922（裁了底），所以 scale = img_w / 1024
                sx = f.size[0] / 1024
                sy = f.size[1] / 922
                tp = (int(text_pos[0]*sx), int(text_pos[1]*sy))
            else:
                tp = (f.size[0]-120, f.size[1]-70)
            composed = add_text(composed, text, tp, font_size=int(f.size[0]*0.05))
        out_frames.append(composed)

    # 缩到 240×240 → 合成到占位色 → 用第一帧的 ADAPTIVE 调色板量化所有帧 → 把所有"占位色附近"的像素统一映射到 bg_idx → GIF 透明
    import numpy as np
    BG_PLACEHOLDER = np.array([255, 0, 255], dtype=np.uint8)
    BG_TOLERANCE = 24

    # 第一步：用第一帧生成统一的 ADAPTIVE 调色板（确保所有帧 palette 一致）
    first_small = out_frames[0].resize((SIZE, SIZE), Image.LANCZOS)
    first_bg = Image.new("RGB", first_small.size, tuple(BG_PLACEHOLDER.tolist()))
    first_bg.paste(first_small, mask=first_small.split()[3])
    first_p = first_bg.convert("P", palette=Image.ADAPTIVE, colors=255)
    shared_pal = first_p.getpalette()  # 256*3 = 768 个 int

    # 找统一 bg_idx
    pal_arr = np.array(shared_pal, dtype=np.uint8).reshape(-1, 3)
    diffs = np.abs(pal_arr.astype(np.int16) - BG_PLACEHOLDER.astype(np.int16)).sum(axis=1)
    bg_idx = int(np.argmin(diffs))
    print(f"  bg_idx={bg_idx}")

    p_frames = []
    for f in out_frames:
        small = f.resize((SIZE, SIZE), Image.LANCZOS)  # RGBA
        bg = Image.new("RGB", small.size, tuple(BG_PLACEHOLDER.tolist()))
        bg.paste(small, mask=small.split()[3])
        # 用共享 palette 量化（保证 idx 一致）
        p_img = bg.quantize(colors=255, palette=first_p)  # use first frame's palette
        arr = np.array(p_img)
        # 把图像里所有"接近 magenta"的像素统一改成 bg_idx
        pix_colors = pal_arr[arr]
        dist = np.abs(pix_colors.astype(np.int16) - BG_PLACEHOLDER.astype(np.int16)).sum(axis=2)
        arr[dist < BG_TOLERANCE*3] = bg_idx
        new_img = Image.fromarray(arr, mode="P")
        new_img.putpalette(shared_pal)
        p_frames.append(new_img)

    p_frames[0].save(
        out_gif,
        save_all=True,
        append_images=p_frames[1:],
        duration=DURATION_MS,
        loop=0,
        optimize=True,
        disposal=2,
        transparency=bg_idx,
    )
    kb = os.path.getsize(out_gif) // 1024
    results_summary.append((name, kb, out_gif))
    print(f"  ✓ {kb} KB")

print("\n=== Summary ===")
for name, kb, p in results_summary:
    print(f"  {name}: {kb} KB")
print(f"Total: {len(results_summary)} GIFs")