# 重点人管控系统

政务级重点人员预警管控平台前端 Demo。

## 目录结构

```
├── app.py                  # Flask 后端主程序
├── gov_monitor_v2.html     # 主页面（预警中心 v2）
├── gov_monitor.html        # 备用页面（预警中心 v1）
├── instance/
│   └── monitor.db          # SQLite 数据库（含演示数据）
├── requirements.txt        # Python 依赖列表
├── start.sh                # Linux/macOS 启动脚本
├── start.bat               # Windows 启动脚本
└── README.md               # 本文件
```

## 环境要求

- Python 3.9+
- pip

## 内网部署步骤

### 方式一：使用启动脚本（推荐）

**Linux / macOS:**
```bash
chmod +x start.sh
./start.sh
```

**Windows:**
```cmd
双击 start.bat
```

### 方式二：手动部署

1. 创建虚拟环境并激活
```bash
python3 -m venv .venv
source .venv/bin/activate      # Linux/macOS
# .venv\Scripts\activate       # Windows
```

2. 安装依赖
```bash
pip install -r requirements.txt
```

3. 启动服务
```bash
python app.py
```

## 访问地址

服务启动后，在浏览器打开：

- 主页面（v2）: http://127.0.0.1:5050/v2
- 备用页面（v1）: http://127.0.0.1:5050/

## 内网离线安装（无互联网环境）

1. 在有网的机器上执行：
```bash
pip download -r requirements.txt -d deps
```
将 `deps` 文件夹一并复制到内网服务器。

2. 在内网服务器安装：
```bash
pip install --no-index --find-links deps -r requirements.txt
```

## 端口修改

编辑 `app.py` 最后一行：
```python
app.run(host='0.0.0.0', port=5050, debug=True)
```
将 `port=5050` 改为需要的端口，如 `port=80`。

生产环境建议关闭 debug：
```python
app.run(host='0.0.0.0', port=5050, debug=False)
```

## 数据说明

- 数据库：`instance/monitor.db`（SQLite）
- 已预置 30 天演示数据，约 3000+ 条预警记录
- 首次启动若数据库不存在会自动初始化并生成模拟数据
