# 验收报告 · media-to-notes v0.3.0

> 日期：2026-08-19
> 版本：v0.3.0（built-in zero-config cleaning + timeline interleave + ASR/OCR upgrades）
> 范围：内置清洗三分支 / 时间轴交错 / ASR·OCR 升级 / 升级向导 / 测试与 CI

---

## 一、验收结论

**通过**。三方面（视频 / 图集 / 文本）内置清洗 + 时间轴交错组装，5/5 单元测试全绿，零配置开箱即用；原产物与"喂 Claude 生成 AI 笔记"流程完整保留。

## 二、新增能力

| 能力 | 说明 | 验证 |
|---|---|---|
| **内置清洗**（`scripts/clean_timeline.py`） | 转写 json 保结构 + 画面逐帧 + 图集/文本通用；**零配置，无外部清洗引擎依赖** | ✅ 三分支测试 |
| **时间轴交错**（`scripts/assemble_md.py`） | 转写 + 画面按时间戳交错成半成品 md，画面与台词对位、不丢失 | ✅ `🎤`/`🖼` 结构 |
| **升级向导**（`scripts/wizard.py`） | OCR 频率 / GLM / 命名 / 课程规则 交互配置，答完即用 | ✅ 语法/导入 |
| **ASR 升级**（`transcribe_funasr.py`） | VAD 静音裁剪 / 热词注入 / 置信度 / 口语清理 / 进度条 | ✅ 语法/导入 |
| **OCR 升级**（`video_frames_ocr.py`） | 坐标排序（阅读顺序）/ 依赖预检 / 进度条 | ✅ 语法/导入 |

## 三、三分支接入

| 分支 | 原产物 | 内置清洗 | 转 md | 测试 |
|---|---|---|---|---|
| 🎬 视频 | 转写 json + 画面 txt | ✅ | 时间轴交错 | ✅ `test_clean.py` 3 用例 |
| 🖼️ 图集 | OCR txt | ✅ | 简单 md | ✅ 1 用例 |
| 📄 文本 | txt | ✅ | 简单 md | ✅ 1 用例 |

## 四、不破坏原流程（关键约束）

- 原产物（json/txt）在清洗后**完整保留**，清洗只额外产出 `*_clean.*`。
- 老"喂 Claude 生成 AI 笔记"流程**不变**：提示照旧，半成品 md 为更优输入。
- 下载 / 检测 / 归位（阶段1）逻辑未动。

## 五、测试与质量

- **5/5 单元测试通过**（`python -m unittest tests/test_clean.py`，报告 `docs/test-report-v0.3.0.md`）。
- 测试样例为模拟数据（`tests/sample/`），不侵权、可复现。
- CI（`.github/workflows/ci.yml`）新增测试步骤，push/PR 自动跑。
- 测试驱动修复 2 个实现 bug：中文重复段不去重（去重顺序修正）、标点规则缺 `,.`/`.,`（补规则）。

## 六、安全与规范

- API Key 走环境变量（`.env.example`），无硬编码绝对路径。
- 纠错词典走 `config/*.example.json` 示例，运行时复制（既有规范，未变）。
- 文档：README / CHANGELOG（中英）已更新；CLAUDE.template / SKILL / ROADMAP 同步。

## 七、遗留（下一步候选）

- 图集 GLM 分支、wizard 向导交互、detect 阶段下载/归位的自动化测试（当前为手动验证）。
- 画面信息结构化提取（表格/公式/代码）——见 `ROADMAP.md`。
