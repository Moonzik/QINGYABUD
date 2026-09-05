# -*- coding: utf-8 -*-
"""Generate side-view and back-view reference images for multi-view 3D."""
import base64
import importlib.util
import json
import os
import sys

CLOUD_SCRIPT = r"C:\wb\WorkBuddy\resources\app.asar.unpacked\resources\plugins\workbuddy-builtin\skills\buddy-multimodal-generation\scripts\buddy-cloud.py"
spec = importlib.util.spec_from_file_location("buddy_cloud", CLOUD_SCRIPT)
buddy_cloud = importlib.util.module_from_spec(spec)
spec.loader.exec_module(buddy_cloud)


def image_to_base64(path: str, max_bytes: int = 6 * 1024 * 1024) -> str:
    with open(path, "rb") as f:
        data = f.read()
    if len(data) > max_bytes:
        raise ValueError(f"Image too large: {len(data)} bytes")
    return base64.b64encode(data).decode("utf-8")


def main():
    token = "tk_OmLRxK4aVjDXMj4Q4r90hamXMkCZWvd8"
    endpoint = buddy_cloud._DEFAULT_ENDPOINT
    cfg = buddy_cloud._PROVIDER_MAP["image"]

    out_dir = r"C:\Users\XIAOMI\Desktop\青芽\WKBD\QINGYABUD\outputs\v4"
    os.makedirs(out_dir, exist_ok=True)

    # Side view prompt — explicit description matching the standard Qingya spec
    side_prompt = (
        "Q版圆润幼态小兽青芽侧视图，巴掌大小坐姿，主体毛色米白色与暖白色，"
        "耳朵外侧、四肢到蓬松大尾巴渐变浅薄荷绿，头顶正中央一根嫩绿色蕨类嫩芽微微发光，"
        "琥珀金色大圆水汪汪眼睛温柔懵懂，粉色小鼻子微笑嘴型，"
        "脖子浅青色叶脉纹理蝴蝶结永远存在，圆乎乎毛茸茸尖圆兽耳内侧暖粉色，"
        "OC渲染，柔光，浅绿色背景，纯色干净，无文字，无水印，可爱治愈"
    )
    back_prompt = (
        "Q版圆润幼态小兽青芽背面图，巴掌大小坐姿，主体毛色米白色与暖白色，"
        "背部、四肢、蓬松大尾巴渐变浅薄荷绿，头顶嫩绿色蕨类嫩芽微微发光，"
        "脖子浅青色叶脉纹理蝴蝶结，毛茸茸兽耳，蓬松圆尾巴，OC渲染，"
        "柔光，浅绿色背景，纯色干净，无文字，无水印，可爱治愈"
    )

    for view_name, prompt in [("side", side_prompt), ("back", back_prompt)]:
        print(f"\n[INFO] Generating {view_name} view...", file=sys.stderr)
        body = {"Prompt": prompt, "Resolution": "1024:1024", "Revise": 1}
        result = buddy_cloud._call_api(
            endpoint, cfg["provider"], cfg["service"], cfg["version"],
            cfg["submit_action"], body, token,
        )
        job_id = result.get("JobId") or result.get("JobID")
        if not job_id:
            print(f"[ERROR] No job id: {result}", file=sys.stderr)
            continue
        print(f"[INFO] Job: {job_id}", file=sys.stderr)
        final = buddy_cloud._poll_job(
            endpoint, cfg["provider"], cfg["service"], cfg["version"],
            cfg["query_action"], job_id, token,
            poll_interval=4, max_poll_time=300,
        )
        meta = os.path.join(out_dir, f"{view_name}_result.json")
        with open(meta, "w", encoding="utf-8") as f:
            json.dump(final, f, ensure_ascii=False, indent=2)
        print(f"[INFO] {view_name} meta saved", file=sys.stderr)
        for img in final.get("ResultFileImages", []):
            print(f"[INFO] {view_name} URL: {img.get('Url')}", file=sys.stderr)


if __name__ == "__main__":
    main()