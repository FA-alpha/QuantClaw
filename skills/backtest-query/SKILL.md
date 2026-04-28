# 回测数据查询与策略组合

查询 AI 回测数据，智能推荐策略组合，创建策略组。

---

## 🎯 主要功能

1. **智能推荐** - 根据需求推荐优质策略组合
2. **创建策略组** - 将策略组合成一个策略组

---

## 📝 使用流程

### 步骤 1：判断用户意图

**创建关键词**：创建、建立、建个、生成

- 包含 → 推荐后**直接创建**
- 不包含 → 推荐后**询问确认**

### 步骤 2：执行推荐

```bash
cd /home/ubuntu/work/QuantClaw
python3 skills/backtest-query/smart_group_recommend.py \
  --query "用户需求描述" \
  --output /tmp/recommend.json
```

**常用参数**：

**查询范围参数**：
- `--coins "BTC,ETH,SOL"` - 币种列表（逗号分隔）
- `--strategy-types "1,7,11"` - 策略类型（1=风霆 7=网格 11=鲲鹏）
- `--directions "long,short"` - 方向（long=做多 short=做空）
- `--search-pcts "80,100,120"` - 网格比例（仅网格策略）
- `--ai-time-ids "5,6"` - AI回测时间ID
- `--versions "v1,v2"` - 策略版本
- `--search-recommand-type 1` - 推荐类型（1=推荐 2=交易中）

**筛选条件参数**：
- `--min-total-win-rate 60` - 最小总胜率（%）
- `--min-recent-profit-rate 10` - 最小近期收益率（%）
- `--max-recent-drawdown 15` - 最大近期回撤（%）
- `--min-trade-count 50` - 最小交易次数
- `--min-stability 0.8` - 最小稳定性（近期/总体）

**排序和组合参数**：
- `--top-per-group 5` - 每种排序方式取几个策略（默认5）
- `--sort-methods "sharpe,return,drawdown"` - 排序方式（可选：sharpe,return,drawdown,win_rate,stability,score）
- `--api-sort 2` - API排序（1=最新 2=收益 3=夏普 4=回撤，默认2）
- `--max-combinations 10` - 最多推荐几个组合（默认10）

### 步骤 3：读取推荐结果

JSON 文件包含：
- `combinations[0]` - 最优组合
- `combinations[0]['strategies'][*]['strategy_token']` - token 列表
- `combinations[0]['score']` - 评分
- `combinations[0]['expected_return']` - 预期收益

### 步骤 4：创建策略组

从 JSON 提取 token 列表，执行创建：

```bash
python3 skills/backtest-query/query.py \
  --create-group \
  --group-name "组合名称" \
  --strategy-tokens "token1,token2,token3"
```

---

## 💡 完整示例

**用户**："帮我找 BTC 和 ETH 的多空策略并创建组合"

**执行**：
```bash
# 1. 推荐（轮询查询多个组合）
cd /home/ubuntu/work/QuantClaw
python3 skills/backtest-query/smart_group_recommend.py \
  --query "BTC和ETH的多空策略" \
  --coins "BTC,ETH" \
  --directions "long,short" \
  --min-total-win-rate 60 \
  --max-recent-drawdown 15 \
  --output /tmp/rec.json

# 2. 读取 JSON 提取 tokens
# (用 read 或 exec cat + jq)

# 3. 创建
python3 skills/backtest-query/query.py \
  --create-group \
  --group-name "BTC优质组合_$(date +%Y%m%d)" \
  --strategy-tokens "提取的tokens"
```

**回复用户**：
```
✅ 策略组创建成功！

组合名称: BTC优质组合_20260428
策略组 ID: 12345
包含策略: 3 个
预期收益: 95.2%
组合回撤: 11.5%

策略列表:
1. BTC / 鲲鹏_做多 (年化102%, 夏普2.35)
2. BTC / 风霆_做空 (年化88%, 夏普2.10)
3. BTC / 网格_震荡 (年化76%, 夏普2.50)
```

---

## 🔑 关键信息

### 典型场景
- **对冲组合** - 做多 + 做空
- **币种分散** - BTC + ETH + SOL
- **策略混合** - 网格 + 趋势

### 策略类型
- `1`: 风霆（马丁策略）
- `7`: 网格策略
- `11`: 鲲鹏（趋势策略）
- 更多类型可通过 `DefaultParams.get_strategy_types()` 获取

### 参数取值范围获取

在 Python 脚本中可以获取可用参数：

```python
from defaults import DefaultParams

manager = DefaultParams(token)

# 获取可用币种
coins = manager.get_coins()  # 所有币种
crypto_coins = manager.get_coins(coin_type="CRYPTO")  # 仅虚拟币

# 获取策略类型
strategy_types = manager.get_strategy_types()  # [1, 7, 11, ...]

# 获取时间ID
time_ids = manager.get_ai_time_ids()  # ["5", "6", ...]

# 获取网格比例
btc_pcts = manager.get_grid_pcts("BTC")  # ['10', '20', ..., '120']
eth_pcts = manager.get_grid_pcts("ETH")  # ['60', '80', ..., '140']
```

### 轮询查询机制

当传入多个参数值时，系统会轮询查询所有组合并去重合并：

**示例**：
```bash
--coins "BTC,ETH" --directions "long,short" --search-pcts "80,100"
# 将执行 2×2×2 = 8 次查询并去重
```
