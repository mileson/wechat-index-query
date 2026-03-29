# Permissions And Blockers

Use this reference when the local probe reports a blocker.

## Required Permissions

### 1. Accessibility

Purpose:
- activate the WeChat window
- send clicks and keystrokes
- inspect whether the `微信指数` window exists

Typical failure signal:
- `System Events` reports error `-1719`
- messages such as `osascript does not have permission to use accessibility features`

Interpretation:
- desktop automation is blocked before any click or typing step

### 2. Screen Recording

Purpose:
- capture the visible `微信指数` window
- run OCR or manual vision on numbers and trend cards

Typical failure signal:
- `screencapture` returns non-zero
- messages such as `could not create image from display`
- messages such as `could not create image from rect`

Interpretation:
- keyword generation still works
- numeric extraction from the mini program does not work yet

## Window Discovery Facts

- The target window is currently exposed as `微信指数` under process `WeChat`.
- The separate `WeApp` process may exist even when the actual visible window belongs to `WeChat`.
- The `微信指数` window may expose zero accessible child elements. In that case, use window-relative coordinates and visual reading instead of control names.

## Fallback Modes

### Assisted Mode

Use when:
- accessibility works but screen recording is blocked
- or the window is found but readable extraction is unreliable

Behavior:
- generate a keyword pack
- explain what is missing
- ask the user for a screenshot or manually observed values
- continue with analysis once the user provides the visual input

### Full Mode

Use only when:
- accessibility works
- screen recording works
- the `微信指数` window is present

Behavior:
- generate keyword pack
- query the window
- capture visible content
- read index signals
- produce analysis and suggestions
