# 测试报告 · v0.3.0 内置清洗三分支

> 日期：2026-08-19
> 范围：`scripts/clean_timeline.py`（内置零配置清洗）+ `scripts/assemble_md.py`（时间轴交错）
> 运行：`python -m unittest tests/test_clean.py -v`
> 样例数据：`tests/sample/`（模拟数据，可复现、不侵权，输出写临时目录不污染样例）

---

## 一、结论

**5/5 测试通过（OK）**。视频 / 图集 / 文本三分支的内置清洗全部可用，无外部清洗引擎依赖，零配置开箱即用。

## 二、测试用例明细

| 分支 | 用例 | 验证点 | 结果 |
|---|---|---|---|
| 🎬 视频 | `test_transcript_kept_structure_and_punct` | 转写 json 保结构清洗：段数 6→5（去重 1 段同文本同时间戳）、标点乱码规范化（`,,`→`,`、`,.`→`.`）、中文教学段保留、时间戳字段保留 | ✅ |
| 🎬 视频 | `test_visual_timestamps_and_watermark` | 画面 txt 切帧清洗：时间戳保留、帧标记/OCR 标签/GLM 标签/界面水印删除、GLM 描述保留 | ✅ |
| 🎬 视频 | `test_interleave_has_speech_and_visual` | 时间轴交错：产物同时含转写（🎤）和画面（🖼），画面不丢失 | ✅ |
| 🖼️ 图集 | `test_album_clean` | OCR txt 清洗：界面水印/按钮碎片删除、图片序号与有效内容保留 | ✅ |
| 📄 文本 | `test_text_clean` | txt 清洗：AI 生成标记/阅读/推荐类 UI 删除、正文保留 | ✅ |

## 三、测试样例（tests/sample/）

| 文件 | 用途 | 覆盖噪音 |
|---|---|---|
| `video_sample.json` | 转写保结构清洗 | 标点乱码 `,,` `,.`、重复段、中文段 |
| `video_sample_visual.txt` | 画面逐帧清洗 | 帧标记、OCR/GLM 标签、界面水印、GLM 描述 |
| `album_sample.txt` | 图集 OCR 清洗 | 界面水印、按钮碎片、图片序号 |
| `text_sample.txt` | 文本清洗 | AI 生成标记、阅读/推荐类 UI |

> 样例为模拟数据，不含真实视频/用户内容，可安全纳入开源仓库。

## 四、回归说明

- 原产物（json/txt）在清洗后**完整保留**，清洗只额外产出 `*_clean.*`。
- 老"喂 Claude 生成 AI 笔记"流程**不变**（提示照旧，半成品 md 为更优输入）。
- 本次修复 2 个实现 bug（见下），均已纳入测试断言防回归。

## 五、本次实现修复（测试驱动发现）

| Bug | 表现 | 修复 |
|---|---|---|
| 中文重复段不去重 | 同文本+同时间戳的中文段保留，数据重复 | 去重判断移到中文豁免之前：同文本+同时间戳中英文都去重，中文段仅在不同时间戳时永不删 |
| 标点规则缺 `,.`/`.,` | `PowerShell对于AI不够友好 ,.` 未规范化 | `_PUNCT_PAIRS` 补 `,\.`→`.` 与 `\.,`→`.` |

## 六、覆盖率与下一步

- 覆盖：三分支清洗核心路径 + 时间轴交错组装。
- 未覆盖（后续可补）：GLM 分支图集、wizard 向导交互、detect 阶段下载/归位。
- 运行方式建议加入 CI（`tests/` 已就绪，`.github/workflows/ci.yml` 可加 `python -m unittest discover tests`）。
