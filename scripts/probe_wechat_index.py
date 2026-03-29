#!/usr/bin/env python3
"""Probe local readiness for automating the WeChat mini program "微信指数"."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

COMMAND_TIMEOUT_SECONDS = 5.0
OSASCRIPT_BIN = shutil.which("osascript") or "/usr/bin/osascript"
SCREEN_CAPTURE_BIN = shutil.which("screencapture") or "/usr/sbin/screencapture"


def run_command(argv: list[str]) -> tuple[int, str, str]:
    try:
        result = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            timeout=COMMAND_TIMEOUT_SECONDS,
        )
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except FileNotFoundError as exc:
        return 127, "", f"executable not found: {exc.filename}"
    except subprocess.TimeoutExpired:
        return 124, "", f"timed out after {COMMAND_TIMEOUT_SECONDS:.1f}s"


def run_osascript(script: str) -> tuple[int, str, str]:
    return run_command([OSASCRIPT_BIN, "-e", script])


def parse_csv_like(text: str) -> list[str]:
    if not text:
        return []
    return [part.strip() for part in text.split(",") if part.strip()]


def parse_rect(text: str) -> dict[str, int] | None:
    parts = [part.strip() for part in text.split(",") if part.strip()]
    if len(parts) != 4:
        return None
    try:
        x, y, width, height = [int(float(part)) for part in parts]
    except ValueError:
        return None
    return {"x": x, "y": y, "width": width, "height": height}


def check_accessibility() -> dict[str, object]:
    code, out, err = run_osascript('tell application "System Events" to count of every process')
    return {
        "ok": code == 0,
        "stdout": out,
        "stderr": err,
    }


def check_wechat_windows() -> dict[str, object]:
    code, out, err = run_osascript(
        'tell application "System Events" to tell process "WeChat" to get name of every window'
    )
    windows = parse_csv_like(out) if code == 0 else []
    return {
        "ok": code == 0,
        "windows": windows,
        "stderr": err,
    }


def check_wechat_index_rect() -> dict[str, object]:
    code, out, err = run_osascript(
        'tell application "System Events" to tell process "WeChat" to get {position, size} of window "微信指数"'
    )
    rect = parse_rect(out) if code == 0 else None
    return {
        "ok": code == 0 and rect is not None,
        "rect": rect,
        "stderr": err,
    }


def check_screen_capture() -> dict[str, object]:
    temp_dir = Path(tempfile.mkdtemp(prefix="wechat-index-probe-"))
    image_path = temp_dir / "screen.png"
    code, out, err = run_command([SCREEN_CAPTURE_BIN, "-x", str(image_path)])
    exists = image_path.exists() and image_path.stat().st_size > 0
    try:
        if image_path.exists():
            image_path.unlink()
        temp_dir.rmdir()
    except OSError:
        pass
    return {
        "ok": code == 0 and exists,
        "stdout": out,
        "stderr": err,
    }


def build_report() -> dict[str, object]:
    accessibility = check_accessibility()
    wechat_windows = check_wechat_windows()
    index_rect = check_wechat_index_rect() if accessibility["ok"] else {"ok": False, "rect": None, "stderr": ""}
    screen_capture = check_screen_capture()

    window_names = wechat_windows.get("windows", [])
    wechat_index_found = "微信指数" in window_names

    if accessibility["ok"] and screen_capture["ok"] and wechat_index_found and index_rect["ok"]:
        status = "ready"
    elif accessibility["ok"] and wechat_index_found:
        status = "assisted"
    else:
        status = "blocked"

    next_actions: list[str] = []
    if not accessibility["ok"]:
        next_actions.append("grant Accessibility permission to the host app or shell that runs OpenClaw/Codex")
    if accessibility["ok"] and not wechat_index_found:
        next_actions.append('open the WeChat mini program window named "微信指数" and keep it visible')
    if not screen_capture["ok"]:
        next_actions.append("grant Screen Recording permission before OCR or screenshot-based reading")
    if status == "ready":
        next_actions.append("full desktop query mode is available")
    elif status == "assisted":
        next_actions.append("use keyword generation now and ask the user for a screenshot if numeric reading is needed")

    return {
        "status": status,
        "system_events_accessible": accessibility["ok"],
        "screen_capture_accessible": screen_capture["ok"],
        "wechat_windows": window_names,
        "wechat_index_window_found": wechat_index_found,
        "wechat_index_window_rect": index_rect["rect"],
        "errors": {
            "accessibility": accessibility["stderr"],
            "wechat_windows": wechat_windows["stderr"],
            "wechat_index_window_rect": index_rect["stderr"],
            "screen_capture": screen_capture["stderr"],
        },
        "next_actions": next_actions,
        "host": {
            "cwd": os.getcwd(),
            "osascript_bin": OSASCRIPT_BIN,
            "screencapture_bin": SCREEN_CAPTURE_BIN,
        },
    }


def main() -> int:
    print(json.dumps(build_report(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
