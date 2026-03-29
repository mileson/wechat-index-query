#!/usr/bin/env python3
"""Bring the WeChat mini program window "微信指数" to the front."""

from __future__ import annotations

import json
import shutil
import subprocess

OSASCRIPT_BIN = shutil.which("osascript") or "/usr/bin/osascript"

SCRIPT = r'''
tell application "WeChat"
  activate
end tell

tell application "System Events"
  tell process "WeChat"
    set frontmost to true
    tell window "微信指数"
      perform action "AXRaise"
      return {name, position, size}
    end tell
  end tell
end tell
'''


def parse_rect(text: str) -> dict[str, int] | None:
    parts = [part.strip() for part in text.split(",") if part.strip()]
    if len(parts) != 5:
        return None
    try:
        x = int(float(parts[1]))
        y = int(float(parts[2]))
        width = int(float(parts[3]))
        height = int(float(parts[4]))
    except ValueError:
        return None
    return {"x": x, "y": y, "width": width, "height": height}


def main() -> int:
    try:
        result = subprocess.run(
            [OSASCRIPT_BIN, "-e", SCRIPT],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except FileNotFoundError as exc:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": f"executable not found: {exc.filename}",
                    "osascript_bin": OSASCRIPT_BIN,
                },
                ensure_ascii=False,
            )
        )
        return 1
    except subprocess.TimeoutExpired:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": "timed out after 5s",
                    "osascript_bin": OSASCRIPT_BIN,
                },
                ensure_ascii=False,
            )
        )
        return 1

    stdout = result.stdout.strip()
    stderr = result.stderr.strip()
    ok = result.returncode == 0
    payload = {
        "ok": ok,
        "stdout": stdout,
        "stderr": stderr,
        "osascript_bin": OSASCRIPT_BIN,
        "window_rect": parse_rect(stdout) if ok else None,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
