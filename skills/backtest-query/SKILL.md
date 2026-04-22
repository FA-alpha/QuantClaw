# 回测数据查询

查询 AI 回测数据，支持多条件筛选。

## 使用场景

- 查询回测结果
- 按条件筛选策略
- 获取策略列表用于组合

## 查询脚本

```bash
python skills/backtest-query/query.py --token <用户token> [选项]
```

## 参数说明

| 参数 | 说明 | 示例 |
|-----|-----|-----|
| `--token` | 用户 token（必填） | `--token qc_xxx` |
| `--page` | 页码 | `--page 1` |
| `--limit` | 每页数量，-1获取全部 | `--limit 20` |
| `--name` | 策略名称 | `--name "BTC网格"` |
| `--status` | 状态：-1删除 2回测中 3成功 4失败 | `--status 3` |
| `--start-date` | 开始日期 | `--start-date 2024-01-01` |
| `--end-date` | 结束日期 | `--end-date 2024-12-31` |
| `--amt-type` | 类型：1现货 2合约 | `--amt-type 2` |
| `--sort` | 排序：1最新 2收益率 3夏普 4回撤 | `--sort 2` |
| `--coin` | 币种，多选逗号分割 | `--coin BTC,ETH` |
| `--type` | 类型：1个人 2AI推荐 3别人推荐 | `--type 2` |
| `--year` | 年份 | `--year 2024` |
| | | |
| `--direction` | 方向：long做多 short做空（仅策略类型1,7,11支持） | `--direction long` |
| `--format` | 输出格式：json/table/summary | `--format json` |

## 使用示例

### 查询 AI 推荐的 BTC 做多策略，按收益率排序

```bash
python skills/backtest-query/query.py \
  --token qc_xxx \
  --type 2 \
  --coin BTC \
  --direction long \
  --sort 2 \
  --status 3
```

### 查询合约策略，获取全部结果

```bash
python skills/backtest-query/query.py \
  --token qc_xxx \
  --amt-type 2 \
  --limit -1 \
  --format json
```

### 查询 2024 年夏普率最高的策略

```bash
python skills/backtest-query/query.py \
  --token qc_xxx \
  --year 2024 \
  --sort 3 \
  --limit 10
```

## 返回字段说明

| 字段 | 说明 |
|-----|-----|
| `id` | 回测记录 ID |
| `name` | 策略名称 |
| `bgn_date` | 开始日期 |
| `end_date` | 结束日期 |
| `year_rate` | 年化收益率 |
| `sharp_rate` | 夏普比率 |
| `max_loss` | 最大回撤 |
| `amt_type` | 类型：1现货 2合约 |
| `win_rate` | 胜率 |
| `score` | 策略评分 |
| `trade_num` | 交易次数 |
| `status` | 状态：1排队 2回测中 3成功 4失败 |
| `strategy_token` | 策略 token |
| `strategy_id` | 策略 ID |
| `version` | 策略版本 |

## 币种管理

```bash
# 列出可用币种（使用缓存，24小时有效）
python skills/backtest-query/query.py --list-coins

# 强制刷新币种缓存
python skills/backtest-query/query.py --refresh-coins
```

缓存文件：`~/.quantclaw/cache/coins.json`

## 注意事项

- Token 从用户认证获取
- 查询成功状态的回测使用 `--status 3`
- 获取全部数据用 `--limit -1`
- 币种列表缓存 24 小时，如需更新用 `--refresh-cache`
- **方向参数限制**：只有策略类型 1、7、11 支持 `--direction` 参数，其他策略类型不传方向
- **版本参数**：如果策略类型有版本列表，需要同时传 `--strategy-type` 和 `--version`
