#!/usr/bin/env python3
"""Shared helpers for WeChat Index OCR parsing and reporting."""

from __future__ import annotations

import json
import re
import subprocess
from typing import Any

INDEX_RE = re.compile(r"\b\d{1,3}(?:,\d{3})+\b")
PCT_RE = re.compile(r"(\d+(?:\.\d+)?)\s*%")
DATE_RE = re.compile(r"\d{1,2}月\d{1,2}日指数")

NO_DATA_MARKERS = (
    "暂无数据",
    "无数据",
    "暂时没有数据",
    "暂无效据",
)

NOT_INCLUDED_MARKERS = (
    "暂未收录",
    "未收录",
    "微信指数没有加入",
    "未被收录",
    "指数暂无收录",
)

LOADING_MARKERS = (
    "加载中",
    "正在加载",
)


def run(argv: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(argv, capture_output=True, text=True, check=False)


def run_json(argv: list[str]) -> dict[str, Any]:
    result = run(argv)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "command failed")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"json parse failed: {exc}") from exc


def _normalize(text: str) -> str:
    return re.sub(r"\s+", "", text or "")


def _contains_marker(text: str, markers: tuple[str, ...]) -> bool:
    normalized = _normalize(text)
    return any(_normalize(marker) in normalized for marker in markers)


def parse_ocr_payload(ocr_payload: dict[str, Any], keyword: str | None = None) -> dict[str, Any]:
    lines_raw = ocr_payload.get("lines", [])
    lines = [str(line.get("text", "")) for line in lines_raw if isinstance(line, dict)]
    full_text = str(ocr_payload.get("fullText", ""))
    normalized_full_text = _normalize(full_text)

    status = "unknown"
    if _contains_marker(full_text, NOT_INCLUDED_MARKERS):
        status = "not_included"
    elif _contains_marker(full_text, NO_DATA_MARKERS):
        status = "no_data"
    elif _contains_marker(full_text, LOADING_MARKERS):
        status = "loading"

    index_value = None
    for line in lines:
        match = INDEX_RE.search(line)
        if match:
            index_value = match.group(0)
            break
    if index_value is None:
        match = INDEX_RE.search(full_text)
        if match:
            index_value = match.group(0)

    day_change_pct = None
    direction = "unknown"
    day_change_line = None
    for line in lines:
        if "%" not in line:
            continue
        match = PCT_RE.search(line)
        if not match:
            continue
        day_change_pct = match.group(1)
        day_change_line = line
        if "-" in line or "−" in line or "下降" in line:
            direction = "down"
        elif "+" in line or "＋" in line or "上涨" in line:
            direction = "up"
        else:
            direction = "up_or_flat"
        break

    date_label = None
    for line in lines:
        match = DATE_RE.search(line)
        if match:
            date_label = match.group(0)
            break
    if date_label is None:
        match = DATE_RE.search(full_text)
        if match:
            date_label = match.group(0)

    if status == "unknown":
        if index_value and day_change_pct:
            status = "ok"
        elif index_value:
            status = "partial"

    evidence = []
    for line in lines:
        if keyword and keyword in line:
            evidence.append(line)
            continue
        if day_change_line and line == day_change_line:
            evidence.append(line)
            continue
        if index_value and index_value in line:
            evidence.append(line)
            continue
        if date_label and date_label in line:
            evidence.append(line)
            continue
        if any(marker in line for marker in ("暂无", "未收录", "加载中", "数据异动记录")):
            evidence.append(line)
    deduped_evidence = []
    seen = set()
    for line in evidence:
        if line in seen:
            continue
        seen.add(line)
        deduped_evidence.append(line)

    keyword_hit = True
    if keyword:
        keyword_hit = _normalize(keyword) in normalized_full_text

    return {
        "status": status,
        "index": index_value,
        "day_change_pct": day_change_pct,
        "direction": direction,
        "date_label": date_label,
        "evidence": deduped_evidence[:8],
        "keyword_hit": keyword_hit,
        "line_count": len(lines),
        "full_text": full_text,
    }
