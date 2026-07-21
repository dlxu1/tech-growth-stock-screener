## ADDED Requirements

### Requirement: NAS 邮件脚本支持多个收件人
系统 SHALL 允许 NAS 邮件发送脚本通过 `MAIL_TO` 配置一个或多个日报收件人。

#### Scenario: 单个收件人保持兼容
- **WHEN** `MAIL_TO` 设置为一个邮箱地址
- **THEN** 脚本 SHALL 向该地址发送日报或失败日志
- **AND** 现有单收件人 cron 配置 SHALL 无需修改即可继续工作

#### Scenario: 逗号分隔多个收件人
- **WHEN** `MAIL_TO` 设置为 `a@example.com,b@example.com`
- **THEN** 脚本 SHALL 分别向 `a@example.com` 和 `b@example.com` 发送同一封日报或失败日志

#### Scenario: 空格或分号分隔多个收件人
- **WHEN** `MAIL_TO` 使用空格或分号分隔多个地址
- **THEN** 脚本 SHALL 将每个非空地址识别为独立收件人

#### Scenario: 没有有效收件人
- **WHEN** `MAIL_TO` 未设置或解析后没有有效地址
- **THEN** 脚本 SHALL 输出明确错误
- **AND** 脚本 SHALL 以状态码 `2` 退出

### Requirement: 多人发送错误处理
系统 SHALL 对多个收件人逐个发送，且任一失败不得阻止继续尝试剩余收件人。

#### Scenario: 部分收件人发送失败
- **WHEN** 多个收件人中某个地址发送失败
- **THEN** 脚本 SHALL 在日志中记录失败地址
- **AND** 脚本 SHALL 继续尝试其他收件人
- **AND** 脚本最终 SHALL 返回非零状态

#### Scenario: 更新失败邮件发送给全部收件人
- **WHEN** `docker compose run --rm update-report` 失败
- **THEN** 脚本 SHALL 将失败日志发送给所有解析出的收件人
- **AND** 脚本 SHALL 保留非零退出状态
