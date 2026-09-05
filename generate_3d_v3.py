# -*- coding: utf-8 -*-
"""Generate refined 3D v3 with high face count for better fur detail."""
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


def generate(ref_path: str, face_count: int, out_meta: str, out_prefix: str):
    print(f"\n[INFO] Reference: {ref_path}", file=sys.stderr)
    print(f"[INFO] Face count: {face_count}", file=sys.stderr)
    img_b64 = image_to_base64(ref_path)
    token = "tk_OmLRxK4aVjDXMj4Q4r90hamXMkCZWvd8"
    endpoint = buddy_cloud._DEFAULT_ENDPOINT

    body = buddy_cloud._build_3d_body(
        prompt="",
        model="3.1",
        image_base64=img_b64,
        enable_pbr=True,
        face_count=face_count,
        generate_type="Normal",
    )

    cfg = buddy_cloud._PROVIDER_MAP["3d"]
    result = buddy_cloud._call_api(
        endpoint, cfg["provider"], cfg["service"], cfg["version"],
        cfg["submit_action"], body, token,
    )

    job_id = result.get("JobId") or result.get("JobID")
    if not job_id:
        print("[ERROR] No job id", file=sys.stderr)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return None

    print(f"[INFO] Job submitted: {job_id}", file=sys.stderr)
    final = buddy_cloud._poll_job(
        endpoint, cfg["provider"], cfg["service"], cfg["version"],
        cfg["query_action"], job_id, token,
        poll_interval=5, max_poll_time=600,
    )

    with open(out_meta, "w", encoding="utf-8") as f:
        json.dump(final, f, ensure_ascii=False, indent=2)
    print(f"[INFO] Meta saved: {out_meta}", file=sys.stderr)

    # Print URLs so we can grab them
    for f3d in final.get("ResultFile3Ds", []):
        print(f"[INFO] {f3d['Type']}: {f3d['Url']}", file=sys.stderr)
        print(f"[INFO] Preview: {f3d.get('PreviewImageUrl')}", file=sys.stderr)

    return final


def main():
    ref = r"C:\Users\XIAOMI\Desktop\青芽\WKBD\QINGYABUD\outputs\v2\qingya_reference_v2.jpg"
    out_dir = r"C:\Users\XIAOMI\Desktop\青芽\WKBD\QINGYABUD\outputs\v3"
    os.makedirs(out_dir, exist_ok=True)

    # High detail run
    result = generate(
        ref,
        face_count=1000000,
        out_meta=os.path.join(out_dir, "qingya_3d_v3_result.json"),
        out_prefix="qingya_3d_v3",
    )

    if result:
        # Save URLs for download
        urls = {
            "glb": None,
            "obj_zip": None,
            "preview": None,
        }
        for f3d in result.get("ResultFile3Ds", []):
            if f3d["Type"] == "GLB":
                urls["glb"] = f3d["Url"]
                urls["preview"] = f3d.get("PreviewImageUrl")
            elif f3d["Type"] == "OBJ":
                urls["obj_zip"] = f3d["Url"]
        with open(os.path.join(out_dir, "urls.json"), "w") as f:
            json.dump(urls, f, indent=2)
        print("[INFO] URLs saved to urls.json", file=sys.stderr)


if __name__ == "__main__":
    main()