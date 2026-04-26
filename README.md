# 重点人管控系统

政务级重点人员预警管控平台。整合预警中心、布控管理、线索管理、Dify 智能分析于一体。

## 目录结构

```
├── app.py                              # Flask 后端主程序（统一入口）
├── run.py                              # 统一启动脚本（Web + 后台调度）
├── config.py                           # 统一配置文件
├── scheduler.py                        # 后台任务调度器
├── gov_monitor_v2.html                 # 主页面（预警中心 v2）
├── gov_monitor_v2_1.html               # 备用页面（预警中心 v2.1）
├── init_mysql.sql                      # MySQL 数据库初始化脚本
├── requirements.txt                    # Python 依赖列表
├── start.sh / start.bat                # 旧版启动脚本（已弃用，请使用 run.py）
├── services/                           # 业务服务层
│   ├── __init__.py
│   └── db.py                           # 数据库连接管理与通用查询
├── static/                             # 静态资源
│   ├── css/
│   ├── fonts/
│   ├── img/
│   └── webfonts/
├── 后端/                               # 后端测试与辅助脚本
│   └── test_linkage.py                 # 端到端联动测试
├── queryPersonByAttrWithPage.py        # Dify: 根据人员身份查人脸
├── queryByImageModelWithPage.py        # Dify: 根据人脸查身份
├── queryDataByImageModelWithPage1.py   # Dify: 根据URL查抓拍
├── insert_face_records.py              # Dify: 抓拍记录入库
├── choose_peoples_together_insert_into_db.py  # 同行人聚类分析
├── find_drivers_insert_into_db.py      # 同机判断分析
├── find_all_young_pk_insert_into_db.py # 重点人员抓拍同步
├── operate_jddb_by_http.py             # 摄像头数据同步
└── clue_routes.py                      # 线索管理路由
```

## 环境要求

- Python 3.9+
- MySQL 5.7+ / 8.0+
- pip

## 快速启动

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置环境变量（或修改 config.py）
export DB_HOST=localhost
export DB_PORT=3306
export DB_USER=root
export DB_PASSWORD=your_password
export DB_NAME=wcnr

# 3. 启动服务（Web + 后台调度）
python run.py
```

访问地址: http://127.0.0.1:5000

## 配置说明

所有配置集中在 `config.py`，支持通过环境变量覆盖：

| 环境变量 | 说明 | 默认值 |
|---------|------|--------|
| `DB_HOST` | 数据库主机 | localhost |
| `DB_PORT` | 数据库端口 | 3306 |
| `DB_USER` | 数据库用户名 | root |
| `DB_PASSWORD` | 数据库密码 | root_password |
| `DB_NAME` | 数据库名 | wcnr |
| `FLASK_HOST` | Web服务绑定地址 | 0.0.0.0 |
| `FLASK_PORT` | Web服务端口 | 5000 |
| `FLASK_DEBUG` | 调试模式 | true |
| `SCHEDULER_ENABLED` | 是否启用后台调度 | true |
| `SYNC_CAPTURE_INTERVAL` | 抓拍同步间隔(分钟) | 30 |
| `CLUSTER_INTERVAL` | 聚类分析间隔(分钟) | 0(不启用) |

## API 路由

### 预警中心
- `GET  /` - 主页面
- `GET  /api/stats` - 预警统计
- `GET  /api/alerts` - 预警列表
- `GET  /proxy-pic` - 图片代理

### 布控管理
- `GET  /api/control/stats` - 布控统计
- `GET  /api/controls` - 布控人员列表
- `POST /api/control/batch_revoke` - 批量撤控
- `POST /api/control/batch_delete` - 批量删除
- `POST /api/control/import` - 导入布控人员
- `GET  /api/control/today` - 今日预警布控人员

### 线索管理
- `GET  /clues` - 线索页面
- `GET  /api/clues` - 线索列表
- `POST /api/clues` - 创建线索
- `GET  /api/clues/<clue_number>` - 线索详情
- `PUT  /api/clues/<clue_id>` - 更新线索
- `DELETE /api/clues/<clue_id>` - 删除线索
- `GET  /api/clues/statistics` - 线索统计

### Dify 智能分析
- `POST /queryPersonByAttrWithPage` - 根据人员身份查人脸
- `POST /queryByImageModelWithPage` - 根据人脸查身份
- `POST /queryDataByImageModelWithPage1` - 根据图片URL查抓拍
- `POST /insertFaceRecordsIntoDb` - 抓拍记录入库
- `POST /cluster` - 同行人聚类
- `POST /judgeDrivers` - 同机判断
- `POST /updateTmpCameras` - 摄像头同步

### 系统
- `GET  /api/health` - 健康检查

## 数据库初始化

```bash
mysql -u root -p < init_mysql.sql
```

## 后台任务

调度器在 `scheduler.py` 中管理，默认任务：

- **capture_sync**: 从海康接口同步重点人员抓拍记录到 `capture_records` 表

手动触发任务：

```python
from scheduler import scheduler
scheduler.run_now('capture_sync')
```

## 端口修改

编辑 `config.py` 中的 `FLASK_PORT` 或设置环境变量：

```bash
export FLASK_PORT=8080
python run.py
```
