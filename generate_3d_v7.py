# -*- coding: utf-8 -*-
"""
Generate V7 3D model from the standard reference image (single front view).
Tries without multi-view first to avoid expired side/back URL download failures.
"""
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
    # 从环境变量读取 token（避免写死过期）
    token = os.environ.get("BUDDY_CLOUD_TOKEN", "").strip()
    if not token:
        print("[ERROR] BUDDY_CLOUD_TOKEN not set.", file=sys.stderr)
        sys.exit(1)

    ref = r"C:\Users\XIAOMI\Desktop\青芽\青芽形象固定\青芽标准参考图_定稿.jpg"
    print("[INFO] Encoding reference...", file=sys.stderr)
    main_b64 = image_to_base64(ref)

    endpoint = buddy_cloud._DEFAULT_ENDPOINT
    cfg = buddy_cloud._PROVIDER_MAP["3d"]

    body = buddy_cloud._build_3d_body(
        prompt="",
        model="3.1",
        image_base64=main_b64,
        enable_pbr=True,
        face_count=150000,
        generate_type="Normal",
    )

    print("[INFO] Submitting V7 3D (single-view)...", file=sys.stderr)
    result = buddy_cloud._call_api(
        endpoint, cfg["provider"], cfg["service"], cfg["version"],
        cfg["submit_action"], body, token,
    )

    job_id = result.get("JobId") or result.get("JobID")
    if not job_id:
        print(f"[ERROR] {json.dumps(result, ensure_ascii=False, indent=2)}", file=sys.stderr)
        sys.exit(1)

    print(f"[INFO] Job: {job_id}", file=sys.stderr)
    final = buddy_cloud._poll_job(
        endpoint, cfg["provider"], cfg["service"], cfg["version"],
        cfg["query_action"], job_id, token,
        poll_interval=5, max_poll_time=600,
    )

    out_dir = r"C:\Users\XIAOMI\Desktop\青芽\WKBD\QINGYABUD\outputs\v7"
    os.makedirs(out_dir, exist_ok=True)
    meta_path = os.path.join(out_dir, "qingya_3d_v7_result.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(final, f, ensure_ascii=False, indent=2)
    print(f"[INFO] Saved meta: {meta_path}", file=sys.stderr)

    # 输出 URL 列表
    urls = {"glb": None, "obj_zip": None, "preview": None}
    for f3d in final.get("ResultFile3Ds", []):
        if f3d["Type"] == "GLB":
            urls["glb"] = f3d["Url"]
            urls["preview"] = f3d.get("PreviewImageUrl")
        elif f3d["Type"] == "OBJ":
            urls["obj_zip"] = f3d["Url"]
    url_path = os.path.join(out_dir, "urls.json")
    with open(url_path, "w") as f:
        json.dump(urls, f, indent=2)
    print("[INFO] URLs:", json.dumps(urls, ensure_ascii=False, indent=2), file=sys.stderr)


if __name__ == "__main__":
    main()
