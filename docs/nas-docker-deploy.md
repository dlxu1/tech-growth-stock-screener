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

如果项目部署在 NAS 的 `/vol1/docker/tech-growth-stock-screener`，则：

```text
NAS 主机路径: /vol1/docker/tech-growth-stock-screener/nas-cache
容器内路径: /app/.cache
```

因此容器内写入的：

```text
/app/.cache/stock_data.sqlite
```

实际会落到 NAS 主机上的：

```text
/vol1/docker/tech-growth-stock-screener/nas-cache/stock_data.sqlite
```

这里的“NAS 主机”指 SSH 登录后看到的 NAS 系统本身；容器有自己的文件系统，
Docker Compose 通过 volume 把 NAS 主机目录挂载进容器。

不要把 `.cache` 打进镜像。缓存应该通过 volume 持久化，避免容器重建后数据丢失。

## 首次部署

在 NAS 上进入项目目录：

```bash
docker compose build
docker compose up -d dashboard
```

`Dockerfile` 和 `docker-compose.yml` 默认给构建过程配置了阿里云 Debian
和 PyPI 镜像源，用于减少 NAS 从官方源拉包过慢的问题。

然后打开：

```text
http://NAS_IP:5001/dashboard
```

NAS 默认启动参数会关闭 `近 30 天好时机+高潜力重复命中` 的现场补算：

```text
--no-recent-high-good-hits
```

这个功能在首次缓存未预热时会补算多个历史日期，容易造成 NAS CPU 波动。
后续可以通过离线预热或性能优化后再打开。

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

如果项目目录在 `/vol1/docker/tech-growth-stock-screener`，可以直接执行：

```bash
cd /vol1/docker/tech-growth-stock-screener
docker compose run --rm update
```

如需把手动更新输出也写入日志：

```bash
cd /vol1/docker/tech-growth-stock-screener
docker compose run --rm update >> /vol1/docker/tech-growth-stock-screener/nas-cache/update.log 2>&1
```

这个任务会运行 `scripts/docker_update.py`，按顺序增量更新：

1. 股票现货快照。
2. 自动选择的财报数据。
3. 沪深 300 成分。
4. 沪深 300 成分股日线行情，从 `2026-01-01` 补到当天。
5. dashboard 数据健康校验。

日线更新使用项目默认的增量缓存策略：已覆盖的股票会跳过，只补缺失尾段。
当天行情会写入 SQLite 的 `quotes_daily` 表。SQLite 文件不是简单在末尾追加文本，
而是由数据库执行 upsert/跳过等写入逻辑，避免同一股票同一交易日重复堆积记录。

## NAS 定时任务

如果 NAS 支持计划任务，可以每天收盘后执行：

```bash
cd /path/to/tech-growth-stock-screener
docker compose run --rm update
```

建议先手动运行一次，确认 NAS 网络可以访问上游公开数据源，再加入定时任务。

如果 NAS 暴露了 Linux cron，也可以用 cron 安排每个工作日 17:00 自动更新。
先通过 SSH 检查 cron 能力：

```bash
which crontab
ps aux | grep -E '[c]ron|[c]rond'
crontab -l
```

如果 `which crontab` 能找到命令，且进程里存在 `cron` 或 `crond`，说明 cron
服务在运行。`crontab -l` 输出 `no crontab for <user>` 只表示当前用户还没有任务，
不是 cron 不可用。

编辑当前用户的 cron：

```bash
crontab -e
```

首次使用时可以选择 `/bin/nano`，它最简单。加入下面这一行即可让任务在每周一到周五
17:00 执行：

```cron
0 17 * * 1-5 cd /vol1/docker/tech-growth-stock-screener && /usr/bin/docker compose run --rm update >> /vol1/docker/tech-growth-stock-screener/nas-cache/update.log 2>&1
```

如果 `which docker` 输出不是 `/usr/bin/docker`，把上面命令里的 `/usr/bin/docker`
换成实际路径。如果当前用户没有 Docker 权限，可以改用 root 的 cron：

```bash
sudo crontab -e
sudo crontab -l
```

cron 行尾的日志重定向含义：

- `>> update.log`：把每次运行的正常输出追加写入日志文件，不覆盖旧日志。
- `2>&1`：把错误输出也合并到同一个日志文件，方便排查失败原因。

检查定时任务是否保存成功：

```bash
crontab -l
```

查看更新日志：

```bash
tail -100 /vol1/docker/tech-growth-stock-screener/nas-cache/update.log
```

如果还没到触发时间，可以临时加入一条每分钟测试任务验证 cron 是否生效：

```cron
* * * * * date >> /vol1/docker/tech-growth-stock-screener/nas-cache/cron-test.log 2>&1
```

等待一两分钟后查看：

```bash
tail -20 /vol1/docker/tech-growth-stock-screener/nas-cache/cron-test.log
```

确认有时间输出后，记得从 `crontab -e` 删除这条测试任务，只保留股票更新任务。

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
