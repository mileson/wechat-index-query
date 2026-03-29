---
name: wechat-index-query
description: WeChat Index desktop-assisted query and analysis workflow for the macOS WeChat mini program `微信指数`. Use this skill when OpenClaw sees requests such as `查询微信指数关于 XXX`, `查询微信指数 XXX`, `看 XXX 的微信指数`, `分析 XXX 在微信指数的涨跌`, `对比微信指数 A、B、C`, `比较 A 和 B 的微信指数`, `微信指数 A vs B`, `XXX 值不值得做`, `这个需求有没有量`, `这个场景该不该做`, `帮我看这张微信指数截图`, `看图里的微信指数`, or `给我一组微信指数关键词`; it should automatically route to single-query, add-compare, screenshot-only, or merged-report mode, expand broad opportunity-evaluation requests into compare keyword packs, detect no-data pages, recover safely, and return concise advice.
---

# WeChat Index Query

Use this skill for `查询微信指数关于 XXX` and adjacent natural-language variants, including comparison and screenshot requests.

## Auto Routing

1. Route to single-query mode when the user gives one topic and does not explicitly ask to compare it with other words.
   Examples: `查询微信指数关于查车牌`, `看下车牌查询的微信指数`, `分析挪车电话的微信指数涨跌`
2. Route to compare mode when the user asks to compare, contrast, benchmark, or evaluate multiple words, or when the user asks whether one broad topic is worth doing.
   Triggers include `对比`, `比较`, `vs`, `VS`, `PK`, `A和B`, `A、B、C`, `值不值得做`, `值得做吗`, `该不该做`, `能不能做`, `有没有量`, `有没有需求`, `需求大不大`, `值得投入吗`, or a request like `这几个词哪个更值得做`.
   Use the first clearly named topic as the base word when the user already gives an ordered list.
   If the user gives only one broad topic but asks whether it is worth doing, do not query only the literal topic. Generate a keyword pack and compare the strongest 3-6 scene words.
3. Route to screenshot mode when the user asks to inspect an image or screenshot of WeChat Index.
   Triggers include `帮我看这张微信指数截图`, `看图里的微信指数`, `根据这张图分析微信指数`, `这张截图有没有数据`.
   Use `run_wechat_index_report.py --image ...` when you have an accessible local image path.
4. Route to merged-report mode when the user wants both compare results and screenshot interpretation in one answer.
   Example: `对比 A、B、C，再结合这张微信指数截图一起分析`
5. Route to keyword-pack generation first when the user asks for keyword suggestions rather than naming all query words.
   Triggers include `给我一组微信指数关键词`, `帮我扩几个微信指数词`, `微信指数相关词有哪些`.
6. If the request is ambiguous, prefer the most concrete mode:
   - screenshot beats text-only query when the user supplies an image and asks to interpret it
   - compare beats single-query when at least two explicit topics are named, or when the user is clearly asking for opportunity judgment rather than literal single-word lookup
   - single-query beats keyword-pack generation when the user clearly wants only one exact word checked

## Quick Start

1. Extract the topic after `关于`.
2. Resolve the skill directory relative to this `SKILL.md`.
3. First raise the visible window so the user can see the automation start:

```bash
python3 <skill_dir>/scripts/focus_wechat_index.py
```

4. Then run the local probe:

```bash
python3 <skill_dir>/scripts/probe_wechat_index.py
```

5. If the probe says `ready`, choose one of these entry points:

```bash
python3 <skill_dir>/scripts/query_wechat_index.py "<topic>"
```

```bash
python3 <skill_dir>/scripts/compare_wechat_index.py "<base-keyword>" "<compare-a>" "<compare-b>"
```

```bash
python3 <skill_dir>/scripts/run_wechat_index_report.py "<topic-a>" "<topic-b>" --compare
```

```bash
python3 <skill_dir>/scripts/run_wechat_index_report.py --image <absolute-image-path>
```

6. If you only need to read the current visible page, run the OCR reader instead:

```bash
python3 <skill_dir>/scripts/read_wechat_index_window.py
```

7. Generate a keyword pack with 6-12 terms across four buckets:
   - exact/core: the exact topic, compact form, main brand or product word
   - alias/variant: abbreviations, mixed Chinese-English form, official short name
   - scenario/intent: audience, use-case, or scene words that can move attention
   - comparison: 2-4 plausible peers, substitutes, or competing phrases
8. If the probe status is not `ready`, switch to assisted mode:
   - explain the missing permission or window state
   - do not claim automation succeeded
   - ask the user for a screenshot or manually observed values if analysis must continue now
9. If the probe status is `ready`, operate the `微信指数` window in `WeChat` as a canvas rather than a standard control tree.
10. Read visible signals for each queried keyword:
   - current index value
   - up/down direction
   - visible relative change
   - obvious peak/trough or breakout/cooling signal
11. Summarize the result with the structure in `template.md`.

## Mode Mapping

- Single-query mode:

```bash
python3 <skill_dir>/scripts/run_wechat_index_report.py "<topic>"
```

- Compare mode:

```bash
python3 <skill_dir>/scripts/run_wechat_index_report.py --compare "<base>" "<compare-a>" "<compare-b>"
```

- Screenshot mode:

```bash
python3 <skill_dir>/scripts/run_wechat_index_report.py --image <absolute-image-path>
```

- Merged compare-plus-image mode:

```bash
python3 <skill_dir>/scripts/run_wechat_index_report.py --compare "<base>" "<compare-a>" "<compare-b>" --image <absolute-image-path>
```

## Keyword Rules

- Keep the pack between 6 and 12 keywords.
- Prefer nouns and stable phrases over full questions.
- For Chinese topics, avoid expanding into long sentence-like keywords.
- For mixed Chinese-English topics, keep both the mixed form and the compact English form when they are common in actual use.
- If the topic is broad, include at least one brand term, one product term, one scenario term, and one comparison term.
- Avoid inventing competitors unless they are obvious.

## Opportunity Expansion Rules

- When the user asks `值不值得做`, `该不该做`, `有没有量`, or a similar demand-validation question, automatically expand the topic into a compare pack before querying.
- Default compare pack size is 3-6 words.
- Build the pack in this order:
  - one exact/core phrase from the user's wording
  - one more common short query phrase
  - one high-intent scenario phrase
  - one adjacent action phrase
  - one or two substitute or neighboring phrases if they are clearly relevant
- Prefer phrases that real users would search, not product-spec language.
- If the user gives a very broad topic, bias toward scenario words over category words.
- If the topic has an obvious long-tail branch that may be uncollected, keep at most one exploratory long-tail word so no-data results can still be recorded.
- If the user asks whether the demand is worth building, summarize by:
  - highest-volume comparable phrase
  - strongest direct-intent phrase
  - no-data rate across the pack
  - recommendation: worth doing / worth narrowing / not enough signal yet
- Example for `查车牌 值不值得做`:
  - `查车牌`
  - `车牌查询`
  - `车牌号查询`
  - `查车主`
  - `车辆违章查询`
  - `挪车电话`

## Desktop Workflow

1. Find the window named `微信指数` under process `WeChat`.
2. Use the window bounds from the probe output.
3. Assume the mini program exposes zero accessible child elements unless verified otherwise.
4. Prefer window-relative coordinates over control names.
5. Use click and type automation only after the probe confirms `system_events_accessible=true`.
6. Use screenshot or OCR only after the probe confirms `screen_capture_accessible=true`.
7. Prefer `query_wechat_index.py` over ad hoc coordinate clicking because it uses OCR to locate the search field first.
8. If OCR output still shows the landing page or a `加载中` state after a query, wait 2-3 seconds and run `read_wechat_index_window.py` again.
9. Wait for the view to settle after each query before reading any numbers.
10. If OCR or visual reading is noisy, say that clearly and ask the user for a tighter screenshot instead of fabricating data.
11. Before a new query, clear stale state:
    - if a compare modal is still open, close it first
    - if the previous page is `暂无数据` or `未收录`, go back first
12. For compare mode, use the visible `添加对比词` button instead of repeatedly replacing the top search word.
13. In compare mode, after each added word:
    - if the page returns to the main chart and the word appears in OCR, record it as added
    - if the modal shows `暂无数据` or `未收录`, close the modal, record the miss, and continue to the next word
14. If the captured scene is no longer the WeChat Index window, abort the batch instead of repeatedly clicking and refocusing.

## Analysis Rules

- Compare absolute index level and recent direction separately.
- Distinguish `high but falling`, `low but rising`, and `high and rising`.
- Call out whether the stronger opportunity is the brand word, product word, or scenario word.
- Give 2-4 practical next-step suggestions.
- Do not infer exact historical numbers beyond what is visible.
- If only direction is readable, state that explicitly.

## References

- Permission meanings and blocker patterns: `references/permissions.md`
- Output structure: `template.md`
- Example response: `examples/sample.md`
- OCR helper: `scripts/ocr_image.swift`
- Visible-page OCR: `scripts/read_wechat_index_window.py`
- Query driver: `scripts/query_wechat_index.py`
- Compare driver: `scripts/compare_wechat_index.py`
- Unified report driver: `scripts/run_wechat_index_report.py`
