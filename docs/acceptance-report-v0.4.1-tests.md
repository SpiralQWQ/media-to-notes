# 验收报告 — media-to-notes 测试补全（v0.4.1 候选）

日期：2026-08-21 · 范围：为分层架构（core/engines/clean/assemble/cli）补全单元测试

## 一、Task 清单（S1 无重叠闭包）

| Task | 范围 | 测试文件 | 用例数 |
|---|---|---|---|
| 01 | core/base（human_size/write_text） | tests/test_base.py | 11 |
| 02 | cli._classify 四模态识别 | tests/test_classify.py | 10 |
| 03 | assemble/album + timeline | tests/test_assemble.py | 11 |
| 04 | engines/asr 纯函数 | tests/test_asr.py | 17 |
| 05 | engines/ocr 纯函数（坐标排序） | tests/test_ocr.py | 12 |
| 06 | core/video|audio|image 编排（mock 引擎） | tests/test_core.py | 10 |
| 07 | 全量合并回归 | — | 5（既有清洗） |

**合计：76 用例，全部通过（Ran 76 tests / OK）**

## 二、修复的缺陷（4 个真实 bug）

| # | 缺陷 | 根因 | 修复 |
|---|---|---|---|
| 1 | `cli._classify(None)` 崩溃 AttributeError | 缺空值防呆 | 加 `if not path: return None` |
| 2 | `timeline` 声称按时间升序但未排序 | 缺 `sort` | `sents.sort(key=start_ms)` |
| 3 | 引擎失败时 `cjson=""` → assemble 读空路径 FileNotFoundError | 编排层缺防呆 | video/audio 空源返回 error dict |
| 4 | `process_image` 的 `_glm_describe` 异常冒泡崩溃 | 外层无 try | 包 try/except 降级空串 |

## 三、穷举覆盖（S2）

- **路径穷举**：三模态「入口→引擎→clean→assemble→md」各含 正常 / 断点重启 / 引擎失败 三态；边界含 空输入/None/空白文本/超大时间/负值字节/空图集。
- **边界严格**：`human_size` 0/1/1K/1M−1/1M/1.5M/1G/负值；`fmt_ts` 0/59s/60s/61.9s/负值；空串/None 全部守住不崩。
- **终点一致性**：
  - `clean_md` 产物：三模态殊途同归——均产出 `*_clean.md` 且 `chars>0`（断点/全量/GLM开关 各路径逐项比对一致）。
  - 引擎失败：video/audio 返回带 `error` 的 dict，image 降级空 GLM 块——同终点状态一致。
  - GLM 标签：yes/no 均按清洗规范删标签、yes 额外保留描述内容——一致。

## 四、四轮审核结论

每 Task 完成均过 完成度 / 回归 / 隐蔽缺陷 / 代码质量 四轮；问题就地修复后复跑全绿，无跨模块副作用。

## 五、残留风险

- `select_key_frames`（依赖 cv2 运行时）未纳入纯函数测试，仅冒烟；建议有 opencv 环境补测。
- `core` 编排测试用 mock 引擎，未跑真实 ASR/OCR 子进程（属集成测试，需真实依赖环境）。

证据：temp/fixloop_evidence/round-036.md
