# -*- coding: utf-8 -*-
"""Generate V4 3D with multi-view constraints (front + side + back) for accurate side profile."""
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
    cfg = buddy_cloud._PROVIDER_MAP["3d"]

    # Main reference (front view, from standard reference)
    main_ref = r"C:\Users\XIAOMI\Desktop\青芽\WKBD\QINGYABUD\outputs\v2\qingya_reference_v2.jpg"
    print(f"[INFO] Encoding main reference: {main_ref}", file=sys.stderr)
    main_b64 = image_to_base64(main_ref)

    # Side and back URLs (already generated, with signed URLs)
    side_url = open(r"C:\Users\XIAOMI\Desktop\青芽\WKBD\QINGYABUD\outputs\v4\side_url.txt").read().strip()
    back_url = open(r"C:\Users\XIAOMI\Desktop\青芽\WKBD\QINGYABUD\outputs\v4\back_url.txt").read().strip()

    multi_view = json.dumps([
        {"ViewType": "left", "ViewImageUrl": side_url},
        {"ViewType": "back", "ViewImageUrl": back_url},
    ])

    out_dir = r"C:\Users\XIAOMI\Desktop\青芽\WKBD\QINGYABUD\outputs\v4"
    os.makedirs(out_dir, exist_ok=True)

    body = buddy_cloud._build_3d_body(
        prompt="",
        model="3.1",
        image_base64=main_b64,
        multi_view=multi_view,
        enable_pbr=True,
        face_count=800000,
        generate_type="Normal",
    )

    print("[INFO] Submitting multi-view 3D generation...", file=sys.stderr)
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

    meta_path = os.path.join(out_dir, "qingya_3d_v4_result.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(final, f, ensure_ascii=False, indent=2)

    urls = {"glb": None, "obj_zip": None, "preview": None}
    for f3d in final.get("ResultFile3Ds", []):
        if f3d["Type"] == "GLB":
            urls["glb"] = f3d["Url"]
            urls["preview"] = f3d.get("PreviewImageUrl")
        elif f3d["Type"] == "OBJ":
            urls["obj_zip"] = f3d["Url"]
    with open(os.path.join(out_dir, "urls.json"), "w") as f:
        json.dump(urls, f, indent=2)

    print("[INFO] Done. URLs:")
    for k, v in urls.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()