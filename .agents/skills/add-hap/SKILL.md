---
name: add-hap
description: 向本仓库收录一个新的鸿蒙 HAP 应用。当用户提供一个 GitHub/Gitee 项目链接，要求"添加 Hap"、"收录应用"、"添加新项目"到 README 表格时使用本技能。
---

# 添加新 Hap 到合集

当用户提供一个新的鸿蒙 HAP 项目链接时，按以下步骤将其收录进 `README.md`。

## 第 1 步：收集项目信息

访问用户提供的项目链接（用 `fetch` 工具抓取 GitHub 仓库页面和 README），收集：

- **项目名**：有中文名就用中文名（通常在 README 中），没有就用仓库英文名。
- **项目简介**：根据 README 用中文写**一句话**简短描述软件功能（不超过 30 字左右，与表格中现有条目风格一致）。

## 第 2 步：判断目标分类表格

按优先级依次检查项目的 `module.json5` 中的 `deviceTypes`：

1. 抓取 `entry/src/main/module.json5`（GitHub raw 链接形如：`https://raw.githubusercontent.com/<owner>/<repo>/<branch>/entry/src/main/module.json5`，分支通常是 `main` 或 `master`）。
2. 如果是 Flutter 跨端项目，鸿蒙代码在 `ohos` 子目录，改抓 `ohos/entry/src/main/module.json5`。
3. 分类规则：
   - `deviceTypes` 同时包含 `phone`、`tablet` 和 `2in1` → **一次开发，多端部署**
   - 包含 `phone`、`tablet` 但**没有** `2in1` → **鸿蒙手机/平板**
   - 只有 `2in1` → **鸿蒙电脑**
   - 抓不到 module.json5 时，根据 README 判断；仍无法判断时，默认放入 **一次开发，多端部署**

## 第 3 步：获取最新 release 日期

访问项目的 releases 页面（`https://github.com/<owner>/<repo>/releases`），获取最新一次 release 的发布日期，格式化为 `MM-DD`（如 `07-31`）。如果最新 release 是去年发布的，使用 `YYYY-MM-DD` 格式。

## 第 4 步：写入 README 表格

在 `README.md` 对应分类的表格中追加一行，格式为：

```markdown
| [项目名](项目链接) | [Link](releases链接) | 一句话描述。 | MM-DD |
```

示例：

```markdown
| [FlClash](https://github.com/tljk/FlClash-ohos) | [Link](https://github.com/tljk/FlClash-ohos/releases) | 基于ClashMeta的多平台代理客户端。 | 07-31 |
```

注意：
- 表格按更新日期**倒序**排列（新的在前），将新行插入到日期正确的位置，不要直接追加到表尾。
- 保持表格列对齐风格与现有条目一致。

## 第 5 步：更新贡献者名单并生成 SVG

1. 检查项目的开发者（仓库 owner 的用户名）是否已在 `CONTRIBUTING.md` 中（该文件每行格式为 `- [显示名](https://github.com/用户名)`，列表按首字母排序）。
2. 如果已存在，流程结束。
3. 如果不存在，将该开发者按 `- [用户名](https://github.com/用户名)` 格式插入到 `CONTRIBUTING.md` 的正确排序位置，然后在项目根目录用终端运行：

```sh
uv run .agents/skills/add-hap/scripts/contributers.py
```

（`uv` 不带参数运行，脚本需要 `GITHUB_TOKEN` 环境变量来获取头像。如果运行失败，报告错误并告知用户。）
