# 任务

## 1. 脚本实现

- [x] 在 `scripts/nas_update_and_mail.sh` 增加 `parse_mail_recipients` helper。
- [x] 增加 `send_mail_to_recipients` helper，逐个调用 `MAIL_BIN`。
- [x] 将成功日报发送路径改为使用 helper。
- [x] 将报告文件缺失错误邮件路径改为使用 helper。
- [x] 将 update-report 失败错误邮件路径改为使用 helper。
- [x] 确保空收件人列表退出状态为 `2`。
- [x] 确保任一收件人发送失败时最终返回非零，但仍继续尝试后续收件人。

## 2. 文档

- [x] 更新 `docs/nas-docker-deploy.md`，说明 `MAIL_TO` 多人写法。
- [x] 更新 cron 示例，优先展示逗号分隔的多人配置。
- [x] 如需要，更新 `docs/handoff.md` 记录新的 NAS 邮件脚本行为。

## 3. 验证

- [x] 增加脚本级测试或等价 shell 验证，覆盖单人收件人。
- [x] 覆盖逗号分隔多人收件人。
- [x] 覆盖空格或分号分隔多人收件人。
- [x] 覆盖空收件人列表。
- [x] 覆盖部分收件人发送失败。
- [x] 运行相关测试。
- [x] 运行 `git diff --check`。
- [x] 代码编辑后运行 `codegraph sync`。
