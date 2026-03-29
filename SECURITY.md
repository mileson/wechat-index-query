# Security Policy

## Supported Scope

This repository contains local desktop automation for the WeChat mini program `微信指数` on macOS. Security-sensitive areas include:

- Accessibility-driven desktop input
- Screen Recording usage
- OCR processing of user-provided screenshots
- Any logic that could mis-handle private desktop content

## Reporting A Vulnerability

Please do not disclose security issues in a public GitHub issue.

Preferred approach:

1. Use a private disclosure channel once the repository is hosted publicly.
2. Share a minimal reproduction with redacted screenshots or logs.
3. Explain whether the issue affects Accessibility access, Screen Recording, OCR handling, or report generation.

## Disclosure Guidance

- Never include real tokens, cookies, or private account data.
- Redact names, chats, and unrelated desktop content from screenshots.
- Avoid publishing permission bypass techniques before a fix is available.
