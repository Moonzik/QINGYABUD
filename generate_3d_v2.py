# -*- coding: utf-8 -*-
"""
Generate a refined 3D model of Qingya from local reference images using
buddy-cloud.py internals (image-base64 path to avoid public URL issues).
"""
import base64
import importlib.util
import json
import os
import sys
import time

# Load buddy-cloud.py as a module (filename contains hyphen, use importlib)
CLOUD_SCRIPT = r"C:\wb\WorkBuddy\resources\app.asar.unpacked\resources\plugins\workbuddy-builtin\skills\buddy-multimodal-generation\scripts\buddy-cloud.py"
spec = importlib.util.spec_from_file_location("buddy_cloud", CLOUD_SCRIPT)
buddy_cloud = importlib.util.module_from_spec(spec)
spec.loader.exec_module(buddy_cloud)


def image_to_base64(path: str, max_bytes: int = 6 * 1024 * 1024) -> str:
    with open(path, "rb") as f:
        data = f.read()
    if len(data) > max_bytes:
        raise ValueError(f"Image {path} is {len(data)} bytes, exceeds {max_bytes} bytes limit.")
    return base64.b64encode(data).decode("utf-8")


def main():
    ref_main = r"C:\Users\XIAOMI\Desktop\青芽\WKBD\QINGYABUD\outputs\v2\qingya_reference_v2.jpg"
    ref_extra = r"C:\Users\XIAOMI\Desktop\青芽\WKBD\QINGYABUD\outputs\v2\qingya_reference_v2b.jpg"

    print("[INFO] Encoding reference images...", file=sys.stderr)
    main_b64 = image_to_base64(ref_main)
    print(f"[INFO] Main reference: {len(main_b64)} base64 chars ({os.path.getsize(ref_main)} bytes)", file=sys.stderr)

    token = "tk_OmLRxK4aVjDXMj4Q4r90hamXMkCZWvd8"
    endpoint = buddy_cloud._DEFAULT_ENDPOINT

    # Image-to-3D: do NOT include prompt when ImageBase64 is provided
    body = buddy_cloud._build_3d_body(
        prompt="",
        model="3.1",
        image_base64=main_b64,
        enable_pbr=True,
        face_count=300000,
        generate_type="Normal",
    )

    cfg = buddy_cloud._PROVIDER_MAP["3d"]
    print("[INFO] Submitting image-to-3D generation request...", file=sys.stderr)
    result = buddy_cloud._call_api(
        endpoint,
        cfg["provider"],
        cfg["service"],
        cfg["version"],
        cfg["submit_action"],
        body,
        token,
    )

    job_id = result.get("JobId") or result.get("JobID")
    if not job_id:
        print("[ERROR] No job ID returned.", file=sys.stderr)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        sys.exit(1)

    print(f"[INFO] Job submitted: {job_id}", file=sys.stderr)

    final = buddy_cloud._poll_job(
        endpoint,
        cfg["provider"],
        cfg["service"],
        cfg["version"],
        cfg["query_action"],
        job_id,
        token,
        poll_interval=5,
        max_poll_time=600,
    )

    print("[INFO] Done.", file=sys.stderr)
    print(json.dumps(final, ensure_ascii=False, indent=2))

    # Save result metadata
    meta_path = r"C:\Users\XIAOMI\Desktop\青芽\WKBD\QINGYABUD\outputs\v2\qingya_3d_v2_result.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(final, f, ensure_ascii=False, indent=2)
    print(f"[INFO] Metadata saved to: {meta_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
