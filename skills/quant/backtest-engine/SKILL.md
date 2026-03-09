# Backtest Engine

Historical backtesting for trading strategies with comprehensive performance metrics.

## Description

Run backtests on trading strategies using historical price data. Supports multiple strategy types, parameter optimization, and detailed performance analysis.

## Trigger Conditions

- "Backtest [strategy] on [coin]"
- "回测 [策略]"
- "Test this strategy historically"
- "What would have happened if..."
- When user wants to evaluate a trading strategy

## Capabilities

1. **Strategy Backtesting**
   - Grid trading
   - Martingale
   - DCA (Dollar Cost Averaging)
   - Trend following
   - Mean reversion
   - Custom strategies

2. **Performance Metrics**
   - Total return (%)
   - Sharpe ratio
   - Max drawdown
   - Win rate
   - Profit factor
   - Average trade duration

3. **Parameter Optimization**
   - Grid search
   - Random search
   - Walk-forward optimization

4. **Visualization**
   - Equity curve
   - Drawdown chart
   - Trade distribution
   - Monthly returns heatmap

## Input Parameters

```yaml
strategy: grid_trading
symbol: BTC/USDT
start_date: 2024-01-01
end_date: 2024-12-31
initial_capital: 10000
leverage: 3

# Strategy-specific params
grid_size: 20
price_range: [40000, 80000]
```

## Usage Examples

**User:** Backtest a grid strategy on BTC for 2024

**Agent:**
```
📊 Backtest Results: Grid Trading on BTC/USDT

📅 Period: 2024-01-01 to 2024-12-31
💰 Initial Capital: $10,000
⚡ Leverage: 3x

📈 Performance:
- Total Return: +156.8%
- Sharpe Ratio: 2.34
- Max Drawdown: -23.5%
- Win Rate: 68.2%
- Total Trades: 847

📉 Risk Metrics:
- Sortino Ratio: 3.12
- Calmar Ratio: 6.67
- Profit Factor: 2.45

💡 Summary: Strong performance in volatile market. 
Grid captured +847 trades with 68% win rate.
Drawdown within acceptable range for 3x leverage.
```

**User:** Optimize the grid parameters

**Agent:**
```
🔧 Parameter Optimization Results:

Best Parameters Found:
- Grid Size: 25 (was 20)
- Price Range: [38000, 82000]
- Take Profit: 1.8%

Performance Improvement:
- Return: 156.8% → 178.2% (+21.4%)
- Sharpe: 2.34 → 2.67
- Max DD: -23.5% → -21.2%
```

## Output Format

- JSON report with all metrics
- CSV trade log
- PNG/HTML charts (optional)

## Dependencies

- Historical price data (via exchange APIs or data providers)
- pandas, numpy for calculations
- matplotlib/plotly for visualization

## Notes

- Past performance doesn't guarantee future results
- Backtests don't account for slippage and fees accurately
- Use walk-forward validation for robust results
- Consider market regime changes
