#!/bin/bash

# 重点人管控系统 - 启动脚本

cd "$(dirname "$0")"

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo "错误：未找到 python3，请先安装 Python 3.9+"
    exit 1
fi

# 创建虚拟环境（如果不存在）
if [ ! -d ".venv" ]; then
    echo "正在创建虚拟环境..."
    python3 -m venv .venv
fi

# 激活虚拟环境并安装依赖
source .venv/bin/activate
pip install -q --no-index --find-links ./deps -r requirements.txt 2>/dev/null || pip install -q -r requirements.txt

echo "启动服务..."
python run.py
