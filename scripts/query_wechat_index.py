#!/usr/bin/env python3
"""Focus WeChat Index, locate the search box, enter a keyword, and OCR the result."""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path

from wechat_index_common import parse_ocr_payload

ROOT = Path(__file__).resolve().parent
FOCUS = ROOT / "focus_wechat_index.py"
READ = ROOT / "read_wechat_index_window.py"
BACK = ROOT / "back_wechat_index.py"
CLICK_SWIFT = ROOT / "click_at.swift"
PASTE_SWIFT = ROOT / "paste_keyword_at.swift"
SWIFT_BIN = "/Library/Developer/CommandLineTools/usr/bin/swift"

SEARCH_HINTS = (
    "搜索关键词",
    "搜索关键",
    "搜索词",
    "Q 搜索关键词",
    "Q ",
    "＜Q",
    "<Q",
)

WECHAT_SCENE_MARKERS = ("微信指数", "搜索关键词", "指数趋势", "添加对比词", "数据异动记录", "反馈与投诉")
OUTSIDE_SCENE_MARKERS = ("桌面", "zsh", "Finder", "日历", "线程", "回收站")


def run(argv: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(argv, capture_output=True, text=True, check=False)


def run_json(argv: list[str]) -> dict[str, object]:
    result = run(argv)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "command failed")
    return json.loads(result.stdout)


def find_search_line(ocr_payload: dict[str, object]) -> dict[str, object]:
    lines = ocr_payload.get("ocr", {}).get("lines", [])
    if not isinstance(lines, list):
        raise RuntimeError("OCR lines are missing")

    for line in lines:
        if not isinstance(line, dict):
            continue
        text = str(line.get("text", ""))
        if any(hint in text for hint in SEARCH_HINTS):
            return line

    # Fallback: on result pages the placeholder may be replaced by the queried keyword
    # and only keep a top-row line like "<Q xxx". Select a top wide line as search bar.
    top_candidates: list[dict[str, object]] = []
    for line in lines:
        if not isinstance(line, dict):
            continue
        box = line.get("boundingBox")
        if not isinstance(box, dict):
            continue
        y = float(box.get("y", 0))
        width = float(box.get("width", 0))
        if y >= 0.82 and width >= 0.20:
            top_candidates.append(line)
    if top_candidates:
        top_candidates.sort(key=lambda item: float(item.get("boundingBox", {}).get("width", 0)), reverse=True)
        return top_candidates[0]
    raise RuntimeError("could not locate the search box text in OCR output")


def normalized_to_screen(rect: dict[str, int], box: dict[str, float]) -> tuple[int, int]:
    x = rect["x"] + round((box["x"] + box["width"] / 2.0) * rect["width"])
    y = rect["y"] + round((1.0 - box["y"] - box["height"] / 2.0) * rect["height"])
    return x, y


def fallback_search_point(rect: dict[str, int]) -> tuple[int, int]:
    # Keep away from back arrow (left-top) and tap the expected search area.
    x = rect["x"] + round(rect["width"] * 0.34)
    y = rect["y"] + round(rect["height"] * 0.07)
    return x, y


def detect_scene(ocr_payload: dict[str, object]) -> str:
    ocr = ocr_payload.get("ocr", {})
    full_text = str(ocr.get("fullText", ""))
    if any(marker in full_text for marker in WECHAT_SCENE_MARKERS):
        return "wechat_index"
    if any(marker in full_text for marker in OUTSIDE_SCENE_MARKERS):
        return "outside"
    return "unknown"


def get_lines(ocr_payload: dict[str, object]) -> list[dict[str, object]]:
    lines = ocr_payload.get("ocr", {}).get("lines", [])
    if not isinstance(lines, list):
        return []
    return [line for line in lines if isinstance(line, dict)]


def close_compare_modal_if_open(before_payload: dict[str, object], rect: dict[str, int]) -> tuple[dict[str, object], bool]:
    full_text = str(before_payload.get("ocr", {}).get("fullText", ""))
    if "添加对比词" not in full_text or ("×" not in full_text and "Q 关键词" not in full_text):
        return before_payload, False

    close_line = None
    for line in get_lines(before_payload):
        text = str(line.get("text", ""))
        if "×" in text or text.strip().lower() == "x":
            close_line = line
            break
    if close_line is None:
        return before_payload, False

    box = close_line.get("boundingBox")
    if not isinstance(box, dict):
        return before_payload, False
    x, y = normalized_to_screen(rect, box)
    action = run([SWIFT_BIN, str(CLICK_SWIFT), str(x), str(y)])
    if action.returncode != 0:
        return before_payload, False
    time.sleep(0.7)
    return run_json(["python3", str(READ)]), True


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("keyword")
    parser.add_argument("--wait-seconds", type=float, default=2.0)
    parser.add_argument("--skip-focus", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.skip_focus:
        focus_payload = {"ok": True, "skipped": True}
    else:
        focus_payload = run_json(["python3", str(FOCUS)])
        if not focus_payload.get("ok"):
            print(json.dumps({"ok": False, "error": "failed to focus window", "focus": focus_payload}, ensure_ascii=False, indent=2))
            return 1

    before_payload = run_json(["python3", str(READ)])
    if not before_payload.get("ok"):
        print(json.dumps({"ok": False, "error": "failed to OCR window before search", "before": before_payload}, ensure_ascii=False, indent=2))
        return 1

    scene = detect_scene(before_payload)
    recover_attempts = 0
    while scene != "wechat_index" and recover_attempts < 2:
        recover_attempts += 1
        run_json(["python3", str(FOCUS)])
        time.sleep(0.5)
        before_payload = run_json(["python3", str(READ)])
        scene = detect_scene(before_payload)
    if scene != "wechat_index":
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": "pre-click scene is not WeChat Index; aborting to avoid click loop",
                    "scene": scene,
                    "recover_attempts": recover_attempts,
                    "before": before_payload,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 1

    probe = before_payload.get("probe", {})
    rect = probe.get("wechat_index_window_rect")
    if not isinstance(rect, dict):
        print(json.dumps({"ok": False, "error": "window rect missing from probe", "before": before_payload}, ensure_ascii=False, indent=2))
        return 1

    before_payload, closed_modal = close_compare_modal_if_open(before_payload, rect)
    pre_state = parse_ocr_payload(before_payload.get("ocr", {}), keyword=args.keyword)
    if pre_state["status"] in {"no_data", "not_included"}:
        back = run(["python3", str(BACK)])
        if back.returncode == 0:
            time.sleep(0.7)
            before_payload = run_json(["python3", str(READ)])
    scene = detect_scene(before_payload)

    used_fallback_point = False
    try:
        search_line = find_search_line(before_payload)
        box = search_line.get("boundingBox")
        if not isinstance(box, dict):
            raise RuntimeError("search line bounding box missing")
        click_x, click_y = normalized_to_screen(rect, box)
    except RuntimeError as exc:
        search_line = {"text": "<fallback-search-point>", "reason": str(exc)}
        click_x, click_y = fallback_search_point(rect)
        used_fallback_point = True
    action = run([SWIFT_BIN, str(PASTE_SWIFT), str(click_x), str(click_y), args.keyword])
    if action.returncode != 0:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": "failed to drive the search box",
                "click_point": {"x": click_x, "y": click_y},
                "search_line": search_line,
                "used_fallback_point": used_fallback_point,
                "closed_modal_before_query": closed_modal,
                "stderr": action.stderr.strip(),
                "stdout": action.stdout.strip(),
                "before": before_payload,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 1

    time.sleep(max(args.wait_seconds, 0.2))
    after_payload = run_json(["python3", str(READ)])
    after_scene = detect_scene(after_payload)
    print(
        json.dumps(
            {
                "ok": bool(after_payload.get("ok")) and after_scene == "wechat_index",
                "keyword": args.keyword,
                "click_point": {"x": click_x, "y": click_y},
                "search_line": search_line,
                "used_fallback_point": used_fallback_point,
                "closed_modal_before_query": closed_modal,
                "scene_before": scene,
                "scene_after": after_scene,
                "before": before_payload,
                "after": after_payload,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if after_payload.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
