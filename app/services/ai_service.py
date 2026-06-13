# -*- coding: utf-8 -*-
"""
AI 标签分析服务
调用大语言模型（LLM）API 对表情包图片进行视觉分析，自动生成分类标签
"""
import base64
import json
import logging
import re
from pathlib import Path
from typing import Any

import httpx

from config import Config

logger = logging.getLogger(__name__)

# 系统提示词：指导 LLM 以结构化 JSON 格式输出标签分析结果
SYSTEM_PROMPT = """你是一个表情包分类专家。分析给定的图片并识别表情包特征。
只返回符合以下结构的有效 JSON 对象：
{
"tags": [
{"name": "tag_name", "confidence": 0.95}
]
}
包含 3-8 个标签，涵盖：表情包格式/模板名称、情绪、风格、主题以及如果可见的文字内容。
置信度必须是介于 0.0 和 1.0 之间的浮点数。"""


def _encode_image(file_path: Path) -> str:
    """将图片文件读取并编码为 Base64 字符串，供 LLM API 传输"""
    with open(file_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def _build_payload(image_base64: str, file_name: str) -> dict[str, Any]:
    """构建 LLM Chat Completions API 请求体，包含系统提示词和图片数据"""
    return {
        "model": Config.LLM_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/{_guess_mime(file_name)};base64,{image_base64}"
                        },
                    },
                    {
                        "type": "text",
                        "text": "分析这个表情包图片，并以指定的 JSON 格式提供标签。",
                    },
                ],
            },
        ],
        "max_tokens": 512,
        "temperature": 0.2,
    }


def _guess_mime(file_name: str) -> str:
    """根据文件扩展名推断 MIME 类型子类型（如 jpeg/png/gif），默认返回 jpeg"""
    suffix = Path(file_name).suffix.lower()
    mime_map = {
        ".jpg": "jpeg",
        ".jpeg": "jpeg",
        ".png": "png",
        ".gif": "gif",
        ".bmp": "bmp",
        ".webp": "webp",
        ".tiff": "tiff",
    }
    return mime_map.get(suffix, "jpeg")


def _parse_response(text: str) -> list[dict[str, Any]]:
    """从 LLM 返回的文本中提取 JSON 对象，解析出标签列表并校验格式"""
    json_match = re.search(r"\{[\s\S]*\}", text)
    if not json_match:
        logger.warning("No JSON object found in LLM response: %s", text[:200])
        return []

    try:
        data = json.loads(json_match.group(0))
    except json.JSONDecodeError:
        logger.warning("Failed to parse JSON from LLM response: %s", text[:200])
        return []

    tags = data.get("tags", [])
    result: list[dict[str, Any]] = []
    for t in tags:
        name = t.get("name", "").strip()
        if not name:
            continue
        confidence = float(t.get("confidence", 0.5))
        confidence = max(0.0, min(1.0, confidence))
        result.append({"name": name, "confidence": confidence})
    return result


def analyze_image(file_path: Path) -> list[dict[str, Any]]:
    """
    分析单张图片并返回标签列表（主入口函数）
    流程：编码图片 → 构建请求 → 调用 LLM API（最多重试3次）→ 解析标签
    """
    if not Config.LLM_API_KEY:
        raise RuntimeError("LLM_API_KEY is not configured")

    image_b64 = _encode_image(file_path)
    payload = _build_payload(image_b64, file_path.name)

    headers = {
        "Authorization": f"Bearer {Config.LLM_API_KEY}",
        "Content-Type": "application/json",
    }

    max_retries = 3
    last_error: Exception | None = None

    for attempt in range(1, max_retries + 1):
        try:
            with httpx.Client(timeout=httpx.Timeout(60.0)) as client:
                response = client.post(
                    f"{Config.LLM_API_BASE.rstrip('/')}/chat/completions",
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                tags = _parse_response(content)
                if tags:
                    return tags
                logger.warning(
                    "LLM returned empty tags on attempt %d/%d", attempt, max_retries
                )
        except httpx.TimeoutException as e:
            logger.warning("LLM API timeout on attempt %d/%d: %s", attempt, max_retries, e)
            last_error = e
        except httpx.HTTPStatusError as e:
            logger.error("LLM API HTTP error %d on attempt %d/%d: %s", e.response.status_code, attempt, max_retries, e)
            last_error = e
        except httpx.RequestError as e:
            logger.warning("LLM API request error on attempt %d/%d: %s", attempt, max_retries, e)
            last_error = e

    if last_error:
        raise last_error
    return []
