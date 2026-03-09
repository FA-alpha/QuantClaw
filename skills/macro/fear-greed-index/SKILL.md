# Fear & Greed Index

Crypto market sentiment indicator tracking fear and greed levels.

## Description

Monitor the Crypto Fear & Greed Index to gauge market sentiment. The index ranges from 0 (Extreme Fear) to 100 (Extreme Greed).

## Trigger Conditions

- "Fear and greed index"
- "Market sentiment"
- "恐惧贪婪指数"
- "Is the market fearful/greedy?"
- When user asks about market mood/sentiment

## Capabilities

1. **Current Index**
   - Real-time index value
   - Sentiment classification
   - Timestamp

2. **Historical Data**
   - Daily history
   - Weekly/monthly trends
   - Extreme value alerts

3. **Analysis**
   - Correlation with price
   - Contrarian signals
   - Trend identification

## Index Levels

| Range | Classification | Signal |
|-------|---------------|--------|
| 0-24 | Extreme Fear | 🟢 Potential buy |
| 25-44 | Fear | 🟢 Accumulate |
| 45-55 | Neutral | ⚪ Hold |
| 56-75 | Greed | 🟡 Caution |
| 76-100 | Extreme Greed | 🔴 Potential sell |

## Data Components

The index is calculated from:
- **Volatility** (25%): Current vs 30/90-day average
- **Market Momentum** (25%): Volume vs average
- **Social Media** (15%): Twitter/Reddit sentiment
- **Surveys** (15%): Crypto polling
- **Dominance** (10%): BTC vs altcoin dominance
- **Trends** (10%): Google search trends

## Usage Examples

**User:** What's the current fear greed index?

**Agent:**
```
😰 Crypto Fear & Greed Index

Current: 23 - Extreme Fear

📊 Components:
- Volatility: 🔴 High (score: 18)
- Momentum: 🔴 Weak (score: 22)
- Social: 🟡 Neutral (score: 45)
- Dominance: 🟢 BTC Strong (score: 35)
- Trends: 🔴 Low Interest (score: 15)

📅 Historical:
- Yesterday: 28 (Fear)
- Last Week: 45 (Neutral)
- Last Month: 72 (Greed)

💡 Insight: Market in extreme fear. Historically, 
buying during extreme fear (< 25) has yielded 
avg +34% returns over 90 days.
```

**User:** Show fear greed history for the past month

**Agent:**
```
📈 Fear & Greed Index - 30 Day History

Week 1: Avg 68 (Greed)
█████████████████░░░

Week 2: Avg 52 (Neutral)
████████████░░░░░░░░

Week 3: Avg 35 (Fear)
████████░░░░░░░░░░░░

Week 4: Avg 23 (Extreme Fear)
█████░░░░░░░░░░░░░░░

📉 Trend: Sharp decline from greed to fear
🔔 Signal: Potential accumulation zone

Historical Performance after Extreme Fear:
- 30 days later: +18% avg
- 90 days later: +34% avg
- 180 days later: +67% avg
```

## Data Source

- Alternative.me Fear & Greed Index API
- Free, no API key required
- Updates daily at 00:00 UTC

## Trading Implications

### Extreme Fear (0-24)
- Market panic = potential opportunity
- "Be greedy when others are fearful"
- Consider DCA buying

### Extreme Greed (76-100)
- Market euphoria = potential top
- "Be fearful when others are greedy"
- Consider taking profits

## Notes

- Index is sentiment-based, not predictive
- Use with other indicators, not alone
- Past correlations may not repeat
- Best used for medium-term decisions
