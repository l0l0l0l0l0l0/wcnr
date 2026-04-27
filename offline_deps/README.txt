# 内网离线部署说明

## 步骤一：在有互联网的机器上下载依赖

```bash
cd offline_deps
bash download.sh
```

这会将所有 Python 依赖下载到 `pip_cache/` 目录。

## 步骤二：拷贝到内网机器

将整个 `offline_deps/` 目录拷贝到内网机器的项目根目录下。

## 步骤三：在内网机器上安装依赖

```bash
cd offline_deps
bash install.sh
```

## 步骤四：启动服务

```bash
python run.py
```

默认管理员账号: admin / admin123（首次部署后请立即修改密码）
