# AGENTS.md - QuantClaw 工作区

## 项目结构
- `strategies/` - 交易策略代码与笔记
- `data/` - 市场数据与分析文件
- `backtests/` - 回测结果与报告
- `skills/` - 量化技能模块（链接自 QuantClaw）
- `analysis/` - 深度分析报告

## 🔑 认证信息

**用户 Token** 存储在 `users.json` 文件中，读取方式：
```bash
TOKEN=$(cat users.json | jq -r '.fourieralpha.usertoken')
```

这个 token 用于：
- 查询策略列表
- 查询回测结果
- 启动回测任务

---

## 📋 查询策略列表

当用户需要查找策略ID时，使用以下命令：

**方法1：使用 Python 脚本（推荐）**
```bash
python3 query_strategies.py
```

**方法2：使用 Shell 脚本**
```bash
./query_strategies.sh
```

**方法3：直接调用 API**
```bash
TOKEN=$(cat users.json | jq -r '.fourieralpha.usertoken')
curl -s -X POST "https://www.fourieralpha.com/Mobile/Strategy/lists" \
  -d "usertoken=$TOKEN" \
  -d "page=1" \
  -d "limit=100" | python3 -c "
import json, sys
data = json.load(sys.stdin)
info = data.get('info', [])
print(f'总策略数: {len(info)}\n')
for s in info:
    print(f\"ID: {s.get('id')} | {s.get('name')} | {s.get('coin')} {s.get('direction')}\")
"
```

**触发关键词**：
- "有哪些策略"
- "什么策略"
- "所有策略"
- "策略列表"
- "最新添加的策略"
- "我的策略"

**重要**：当用户提到"最新添加的X个策略"、"我的X个策略"等，**必须先查询策略列表**，找出符合条件的策略ID，然后再执行回测。

---

## 📝 多策略回测命令格式（必须遵守）

**推荐脚本：backtest_helper.py（位置：/home/ubuntu/QuantClaw/skills/start-backtest/）**

这个脚本使用正确的 API 参数格式，简单可靠。

**用法：**
```bash
# 先读取 token
TOKEN=$(cat users.json | jq -r '.fourieralpha.usertoken')

# 执行回测
python3 backtest_helper.py "$TOKEN" <策略IDs> [选项]
```

**示例：**

1. 独占模式（默认）：
```bash
TOKEN=$(cat users.json | jq -r '.fourieralpha.usertoken')
python3 backtest_helper.py "$TOKEN" "4619,4682,4681" \
  --start 2025-03-24 --end 2025-04-23
```

2. 共享模式（平分）：
```bash
TOKEN=$(cat users.json | jq -r '.fourieralpha.usertoken')
python3 backtest_helper.py "$TOKEN" "4619,4682,4681" \
  --shared \
  --allocation 33.33,33.33,33.34 \
  --start 2025-03-24 --end 2025-04-23
```

3. 共享模式（自定义分配）：
```bash
TOKEN=$(cat users.json | jq -r '.fourieralpha.usertoken')
python3 backtest_helper.py "$TOKEN" "4619,4682,4681" \
  --shared \
  --allocation 40,30,30 \
  --start 2024-01-01 --end 2024-12-31 \
  --balance 20000
```

**可用选项：**
- `--shared` - 启用共享保证金模式
- `--allocation 30,30,40` - 共享模式分配比例
- `--start YYYY-MM-DD` - 开始日期
- `--end YYYY-MM-DD` - 结束日期
- `--balance 10000` - 初始保证金（默认10000）

**强制规则：多策略回测必须使用 backtest_helper.py 脚本！**

该脚本使用正确的 API 参数格式：
```json
{
  "date_lists": [{"bgn_date": "2025-03-24", "end_date": "2025-04-23"}],
  "margin_mode_config": {
    "is_shared_margin": true,
    "global_margin_limit": 10000,
    "strategy_margin_limit": {
      "4619": "3333",
      "4682": "3333",
      "4681": "3334"
    }
  }
}
```

**❌ 不要使用旧的 curl 命令格式**（会导致独占模式）：
```bash
# 错误的格式（不要使用！）
curl -d "margin_mode=shared" -d "margin_ratio=33.33,33.33,33.34"
```

---

## ⚠️ 多策略回测强制流程（最重要）

**当检测到以下情况时，必须先询问用户，不能直接执行回测：**
- 用户提到"策略组"
- 用户要回测多个策略
- 用户要同时对多个策略进行操作

### 强制执行步骤：

**步骤0：如果用户没有指定策略ID，先查询策略列表**

当用户说"最新添加的X个策略"、"我的X个策略"等时：
```bash
python3 query_strategies.py
```
筛选出符合条件的策略ID，然后进入步骤1。

**步骤1：检测到多策略回测需求后，立即询问保证金模式**

```
您要对多个策略进行回测，请先选择保证金模式：

1️⃣ **独占模式** - 每个策略独立使用保证金，互不影响
2️⃣ **共享模式** - 多个策略共享同一保证金池

请回复 1 或 2
```

**步骤2：等待用户回复**

- 用户回复 1 → 使用独占模式，继续执行回测
- 用户回复 2 → 进入步骤3

**步骤3：如果用户选择共享模式，询问保证金分配比例**

```
请为 3 个策略分配保证金比例（总和100%）：

| # | 策略 |
|---|------|
| 1 | XXX-策略 |
| 2 | YYY-策略 |
| 3 | ZZZ-策略 |

格式如：**40,30,30**

或回复 **平均** 自动平均分配（每个约33.33%）
```

**步骤4：执行回测**

先从 `users.json` 读取 token，然后使用 backtest_helper.py 脚本执行回测：
```bash
TOKEN=$(cat users.json | jq -r '.fourieralpha.usertoken')
python3 backtest_helper.py "$TOKEN" "策略IDs" [选项]
```

---

## 常用策略ID

### 最新3个风霆V4.2策略
| ID | 策略名 | 币种 | 方向 |
|----|--------|------|------|
| 4619 | SOL-风霆V4.2-做空 | SOL | 做空 |
| 4682 | BTC-风霆V4.2-做空 | BTC | 做空 |
| 4681 | ETH-风霆V4.2-做空 | ETH | 做空 |

### 策略组12333（6个策略）
4300,4679,4680,4619,4681,4682

---

## API 端点参考

### FourierAlpha Mobile API
- 基础 URL: `https://www.fourieralpha.com/Mobile`
- 认证: 通过 `usertoken` 参数（从 `users.json` 读取）

**主要端点：**

| 端点 | 说明 |
|------|------|
| `/Strategy/lists` | 查询策略列表 |
| `/Strategy/group_lists` | 查询策略组列表 |
| `/Backtrack/apply_do` | 启动回测 |
| `/Backtrack/lists` | 查询回测结果 |

**重要提示：**
- 回测时必须使用 `date_lists` JSON 数组格式
- 保证金配置必须使用 `margin_mode_config` JSON 对象
- 不要使用旧的 `bgn_date`/`end_date` 和 `margin_mode`/`margin_ratio` 参数

---

## 工作流程示例

**完整流程：用户回测最新策略**

1. **用户输入**："帮我回测我的最新添加的3个风霆V4.2策略，用共享模式，平分保证金，最近30天"

2. **步骤0 - 查询策略**：
   ```bash
   python3 query_strategies.py
   ```
   筛选出最新的3个风霆V4.2策略：4619, 4682, 4681

3. **步骤1 - 确认策略**：
   ```
   我找到了您的最新3个风霆V4.2策略：
   - SOL-风霆V4.2-做空 (ID: 4619)
   - BTC-风霆V4.2-做空 (ID: 4682)
   - ETH-风霆V4.2-做空 (ID: 4681)
   
   用共享模式回测，平分保证金，最近30天，对吗？
   ```

4. **步骤2 - 执行回测**：
   ```bash
   TOKEN=$(cat users.json | jq -r '.fourieralpha.usertoken')
   python3 backtest_helper.py "$TOKEN" "4619,4682,4681" \
     --shared \
     --allocation 33.33,33.33,33.34 \
     --start $(date -d "30 days ago" +%Y-%m-%d) \
     --end $(date +%Y-%m-%d)
   ```

5. **返回结果**：
   ```
   ✅ 回测已提交
   回测ID: 5655
   策略: SOL/BTC/ETH 风霆V4.2-做空
   保证金模式: 共享（10000）
   分配: 平均（各33.33%）
   ```
