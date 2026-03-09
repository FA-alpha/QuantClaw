# Crypto Price

Real-time cryptocurrency price queries with multi-source aggregation.

## Description

Query real-time prices for any cryptocurrency from multiple sources including CoinGecko, CoinMarketCap, and major exchanges.

## Trigger Conditions

- "What's the price of [coin]?"
- "BTC/ETH/SOL price"
- "查询 [币种] 价格"
- "Current market price"
- When user asks about crypto prices or market data

## Capabilities

1. **Real-time Prices**
   - Current price in USD/USDT
   - 24h change percentage
   - 24h high/low
   - Trading volume

2. **Multi-coin Query**
   - Query multiple coins at once
   - Price comparison across exchanges

3. **Price Alerts**
   - Set price alerts
   - Notify when price reaches target

## Data Sources

- CoinGecko API (free, no key required)
- CoinMarketCap API (requires key for advanced features)
- Exchange APIs (Binance, OKX, etc.)

## Usage Examples

**User:** What's the current BTC price?

**Agent:** 
```
📊 BTC/USDT
💰 $67,500
📈 24h: +2.3%
📊 24h Volume: $25.8B
🔺 High: $68,200
🔻 Low: $65,800
```

**User:** Compare ETH price across exchanges

**Agent:**
```
ETH Price Comparison:
- Binance: $3,450.20
- OKX: $3,449.85
- Coinbase: $3,451.10
- Gate: $3,450.50
```

## Dependencies

- Python requests library
- API Keys (optional for advanced features)

## Notes

- Free tier APIs have rate limits
- Prices may have slight delays (1-5 seconds)
- Always verify critical trades with exchange directly
