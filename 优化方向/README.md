# media-to-notes × MinerU 优化方向

> **文档目的**：分析 media-to-notes 如何借鉴 MinerU 的文档解析能力，提升视频/图片→笔记的质量
> **创建日期**：2026-08-07
> **核心思路**：不融合整个 MinerU，而是**抽取其专项模型**增强 media-to-notes 的特定能力

---

## 一、当前架构 vs MinerU 能力对比

### media-to-notes 当前流程
```
视频/图集
  ↓
关键帧提取（ffmpeg）
  ↓
OCR 文字提取（PaddleOCR/RapidOCR）
  ↓
（可选）GLM 视觉理解（生成语义描述）
  ↓
Claude 整合 → AI 教材
```

### MinerU 的专项能力
| 能力 | MinerU 实现 | media-to-notes 现状 |
|---|---|---|
| **表格识别** | TableMaster/LORE → HTML/Markdown 表格 | ❌ 无（表格变纯文字） |
| **公式识别** | LaTeX-OCR/UniMERNet → LaTeX | ❌ 无（公式变纯文字） |
| **版面分析** | LayoutLM/YOLO → 标题/段落/代码块 | ⚠️ 弱（只有文字 bbox） |
| **图片提取** | 自动裁切保存 + 引用 | ✅ 有（但无结构化引用） |

---

## 二、可优化的场景

### 场景 1：视频截图包含表格

**现状**：
```
输入：视频帧（展示数据表格）
PaddleOCR 输出：
  姓名 年龄 城市
  张三 25 北京
  李四 30 上海

问题：表格结构丢失，变成纯文字
```

**优化后**：
```
输入：视频帧（展示数据表格）
TableMaster 识别 → Markdown 表格：

| 姓名 | 年龄 | 城市 |
|------|------|------|
| 张三 | 25   | 北京 |
| 李四 | 30   | 上海 |

GLM 理解："这是一个学生信息表格..."
```

**实现方案**：
1. 在 `ocr_images.py` 中增加 TableMaster 调用
2. 对识别出的表格区域，用 TableMaster 提取结构
3. 输出 Markdown 表格格式

**难度**：⭐⭐⭐（中等）
- TableMaster 是独立模型，可直接调用
- 需要训练/调用表格检测器定位表格区域
- 预计开发时间：2-3 天

---

### 场景 2：视频截图包含数学公式

**现状**：
```
输入：视频帧（展示数学公式）
PaddleOCR 输出：
  E = mc^2
  ∫f(x)dx

问题：公式格式丢失，无法用于后续计算/LaTeX渲染
```

**优化后**：
```
输入：视频帧（展示数学公式）
LaTeX-OCR 识别：
  $$E = mc^2$$
  $$\int f(x) dx$$

GLM 理解："这是质能方程和积分公式..."
```

**实现方案**：
1. 增加 LaTeX-OCR 模型调用
2. 对识别出的公式区域，输出 LaTeX 格式
3. 在 Markdown 中用 `$$...$$` 包裹

**难度**：⭐⭐⭐（中等）
- UniMERNet/LaTeX-OCR 是成熟模型
- 需要公式检测器定位公式区域
- 预计开发时间：2-3 天

---

### 场景 3：视频截图包含代码块

**现状**：
```
输入：视频帧（展示 Python 代码）
PaddleOCR 输出：
  def hello():
      print("Hello")
  
  for i in range(10):
      print(i)

问题：代码结构丢失（缩进可能错乱），无法语法高亮
```

**优化后**：
```
输入：视频帧（展示 Python 代码）
代码检测 + OCR → 保留缩进和结构：

```python
def hello():
    print("Hello")

for i in range(10):
    print(i)
```

**实现方案**：
1. 增加代码块检测（基于 YOLO 或规则）
2. 对代码区域，用 PaddleOCR + 后处理保留缩进
3. 输出 Markdown 代码块格式

**难度**：⭐⭐（简单）
- PaddleOCR 已经能提取代码文字
- 只需要后处理：检测缩进、包装代码块
- 预计开发时间：1 天

---

### 场景 4：混合内容（文字+表格+公式）

**现状**：
```
输入：视频帧（包含标题、段落、表格、公式）
PaddleOCR 输出：所有文字混在一起，无法区分

问题：结构完全丢失
```

**优化后**：
```
输入：视频帧
版面分析 → 检测各区域类型
  - 标题区域 → PaddleOCR + 标题标记
  - 段落区域 → PaddleOCR
  - 表格区域 → TableMaster → Markdown 表格
  - 公式区域 → LaTeX-OCR → LaTeX
  - 代码区域 → PaddleOCR + 代码块包装

GLM 理解："这是一个教程截图，包含..."

输出：结构化 Markdown
```

**实现方案**：
1. 集成 MinerU 的版面分析模型（LayoutLM/YOLO）
2. 根据区域类型调用对应模型
3. 合并输出结构化 Markdown

**难度**：⭐⭐⭐⭐（较难）
- 需要训练/调用版面检测模型
- 需要协调多个模型的输出
- 预计开发时间：5-7 天

---

## 三、实现优先级建议

| 优先级 | 优化项 | 收益 | 开发成本 | 建议 |
|---|---|---|---|---|
| **P0** | 代码块保留结构 | ⭐⭐⭐ | ⭐⭐ | ✅ 立即做（1天） |
| **P1** | 表格识别 → Markdown | ⭐⭐⭐⭐ | ⭐⭐⭐ | ✅ 优先做（2-3天） |
| **P2** | 公式识别 → LaTeX | ⭐⭐⭐ | ⭐⭐⭐ | ⏸️ 按需做 |
| **P3** | 版面分析 + 混合内容 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⏸️ 长期规划 |

---

## 四、技术方案（以表格识别为例）

### 4.1 依赖安装

```bash
# 在新建的 OCR 虚拟环境中安装（或直接复用已有的 OCR 环境）
pip install tablemaster  # 或从 ModelScope 下载
pip install rapidocr-onnxruntime  # 已有
```

### 4.2 代码修改（`scripts/ocr_images.py`）

```python
def _ocr_with_table_detection(images):
    """增强版 OCR：检测表格并提取结构"""
    from rapidocr_onnxruntime import RapidOCR
    from tablemaster import TableMaster  # 假设有这个包
    
    ocr = RapidOCR()
    table_detector = TableMaster()
    
    out = []
    for img in images:
        # 1. 检测表格区域
        table_regions = table_detector.detect(img)
        
        if table_regions:
            # 2. 对表格区域提取结构
            markdown_tables = []
            for region in table_regions:
                table_img = crop(img, region)
                markdown_table = table_master.extract(table_img)
                markdown_tables.append(markdown_table)
            
            # 3. 对非表格区域用普通 OCR
            text_regions = get_non_table_regions(img, table_regions)
            texts = [ocr(region) for region in text_regions]
            
            # 4. 合并输出
            out.append(merge_tables_and_text(markdown_tables, texts))
        else:
            # 无表格，用普通 OCR
            result, _ = ocr(img)
            out.append("\n".join(item[1] for item in (result or [])))
    
    return out
```

### 4.3 输出格式

```markdown
## 视频截图 OCR 结果

### 文字内容
这是一个关于 Python 数据结构的教程...

### 表格内容

| 数据结构 | 时间复杂度 | 空间复杂度 |
|---------|-----------|-----------|
| 列表    | O(1)      | O(n)      |
| 字典    | O(1)      | O(n)      |

### 公式内容
$$O(n \log n)$$
```

---

## 五、不融合 MinerU 的原因

### 为什么不用整个 MinerU？

1. **MinerU 不支持单张图片输入**
   - MinerU 设计为文档解析工具，输入是 PDF/PPT
   - 视频帧是单张图片，MinerU 无法直接处理

2. **MinerU 太重**
   - 加载多个模型（LayoutLM + TableMaster + LaTeX-OCR + PaddleOCR）
   - 对单张图片不划算，启动就要 10-20 秒

3. **MinerU 不理解语义**
   - MinerU 只能还原结构，不能"理解"图片内容
   - media-to-notes 需要 GLM 视觉理解"这张图在讲什么"

### 为什么抽取专项模型？

1. **轻量**：只加载需要的模型（表格/公式/版面）
2. **灵活**：按需调用，不影响现有流程
3. **兼容**：和 PaddleOCR + GLM 无缝集成

---

## 六、实施路线图

### Phase 1：代码块优化（1天）
- [ ] 在 `ocr_images.py` 中增加代码块检测
- [ ] 保留代码缩进和结构
- [ ] 输出 Markdown 代码块格式
- [ ] 测试：Python/Java/C++ 代码截图

### Phase 2：表格识别（2-3天）
- [ ] 集成 TableMaster 模型
- [ ] 实现表格检测 + 结构提取
- [ ] 输出 Markdown 表格格式
- [ ] 测试：数据表格、对比表格、复杂表格

### Phase 3：公式识别（2-3天）
- [ ] 集成 LaTeX-OCR/UniMERNet
- [ ] 实现公式检测 + LaTeX 转换
- [ ] 输出 `$$...$$` 格式
- [ ] 测试：数学公式、化学公式

### Phase 4：版面分析（5-7天）
- [ ] 集成 LayoutLM/YOLO 版面检测
- [ ] 实现区域分类（标题/段落/表格/公式/代码）
- [ ] 协调多模型输出
- [ ] 测试：混合内容截图

---

## 七、预期效果

### 优化前（当前）
```
视频截图 → OCR 纯文字 → Claude → AI 教材
问题：表格/公式/代码结构丢失
```

### 优化后
```
视频截图 → 版面分析 → 
  ├─ 表格 → TableMaster → Markdown 表格
  ├─ 公式 → LaTeX-OCR → LaTeX
  ├─ 代码 → OCR + 后处理 → 代码块
  └─ 文字 → PaddleOCR → 段落
→ GLM 视觉理解（可选）
→ Claude 整合 → AI 教材
优势：保留完整结构，可读性大幅提升
```

---

## 八、风险评估

| 风险 | 影响 | 缓解措施 |
|---|---|---|
| 视频帧质量低（模糊/压缩） | 表格/公式识别失败 | 降级到纯 OCR |
| 模型加载慢 | 启动时间增加 | 懒加载（按需初始化） |
| 开发周期长 | 项目延期 | 分阶段实施，先做 P0/P1 |
| 依赖包冲突 | 环境不稳定 | 新建独立虚拟环境 |

---

## 九、参考资料

- **MinerU 文档**：见 [MinerU 官方文档](https://mineru.net/docs)（本地安装版手册随 MinerU 环境自带）
- **TableMaster**：https://github.com/minend/TableMaster
- **LaTeX-OCR**：https://github.com/lukas-blecher/LaTeX-OCR
- **UniMERNet**：https://github.com/opendatalab/UniMERNet
- **PaddleOCR**：https://github.com/PaddlePaddle/PaddleOCR

---

**下一步**：确认优先级，开始 Phase 1（代码块优化）。
