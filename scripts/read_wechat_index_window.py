#!/usr/bin/env python3
"""Capture the WeChat Index window and OCR the visible text with macOS Vision."""

from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROBE = ROOT / "probe_wechat_index.py"
OCR_SWIFT = ROOT / "ocr_image.swift"
SCREEN_CAPTURE_BIN = "/usr/sbin/screencapture"
SWIFT_BIN = "/Library/Developer/CommandLineTools/usr/bin/swift"


def run(argv: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(argv, capture_output=True, text=True, check=False)


def load_probe() -> dict[str, object]:
    result = run(["python3", str(PROBE)])
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "probe failed")
    return json.loads(result.stdout)


def capture_window(rect: dict[str, int], image_path: Path) -> subprocess.CompletedProcess[str]:
    region = ",".join(str(rect[key]) for key in ("x", "y", "width", "height"))
    return run([SCREEN_CAPTURE_BIN, "-x", "-R", region, str(image_path)])


def run_ocr(image_path: Path) -> dict[str, object]:
    result = run([SWIFT_BIN, str(OCR_SWIFT), str(image_path)])
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "OCR failed")
    return json.loads(result.stdout)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--keep-image", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    probe = load_probe()
    rect = probe.get("wechat_index_window_rect")
    if probe.get("status") != "ready" or not isinstance(rect, dict):
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": "wechat index window is not ready for OCR",
                    "probe": probe,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 1

    temp_dir = Path(tempfile.mkdtemp(prefix="wechat-index-read-"))
    image_path = temp_dir / "window.png"

    try:
        capture = capture_window(rect, image_path)
        if capture.returncode != 0 or not image_path.exists() or image_path.stat().st_size <= 0:
            payload = {
                "ok": False,
                "error": "failed to capture window",
                "capture_stdout": capture.stdout.strip(),
                "capture_stderr": capture.stderr.strip(),
                "probe": probe,
            }
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            return 1

        ocr = run_ocr(image_path)
        payload = {
            "ok": bool(ocr.get("ok")),
            "probe": probe,
            "image_path": str(image_path),
            "ocr": ocr,
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0 if payload["ok"] else 1
    finally:
        if not args.keep_image:
            try:
                if image_path.exists():
                    image_path.unlink()
                temp_dir.rmdir()
            except OSError:
                pass


if __name__ == "__main__":
    raise SystemExit(main())
