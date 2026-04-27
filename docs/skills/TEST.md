# 智能推荐技能测试指南

## 🎯 测试目标

验证智能推荐功能的：
1. 参数自动补全
2. 多维评分算法
3. 组合优化逻辑
4. 输出格式

---

## 🚀 快速测试

### 前置条件

1. **获取 Token**
   ```bash
   # 如果是新用户，先访问服务端注册
   curl http://localhost:8000/api/register
   # 返回: {"token": "qc_xxx", ...}
   ```

2. **确保环境**
   ```bash
   cd /home/ubuntu/work/QuantClaw/skills/backtest-query
   python3 --version  # 确保 Python 3.7+
   ```

---

### 方法 1: 自动化测试脚本 ⭐推荐

运行完整测试套件（5个测试场景）：

```bash
cd /home/ubuntu/work/QuantClaw/skills/backtest-query

# 使用你的 token
./test_smart_recommend.sh qc_YOUR_TOKEN

# 或指定工作区
./test_smart_recommend.sh qc_YOUR_TOKEN /home/ubuntu/quantclaw
```

**测试内容**：
- ✅ 基础查询（验证 API 连通性）
- ✅ 快速推荐（探索模式，不获取详情）
- ✅ 指定币种推荐
- ✅ 完整推荐（含详情和记忆保存）
- ✅ JSON 格式输出

**预计耗时**：2-5 分钟

---

### 方法 2: 手动单步测试

#### 测试 1: 验证 API 连通性

```bash
# 查询可用币种
python3 query.py --token qc_YOUR_TOKEN --list-coins

# 查询可用策略类型
python3 query.py --token qc_YOUR_TOKEN --list-strategies

# 查询可用时间段
python3 query.py --token qc_YOUR_TOKEN --list-ai-times
```

**预期输出**：
```
可用币种:
  - BTC
  - ETH
  - SOL
  ...
```

---

#### 测试 2: 完全开放式推荐（参数自动补全）

```bash
python3 smart_recommend.py \
  --token qc_YOUR_TOKEN \
  --group-size 2 \
  --top-n 2 \
  --no-detail
```

**验证点**：
- ℹ️  应显示"未指定币种，使用默认主流币种: BTC, ETH, SOL"
- ℹ️  应显示"未指定策略类型，查询多种类型: 风霆/网格/鲲鹏"
- 🔍 应查询 3币种 × 3策略 = 9次
- 🏆 应返回 2个推荐组合

---

#### 测试 3: 指定币种推荐

```bash
python3 smart_recommend.py \
  --token qc_YOUR_TOKEN \
  --coins "BTC" \
  --year 2024 \
  --group-size 2 \
  --top-n 2 \
  --no-detail
```

**验证点**：
- 🔍 应只查询 BTC
- ℹ️  应显示"未指定策略类型，查询多种类型"
- 🔍 应查询 1币种 × 3策略 = 3次

---

#### 测试 4: 完整推荐（含详情）

```bash
python3 smart_recommend.py \
  --token qc_YOUR_TOKEN \
  --coins "BTC,ETH" \
  --strategy-type 11 \
  --year 2024 \
  --group-size 3 \
  --top-n 3 \
  --workspace /home/ubuntu/quantclaw \
  --save-memory
```

**验证点**：
- 📊 应显示"获取策略详情"
- 🏆 应返回 3个推荐组合
- 💾 应保存到 `workspace/memory/portfolio_history.md`

**检查记忆**：
```bash
cat /home/ubuntu/quantclaw/memory/portfolio_history.md
```

---

#### 测试 5: JSON 输出

```bash
python3 smart_recommend.py \
  --token qc_YOUR_TOKEN \
  --coins "BTC" \
  --year 2024 \
  --group-size 2 \
  --top-n 1 \
  --no-detail \
  --format json \
  --quiet
```

**验证点**：
- 输出应为有效 JSON
- 包含 `rank`, `score`, `strategies`, `correlation` 等字段

**解析 JSON**：
```bash
python3 smart_recommend.py ... | jq '.[] | {rank, score, correlation}'
```

---

## 🧪 测试场景

### 场景 1: 保守型投资者

```bash
python3 smart_recommend.py \
  --token qc_YOUR_TOKEN \
  --coins "BTC,ETH" \
  --min-sharpe 1.8 \
  --max-drawdown 15 \
  --max-correlation 0.4 \
  --group-size 3 \
  --workspace /home/ubuntu/quantclaw \
  --save-memory
```

**预期结果**：
- 推荐的组合夏普率 ≥ 1.8
- 回撤 ≤ 15%
- 相关性 ≤ 0.4

---

### 场景 2: 激进型投资者

```bash
python3 smart_recommend.py \
  --token qc_YOUR_TOKEN \
  --coins "BTC,SOL,BNB" \
  --max-drawdown 25 \
  --min-sharpe 1.0 \
  --sort 2 \
  --group-size 3 \
  --workspace /home/ubuntu/quantclaw \
  --save-memory
```

**预期结果**：
- 可接受更高回撤
- 追求更高收益

---

### 场景 3: 单币种多策略

```bash
python3 smart_recommend.py \
  --token qc_YOUR_TOKEN \
  --coins "BTC" \
  --direction long \
  --year 2024 \
  --group-size 3 \
  --workspace /home/ubuntu/quantclaw \
  --save-memory
```

**预期结果**：
- 只包含 BTC 策略
- 跨越多种策略类型（风霆/网格/鲲鹏）

---

## 🔍 验证评分算法

### 检查评分分布

```bash
python3 smart_recommend.py \
  --token qc_YOUR_TOKEN \
  --coins "BTC,ETH" \
  --year 2024 \
  --group-size 3 \
  --top-n 10 \
  --no-detail \
  | grep "评分:"
```

**验证点**：
- 评分应降序排列
- 评分范围 0-100
- 高分组合应同时满足：高夏普、低回撤、低相关性

---

### 检查相关性计算

查看推荐理由中的相关性说明：

```bash
python3 smart_recommend.py \
  --token qc_YOUR_TOKEN \
  --coins "BTC,ETH" \
  --year 2024 \
  --group-size 2 \
  --top-n 3 \
  --no-detail \
  | grep -A 5 "组合分析"
```

**验证点**：
- 相关性应在 -1 到 1 之间
- 低相关性（<0.5）的组合评分更高

---

## 📊 输出示例

### 文本格式

```
============================================================
🏆 推荐组合 #1 (评分: 78.5/100)
============================================================

📋 策略列表:
   1. BTC风霆做多v2
      币种: BTC | 年化: 32.5% | 夏普: 2.1 | 回撤: 11.2%
      Token: st_abc123

   2. ETH网格策略v3
      币种: ETH | 年化: 24.3% | 夏普: 1.9 | 回撤: 8.7%
      Token: st_def456

   3. BTC鲲鹏趋势v1
      币种: BTC | 年化: 28.1% | 夏普: 2.0 | 回撤: 10.5%
      Token: st_xyz789

📊 组合分析:
   相关性: 0.32 (越低越好，<0.5为佳)
   组合夏普: 2.00
   组合回撤: 10.13%
   胜率: 65.33%
   回撤重叠: 22.5%

💡 推荐理由: 相关性较低(0.32)、高夏普率(2.00)、低回撤(10.1%)

🔧 创建命令:
   python query.py --token <token> --create-group --group-name "组合1" --strategy-tokens "st_abc123,st_def456,st_xyz789"
============================================================
```

### JSON 格式

```json
[
  {
    "rank": 1,
    "score": 78.5,
    "strategies": [
      {
        "name": "BTC风霆做多v2",
        "coin": "BTC",
        "year_rate": 32.5,
        "sharp_rate": 2.1,
        "max_loss": 11.2,
        "strategy_token": "st_abc123"
      }
    ],
    "correlation": 0.32,
    "portfolio_risk": {
      "sharpe_ratio": 2.0,
      "max_drawdown": 10.13,
      "win_rate": 65.33
    },
    "drawdown_overlap": 22.5,
    "reason": "相关性较低(0.32)、高夏普率(2.00)、低回撤(10.1%)"
  }
]
```

---

## 🐛 常见问题

### 1. Token 无效

**错误**：`❌ Token 验证失败`

**解决**：
```bash
# 重新注册或检查 token
curl http://localhost:8000/api/register
```

---

### 2. 未找到策略

**错误**：`❌ 未找到符合条件的策略`

**原因**：
- 筛选条件过严（min_sharpe 太高，max_drawdown 太低）
- 指定的币种/策略类型没有数据
- 年份或时间范围不正确

**解决**：
```bash
# 放宽筛选条件或使用默认参数
python3 smart_recommend.py --token qc_xxx --no-detail
```

---

### 3. 组合数量不足

**错误**：`⚠️  策略数量(5)不足以组成3个策略的组合`

**解决**：
```bash
# 减小 group_size
python3 smart_recommend.py --token qc_xxx --group-size 2
```

---

### 4. 获取详情失败

**错误**：`⚠️  策略 xxx 详情获取失败`

**原因**：API 限流或网络问题

**解决**：
```bash
# 使用快速模式（不获取详情）
python3 smart_recommend.py --token qc_xxx --no-detail
```

---

## 📝 测试清单

- [ ] API 连通性测试
- [ ] 参数自动补全（完全开放式）
- [ ] 指定币种推荐
- [ ] 指定策略类型推荐
- [ ] 筛选条件（min_sharpe, max_drawdown）
- [ ] 评分算法验证
- [ ] 相关性计算验证
- [ ] 回撤错位分析
- [ ] JSON 输出格式
- [ ] 记忆保存功能

---

## 🎉 完成测试后

1. 查看记忆文件：
   ```bash
   cat /home/ubuntu/quantclaw/memory/portfolio_history.md
   ```

2. 检查 Git 状态：
   ```bash
   cd /home/ubuntu/work/QuantClaw
   git log --oneline -5
   ```

3. 报告测试结果 ✅

---

**相关文档**：
- 算法详解：`docs/skills/SMART_RECOMMEND_ALGORITHM.md`
- 使用说明：`skills/backtest-query/skills/smart_recommend.md`
- 工作流指南：`docs/skills/BACKTEST_QUERY_WORKFLOW.md`
