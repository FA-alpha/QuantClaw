# QuantClaw - Crypto Quant Skills for OpenClaw

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Skills](https://img.shields.io/badge/Skills-100+-blue.svg)](./skills)

The largest open-source crypto quantitative trading skill library, designed for OpenClaw/Clawdbot framework.

**100+ curated skills · Trading · On-chain Analytics · Backtesting · Risk Management · Macro Data**

[English](#) | [中文](./README_zh.md)

## Overview

QuantClaw is a curated collection of **100+ AI Agent skills** covering the complete spectrum of cryptocurrency trading and quantitative research. These skills are designed for [OpenClaw](https://github.com/openclaw/openclaw) / [Clawdbot](https://github.com/clawdbot/clawdbot) — Claude-based personal AI assistant frameworks — transforming general-purpose AI agents into powerful crypto trading research partners.

Each skill is a self-contained module (SKILL.md file) that:
- Injects domain expertise and workflows into your agent
- Connects to real exchanges, on-chain data, and analysis tools
- Outputs structured trading signals and research insights

### Why This Skill Library?

| Without Skills | With QuantClaw |
|----------------|----------------|
| Generic crypto answers | Real-time exchange & on-chain data queries |
| No quantitative capabilities | Backtesting, strategy analysis, risk metrics |
| No trading execution | Multi-exchange API integration |
| No on-chain intelligence | Whale tracking, smart money, DEX analysis |
| No macro analysis | NFP, CPI, FOMC real-time alerts |

## Skill Categories

| Category | Count | Key Skills |
|----------|-------|------------|
| **Exchanges** | 15+ | Binance, OKX, Gate, Bybit, Coinbase API |
| **Market Data** | 10+ | Real-time prices, K-lines, depth, funding rates |
| **On-chain** | 20+ | Whale tracking, wallet analysis, DEX trades |
| **Quant Tools** | 15+ | Backtesting, optimization, risk metrics |
| **Strategies** | 10+ | Grid, Martingale, DCA, arbitrage |
| **Risk Management** | 10+ | Position sizing, stop-loss, liquidation alerts |
| **Macro Data** | 10+ | NFP, CPI, FOMC, Fear & Greed Index |
| **News & Intel** | 10+ | Project alerts, airdrops, listings |
| **DeFi** | 15+ | Yield aggregation, liquidity mining, lending |
| **Reports** | 5+ | Daily/weekly reports, strategy analysis |

**Total: 100+ Skills**

## Installation

### Prerequisites

- [OpenClaw](https://github.com/openclaw/openclaw) or [Clawdbot](https://github.com/clawdbot/clawdbot) installed and running
- Git (for cloning this repository)

### Method 1 — Clone & Copy (Recommended)

```bash
# Clone this repository
git clone https://github.com/FA-alpha/QuantClaw.git

# Install to your workspace skills directory
cp -r QuantClaw/skills/* <your-workspace>/skills/

# Or install globally (available to all agents)
cp -r QuantClaw/skills/* ~/.clawdbot/skills/
```

### Method 2 — Install Selected Skills

```bash
# Example: Trading + Risk skills combo
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

### Method 3 — ClawHub CLI

```bash
clawdbot skill install crypto-whale-tracker
clawdbot skill install binance-api
```

## Directory Structure

```
QuantClaw/
├── README.md
├── README_zh.md
├── LICENSE
├── skills/
│   ├── exchanges/          # Exchange integrations
│   ├── market-data/        # Price & market data
│   ├── onchain/            # On-chain analytics
│   ├── quant/              # Quantitative tools
│   ├── strategies/         # Strategy templates
│   ├── risk/               # Risk management
│   ├── macro/              # Macro economic data
│   ├── news/               # News & intelligence
│   ├── defi/               # DeFi tools
│   └── reports/            # Report generation
└── docs/
    ├── INSTALLATION.md
    ├── SKILL_GUIDE.md
    └── API_REFERENCE.md
```

## Quick Start

After installation, ask your agent:

> What crypto quantitative skills do you have?

The agent should list all installed skills and their capabilities.

### Example Queries

```
"What's the current BTC price?"
"Track whale movements for ETH"
"Backtest a grid strategy on BTC from 2024"
"Show me the Fear & Greed Index"
"Generate a daily crypto report"
```

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](./docs/CONTRIBUTING.md) for guidelines.

## License

MIT License - see [LICENSE](./LICENSE) for details.

## Acknowledgments

- Inspired by [OpenClaw-Medical-Skills](https://github.com/galenhuang/OpenClaw-Medical-Skills)
- Built for the [Clawdbot](https://github.com/clawdbot/clawdbot) ecosystem

---

**FourierAlpha** | Building the future of AI-powered quantitative trading
