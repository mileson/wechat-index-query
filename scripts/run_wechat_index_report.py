#!/usr/bin/env python3
"""Run single/multi keyword WeChat Index queries and merge a structured report."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from wechat_index_common import parse_ocr_payload, run, run_json

ROOT = Path(__file__).resolve().parent
QUERY = ROOT / "query_wechat_index.py"
BACK = ROOT / "back_wechat_index.py"
COMPARE = ROOT / "compare_wechat_index.py"
OCR_SWIFT = ROOT / "ocr_image.swift"
SWIFT_BIN = "/Library/Developer/CommandLineTools/usr/bin/swift"


def query_keyword(keyword: str, wait_seconds: float, auto_back_on_miss: bool, skip_focus: bool = False) -> dict[str, Any]:
    cmd = ["python3", str(QUERY), keyword, "--wait-seconds", f"{wait_seconds:.2f}"]
    if skip_focus:
        cmd.append("--skip-focus")
    record: dict[str, Any] = {
        "type": "keyword",
        "keyword": keyword,
        "query_ok": False,
        "status": "error",
        "index": None,
        "day_change_pct": None,
        "direction": None,
        "date_label": None,
        "evidence": [],
        "keyword_hit": False,
        "attempts": 0,
        "back_performed": False,
        "error": None,
    }

    last_error = None
    for attempt in range(1, 3):
        proc = run(cmd)
        record["attempts"] = attempt
        if proc.returncode != 0:
            last_error = (proc.stderr.strip() or proc.stdout.strip() or f"exit {proc.returncode}")[:500]
            continue

        payload = json.loads(proc.stdout)
        ocr = payload.get("after", {}).get("ocr", {})
        parsed = parse_ocr_payload(ocr, keyword=keyword)
        record.update(parsed)
        record["query_ok"] = True
        if parsed.get("keyword_hit"):
            break
        last_error = "keyword mismatch after OCR (queried term not detected on result page)"
        record["status"] = "mismatch"
        if attempt < 2:
            continue

    if not record["query_ok"]:
        record["error"] = last_error
        return record
    if record.get("status") == "mismatch":
        record["error"] = last_error

    if auto_back_on_miss and parsed["status"] in {"no_data", "not_included"}:
        back = run(["python3", str(BACK)])
        record["back_performed"] = back.returncode == 0
        if back.returncode != 0:
            record["error"] = f"back failed: {(back.stderr.strip() or back.stdout.strip())[:180]}"

    return record


def analyze_image(image_path: str) -> dict[str, Any]:
    record: dict[str, Any] = {
        "type": "image",
        "image_path": image_path,
        "status": "error",
        "index": None,
        "day_change_pct": None,
        "direction": None,
        "date_label": None,
        "evidence": [],
        "error": None,
    }
    proc = run([SWIFT_BIN, str(OCR_SWIFT), image_path])
    if proc.returncode != 0:
        record["error"] = (proc.stderr.strip() or proc.stdout.strip() or f"exit {proc.returncode}")[:500]
        return record
    ocr = json.loads(proc.stdout)
    parsed = parse_ocr_payload(ocr, keyword=None)
    record.update(parsed)
    return record


def run_compare_keywords(keywords: list[str], wait_seconds: float) -> dict[str, Any]:
    proc = run(["python3", str(COMPARE), *keywords, "--wait-seconds", f"{wait_seconds:.2f}"])
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError:
        payload = {
            "ok": False,
            "records": [],
            "error": (proc.stderr.strip() or proc.stdout.strip() or f"exit {proc.returncode}")[:500],
        }
    payload["exit_code"] = proc.returncode
    return payload


def summarize(records: list[dict[str, Any]]) -> dict[str, Any]:
    counts: dict[str, int] = {}
    for record in records:
        status = str(record.get("status", "unknown"))
        counts[status] = counts.get(status, 0) + 1

    sortable = []
    for record in records:
        if str(record.get("status", "unknown")) not in {"ok", "partial"}:
            continue
        index_str = record.get("index")
        if not index_str:
            continue
        try:
            numeric = int(str(index_str).replace(",", ""))
        except ValueError:
            continue
        sortable.append((numeric, record.get("keyword", record.get("image_path", ""))))
    sortable.sort(reverse=True)

    return {
        "total_records": len(records),
        "status_counts": counts,
        "top_by_index": [{"item": name, "index": value} for value, name in sortable[:5]],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("keywords", nargs="*", help="keywords for WeChat Index query")
    parser.add_argument("--compare", action="store_true", help="use the add-compare flow with the first keyword as base")
    parser.add_argument("--image", action="append", default=[], help="analyze an existing screenshot")
    parser.add_argument("--wait-seconds", type=float, default=2.2)
    parser.add_argument("--auto-back-on-miss", action="store_true", default=True)
    parser.add_argument("--out", help="output report json path")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.keywords and not args.image:
        print(json.dumps({"ok": False, "error": "provide at least one keyword or --image"}, ensure_ascii=False, indent=2))
        return 1

    records: list[dict[str, Any]] = []
    aborted_reason = None
    overall_ok = True
    compare_payload: dict[str, Any] | None = None
    if args.compare and args.keywords:
        compare_payload = run_compare_keywords(args.keywords, wait_seconds=max(args.wait_seconds, 1.0))
        records.extend(compare_payload.get("records", []))
        overall_ok = bool(compare_payload.get("ok"))
        aborted_reason = compare_payload.get("aborted_reason")
    else:
        for index, keyword in enumerate(args.keywords):
            record = query_keyword(
                keyword,
                wait_seconds=args.wait_seconds,
                auto_back_on_miss=args.auto_back_on_miss,
                skip_focus=index > 0,
            )
            records.append(record)
            error_text = str(record.get("error") or "")
            if "pre-click scene is not WeChat Index" in error_text:
                aborted_reason = "scene lost before click; stopped batch to avoid repeated window toggling"
                overall_ok = False
                break

    for image_path in args.image:
        records.append(analyze_image(image_path))

    report = {
        "ok": overall_ok,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "records": records,
        "summary": summarize(records),
    }
    if aborted_reason:
        report["aborted_reason"] = aborted_reason
    if compare_payload:
        for key in ("mode", "base_keyword", "final_page_entries", "final_page_error", "fatal_error"):
            if key in compare_payload:
                report[key] = compare_payload[key]

    if args.out:
        out_path = Path(args.out).expanduser().resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        report["output_path"] = str(out_path)

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
