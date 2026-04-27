# 智能推荐（跨策略类型）

## 适用场景

**核心原则**：任何需要"组合推荐"但**参数不完整**的场景

- 用户未指定具体策略类型
- 用户指定了策略类型但未明确版本/时间/排序等参数
- 需要多币种、多策略类型的组合
- 需要根据行情或风险偏好推荐
- 任何参数模糊或需要"智能选择"的组合请求

## 典型问题

### 跨币种/跨策略类型
- "给我推荐BTC和ETH的组合"
- "BTC、ETH、SOL怎么组合？"
- "震荡行情下的策略组合"
- "保守型的投资组合"

### 单币种但参数不完整
- "BTC做多的组合"（未指定策略类型）
- "BTC风霆的组合"（未指定版本/时间）
- "ETH网格比较好的组合"（"比较好"表示需要智能推荐）
- "SOL做多推荐"（需要推荐）

### 与高级查询的区别
- ✅ 智能推荐："BTC风霆的组合" → 自动推荐最优策略并组合
- ❌ 高级查询："BTC风霆有哪些策略？" → 只列出策略，不推荐组合

---

## 🚀 使用方法

一键完成：查询 → 分析 → 推荐 → 记忆

```bash
python skills/backtest-query/smart_recommend.py \
  --token <用户token> \
  --coins "BTC,ETH,SOL" \
  --year 2024 \
  --workspace <工作区路径> \
  --save-memory
```

---

## 📋 参数说明

| 参数 | 说明 | 默认值 | 必填 |
|-----|-----|-------|-----|
| `--token` | 用户 token | - | ✅ |
| `--coins` | 币种列表，逗号分隔 | **接口前3个** | ❌ 可选 |
| `--strategy-type` | 策略类型 | **接口前3个** | ❌ 可选 |
| `--workspace` | 工作区路径（保存记忆用） | - | 推荐 |
| `--ai-time-id` | 时间ID（**推荐**） | **接口第1个** | ❌ 可选 |
| `--year` | 年份（优先级低于 ai-time-id） | - | ❌ 可选 |
| `--direction` | 方向 long/short | - | - |

**参数默认值说明**（动态获取）：
- **币种**：从接口获取前3个币种作为默认
- **策略类型**：从接口获取前3个策略类型作为默认
- **时间**：从接口获取第1个时间ID作为默认
- **优先级**：`--ai-time-id` > `--year`
- **容错**：接口失败时使用内置默认值
| `--group-size` | 组合大小 | 3 | - |
| `--top-n` | 返回推荐数量 | 5 | - |
| `--min-sharpe` | 最小夏普率（筛选） | - | - |
| `--max-drawdown` | 最大回撤（筛选） | - | - |
| `--max-correlation` | 最大相关性 | 0.5 | - |
| `--save-memory` | 保存到记忆 | false | - |
| `--format` | 输出格式 json/text | text | - |
| `--no-detail` | 快速模式（不获取详情）| false | - |

---

## 📝 使用示例

### 1. 指定币种的保守型组合
```bash
python smart_recommend.py \
  --token qc_xxx \
  --coins "BTC,ETH" \
  --year 2024 \
  --min-sharpe 1.8 \
  --max-drawdown 15 \
  --max-correlation 0.4 \
  --workspace ~/clawd-qc-xxx \
  --save-memory
```

### 2. 完全开放式推荐（探索模式）
```bash
# 不指定币种和策略类型，自动使用默认配置
python smart_recommend.py \
  --token qc_xxx \
  --year 2024 \
  --workspace ~/clawd-qc-xxx \
  --save-memory

# 等同于：
# --coins "BTC,ETH,SOL"
# --strategy-type 11,7,1（风霆、网格、鲲鹏）
```

### 3. 指定策略类型的组合
```bash
# 只推荐风霆策略的组合
python smart_recommend.py \
  --token qc_xxx \
  --strategy-type 11 \
  --year 2024 \
  --workspace ~/clawd-qc-xxx \
  --save-memory
```

### 4. 单币种多策略类型
```bash
# BTC的多策略组合
python smart_recommend.py \
  --token qc_xxx \
  --coins "BTC" \
  --year 2024 \
  --workspace ~/clawd-qc-xxx \
  --save-memory
```

### 5. 快速查看（不获取详情）
```bash
python smart_recommend.py \
  --token qc_xxx \
  --year 2024 \
  --no-detail \
  --format json
```

---

## 🎯 风险偏好参数配置

| 风险偏好 | 参数配置 |
|---------|---------|
| 保守/稳健 | `--max-drawdown 12 --min-sharpe 2.0 --max-correlation 0.4` |
| 平衡 | `--max-drawdown 15 --min-sharpe 1.5 --max-correlation 0.5` |
| 进取/激进 | `--max-drawdown 20 --min-sharpe 1.2 --max-correlation 0.6` |

---

## 📊 输出说明

智能推荐会显示：
- 📋 策略列表（币种、年化、夏普、回撤）
- 📊 组合分析（相关性、组合夏普、回撤重叠）
- 💡 推荐理由
- 🔧 创建命令（一键复制）

并自动保存到 `workspace/memory/portfolio_history.md`

---

## 🔄 工作原理

```
1. 根据币种查询回测策略
         ↓
2. 计算策略间的相关性
         ↓
3. 分析回撤重叠情况
         ↓
4. 综合评分排序
         ↓
5. 推荐低相关性、高夏普、风险互补的组合
         ↓
6. 保存到记忆文件（如启用 --save-memory）
```

---

## ⚠️ 注意事项

- 自动跨策略类型选择（马丁、网格、趋势）
- 优先选择相关性低的策略组合
- 需要获取净值曲线数据，首次查询较慢
- 使用 `--no-detail` 可快速预览（不含详细分析）

**重要**：
- 只要用户问的是"组合"或"推荐"，且参数不完整，就应该用智能推荐
- 不仅仅是跨币种才用，单币种、单策略类型但参数不完整也要用
- 参数完整性判断：币种、策略类型、版本、方向、时间范围是否全部明确

---

## 📖 详细文档

**算法详解**：`docs/skills/SMART_RECOMMEND_ALGORITHM.md`
- 完整的评分公式和数学原理
- 参数补全逻辑
- 性能优化策略
- 使用示例和场景分析
