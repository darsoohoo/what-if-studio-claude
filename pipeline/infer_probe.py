#!/usr/bin/env python3
"""
Cheap one-clip probe for the tryinfer API.

Submits a SINGLE 5-second image-to-video job and prints the full poll
response, so you can confirm your key + model work (and see the exact
response shape) before spending on a whole video. Costs one clip.

Usage (from the pipeline folder, with your key set):
    python infer_probe.py                     # default model seedance-2.0-pro
    python infer_probe.py happyhorse          # try another model id
"""

import json
import sys
import time

import make_videos as mv


def main():
    key = mv.infer_api_key()
    if not key:
        sys.exit("No key found. Set TRYINFER_API_KEY or put it in pipeline/tryinfer_key.txt")
    model = sys.argv[1] if len(sys.argv) > 1 else "seedance-2.0-pro"

    image_url = mv.pollinations_image_url("a glowing planet in deep space, cinematic, vertical", seed=3)
    print(f"Submitting ONE 5s image-to-video test to '{model}' (this bills one clip)...")
    rid = mv.infer_submit(model, "image-to-video", {
        "image_url": image_url,
        "prompt": "slow push in, embers drifting, cinematic, smooth motion",
        "duration_seconds": "5",
        "aspect_ratio": "9:16",
    }, key)
    print("request_id:", rid)

    waited = 0
    while waited < mv.INFER_POLL_TIMEOUT:
        time.sleep(mv.INFER_POLL_INTERVAL)
        waited += mv.INFER_POLL_INTERVAL
        resp = mv.infer_poll(rid, key)
        status = mv._find_status(resp)
        print(f"[{waited:3d}s] status = {status}")
        if status in ("COMPLETED", "SUCCEEDED", "SUCCESS", "FAILED", "ERROR", "CANCELLED", "CANCELED"):
            print("\n--- FULL POLL RESPONSE ---")
            print(json.dumps(resp, indent=2)[:2500])
            print("\nextracted video URL:", mv._find_video_url(resp))
            return
    print("Timed out - the job never reached a terminal status.")


if __name__ == "__main__":
    main()
