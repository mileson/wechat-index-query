#!/usr/bin/env python3
"""Return from current WeChat Index page by clicking the top-left back area."""

from __future__ import annotations

import json
import time
from pathlib import Path

from wechat_index_common import run, run_json

ROOT = Path(__file__).resolve().parent
FOCUS = ROOT / "focus_wechat_index.py"
PROBE = ROOT / "probe_wechat_index.py"
CLICK_SWIFT = ROOT / "click_at.swift"
SWIFT_BIN = "/Library/Developer/CommandLineTools/usr/bin/swift"


def main() -> int:
    focus = run_json(["python3", str(FOCUS)])
    probe = run_json(["python3", str(PROBE)])
    rect = probe.get("wechat_index_window_rect")
    if not isinstance(rect, dict):
        print(json.dumps({"ok": False, "error": "window rect not found", "probe": probe}, ensure_ascii=False, indent=2))
        return 1

    x = int(rect["x"]) + 20
    y = int(rect["y"]) + 20
    click = run([SWIFT_BIN, str(CLICK_SWIFT), str(x), str(y)])
    time.sleep(0.5)

    payload = {
        "ok": click.returncode == 0,
        "click_point": {"x": x, "y": y},
        "focus": focus,
        "probe": probe,
        "click_stdout": click.stdout.strip(),
        "click_stderr": click.stderr.strip(),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
