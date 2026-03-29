# Contributing

## Scope

This repository is a macOS desktop automation skill bundle for `微信指数`. Contributions should preserve the current interaction model:

- probe before driving the UI
- explain blockers instead of claiming automation succeeded
- prefer structured JSON output
- keep manual fallback paths explicit

## Development Checklist

1. Read `SKILL.md`, `template.md`, and `references/permissions.md` before changing behavior.
2. Update examples or references when the user-facing workflow changes.
3. Keep Python scripts standard-library only unless there is a strong reason to add dependencies.
4. Do not commit real credentials, private screenshots, or desktop recordings.

## Local Verification

Run the following before opening a pull request:

```bash
python3 -m py_compile scripts/*.py
python3 scripts/run_wechat_index_report.py --help
python3 scripts/probe_wechat_index.py
```

If you change OCR heuristics or click paths, also verify against a real `微信指数` window on macOS and update `examples/sample.md` when the output shape changes.

## Pull Request Notes

- Describe the user-visible impact first.
- Call out permission or platform assumptions.
- Include screenshots only if they do not leak private account information.
- Mention whether the change affects single-query, compare, screenshot, or fallback mode.
