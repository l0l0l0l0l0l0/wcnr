#!/bin/bash
# ============================================================
# 下载所有 Python 依赖到本地缓存（在有互联网的机器上运行）
# 用法: bash download.sh
# ============================================================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REQUIREMENTS="$SCRIPT_DIR/../requirements.txt"
CACHE_DIR="$SCRIPT_DIR/pip_cache"

echo "正在下载依赖到 $CACHE_DIR ..."
mkdir -p "$CACHE_DIR"

pip download \
    -r "$REQUIREMENTS" \
    -d "$CACHE_DIR" \
    --platform manylinux2014_x86_64 \
    --platform manylinux2014_aarch64 \
    --platform macosx_11_0_arm64 \
    --platform macosx_11_0_x86_64 \
    --python-version 311 \
    --only-binary=:all: \
    2>/dev/null || true

# 下载纯 Python 包（不指定 platform）
pip download \
    -r "$REQUIREMENTS" \
    -d "$CACHE_DIR" \
    2>/dev/null

echo ""
echo "下载完成！文件保存在: $CACHE_DIR"
echo "将 offline_deps/ 整个目录拷贝到内网机器，然后运行 install.sh"
ls -la "$CACHE_DIR" | head -5
echo "..."
echo "共 $(ls "$CACHE_DIR" | wc -l) 个文件"
