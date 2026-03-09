# QuantClaw - 加密量化技能库

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Skills](https://img.shields.io/badge/技能-100+-blue.svg)](./skills)

最大的开源加密量化 AI 技能库，专为 OpenClaw/Clawdbot 框架设计。

**100+ 精选技能 · 交易执行 · 链上分析 · 量化回测 · 风险管理 · 宏观数据**

[English](./README.md) | [中文](#)

## 项目简介

QuantClaw 是一个包含 **100+ AI Agent 技能**的精选集合，覆盖加密货币交易和量化研究的完整领域。这些技能专为 [OpenClaw](https://github.com/openclaw/openclaw) / [Clawdbot](https://github.com/clawdbot/clawdbot) —— 基于 Claude 的个人 AI 助手框架 —— 设计，能将通用 AI 智能体转变为强大的加密量化交易研究伙伴。

每个技能都是一个独立模块（SKILL.md 文件），它：
- 为 Agent 注入专业领域知识与工作流
- 连接真实的交易所、链上数据和分析工具
- 输出结构化的交易信号和研究洞察

### 为什么需要这个技能库？

| 没有技能 | 配备 QuantClaw 后 |
|----------|-------------------|
| 对加密货币的通用 AI 回答 | 实时查询交易所/链上数据 |
| 无量化分析能力 | 回测、策略分析、风险计算 |
| 无交易执行能力 | 多交易所 API 接入、自动化交易 |
| 无链上情报 | 鲸鱼追踪、智能钱包、DEX 分析 |
| 无宏观分析 | 非农、CPI、FOMC 实时推送 |

## 技能总览

| 类别 | 数量 | 代表技能 |
|------|------|----------|
| **交易所集成** | 15+ | Binance、OKX、Gate、Bybit、Coinbase API |
| **行情数据** | 10+ | 实时价格、K线、深度、资金费率 |
| **链上分析** | 20+ | 鲸鱼追踪、钱包分析、DEX 交易、Gas 监控 |
| **量化回测** | 15+ | 策略回测、参数优化、风险指标 |
| **策略执行** | 10+ | 网格、马丁、DCA、套利、跟单 |
| **风险管理** | 10+ | 仓位计算、止损止盈、爆仓预警 |
| **宏观数据** | 10+ | 非农、CPI、利率决议、恐惧贪婪指数 |
| **新闻情报** | 10+ | 项目公告、空投监控、上币预警 |
| **DeFi 工具** | 15+ | 收益聚合、流动性挖矿、借贷利率 |
| **报告生成** | 5+ | 日报、周报、策略分析报告 |

**总计：100+ 技能**

## 安装方法

### 前置要求

- 已安装并运行 [OpenClaw](https://github.com/openclaw/openclaw) 或 [Clawdbot](https://github.com/clawdbot/clawdbot)
- Git（用于克隆本仓库）

### 方法一 — 克隆并复制（推荐）

```bash
# 克隆本仓库
git clone https://github.com/FA-alpha/QuantClaw.git

# 安装到当前工作区的 skills 目录
cp -r QuantClaw/skills/* <your-workspace>/skills/

# 或安装到全局（所有 Agent 均可使用）
cp -r QuantClaw/skills/* ~/.clawdbot/skills/
```

### 方法二 — 按需安装

```bash
# 示例：交易 + 风控技能组合
SKILLS=(
  "binance-api"
  "grid-trading"
  "backtest-engine"
  "risk-calculator"
  "whale-tracker"
)

for skill in "${SKILLS[@]}"; do
  cp -r QuantClaw/skills/*/$skill ~/.clawdbot/skills/
done
```

### 方法三 — ClawHub CLI

```bash
clawdbot skill install crypto-whale-tracker
clawdbot skill install binance-api
```

## 目录结构

```
QuantClaw/
├── README.md           # 英文说明
├── README_zh.md        # 中文说明
├── LICENSE
├── skills/
│   ├── exchanges/      # 交易所集成
│   ├── market-data/    # 行情数据
│   ├── onchain/        # 链上分析
│   ├── quant/          # 量化工具
│   ├── strategies/     # 策略模板
│   ├── risk/           # 风险管理
│   ├── macro/          # 宏观数据
│   ├── news/           # 新闻情报
│   ├── defi/           # DeFi 工具
│   └── reports/        # 报告生成
└── docs/
    ├── INSTALLATION.md
    ├── SKILL_GUIDE.md
    └── API_REFERENCE.md
```

## 快速开始

安装完成后，向你的 Agent 提问：

> 你现在有哪些加密量化方面的技能？

Agent 应列出已安装的技能及功能说明。

### 示例查询

```
"查询 BTC 当前价格"
"追踪 ETH 鲸鱼动向"
"回测 BTC 网格策略，时间范围 2024 年"
"查看恐惧贪婪指数"
"生成今日加密日报"
```

## 核心技能详解

### 交易所集成

#### binance-api
连接币安交易所，支持现货、合约、杠杆交易。
- 账户余额查询
- 现货/合约下单
- 持仓管理
- 历史订单查询

#### exchange-aggregator
统一接口访问多个交易所，比较价格、执行最优路径。

### 链上分析

#### whale-tracker
监控大户钱包动向，追踪聪明钱操作。
- Top 100 钱包监控
- 大额转账预警
- 交易所流入流出
- 累积/分发分析

#### smart-money
追踪机构、做市商、早期投资者的链上行为。

### 量化工具

#### backtest-engine
对交易策略进行历史回测，输出绩效指标。
- 支持多币种回测
- 自定义参数优化
- 输出 Sharpe、最大回撤、胜率
- 可视化收益曲线

#### risk-calculator
计算仓位大小、止损点、预期收益。
- Kelly 公式仓位
- 固定风险仓位
- 波动率调整
- VaR 计算

### 宏观数据

#### nfp-tracker
监控美国非农就业数据发布，自动推送分析。

#### fear-greed-index
获取加密市场情绪指标。

### 策略模板

#### grid-trading
自动化网格交易，适合震荡行情。

#### martingale
分层加仓策略，配合止盈。

## 贡献指南

欢迎贡献！请查看 [CONTRIBUTING.md](./docs/CONTRIBUTING.md) 了解详情。

## 许可证

MIT License - 详见 [LICENSE](./LICENSE)

## 致谢

- 结构参考 [OpenClaw-Medical-Skills](https://github.com/galenhuang/OpenClaw-Medical-Skills)
- 为 [Clawdbot](https://github.com/clawdbot/clawdbot) 生态系统构建

---

**FourierAlpha** | 构建 AI 驱动的量化交易未来
