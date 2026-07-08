# Screening Rules

Use this reference when explaining or adjusting the `tech-growth-stock-screener` filter.

## Required Gates

### 1. Technology Exposure

Treat a stock as technology-related only if it belongs to an industry board whose name matches technology keywords such as:

- 半导体
- 电子
- 元件
- 光学光电子
- 消费电子
- 通信设备
- 通信服务
- 软件开发
- 计算机设备
- 互联网服务
- IT服务
- 人工智能
- 自动化设备
- 专用设备, only when the context is semiconductor, robotics, automation, or advanced manufacturing

Do not pass a company only because its stock price is strong or it appears in social-media themes.

### 2. Industry Market-Cap Top 10

Rank candidates inside each matched technology industry board by total market capitalization.

Pass only stocks whose market-cap rank is `<= --industry-rank`, default `10`.

If a stock appears in multiple matched boards, keep the best rank and record the board that produced it.

### 3. Real One-Year Growth

Require both of these public financial-report fields to be positive:

- revenue YoY growth;
- net-profit YoY growth.

Prefer the latest available quarterly or annual performance report from Eastmoney/AKShare. Do not use price momentum, order rumors, concept membership, or analyst expectations as substitutes for real growth.

When a field is missing, exclude the stock instead of guessing.

## Ranking After Passing Gates

After all required gates pass, rank by:

1. market-cap leadership within the technology board;
2. net-profit YoY growth;
3. revenue YoY growth;
4. liquidity/market-cap size as a tie breaker.

The rank is a research priority, not a trading recommendation.

## Risk Checks To Mention

For the final answer, name at least one failure condition:

- growth is driven by one-time gains rather than operations;
- revenue grows but receivables or inventory rises faster;
- industry cycle turns down;
- valuation already prices in perfect execution;
- policy/export-control risk affects the business.

Use wording such as:

`这是优先研究名单，不构成投资建议。下一步应核对最新财报附注、现金流、应收和存货。`
