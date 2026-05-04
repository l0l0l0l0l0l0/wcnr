#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 LLM 调用是否正常
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from services.ai_llm import call_llm


def main():
    print("=" * 60)
    print("🚀 测试 LLM 调用")
    print("=" * 60)
    print()

    try:
        test_prompt = "你好，请用一句话介绍一下自己"
        print(f"📝 发送提示词: {test_prompt}")
        print()

        result = call_llm(test_prompt)

        print("✅ 调用成功！")
        print("-" * 60)
        print(result)
        print("-" * 60)
        print()
        print("🎉 LLM 调用正常！")
        return 0

    except Exception as e:
        print("❌ 调用失败:", e)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
