# -*- coding: utf-8 -*-
"""
Generate V5 3D model with multi-view constraint, reusing V4's side+back images.
Quick test if cloud API quota is restored.
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


def image_to_base64(path, max_bytes=6*1024*1024):
    with open(path, "rb") as f:
        data = f.read()
    if len(data) > max_bytes:
        raise ValueError(f"Image too large: {len(data)} bytes")
    return base64.b64encode(data).decode("utf-8")


def main():
    ref = r"C:\Users\XIAOMI\Desktop\青芽\青芽形象固定\青芽标准参考图_定稿.jpg"
    print("[INFO] Encoding reference...", file=sys.stderr)
    main_b64 = image_to_base64(ref)

    # Read V4 side/back URLs
    with open(r"C:\Users\XIAOMI\Desktop\青芽\WKBD\QINGYABUD\outputs\v4\side_url.txt") as f:
        side_url = f.read().strip()
    with open(r"C:\Users\XIAOMI\Desktop\青芽\WKBD\QINGYABUD\outputs\v4\back_url.txt") as f:
        back_url = f.read().strip()

    token = "tk_sblktoiXB2cSHSVVgJ3xIYGivDEG1XWu"
    endpoint = buddy_cloud._DEFAULT_ENDPOINT

    multi_view = json.dumps([
        {"ViewType": "left", "ViewImageUrl": side_url},
        {"ViewType": "back", "ViewImageUrl": back_url},
    ])

    body = buddy_cloud._build_3d_body(
        prompt="",
        model="3.1",
        image_base64=main_b64,
        enable_pbr=True,
        face_count=150000,
        generate_type="Normal",
        multi_view=multi_view,
    )

    cfg = buddy_cloud._PROVIDER_MAP["3d"]
    print("[INFO] Submitting...", file=sys.stderr)
    try:
        result = buddy_cloud._call_api(
            endpoint, cfg["provider"], cfg["service"], cfg["version"],
            cfg["submit_action"], body, token,
        )
    except Exception as e:
        print(f"[FAIL] API call failed: {e}", file=sys.stderr)
        sys.exit(1)

    job_id = result.get("JobId") or result.get("JobID")
    if not job_id:
        print("[ERROR] No job ID.", file=sys.stderr)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        sys.exit(1)

    print(f"[INFO] Job: {job_id}", file=sys.stderr)
    final = buddy_cloud._poll_job(
        endpoint, cfg["provider"], cfg["service"], cfg["version"],
        cfg["query_action"], job_id, token,
        poll_interval=5, max_poll_time=600,
    )
    print("[INFO] Done.", file=sys.stderr)
    print(json.dumps(final, ensure_ascii=False, indent=2))

    meta = r"C:\Users\XIAOMI\Desktop\青芽\WKBD\QINGYABUD\outputs\v4\qingya_3d_v5_result.json"
    with open(meta, "w", encoding="utf-8") as f:
        json.dump(final, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
