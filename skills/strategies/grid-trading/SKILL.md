# Grid Trading Strategy

Automated grid trading for capturing profits in ranging markets.

## Description

Deploy grid trading bots that automatically buy low and sell high within a defined price range. Ideal for sideways/volatile markets.

## Trigger Conditions

- "Set up grid trading"
- "网格交易"
- "Deploy grid bot"
- "Create buy/sell grid"
- When user wants automated range trading

## Capabilities

1. **Grid Configuration**
   - Arithmetic grids (equal spacing)
   - Geometric grids (percentage spacing)
   - Custom grid levels

2. **Order Management**
   - Automatic order placement
   - Order refresh on fill
   - Position tracking

3. **Risk Controls**
   - Stop loss trigger
   - Take profit trigger
   - Max position limit
   - Daily loss limit

4. **Analytics**
   - Grid profit tracking
   - Fill rate analysis
   - APR calculation

## Parameters

| Parameter | Description | Example |
|-----------|-------------|---------|
| symbol | Trading pair | BTC/USDT |
| upper_price | Grid ceiling | 70,000 |
| lower_price | Grid floor | 60,000 |
| grid_count | Number of grids | 20 |
| investment | Total capital | $10,000 |
| leverage | Leverage (optional) | 3x |

## Usage Examples

**User:** Set up a BTC grid from 60k to 70k with 20 grids

**Agent:**
```
📊 Grid Trading Setup

Symbol: BTC/USDT
Price Range: $60,000 - $70,000
Grids: 20
Grid Spacing: $500 (0.77%)
Investment: $10,000

📋 Grid Levels:
Buy Orders:
- $60,000: 0.0083 BTC
- $60,500: 0.0082 BTC
- $61,000: 0.0082 BTC
... (17 more levels)

Sell Orders:
- $69,500: 0.0072 BTC
- $70,000: 0.0071 BTC

💰 Expected Profit per Grid: $8.25 (0.16%)
📈 If all grids complete: ~$165 profit

⚠️ Risk: If price drops below $60,000, all capital will be in BTC position.

Confirm to deploy? [Y/N]
```

**User:** Show my grid performance

**Agent:**
```
📊 Grid Performance (Last 7 Days)

Active Grids: 18/20
Completed Cycles: 47
Total Profit: $387.50

📈 Metrics:
- Grid APR: 201.5%
- Fill Rate: 89%
- Avg Hold Time: 4.2 hours

💰 Profit Breakdown:
- Realized: $387.50
- Unrealized: -$45.20
- Net: $342.30

📍 Current Position:
- BTC: 0.125 ($8,437)
- USDT: $1,563
```

## Strategy Variations

### Neutral Grid
- Equal buy/sell grids
- Best for ranging markets

### Long Bias Grid
- More buy levels below current price
- Bullish outlook

### Short Bias Grid  
- More sell levels above current price
- Bearish outlook

### Infinity Grid
- No upper limit
- Never fully exits position

## Risk Warnings

⚠️ **Key Risks:**
- Price breaking out of range = holding losing position
- High volatility can trigger stop loss
- Funding fees accumulate in futures
- Liquidity risk in low-volume pairs

## Best Practices

1. Choose pairs with high volatility but clear range
2. Set stop loss at 1.5-2x grid range below
3. Don't use >3x leverage for grid trading
4. Monitor exchange rate limits
5. Have capital reserve for range expansion

## Dependencies

- Exchange API access
- Real-time price feed
- Order management system
