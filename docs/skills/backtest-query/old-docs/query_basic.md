# 基础查询

## 适用场景

- 查询回测列表
- 查看策略详情
- 获取策略类型/币种/时间列表

## 典型问题

- "查询BTC做多的策略"
- "2024年夏普率最高的策略"
- "有哪些可用的策略类型？"
- "查看策略12345的详情"

---

## 🔍 查询命令

```bash
python skills/backtest-query/query.py --token <token> [选项]
```

---

## 📋 必填参数（查询列表时）

| 参数 | 说明 | 示例 |
|-----|-----|-----|
| `--token` | 用户 token | `--token qc_xxx` |
| `--coin` | 币种（多选逗号分割） | `--coin BTC,ETH` |
| `--sort` | 排序方式 | `--sort 2` |
| `--strategy-type` | 策略类型 ID | `--strategy-type 1` |

**排序方式**：
- 1 = 最新
- 2 = 收益率最高
- 3 = 夏普率最高
- 4 = 回撤率最低

---

## 🔧 常用功能

### 1. 列出策略类型

```bash
python query.py --token xxx --list-strategies
```

**返回示例**：
```
AI 回测策略:
  [1] 风霆现货 (id: 1)
      - 风霆现货 v1.0 (版本: 1.0, 杠杆: 1)
  [7] 星辰 (id: 7)
      - 星辰 v1.0 (版本: 1.0, 杠杆: 1)
  [3] 鲲鹏V1 (id: 3)
```

### 2. 列出币种

```bash
python query.py --token xxx --list-coins
```

### 3. 列出AI回测时间

```bash
python query.py --token xxx --list-ai-times
```

### 4. 查询回测列表

```bash
python query.py --token xxx \
  --coin BTC \
  --strategy-type 1 \
  --year 2024 \
  --sort 2 \
  --limit 10
```

### 5. 查看详情

```bash
python query.py --token xxx --detail <回测ID>
```

**返回**：完整的回测统计信息、净值曲线、交易明细

---

## 📝 可选参数

| 参数 | 说明 | 示例 |
|-----|-----|-----|
| `--page` | 页码 | `--page 1` |
| `--limit` | 每页数量（-1全部） | `--limit 20` |
| `--year` | 按年份查询 | `--year 2024` |
| `--ai-time-id` | 按时间ID查询 | `--ai-time-id xxx` |
| `--status` | 状态筛选 | `--status 3` |
| `--direction` | 方向（策略类型1,7,11） | `--direction long` |
| `--version` | 策略版本 | `--version 1.0` |
| `--name` | 策略名称 | `--name "BTC网格"` |
| `--format` | 输出格式 | `--format json` |

**状态码**：
- -1 = 已删除
- 2 = 回测中
- 3 = 回测成功（推荐）
- 4 = 回测失败

---

## 🎯 使用示例

### 查询 BTC 做多策略（按收益率）

```bash
python query.py --token xxx \
  --coin BTC \
  --direction long \
  --strategy-type 1 \
  --year 2024 \
  --sort 2 \
  --limit 10
```

### 查询 2024 年夏普率最高的策略

```bash
python query.py --token xxx \
  --coin BTC \
  --strategy-type 7 \
  --year 2024 \
  --sort 3 \
  --limit 10
```

### 查询全部结果（JSON格式）

```bash
python query.py --token xxx \
  --coin BTC \
  --strategy-type 3 \
  --year 2024 \
  --sort 2 \
  --limit -1 \
  --format json
```

---

## ⭐ 创建策略组合

查询后获取 `strategy_token`，然后创建组合：

```bash
python query.py --token xxx \
  --create-group \
  --group-name "BTC多空对冲组合" \
  --strategy-tokens "st_xxx,st_yyy,st_zzz"
```

**返回**：策略组 ID

---

## ⚠️ 重要规则

1. **时间参数**：`--year` 和 `--ai-time-id` 二选一必传
2. **方向参数**：只有 strategy_type=1,7,11 支持 `--direction`
3. **版本参数**：有多版本时需传 `--version`
4. **状态筛选**：推荐使用 `--status 3`（成功）
5. **缓存机制**：币种、策略、时间列表缓存 24 小时

---

## 📊 返回字段

| 字段 | 说明 |
|-----|-----|
| `id` | 回测记录 ID |
| `name` | 策略名称 |
| `year_rate` | 年化收益率 |
| `sharp_rate` | 夏普比率 |
| `max_loss` | 最大回撤 |
| `win_rate` | 胜率 |
| `strategy_token` | 策略 token（用于创建组合） |
| `status` | 状态 |
