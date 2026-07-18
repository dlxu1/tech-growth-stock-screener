# NAS Docker 部署说明

本项目推荐在 NAS 上以 Docker Compose 常驻运行 `dashboard-server`。浏览器访问
`http://NAS_IP:5001/dashboard` 后即可使用 dashboard、历史日期重算和
`/api/dashboard` 数据接口。

本项目仅用于公开数据研究和辅助决策，不构成投资建议。

## 部署结构

容器内固定使用：

```text
/app/.cache
```

作为缓存目录，并通过 Compose 挂载到宿主机：

```text
./nas-cache:/app/.cache
```

这个目录会保存：

- `stock_data.sqlite`：股票、财报、指数成分、日线行情、dashboard 快照。
- `reports/`：静态 HTML 报表输出。
- dashboard 快照和矩阵信号缓存表。

不要把 `.cache` 打进镜像。缓存应该通过 volume 持久化，避免容器重建后数据丢失。

## 首次部署

在 NAS 上进入项目目录：

```bash
docker compose build
docker compose up -d dashboard
```

然后打开：

```text
http://NAS_IP:5001/dashboard
```

如果你已经在本机生成过缓存，推荐先复制本机数据库到 NAS：

```bash
mkdir -p nas-cache
cp .cache/stock_data.sqlite nas-cache/stock_data.sqlite
```

这样 dashboard 服务启动后会直接使用已有缓存，不需要第一次打开时等待全量数据同步。

## 更新数据

需要手动更新数据时运行：

```bash
docker compose run --rm update
```

这个任务会运行 `scripts/docker_update.py`，按顺序增量更新：

1. 股票现货快照。
2. 自动选择的财报数据。
3. 沪深 300 成分。
4. 沪深 300 成分股日线行情，从 `2026-01-01` 补到当天。
5. dashboard 数据健康校验。

日线更新使用项目默认的增量缓存策略：已覆盖的股票会跳过，只补缺失尾段。

## NAS 定时任务

如果 NAS 支持计划任务，可以每天收盘后执行：

```bash
cd /path/to/tech-growth-stock-screener
docker compose run --rm update
```

建议先手动运行一次，确认 NAS 网络可以访问上游公开数据源，再加入定时任务。

## 常用命令

查看服务状态：

```bash
docker compose ps
```

查看 dashboard 日志：

```bash
docker compose logs -f dashboard
```

重启 dashboard：

```bash
docker compose restart dashboard
```

停止服务：

```bash
docker compose down
```

重新构建镜像：

```bash
docker compose build
docker compose up -d dashboard
```

## 端口和访问控制

默认端口映射是：

```yaml
ports:
  - "5001:5001"
```

如果 NAS 上 `5001` 已被占用，可以改成：

```yaml
ports:
  - "15001:5001"
```

然后访问：

```text
http://NAS_IP:15001/dashboard
```

当前服务没有内置登录鉴权。建议只在家庭局域网或 NAS 反向代理的受控访问范围内使用。

## 网络和代理

容器默认使用 `--source cache` 启动 dashboard，打开页面时不会主动联网拉取数据。
数据更新任务使用 `--source auto`，会访问公开第三方数据源。

如果 NAS 需要代理，可以在 `docker-compose.yml` 的 `environment` 中加入：

```yaml
TECH_GROWTH_PROXY: http://代理地址:端口
```

如果上游数据源直连更稳定，可以临时进入容器或调整更新命令加 `--no-proxy`。

## 数据备份

建议定期备份：

```text
nas-cache/stock_data.sqlite
```

这个文件是部署中最重要的数据资产。只要它还在，容器和镜像都可以重新构建。
