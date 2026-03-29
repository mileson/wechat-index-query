#!/usr/bin/env python3
"""Use the WeChat Index "add compare word" flow for multi-keyword comparison."""

from __future__ import annotations

import argparse
import json
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from wechat_index_common import INDEX_RE, PCT_RE, parse_ocr_payload, run

ROOT = Path(__file__).resolve().parent
QUERY = ROOT / "query_wechat_index.py"
READ = ROOT / "read_wechat_index_window.py"
FOCUS = ROOT / "focus_wechat_index.py"
CLICK_SWIFT = ROOT / "click_at.swift"
PASTE_SWIFT = ROOT / "paste_keyword_at.swift"
SWIFT_BIN = "/Library/Developer/CommandLineTools/usr/bin/swift"

MAIN_SCENE_MARKERS = ("微信指数", "搜索关键词", "指数趋势", "添加对比词")
OUTSIDE_SCENE_MARKERS = ("桌面", "zsh", "Finder", "日历", "线程", "回收站")


def run_json(argv: list[str]) -> dict[str, Any]:
    result = run(argv)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "command failed")
    return json.loads(result.stdout)


def normalize(text: str) -> str:
    return re.sub(r"\s+", "", text or "")


def normalized_to_screen(rect: dict[str, int], box: dict[str, float]) -> tuple[int, int]:
    x = rect["x"] + round((box["x"] + box["width"] / 2.0) * rect["width"])
    y = rect["y"] + round((1.0 - box["y"] - box["height"] / 2.0) * rect["height"])
    return x, y


def detect_scene(payload: dict[str, Any]) -> str:
    full_text = str(payload.get("ocr", {}).get("fullText", ""))
    if "添加对比词" in full_text and ("Q 关键词" in full_text or "暂无数据" in full_text or "反馈与投诉" in full_text or "×" in full_text):
        return "compare_modal"
    if any(marker in full_text for marker in MAIN_SCENE_MARKERS):
        return "main"
    if any(marker in full_text for marker in OUTSIDE_SCENE_MARKERS):
        return "outside"
    return "unknown"


def direction_from_text(text: str) -> str:
    if "-" in text or "−" in text or "下降" in text:
        return "down"
    if "+" in text or "＋" in text or "上涨" in text:
        return "up"
    return "up_or_flat"


def extract_rect(payload: dict[str, Any]) -> dict[str, int]:
    rect = payload.get("probe", {}).get("wechat_index_window_rect")
    if not isinstance(rect, dict):
        raise RuntimeError("window rect missing from OCR payload")
    return rect


def get_lines(payload: dict[str, Any]) -> list[dict[str, Any]]:
    lines = payload.get("ocr", {}).get("lines", [])
    if not isinstance(lines, list):
        raise RuntimeError("OCR lines missing")
    return [line for line in lines if isinstance(line, dict)]


def choose_line(payload: dict[str, Any], predicate, *, prefer: str = "first") -> dict[str, Any]:
    candidates = [line for line in get_lines(payload) if predicate(str(line.get("text", "")))]
    if not candidates:
        raise RuntimeError("matching OCR line not found")
    if prefer == "widest":
        candidates.sort(key=lambda line: float(line.get("boundingBox", {}).get("width", 0.0)), reverse=True)
    elif prefer == "lowest_y":
        candidates.sort(key=lambda line: float(line.get("boundingBox", {}).get("y", 0.0)))
    elif prefer == "highest_y":
        candidates.sort(key=lambda line: float(line.get("boundingBox", {}).get("y", 0.0)), reverse=True)
    return candidates[0]


def click_line(payload: dict[str, Any], predicate, *, prefer: str = "first") -> dict[str, int]:
    rect = extract_rect(payload)
    line = choose_line(payload, predicate, prefer=prefer)
    box = line.get("boundingBox")
    if not isinstance(box, dict):
        raise RuntimeError("line bounding box missing")
    x, y = normalized_to_screen(rect, box)
    click = run([SWIFT_BIN, str(CLICK_SWIFT), str(x), str(y)])
    if click.returncode != 0:
        raise RuntimeError(click.stderr.strip() or click.stdout.strip() or "click failed")
    return {"x": x, "y": y}


def read_visible(delay_seconds: float = 0.0) -> dict[str, Any]:
    if delay_seconds > 0:
        time.sleep(delay_seconds)
    return run_json(["python3", str(READ)])


def ensure_main_scene() -> dict[str, Any]:
    payload = read_visible()
    scene = detect_scene(payload)
    if scene == "main":
        return payload
    if scene == "compare_modal":
        ok, closed_payload = close_compare_modal(payload)
        if ok:
            return closed_payload
    run_json(["python3", str(FOCUS)])
    payload = read_visible(0.6)
    scene = detect_scene(payload)
    if scene != "main":
        raise RuntimeError(f"current scene is {scene}, not WeChat Index main page")
    return payload


def open_compare_modal(main_payload: dict[str, Any]) -> dict[str, Any]:
    for _ in range(2):
        click_line(
            main_payload,
            lambda text: "添加对比词" in text,
            prefer="highest_y",
        )
        modal_payload = read_visible(0.9)
        if detect_scene(modal_payload) == "compare_modal":
            return modal_payload
        main_payload = modal_payload
    raise RuntimeError("failed to open compare modal")


def close_compare_modal(modal_payload: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    for _ in range(2):
        click_line(
            modal_payload,
            lambda text: "×" in text or text.strip().lower() == "x",
            prefer="highest_y",
        )
        page_payload = read_visible(0.8)
        if detect_scene(page_payload) == "main":
            return True, page_payload
        modal_payload = page_payload
    return False, modal_payload


def keyword_from_line(text: str, candidates: list[str]) -> str | None:
    normalized_text = normalize(text)
    matches = [keyword for keyword in candidates if normalize(keyword) and normalize(keyword) in normalized_text]
    if not matches:
        return None
    matches.sort(key=lambda keyword: len(normalize(keyword)), reverse=True)
    return matches[0]


def parse_compare_entries(payload: dict[str, Any], candidates: list[str]) -> list[dict[str, Any]]:
    lines = [str(line.get("text", "")) for line in get_lines(payload)]
    if not lines:
        return []

    section_started = False
    current_keyword: str | None = None
    entries: list[dict[str, Any]] = []
    entry_by_keyword: dict[str, dict[str, Any]] = {}

    for line in lines:
        if not section_started:
            if "日环比" in line:
                section_started = True
            continue
        if "添加对比词" in line or "订阅" in line or "指数趋势" in line:
            break
        if not line.strip():
            continue

        matched_keyword = keyword_from_line(line, candidates)
        if matched_keyword:
            current_keyword = matched_keyword
            entry = entry_by_keyword.setdefault(
                matched_keyword,
                {
                    "keyword": matched_keyword,
                    "status": "ok",
                    "index": None,
                    "day_change_pct": None,
                    "direction": "unknown",
                    "evidence": [],
                },
            )
            if line not in entry["evidence"]:
                entry["evidence"].append(line)
            if entry not in entries:
                entries.append(entry)
            continue

        index_match = INDEX_RE.search(line)
        if index_match and current_keyword:
            entry = entry_by_keyword[current_keyword]
            if entry["index"] is None:
                entry["index"] = index_match.group(0)
            if line not in entry["evidence"]:
                entry["evidence"].append(line)
            continue

        pct_match = PCT_RE.search(line)
        if pct_match and current_keyword:
            entry = entry_by_keyword[current_keyword]
            if entry["day_change_pct"] is None:
                entry["day_change_pct"] = pct_match.group(1)
                entry["direction"] = direction_from_text(line)
            if line not in entry["evidence"]:
                entry["evidence"].append(line)

    return entries


def query_base_keyword(keyword: str, wait_seconds: float) -> tuple[dict[str, Any], dict[str, Any]]:
    proc = run(["python3", str(QUERY), keyword, "--wait-seconds", f"{wait_seconds:.2f}"])
    record: dict[str, Any] = {
        "type": "keyword",
        "keyword": keyword,
        "compare_role": "base",
        "query_ok": proc.returncode == 0,
        "status": "error",
        "index": None,
        "day_change_pct": None,
        "direction": "unknown",
        "date_label": None,
        "evidence": [],
        "keyword_hit": False,
        "error": None,
    }
    if proc.returncode != 0:
        record["error"] = (proc.stderr.strip() or proc.stdout.strip() or f"exit {proc.returncode}")[:500]
        return record, {}

    payload = json.loads(proc.stdout)
    parsed = parse_ocr_payload(payload.get("after", {}).get("ocr", {}), keyword=keyword)
    record.update(parsed)
    return record, payload


def submit_compare_term(
    modal_payload: dict[str, Any],
    base_keyword: str,
    keyword: str,
    tracked_keywords: list[str],
    wait_seconds: float,
) -> tuple[dict[str, Any], dict[str, Any]]:
    rect = extract_rect(modal_payload)
    search_line = choose_line(
        modal_payload,
        lambda text: "关键词" in text and "搜索关键词" not in text,
        prefer="highest_y",
    )
    box = search_line.get("boundingBox")
    if not isinstance(box, dict):
        raise RuntimeError("compare modal search field bounding box missing")

    x, y = normalized_to_screen(rect, box)
    paste = run([SWIFT_BIN, str(PASTE_SWIFT), str(x), str(y), keyword])
    record: dict[str, Any] = {
        "type": "compare_keyword",
        "base_keyword": base_keyword,
        "keyword": keyword,
        "query_ok": paste.returncode == 0,
        "status": "error",
        "index": None,
        "day_change_pct": None,
        "direction": "unknown",
        "date_label": None,
        "evidence": [],
        "keyword_hit": False,
        "added_to_compare": False,
        "modal_closed": False,
        "error": None,
    }
    if paste.returncode != 0:
        record["error"] = (paste.stderr.strip() or paste.stdout.strip() or "failed to type compare keyword")[:500]
        return record, modal_payload

    after_payload = read_visible(max(wait_seconds, 0.8))
    scene = detect_scene(after_payload)
    parsed = parse_ocr_payload(after_payload.get("ocr", {}), keyword=keyword)
    record.update(parsed)

    if scene == "compare_modal" and parsed["status"] in {"no_data", "not_included"}:
        record["index"] = None
        record["day_change_pct"] = None
        record["direction"] = "unknown"
        record["date_label"] = None
        closed, page_payload = close_compare_modal(after_payload)
        record["modal_closed"] = closed
        if not closed:
            record["error"] = "compare modal could not be closed after no-data result"
        return record, page_payload

    if scene != "main":
        record["status"] = "scene_lost"
        record["error"] = f"unexpected scene after compare submit: {scene}"
        return record, after_payload

    entries = parse_compare_entries(after_payload, tracked_keywords + [keyword])
    record["page_entries_snapshot"] = entries
    for entry in entries:
        if entry["keyword"] != keyword:
            continue
        record["status"] = entry["status"]
        record["index"] = entry["index"]
        record["day_change_pct"] = entry["day_change_pct"]
        record["direction"] = entry["direction"]
        record["added_to_compare"] = True
        merged_evidence = list(record.get("evidence", []))
        for line in entry.get("evidence", []):
            if line not in merged_evidence:
                merged_evidence.append(line)
        record["evidence"] = merged_evidence[:8]
        return record, after_payload

    record["status"] = "mismatch"
    record["error"] = "compare term not found on final compare page"
    return record, after_payload


def summarize(records: list[dict[str, Any]]) -> dict[str, Any]:
    counts: dict[str, int] = {}
    sortable: list[tuple[int, str]] = []
    for record in records:
        status = str(record.get("status", "unknown"))
        counts[status] = counts.get(status, 0) + 1
        if status not in {"ok", "partial"}:
            continue
        index_value = record.get("index")
        if not index_value:
            continue
        try:
            numeric = int(str(index_value).replace(",", ""))
        except ValueError:
            continue
        sortable.append((numeric, str(record.get("keyword", ""))))
    sortable.sort(reverse=True)
    return {
        "total_records": len(records),
        "status_counts": counts,
        "top_by_index": [{"item": name, "index": value} for value, name in sortable[:5]],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("keywords", nargs="+", help="base keyword followed by compare keywords")
    parser.add_argument("--wait-seconds", type=float, default=1.2)
    parser.add_argument("--out", help="output report json path")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if len(args.keywords) < 2:
        print(json.dumps({"ok": False, "error": "provide a base keyword and at least one compare keyword"}, ensure_ascii=False, indent=2))
        return 1

    base_keyword = args.keywords[0]
    compare_keywords = args.keywords[1:]

    records: list[dict[str, Any]] = []
    report: dict[str, Any] = {
        "ok": True,
        "mode": "compare",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "base_keyword": base_keyword,
        "records": records,
    }

    try:
        base_record, base_payload = query_base_keyword(base_keyword, wait_seconds=max(args.wait_seconds, 2.0))
        records.append(base_record)
        if not base_record.get("query_ok"):
            report["ok"] = False
            report["summary"] = summarize(records)
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 1

        current_page = base_payload.get("after", {})
        tracked_keywords = [base_keyword]

        for keyword in compare_keywords:
            try:
                current_page = ensure_main_scene()
                modal_payload = open_compare_modal(current_page)
                record, current_page = submit_compare_term(
                    modal_payload,
                    base_keyword=base_keyword,
                    keyword=keyword,
                    tracked_keywords=tracked_keywords,
                    wait_seconds=args.wait_seconds,
                )
                records.append(record)
                if record.get("added_to_compare"):
                    tracked_keywords.append(keyword)
                if record.get("status") == "scene_lost":
                    report["ok"] = False
                    report["aborted_reason"] = str(record.get("error") or "scene lost during compare flow")
                    break
            except Exception as exc:  # noqa: BLE001
                records.append(
                    {
                        "type": "compare_keyword",
                        "base_keyword": base_keyword,
                        "keyword": keyword,
                        "query_ok": False,
                        "status": "error",
                        "index": None,
                        "day_change_pct": None,
                        "direction": "unknown",
                        "date_label": None,
                        "evidence": [],
                        "keyword_hit": False,
                        "added_to_compare": False,
                        "modal_closed": False,
                        "error": str(exc)[:500],
                    }
                )
                report["ok"] = False
                report["aborted_reason"] = f"compare flow failed on {keyword}: {exc}"
                break

        try:
            final_page = ensure_main_scene()
            report["final_page_entries"] = parse_compare_entries(final_page, tracked_keywords)
        except Exception as exc:  # noqa: BLE001
            report["final_page_error"] = str(exc)[:300]

        report["summary"] = summarize(records)

        if args.out:
            out_path = Path(args.out).expanduser().resolve()
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
            report["output_path"] = str(out_path)

        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["ok"] else 1
    except Exception as exc:  # noqa: BLE001
        report["ok"] = False
        report["fatal_error"] = str(exc)[:500]
        report["summary"] = summarize(records)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
