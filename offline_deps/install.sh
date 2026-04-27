#!/bin/bash
# ============================================================
# 内网离线安装 Python 依赖（在无互联网的内网机器上运行）
# 前提: 已将 offline_deps/ 目录拷贝到内网机器
# 用法: bash install.sh
# ============================================================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REQUIREMENTS="$SCRIPT_DIR/../requirements.txt"
CACHE_DIR="$SCRIPT_DIR/pip_cache"

if [ ! -d "$CACHE_DIR" ]; then
    echo "错误: 未找到 pip_cache 目录"
    echo "请先在有互联网的机器上运行 download.sh 下载依赖"
    exit 1
fi

echo "正在从本地缓存安装依赖 ..."
pip install --no-index --find-links="$CACHE_DIR" -r "$REQUIREMENTS"

if [ $? -eq 0 ]; then
    echo ""
    echo "安装完成！"
    echo "运行项目: python run.py"
else
    echo ""
    echo "安装失败，请检查 pip_cache 目录是否包含所有依赖"
    exit 1
fi
