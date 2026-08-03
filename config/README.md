# config/ — 配置文件示例

本目录放的是**示例配置**，运行时需按需复制到 `scripts/` 目录（脚本从自身所在目录加载）。

| 文件 | 作用 | 使用 |
|---|---|---|
| `corrections.example.json` | ASR 语音转写纠错词典（如把 "get up" 纠正为 "github"） | 复制为 `scripts/corrections.json`，转写管线**自动套用** |
| `ocr_corrections.example.json` | OCR 画面文字识别纠错词典 | 复制为 `scripts/ocr_corrections.json`，作为生成笔记时的**参考词典**（OCR 误识由生成方结合上下文纠正，非脚本自动化套用） |

```powershell
# 复制示例配置到脚本目录
copy config\corrections.example.json   scripts\corrections.json
copy config\ocr_corrections.example.json scripts\ocr_corrections.json
```

**环境变量**见仓库根 `.env.example`：`DD_BASE` / `DD_DL_PY` / `DD_DL_SRC` / `DD_ASR_PY` / `DD_OCR_PY` / `DD_YTDLP` / `GLM_API_KEY`。`.env` 需 `pip install python-dotenv`（已在 requirements.txt）才会被自动加载。
