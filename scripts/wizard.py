#!/usr/bin/env python3
"""转写配置向导（交互式，产品经理风格）—— 每个问题讲清"干嘛的/选错会怎样/默认是啥"。

设计原则：
- 开箱即用：纯问答，每项有默认值，直接回车就用默认的
- 记忆设置：批量模式第一遍问，后面沿用（可中途改）
- 自动检测：字幕/降噪不弹问题，自动探测后确认

用法:
  from wizard import run_wizard, load_config, save_config, DEFAULT_CONFIG

返回配置 dict:
{
  "mode": "single|serial|parallel",   # 精读=单次 / 快速=串行或并行
  "interval": 1.0,                     # 抽帧间隔(秒)
  "smart_frame": True,                 # 固定+智能结合(默认) / False=纯固定
  "glm": "yes|no",                     # 画面理解
  "speaker": "single|multi",           # 说话人
  "note_style": "new|old",             # 笔记结构（默认 new）
  "precheck": True,
}
"""
import os
import sys

# Windows 控制台 UTF-8 输出（防 gbk 编码崩溃，尤其是 emoji/中文混合）
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import re

# 配置文件位置（本地，不进 git）
CONFIG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".config")
CONFIG_FILE = os.path.join(CONFIG_DIR, "wizard.json")
ENV_FILE = os.path.join(CONFIG_DIR, ".env")

DEFAULT_CONFIG = {
    "mode": "single",
    "interval": 1.0,
    "smart_frame": True,
    "glm": "yes",
    "speaker": "single",
    "note_style": "new",
    "precheck": True,
    # 存储配置（v0.5.0 新增）
    "notes_root": "",          # 根目录：空=自动推导(M.AIStudy)；自定义填路径
    "cleanup": "keep",         # 中间产物: keep保留 / slim清wav / clean全清理
    "cache_place": "default",  # 缓存位置: default=_转写缓存 / with_notes=跟笔记 / custom=自定义
    "naming": "default",       # 命名: default=NN_XX_X_小节 / simple=只小节名 / custom=自定义前缀
    "naming_prefix": "",       # 自定义命名前缀（naming=custom 时生效）
    # 课程名规则（v0.6.5 新增）
    "course_rule": "auto",     # 课程名(笔记最外层文件夹): auto自动识别 / fixed固定 / folder源文件名
    "course_fixed": "",        # course_rule=fixed 时的固定课程名
}


def load_config() -> dict:
    """读取已保存的向导配置（无则返回默认）。"""
    if not os.path.exists(CONFIG_FILE):
        return dict(DEFAULT_CONFIG)
    try:
        import json
        with open(CONFIG_FILE, encoding="utf-8") as f:
            d = json.load(f)
        cfg = dict(DEFAULT_CONFIG)
        cfg.update(d)
        return cfg
    except Exception:
        return dict(DEFAULT_CONFIG)


def save_config(cfg: dict) -> None:
    """保存向导配置到本地（供批量模式沿用 / 下次默认）。"""
    try:
        import json
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def _ask(question: str, options: dict, default_key: str) -> str:
    """产品经理风格提问。options: {key: (label, desc)}，default_key 为默认。
    用户输入 key（不区分大小写）或回车（用默认）。"""
    print(f"\n{question}")
    for k, (label, desc) in options.items():
        mark = "（默认）" if k == default_key else ""
        print(f"  {k}. {label} {mark} —— {desc}")
    while True:
        ans = input(f"请输入 [{default_key}]: ").strip().upper()  # 统一大写匹配（options key 均为大写）
        if not ans:
            return default_key
        if ans in options:
            return ans
        print(f"  [X] 请输入 {list(options.keys())} 中的一个（或直接回车用默认）")


def _ask_glm_config() -> None:
    """GLM 视觉理解 API 配置引导（多供应商预置，Key 打码存 .env）。"""
    print("\n【画面理解设置】—— 让 AI 看懂图，需要连接一个视觉 AI")
    # 已配置 → 显示详情 + 三选（用当前/换供应商/只换模型）
    if _glm_configured():
        cur = _glm_current()
        print("  当前配置：")
        print(f"    ▸ 供应商：{cur.get('provider', '未知')}")
        print(f"    ▸ 模型：{cur.get('model', '未知')}")
        print(f"    ▸ 接口：{cur.get('url', '未知')}")
        action = _ask(
            "  接下来怎么做？",
            {
                "A": ("用当前配置", "直接用现有供应商/模型，推荐"),
                "B": ("换供应商/模型", "重新配置地址+Key+模型"),
                "C": ("只换模型", "供应商/地址/Key 不变，只改模型名"),
            },
            default_key="A")
        if action == "A":
            print("  [OK] 使用当前配置")
            return
        if action == "C":
            _ask_only_model()
            return
        # action == "B" → 走完整重新配置
    _ask_full_config()


def _glm_current() -> dict:
    """读取当前 GLM 配置详情（provider/model/url），用于显示。"""
    info = {"provider": "智谱 GLM", "model": "glm-4.6v-flashx",
            "url": "https://open.bigmodel.cn/api/paas/v4/chat/completions"}
    try:
        if os.path.exists(ENV_FILE):
            with open(ENV_FILE, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("GLM_API_URL="):
                        info["url"] = line.split("=", 1)[1]
                    elif line.startswith("GLM_MODEL="):
                        info["model"] = line.split("=", 1)[1]
        # 从 URL 推断供应商名
        url = info["url"]
        if "bigmodel" in url:
            info["provider"] = "智谱 GLM"
        elif "dashscope" in url:
            info["provider"] = "阿里通义千问"
        elif "openai" in url:
            info["provider"] = "OpenAI"
        elif "baidu" in url or "qianfan" in url:
            info["provider"] = "百度文心"
    except OSError:
        pass
    return info


def _ask_full_config() -> None:
    """完整配置（换供应商/模型）：预置地址 + 自定义 + Key + 模型名 + 测试连接。"""
    print("  ① 供应商（默认：智谱 GLM，中文最好；也可选其他）")
    providers = {
        "glm": ("智谱 GLM", "https://open.bigmodel.cn/api/paas/v4/chat/completions", "glm-4.6v-flashx"),
        "qwen": ("阿里通义千问", "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions", "qwen-vl-max"),
        "openai": ("OpenAI", "https://api.openai.com/v1/chat/completions", "gpt-4o-mini"),
        "baidu": ("百度文心", "https://qianfan.baidubce.com/v2/chat/completions", "ernie-4.5-vl-8b"),
    }
    print("     默认：智谱 GLM（地址已预填）；也可选 qwen/openai/baidu 或自定义")
    provider_input = input("  供应商[glm/qwen/openai/baidu，回车=智谱，或填自定义地址]: ").strip().lower()
    if "http" in provider_input:
        # 用户直接填了自定义地址
        api_url = provider_input
        default_model = "glm-4.6v-flashx"
        provider_name = "自定义"
    elif provider_input in providers:
        provider_name, api_url, default_model = providers[provider_input]
    else:
        provider_name, api_url, default_model = providers["glm"]
    print(f"  接口地址：{api_url}")
    api_key = input(f"  ② API Key（粘贴密钥，输入时打码不显示明文）: ").strip()
    if not api_key:
        print("  [X] 未输入 API Key，画面理解将无法使用")
        return
    model = input(f"  ③ 模型名（回车用默认 {default_model}）: ").strip() or default_model
    print(f"  ④ 测试连接（模型: {model}）...")
    # 测试失败 → 循环重试（可重新填 Key/模型，或退出用默认）
    while True:
        result = _test_glm(api_url, api_key, model)
        if result == "ok":
            _save_glm(provider_name, api_url, api_key, model)
            print("  [OK] 连接成功，配置已保存（.env，之后不再问）")
            return
        # 分类提示
        if result == "key":
            print(f"  [X] API Key 无效（服务器拒绝 401/403），请检查密钥是否正确")
        elif result == "model":
            print(f"  [X] 模型名可能有误（{model}）——服务器返回 400/404，请确认该模型名存在")
        else:
            print(f"  [X] 网络连接失败，请检查网络或接口地址")
        retry = input("  重新填 Key/模型(A) 还是 退出(B)? [A]: ").strip().upper() or "A"
        if retry == "B":
            print("  已取消画面理解配置")
            return
        # 重填 Key 和模型
        api_key = input("  重填 API Key（回车保留原值）: ").strip() or api_key
        model = input(f"  重填模型名（回车保留 {model}）: ").strip() or model
        print(f"  再测试（模型: {model}）...")


def _ask_only_model() -> None:
    """只换模型：保留供应商/地址/Key，填新模型名 + 测试成功才保存。"""
    cur = _glm_current()
    print(f"  当前供应商：{cur['provider']}（地址/Key 不变）")
    model = input(f"  新模型名（当前: {cur['model']}，直接填新名）: ").strip()
    if not model:
        print("  [X] 未输入模型名，取消")
        return
    # 测试失败 → 循环重试（重填模型名，或退出）
    while True:
        print(f"  测试连接（模型: {model}）...")
        result = _test_glm(cur["url"], _glm_key(), model)
        if result == "ok":
            _save_glm(cur["provider"], cur["url"], _glm_key(), model)
            print("  [OK] 连接成功，模型已更新（.env）")
            return
        # 分类提示：只换模型时 Key 已配置，重点提示模型名
        if result == "key":
            print(f"  [X] 检测到 API Key 无效（401/403）——当前已配置的 Key 可能过期，需在'换供应商'里重填 Key")
        elif result == "model":
            print(f"  [X] 模型名可能有误（{model}）——服务器返回 400/404，请确认该模型名存在")
        else:
            print(f"  [X] 网络连接失败，请检查网络或接口地址")
        retry = input("  重填模型名(A) 还是 退出(B)? [A]: ").strip().upper() or "A"
        if retry == "B":
            print("  已取消，模型未更改")
            return
        model = input("  重填模型名: ").strip()
        if not model:
            print("  [X] 未输入模型名，取消")
            return


def _glm_key() -> str:
    """读取 GLM API Key。"""
    if os.path.exists(ENV_FILE):
        try:
            with open(ENV_FILE, encoding="utf-8") as f:
                for line in f:
                    if line.startswith("GLM_API_KEY="):
                        return line.split("=", 1)[1].strip()
        except OSError:
            pass
    return os.environ.get("GLM_API_KEY", "")


def _save_glm(provider: str, api_url: str, api_key: str, model: str) -> None:
    """保存 GLM 配置到 .env。"""
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(ENV_FILE, "w", encoding="utf-8") as f:
            f.write(f"GLM_API_KEY={api_key}\n")
            f.write(f"GLM_API_URL={api_url}\n")
            f.write(f"GLM_MODEL={model}\n")
            f.write(f"GLM_PROVIDER={provider}\n")
    except OSError:
        pass


def _glm_configured() -> bool:
    """检查是否已配置 GLM（.env 存在且含 Key）。"""
    if os.path.exists(ENV_FILE):
        try:
            with open(ENV_FILE, encoding="utf-8") as f:
                return "GLM_API_KEY=" in f.read()
        except OSError:
            return False
    return bool(os.environ.get("GLM_API_KEY"))


def _validate_root(root: str) -> bool:
    """校验存储根目录：存在且可写，或可创建。"""
    if not root:
        return False
    try:
        if os.path.exists(root):
            return os.access(root, os.W_OK) or os.access(os.path.dirname(root), os.W_OK)
        # 不存在 → 检查父级可创建
        parent = os.path.dirname(root.rstrip("\\/")) or root
        return os.path.exists(parent) and os.access(parent, os.W_OK)
    except Exception:
        return False


def _default_root() -> str:
    """自动推导的默认根目录（= M.AIStudy，跟随脚本位置，与主脚本一致）。
    wizard.py 位于 _video_tools/scripts/，向上 3 级即 M.AIStudy。"""
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _preview_storage(root: str) -> None:
    """显示存储根目录下的完整结构预览（笔记+缓存两层），含具体绝对路径。"""
    nb = os.path.join(root, "NoteBooks")
    cache = os.path.join(root, "_转写缓存")
    print(f"\n  存储根目录：{root}")
    print("  将自动创建以下结构：")
    print(f"    ▸ 笔记目录：  {nb}\\课程\\第XX讲_标题\\NN_XX_X_小节.md")
    print(f"    ▸ 视频副本：  {nb}\\课程\\第XX讲_标题\\源数据_小节\\视频.mp4")
    print(f"    ▸ 中间产物：  {cache}\\课程\\第XX讲\\源数据_小节\\wav+json+srt+visual")
    print()


def _ask_storage_root(cfg: dict) -> None:
    """问题5：存储根目录。默认/自定义都显示具体路径预览 → 确认；N 打回重选。"""
    while True:
        dr = _default_root()
        root_choice = _ask(
            "【问题5】笔记和中间产物存哪里？选\"默认\"就用当前项目目录"
            "（自动建 NoteBooks/_转写缓存）；选\"自定义\"只需填最外层地址，内层自动建。",
            {
                "A": ("用默认目录（推荐）",
                      f"例子：笔记存 {os.path.join(dr, 'NoteBooks')}，中间文件存 {os.path.join(dr, '_转写缓存')}"),
                "B": ("自定义目录",
                      "例子：填 D:\\我的学习 → 自动建 D:\\我的学习\\NoteBooks\\ + D:\\我的学习\\_转写缓存\\"),
            },
            default_key="A")
        if root_choice == "A":
            # 默认也要显示具体地址，让用户亲眼确认默认位置在哪
            _preview_storage(_default_root())
            confirm = input("  确认用这个默认位置？(Y/N，或直接回车=确认): ").strip().upper()
            if confirm == "" or confirm == "Y":
                cfg["notes_root"] = ""
                return
            print("  已取消默认位置，请重新选择（默认/自定义）")
            continue
        # B 自定义：填路径 → 校验 → 预览 → 确认（N 回到重填）
        while True:
            custom_root = input("  请输入存储根目录（如 D:\\我的学习）: ").strip()
            if not custom_root:
                print("  [X] 未输入路径，回到选择")
                break
            # 校验路径合法性（存在或可创建）
            if not _validate_root(custom_root):
                print(f"  [X] 目录不可写/不可创建: {custom_root}")
                ok = input("  重新填(A) 还是 回到选择(B)? [A]: ").strip().upper() or "A"
                if ok == "B":
                    break
                continue
            # 立即显示完整结构预览（视觉感，含具体路径）
            _preview_storage(custom_root)
            confirm = input("  确认使用此目录？(Y/N，或直接回车=确认): ").strip().upper()
            if confirm == "" or confirm == "Y":
                cfg["notes_root"] = custom_root
                return
            # N → 回到重填（不丢已填，可重输）
            print("  已取消该路径，请重新输入（或直接回车用默认）")


def _preview_naming(root: str, naming: str, prefix: str = "", course_txt: str = "课程名") -> None:
    """问题7：显示选定命名规则下的完整最终路径（笔记文件示例）。"""
    nb = os.path.join(root, "NoteBooks")
    if naming == "simple":
        fname = "小节名.md"
    elif naming == "custom":
        fname = f"{prefix}_小节名.md" if prefix else "小节名.md"
    else:
        fname = "NN_XX_X_小节名.md"
    rule_txt = {"default": "默认规则", "simple": "只留小节名",
                "custom": f"自定义前缀「{prefix}」"}[naming]
    print(f"\n  命名规则：{rule_txt}")
    print(f"  笔记将生成在（根目录: {root}）：")
    print(f"    ▸ 笔记文件：  {nb}\\{course_txt}\\第XX讲_标题\\{fname}")
    print()


def _ask_course_rule(cfg: dict) -> None:
    """问题6：课程名（笔记最外层文件夹）怎么定。存配置，之后所有视频沿用。"""
    root = cfg.get("notes_root") or _default_root()
    nb = os.path.join(root, "NoteBooks")
    while True:
        rule_choice = _ask(
            "【问题6】课程名（笔记最外层文件夹）怎么定？"
            "课程名 = 笔记最外面那层文件夹，以后笔记全部放它下面。"
            "以前是电脑自己猜，现在你定规则，之后所有视频都按这个归类。",
            {
                "A": ("自动识别（推荐）",
                      f"例子：视频在「斯坦福NLP」文件夹 → 课程名自动=01-斯坦福NLP → "
                      f"笔记存 {nb}\\01-斯坦福NLP\\第01讲_标题\\；认不出 → 用视频所在文件夹名"),
                "B": ("固定课程名",
                      f"例子：输「我的英语课」→ 全部笔记都进 {nb}\\我的英语课\\第01讲_标题\\"),
                "C": ("源文件名",
                      f"例子：视频放在「历史课」文件夹 → 课程名=历史课 → "
                      f"笔记存 {nb}\\历史课\\第01讲_标题\\"),
            },
            default_key="A")
        if rule_choice == "A":
            cfg["course_rule"] = "auto"
            cfg.pop("course_fixed", None)
            print(f"\n  课程名规则：自动识别（从路径/文件名推断，识别不到用所在文件夹名）")
            print(f"    ▸ 笔记目录：  {nb}\\（自动识别结果）\\第XX讲_标题\\NN_XX_X_小节.md")
            confirm = input("  确认这个课程名规则？(Y/N，或直接回车=确认): ").strip().upper()
            if confirm == "" or confirm == "Y":
                return
            print("  已取消，请重新选择课程名规则")
        elif rule_choice == "B":
            fixed = input("  输入固定课程名（所有视频都归到这一课，如：我的英语课）: ").strip()
            if not fixed:
                print("  [X] 未输入课程名，请重新选择")
                continue
            cfg["course_rule"] = "fixed"
            cfg["course_fixed"] = fixed
            print(f"\n  课程名规则：固定课程名「{fixed}」")
            print(f"    ▸ 笔记目录：  {nb}\\{fixed}\\第XX讲_标题\\NN_XX_X_小节.md")
            confirm = input("  确认这个课程名和路径？(Y/N，或直接回车=确认): ").strip().upper()
            if confirm == "" or confirm == "Y":
                return
            print("  已取消，请重新选择课程名规则")
        else:
            cfg["course_rule"] = "folder"
            cfg.pop("course_fixed", None)
            print(f"\n  课程名规则：源文件名（用视频所在文件夹名）")
            print(f"    ▸ 笔记目录：  {nb}\\（视频所在文件夹名）\\第XX讲_标题\\NN_XX_X_小节.md")
            confirm = input("  确认这个课程名规则？(Y/N，或直接回车=确认): ").strip().upper()
            if confirm == "" or confirm == "Y":
                return
            print("  已取消，请重新选择课程名规则")


def _ask_naming(cfg: dict) -> None:
    """问题7：笔记命名。选定后显示完整最终路径 → 确认；N 打回重选。"""
    root = cfg.get("notes_root") or _default_root()
    nb = os.path.join(root, "NoteBooks")
    # 课程名展示（跟随问题6课程名规则）
    cr = cfg.get("course_rule", "auto")
    if cr == "fixed":
        course_txt = cfg.get("course_fixed", "固定课程名")
    elif cr == "folder":
        course_txt = "视频所在文件夹名"
    else:
        course_txt = "课程名（自动识别）"
    while True:
        name_choice = _ask(
            "【问题7】笔记文件用什么命名规则？",
            {
                "A": ("默认规则（推荐）",
                      f"例子：{nb}\\{course_txt}\\第01讲_标题\\01_3-1_定义.md（带序号排序）"),
                "B": ("只留小节名",
                      f"例子：{nb}\\{course_txt}\\第01讲_标题\\定义.md（不带序号）"),
                "C": ("自定义前缀",
                      f"例子：输前缀「基础」→ {nb}\\{course_txt}\\第01讲_标题\\基础_定义.md"),
            },
            default_key="A")
        if name_choice == "C":
            prefix = input("  输入自定义前缀（生成 前缀_小节名.md）: ").strip()
            if not prefix:
                print("  [X] 未输入前缀，无法生成 前缀_小节名.md，请重新选择")
                continue
            cfg["naming"] = "custom"
            cfg["naming_prefix"] = prefix
        else:
            cfg["naming"] = "default" if name_choice == "A" else "simple"
            cfg.pop("naming_prefix", None)
        # 显示完整最终路径并确认（N → 打回重新选命名）
        _preview_naming(root, cfg["naming"], cfg.get("naming_prefix", ""), course_txt)
        confirm = input("  确认这个命名和最终路径？(Y/N，或直接回车=确认): ").strip().upper()
        if confirm == "" or confirm == "Y":
            return
        print("  已取消，请重新选择命名规则")


def _test_glm(api_url: str, api_key: str, model: str = "glm-4.6v-flashx") -> str:
    """发一张 1x1 透明 PNG 测试 GLM 连接。model 参数指定模型名。
    返回错误码：'ok' 成功 / 'key' Key无效(401/403) / 'model' 模型名错(400/404) / 'network' 网络错误。
    """
    import base64
    import json
    import urllib.error
    import urllib.request
    # 1x1 透明 PNG（最小可用）
    png_b64 = ("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8"
               "/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg==")
    body = {
        "model": model,
        "messages": [{"role": "user", "content": [
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{png_b64}"}},
            {"type": "text", "text": "测试，请回复 OK"},
        ]}],
    }
    req = urllib.request.Request(
        api_url, data=json.dumps(body).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return "ok" if resp.status == 200 else "network"
    except urllib.error.HTTPError as e:
        # 401/403 → Key 无效；400/404 → 模型名错（含 1301 内容过滤）
        if e.code in (401, 403):
            return "key"
        if e.code in (400, 404):
            return "model"
        return "network"
    except Exception:
        return "network"


def run_wizard(first: bool = True, mode_override: str = None, media_type: str = "video") -> dict:
    """运行配置向导。first=True 显示完整向导；批量模式后续沿用。
    mode_override：批量模式下已由外层指定 mode（serial/parallel），跳过问题1。
    media_type ∈ {video, image, audio}：按类型只问相关项（视频全问；图集跳抽帧/说话人；
    音频跳抽帧/GLM画面/课程）。
    """
    cfg = load_config()
    print("\n" + "=" * 50)
    print("【转写开始前的设置向导】")
    print("开始前，我们先花一分钟确认几个设置。每项都有默认值，")
    print("直接按回车就用默认的，不用每个都改。")
    print("=" * 50)

    # 问题1：这次怎么转？（最先问）
    if mode_override:
        cfg["mode"] = mode_override
        print(f"\n批量模式：{cfg['mode']}（设置将沿用）")
    else:
        mode = _ask(
            "【问题1】这次怎么转？",
            {
                "A": ("精读（推荐）", "例子：1个视频专心转，质量最好"),
                "B": ("快速/批量", "例子：一次转 5 个视频，快但稍粗"),
            },
            default_key="A")
        cfg["mode"] = "single" if mode == "A" else "serial"
        if mode == "B":
            sub = _ask(
                "  批量模式：同时转几个视频？",
                {
                    "A": ("连续串行", "例子：第1个转完再转第2个，稳"),
                    "B": ("连续并行", "例子：5个一起转，最快但占资源"),
                },
                default_key="A")
            cfg["mode"] = "serial" if sub == "A" else "parallel"

    # 问题2：视频画面怎么截图？（固定+智能结合）—— 仅视频
    if media_type == "video":
        interval_choice = _ask(
            "【问题2】视频画面怎么截图？为了看懂幻灯片和公式要截图，越密越细但越慢。",
            {
                "A": ("每 1 秒截 1 张（最细）", "例子：1小时课≈3600张图，代码/公式多也不漏"),
                "B": ("每 2 秒截 1 张", "例子：1小时课≈1800张图，普通课够用"),
                "C": ("每 5 秒截 1 张", "例子：1小时课≈720张图，画面基本不动最快"),
            },
            default_key="A")
        cfg["interval"] = {"A": 1.0, "B": 2.0, "C": 5.0}[interval_choice]

        smart = _ask(
            "  要不要【智能省帧】？画面没变化就不重复截（翻页之间不狂截），省时间。",
            {
                "A": ("开启（推荐）", "例子：同一页PPT停10秒→只截1张，不白截9张"),
                "B": ("不开启", "例子：固定频率每张都截，最稳但慢"),
            },
            default_key="A")
        cfg["smart_frame"] = (smart == "A")

    # 问题3：让 AI 看懂画面（GLM 关键帧）—— 视频/图集（文案按类型）
    if media_type in ("video", "image"):
        glm_question = (
            "【问题3】要不要让 AI【看懂】每张图？OCR 能读出图上文字，看懂是理解图的内容"
            "（如'这是编辑距离的表格'）。花一点云端费用（每次几厘钱）。"
            if media_type == "image"
            else "【问题3】要不要让 AI【看懂】画面？截图只能读出文字；看懂是理解图的意思"
                 "（如'这是编辑距离的表格'）。花一点云端费用（每次几厘钱）。"
        )
        glm_choice = _ask(glm_question,
            {
                "A": ("开启（推荐）", "例子：截图里的表格，AI能解释'这是算编辑距离的'，笔记更深入"),
                "B": ("关闭", "例子：只记录截图上的文字，不解释图，省钱但笔记浅一些"),
            },
            default_key="A")
        cfg["glm"] = "yes" if glm_choice == "A" else "no"
        if cfg["glm"] == "yes":
            _ask_glm_config()

    # 问题4：几个人说话 —— 视频/音频（文案按类型）
    if media_type in ("video", "audio"):
        spk = _ask(
            "【问题4】音频里几个人在说话？" if media_type == "audio"
            else "【问题4】视频里几个人在说话？",
            {
                "A": ("就一个人讲", "例子：老师自己讲课，不标谁说的，转写快"),
                "B": ("多人讨论/访谈", "例子：访谈节目，标'讲师A 说…讲师B 说…'"),
            },
            default_key="A")
        cfg["speaker"] = "single" if spk == "A" else "multi"

    # 问题5：存储根目录（默认/自定义都显示具体路径预览 → 确认；N 打回重选）
    _ask_storage_root(cfg)

    # 问题6：课程名（笔记最外层文件夹）—— 仅视频（图集/音频用默认，不强制课程）
    if media_type == "video":
        _ask_course_rule(cfg)

    # 问题7：笔记文件怎么命名（选定 → 显示完整最终路径 → 确认；N 打回重选）
    _ask_naming(cfg)

    # 问题8：中间产物怎么处理
    clean_choice = _ask(
        "【问题8】转写过程会生成一堆中间文件（音频、转写文字、字幕、画面文字），"
        "转写完后这些怎么处理？",
        {
            "A": ("保留（推荐）", "例子：音频+文字+字幕全留着，方便改笔记/复查，占空间"),
            "B": ("精简（只删音频）", "例子：只删最大的音频文件，省空间但仍能改笔记"),
            "C": ("全部清理", "例子：笔记完成后全删，最省空间，以后不能改笔记"),
        },
        default_key="A")
    cfg["cleanup"] = {"A": "keep", "B": "slim", "C": "clean"}[clean_choice]

    # 问题9：中间产物放哪里
    _root9 = cfg.get("notes_root") or _default_root()
    cache_choice = _ask(
        "【问题9】上面这些中间文件（音频/文字/字幕）放哪里？",
        {
            "A": ("独立缓存目录（推荐）",
                  f"例子：放 {os.path.join(_root9, '_转写缓存')}\\课程\\第XX讲\\，和笔记分开，清爽"),
            "B": ("跟笔记放一起",
                  f"例子：放进 {os.path.join(_root9, 'NoteBooks')}\\课程\\第XX讲_标题\\源数据_小节\\，视频和产物同处"),
        },
        default_key="A")
    cfg["cache_place"] = "default" if cache_choice == "A" else "with_notes"

    # 笔记结构：默认新结构（不问，超集）
    cfg["note_style"] = "new"

    save_config(cfg)
    _print_summary(cfg, media_type)
    return cfg


def _print_summary(cfg: dict, media_type: str = "video") -> None:
    """向导收尾确认清单（按类型显示相关项）。"""
    mode_txt = {"single": "精读", "serial": "连续串行", "parallel": "连续并行"}[cfg["mode"]]
    naming_txt = {"default": "默认规则", "simple": "只留小节名",
                  "custom": f"前缀「{cfg.get('naming_prefix', '')}」"}[cfg.get("naming", "default")]
    print("\n[OK] 设置确认完毕，开始转写！")
    print(f"   • 模式：{mode_txt} · 新结构笔记")
    if media_type == "video":
        frame_txt = f"每 {cfg['interval']:g} 秒 1 张" + (" + 智能省帧" if cfg["smart_frame"] else "")
        glm_txt = "开（GLM 关键帧）" if cfg["glm"] == "yes" else "关"
        spk_txt = "单讲师" if cfg["speaker"] == "single" else "多人"
        cr = cfg.get("course_rule", "auto")
        course_txt = (f"固定「{cfg.get('course_fixed', '')}」" if cr == "fixed"
                      else "源文件夹名" if cr == "folder" else "自动识别")
        print(f"   • 画面：{frame_txt}")
        print(f"   • 看懂画面：{glm_txt}")
        print(f"   • 说话人：{spk_txt}")
        print(f"   • 字幕/降噪：自动检测")
        print(f"   • 课程名：{course_txt} · 命名：{naming_txt}")
    elif media_type == "image":
        glm_txt = "开（GLM 逐张看懂）" if cfg["glm"] == "yes" else "关"
        print(f"   • 看懂每张图：{glm_txt}")
        print(f"   • 命名：{naming_txt}")
    elif media_type == "audio":
        spk_txt = "单说话人" if cfg["speaker"] == "single" else "多人"
        print(f"   • 说话人：{spk_txt}")
        print(f"   • 命名：{naming_txt}")
    input("\n按回车开始...")


def ask_course_classification(video: str, notes_root: str = "") -> str:
    """课程归类：detect_parts 识别不到课程信息时，让用户选课程名。
    4 选项（A 父目录 / B 自定义 / C 系统推荐 / D 默认未分类）+ 显示完整路径预览 + 确认。
    返回课程名。
    """
    parent = os.path.basename(os.path.dirname(os.path.abspath(video)))
    parent = parent or "未分类课程"
    fn = os.path.splitext(os.path.basename(video))[0]
    # 系统推荐：从文件名推断（去掉序号/后缀，取核心词）
    rec = re.sub(r"^\d+\s*-\s*\d+\s*-\s*", "", fn)
    rec = re.split(r"-\s*(?:Stanford|YouTube|NLP|Professor|Dan|Chris)", rec)[0].strip() or parent

    print("\n【课程归类】视频路径没识别出课程/讲次信息，请选择课程名称：")
    choice = _ask(
        "  课程名用哪个？",
        {
            "A": (f"用视频所在文件夹名", f"将显示为: {parent}"),
            "B": ("自定义", "你输入课程名（如'我的英语课'）"),
            "C": (f"系统推荐", f"推荐: {rec}（从文件名推断，可确认）"),
            "D": ("用默认", "未分类课程"),
        },
        default_key="A")
    if choice == "A":
        course = parent
    elif choice == "B":
        course = input("  输入课程名: ").strip() or "未分类课程"
    elif choice == "C":
        course = rec
    else:
        course = "未分类课程"

    # 显示完整路径预览并确认（Y继续 / N重来）
    root = notes_root or ""
    nb = os.path.join(root, "NoteBooks") if root else os.path.join("NoteBooks")
    cache = os.path.join(root, "_转写缓存") if root else os.path.join("_转写缓存")
    while True:
        print(f"\n  将按以下结构归类（课程名: {course}）：")
        print(f"    ▸ 笔记目录：  {nb}\\{course}\\第XX讲_标题\\NN_XX_X_小节.md")
        print(f"    ▸ 视频副本：  {nb}\\{course}\\第XX讲_标题\\源数据_小节\\视频.mp4")
        print(f"    ▸ 中间产物：  {cache}\\{course}\\第XX讲\\源数据_小节\\wav+json+srt+visual")
        confirm = input("\n  确认这个课程名和路径？(Y/N): ").strip().upper() or "Y"
        if confirm == "Y":
            return course
        # N → 重新选课程名
        choice = _ask(
            "  重新选课程名？",
            {
                "A": ("用视频所在文件夹名", f"将显示为: {parent}"),
                "B": ("自定义", "你输入课程名"),
                "C": ("系统推荐", f"推荐: {rec}"),
                "D": ("用默认", "未分类课程"),
            },
            default_key="A")
        if choice == "A":
            course = parent
        elif choice == "B":
            course = input("  输入课程名: ").strip() or "未分类课程"
        elif choice == "C":
            course = rec
        else:
            course = "未分类课程"


if __name__ == "__main__":
    import json
    cfg = run_wizard()
    print(json.dumps(cfg, ensure_ascii=False, indent=2))
