# wechat-index-query

> 一个面向 macOS 的微信指数桌面辅助查询与分析 skill 仓库。

[English](README.md)

![工作流概览](docs/images/workflow.svg)

## 项目简介

`wechat-index-query` 用来驱动 WeChat 桌面端里的 `微信指数` 小程序窗口，完成聚焦窗口、权限探测、截图 OCR、单词查询、对比词查询，以及截图辅助分析。它适合接入 OpenClaw、Codex 或其他本地 Agent 工作流，作为一个可复用的技能包来使用。

## 核心能力

- 探测辅助功能、屏幕录制、窗口可见性是否就绪
- 自动聚焦 `微信指数` 窗口
- 支持单关键词查询与结果读取
- 支持 `添加对比词` 方式的多词对比
- 支持对已有截图做 OCR 分析
- 输出结构化 JSON，方便继续做总结或判断
- 核心 Python 脚本只依赖标准库

## 效果展示

<table>
  <tr>
    <td width="42%">
      <img src="docs/images/screenshots/wechat-index-ui.png" alt="微信指数对比界面" />
    </td>
    <td width="58%">
      <img src="docs/images/screenshots/openclaw-wechat-index-result.png" alt="OpenClaw 汇总结论界面" />
    </td>
  </tr>
  <tr>
    <td><strong>微信指数结果页</strong><br/>展示对比词、指数值、日环比与趋势区域。</td>
    <td><strong>OpenClaw 汇总输出</strong><br/>查询完成后可把结构化结论直接回传到聊天界面。</td>
  </tr>
</table>

## 运行前提

- macOS 13 及以上
- 已安装并登录 WeChat 桌面端
- 已打开名为 `微信指数` 的小程序窗口
- 已安装 Xcode Command Line Tools
- Python 3.11 及以上
- 已为运行终端或宿主应用授予辅助功能权限
- 已为运行终端或宿主应用授予屏幕录制权限

## 快速开始

先检查环境是否具备完整自动化能力：

```bash
python3 scripts/probe_wechat_index.py
```

如需把窗口拉到前台：

```bash
python3 scripts/focus_wechat_index.py
```

单词查询：

```bash
python3 scripts/run_wechat_index_report.py "车牌查询"
```

多词对比：

```bash
python3 scripts/run_wechat_index_report.py --compare "查车牌" "车牌查询" "挪车电话"
```

截图分析：

```bash
python3 scripts/run_wechat_index_report.py --image /absolute/path/to/wechat-index.png
```

## 目录结构

```text
.
|-- SKILL.md
|-- template.md
|-- examples/
|-- references/
`-- scripts/
```

其中：

- `SKILL.md` 定义触发词、路由规则和推荐工作流
- `template.md` 定义面向最终回答的结构模板
- `references/permissions.md` 说明权限阻塞与降级模式
- `examples/sample.md` 提供输出样例
- `scripts/` 包含探测、聚焦、点击、OCR、查询、对比与汇总脚本

## 推荐使用方式

如果把它接进 Agent：

```text
1. 先运行 focus_wechat_index.py
2. 再运行 probe_wechat_index.py
3. ready 状态下执行单词、对比词或截图模式
4. 非 ready 状态下改为截图辅助模式，并明确说明缺失权限
5. 按 template.md 的结构输出结论和建议
```

## 验证

建议至少执行以下本地检查：

```bash
python3 -m py_compile scripts/*.py
python3 scripts/run_wechat_index_report.py --help
python3 scripts/probe_wechat_index.py
```

最后一个命令需要真实桌面权限和可见的 `微信指数` 窗口。

## 贡献与安全

- 开发和提交流程见 [CONTRIBUTING.md](CONTRIBUTING.md)
- 安全披露流程见 [SECURITY.md](SECURITY.md)

## 许可证

本项目使用 [MIT License](LICENSE)。

## 作者
- X: [Mileson07](https://x.com/Mileson07)
- 小红书: [超级峰](https://xhslink.com/m/4LnJ9aB1f97)
- 抖音: [超级峰](https://v.douyin.com/rH645q7trd8/)
