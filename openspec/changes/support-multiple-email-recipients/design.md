# 设计

## 概览

在 `scripts/nas_update_and_mail.sh` 中增加两个小型 shell helper：

- `parse_mail_recipients`: 从 `MAIL_TO` 中解析有效收件人数组。
- `send_mail_to_recipients`: 对收件人数组逐个调用 `mail`，记录每个地址的发送结果。

脚本仍然保持当前职责：运行 `docker compose run --rm update-report`，读取已生成的主题和正文，然后用 NAS 主机上的 `mail` 或 `msmtp` 兼容命令发送。

## 收件人格式

`MAIL_TO` 支持以下分隔方式：

```bash
MAIL_TO="a@example.com"
MAIL_TO="a@example.com,b@example.com"
MAIL_TO="a@example.com b@example.com"
MAIL_TO="a@example.com;b@example.com"
```

内部解析规则：

1. 将逗号和分号统一替换为空格。
2. 用 shell word splitting 形成候选地址。
3. 过滤空字符串。
4. 不做复杂邮箱正则校验，避免误伤合法地址；实际可达性由 `mail` 命令决定。

## 发送行为

成功日报：

1. 先运行 `docker compose run --rm update-report`。
2. 如果日报正文文件存在，读取主题。
3. 对每个收件人执行：

```bash
"$MAIL_BIN" -s "$subject" "$recipient" < "$BODY_FILE"
```

4. 记录每个收件人的成功或失败。
5. 如果任一发送失败，脚本最终返回 `1`。

失败日志：

如果数据更新或日报生成失败，脚本仍向同一批收件人发送 `update.log` 后 200 行。此路径也使用同一个 `send_mail_to_recipients` helper，避免成功和失败邮件行为不一致。

## 错误处理

- `MAIL_TO` 未设置或解析后没有有效地址：输出 `MAIL_TO is required`，退出 `2`。
- 正文缺失：发送“报告文件缺失”错误邮件；如果错误邮件也发送失败，退出 `1`。
- 更新失败：发送“股票数据更新失败”错误邮件；发送完成后返回原始更新失败状态，除非邮件发送失败，此时也保持非零。
- 单个地址发送失败不应阻止继续尝试后续地址。

## 文档

更新 `docs/nas-docker-deploy.md`：

- 说明 `MAIL_TO` 支持逗号、空格、分号分隔。
- 推荐 cron 示例使用逗号分隔，因为最不容易被 shell 误拆。
- 保留单人邮箱示例。
- 对“17:00 更新、次日 09:00 发送”的拆分方案，说明 09:00 纯 `mail` 命令如果要多人收件，推荐调用项目新增的发送 helper 或在文档中给出逐个发送示例。

## 测试

新增 shell 脚本测试，使用临时目录和假的 `mail` / `docker` 命令验证：

- 单个 `MAIL_TO` 发送一次。
- 逗号、空格、分号分隔时分别发送多次。
- 空 `MAIL_TO` 返回 `2`。
- 某个收件人发送失败时仍尝试其他地址，最终返回非零。
- `update-report` 失败时向每个收件人发送失败日志。

测试应避免真实 Docker 和真实邮件发送。
