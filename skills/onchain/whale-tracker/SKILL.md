# Whale Tracker

Monitor large wallet movements and smart money activities on-chain.

## Description

Track whale wallets, detect large transfers, and analyze accumulation/distribution patterns across major blockchains.

## Trigger Conditions

- "Track whale movements"
- "Large transfers for [coin]"
- "鲸鱼追踪"
- "Smart money activities"
- "Exchange inflow/outflow"
- When user asks about large wallet activities

## Capabilities

1. **Whale Wallet Monitoring**
   - Track top 100 wallets by holdings
   - Real-time large transfer alerts
   - Wallet labeling (exchanges, funds, whales)

2. **Exchange Flow Analysis**
   - Net inflow/outflow to exchanges
   - Accumulation vs distribution signals
   - Exchange reserve tracking

3. **Smart Money Tracking**
   - VC wallet movements
   - Market maker activities
   - Early investor behavior

4. **Alert System**
   - Large transfer notifications
   - Unusual activity detection
   - Custom threshold alerts

## Data Sources

- Arkham Intelligence
- Nansen
- Whale Alert
- Dune Analytics
- On-chain node queries

## Usage Examples

**User:** Track BTC whale movements today

**Agent:**
```
🐋 BTC Whale Activity (24h)

📥 Exchange Inflow: 12,500 BTC ($845M)
📤 Exchange Outflow: 18,200 BTC ($1.23B)
📊 Net Flow: -5,700 BTC (Accumulation signal)

🔔 Large Transfers:
- 2,000 BTC moved from Binance to cold wallet
- 1,500 BTC transferred between unknown wallets
- 800 BTC deposited to Coinbase

📈 30-day Trend: Whales accumulating (+27,000 BTC)
```

**User:** Who are the top ETH holders?

**Agent:**
```
🏆 Top 10 ETH Holders:
1. Beacon Chain Deposit: 34.2M ETH
2. Binance: 4.8M ETH
3. Wrapped ETH: 3.2M ETH
4. Kraken: 1.9M ETH
5. Unknown Whale #1: 1.2M ETH
...
```

## Risk Indicators

- 🟢 Accumulation: Net outflow from exchanges
- 🟡 Neutral: Balanced flow
- 🔴 Distribution: Net inflow to exchanges

## Dependencies

- API keys for premium data sources
- Web scraping for public data

## Notes

- On-chain data has 1-3 block confirmation delay
- Some wallets may be mislabeled
- Large transfers don't always indicate selling intent
