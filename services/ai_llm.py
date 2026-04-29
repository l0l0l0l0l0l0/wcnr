# -*- coding: utf-8 -*-
"""
AI 画像 —— LLM API 调用封装
支持 Anthropic (Messages API) 与 OpenAI-compatible (Chat Completions API) 两种协议，
使用项目已有的 httpx 发起请求，无需新增依赖。
"""

import json
import logging
from typing import Any

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 120.0


def _build_anthropic_payload(model: str, max_tokens: int, prompt: str) -> dict:
    return {
        "model": model,
        "max_tokens": max_tokens,
        "messages": [
            {"role": "user", "content": prompt}
        ],
    }


def _build_openai_payload(model: str, max_tokens: int, prompt: str) -> dict:
    return {
        "model": model,
        "max_tokens": max_tokens,
        "messages": [
            {"role": "system", "content": "你是一名资深公安情报分析师。"},
            {"role": "user", "content": prompt}
        ],
    }


def _parse_anthropic_response(response_json: dict) -> str:
    content = response_json.get("content", [])
    if content and isinstance(content, list):
        return content[0].get("text", "")
    return response_json.get("completion", "")


def _parse_openai_response(response_json: dict) -> str:
    choices = response_json.get("choices", [])
    if choices and isinstance(choices, list):
        return choices[0].get("message", {}).get("content", "")
    return ""


def call_llm(prompt: str) -> str:
    """
    根据配置调用指定 LLM Provider，返回生成的文本。

    Raises:
        RuntimeError: API 调用失败或返回异常时抛出。
    """
    settings = get_settings()
    provider = settings.llm_provider.lower().strip()
    api_key = settings.llm_api_key.strip()
    base_url = settings.llm_base_url.strip()
    model = settings.llm_model.strip()
    max_tokens = settings.llm_max_tokens

    if not api_key:
        raise RuntimeError("LLM API Key 未配置，请在 .env 中设置 LLM_API_KEY")

    if provider == "anthropic":
        url = (base_url or "https://api.anthropic.com") + "/v1/messages"
        payload = _build_anthropic_payload(model, max_tokens, prompt)
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        parse_fn = _parse_anthropic_response
    elif provider == "openai":
        url = (base_url or "https://api.openai.com") + "/v1/chat/completions"
        payload = _build_openai_payload(model, max_tokens, prompt)
        headers = {
            "authorization": f"Bearer {api_key}",
            "content-type": "application/json",
        }
        parse_fn = _parse_openai_response
    else:
        raise RuntimeError(f"不支持的 LLM Provider: {provider}")

    logger.info(f"[LLM] 请求 {provider} 模型 {model}, prompt 长度约 {len(prompt)} 字符")

    try:
        with httpx.Client(timeout=DEFAULT_TIMEOUT, follow_redirects=True) as client:
            resp = client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as e:
        logger.error(f"[LLM] HTTP 错误: {e.response.status_code} - {e.response.text}")
        raise RuntimeError(f"LLM API 返回错误: {e.response.status_code}")
    except httpx.RequestError as e:
        logger.error(f"[LLM] 网络请求失败: {e}")
        raise RuntimeError(f"LLM API 请求失败: {e}")
    except json.JSONDecodeError as e:
        logger.error(f"[LLM] 响应 JSON 解析失败: {e}")
        raise RuntimeError("LLM API 响应格式异常")

    text = parse_fn(data)
    if not text:
        logger.warning(f"[LLM] 返回内容为空，原始响应: {json.dumps(data, ensure_ascii=False)[:500]}")
        raise RuntimeError("LLM 返回内容为空")

    logger.info(f"[LLM] 成功获取响应，长度约 {len(text)} 字符")
    return text
