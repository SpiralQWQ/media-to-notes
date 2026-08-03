#!/usr/bin/env python3
"""GLM 视觉理解(glm-4.6v-flashx) —— 独立脚本，与路由解耦。

用法: python glm_vision.py --image <图片> --prompt "<提示词>"
依赖: 环境变量 GLM_API_KEY
"""
import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.request

try:  # 允许从仓库根 .env 加载 GLM_API_KEY（可选依赖 python-dotenv）
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

API_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
MODEL = "glm-4.6v-flashx"


def main():
    parser = argparse.ArgumentParser(description="GLM 视觉理解")
    parser.add_argument("--image", required=True, help="图片路径")
    parser.add_argument("--prompt", default="请用中文简洁描述这张图片的内容", help="提示词")
    args = parser.parse_args()

    api_key = os.environ.get("GLM_API_KEY")
    if not api_key:
        sys.exit("[ERR] 未设置 GLM_API_KEY 环境变量")

    if not os.path.exists(args.image):
        sys.exit(f"[ERR] 图片不存在: {args.image}")

    with open(args.image, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    ext = os.path.splitext(args.image)[1].lstrip(".").lower()
    if ext == "jpg":
        ext = "jpeg"
    data_url = f"data:image/{ext};base64,{b64}"

    body = {
        "model": MODEL,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": data_url}},
                {"type": "text", "text": args.prompt},
            ],
        }],
    }
    req = urllib.request.Request(
        API_URL,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            raw = resp.read().decode("utf-8")
        data = json.loads(raw)
    except urllib.error.HTTPError as e:
        sys.exit(f"[ERR] GLM API HTTP 错误 {e.code}: {e.read().decode('utf-8', errors='replace')[:500]}")
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        sys.exit(f"[ERR] GLM API 连接失败（网络/超时）: {e}")
    except json.JSONDecodeError as e:
        sys.exit(f"[ERR] GLM 返回内容不是合法 JSON: {e}")
    try:
        print(data["choices"][0]["message"]["content"])
    except (KeyError, IndexError, TypeError):
        sys.exit(f"[ERR] GLM 返回异常: {json.dumps(data, ensure_ascii=False)[:500]}")


if __name__ == "__main__":
    main()
