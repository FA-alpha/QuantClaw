# list_bots.py 设计文档

## 📋 功能

查询交易机器人列表，支持多维度筛选、排序、分页。

---

## 🔌 API

**端点**: `POST /Trade/lists`

### 请求参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `usertoken` | str | ✅ | 用户 token |
| `page` | int | ❌ | 第几页，默认 1 |
| `limit` | int | ❌ | 每页条数，默认 10，传 -1 获取全部 |
| `search_val` | str | ❌ | 搜索机器人名称 |
| `search_status` | int | ❌ | -1=已删除, 1=实盘运行中, 2=模拟运行, 3=已停止；不传=全部 |
| `search_exchange` | str | ❌ | 交易所 ID，多个逗号分隔 |
| `search_amt_type` | int | ❌ | 1=现货, 2=合约；不传=全部 |
| `strategy_type` | int | ❌ | 策略类型 ID；传 0=全部 |
| `account_id` | int | ❌ | 交易所账号 ID；传 0=全部 |
| `search_direction` | str | ❌ | `long`=做多, `short`=做空；不传=全部 |
| `sort_type` | int | ❌ | 1=最新 2=收益率 3=运行时间 4=投资额 5=净值 6=停止时间 |
| `sort_desc_type` | int | ❌ | 1=降序, 2=升序 |

### 返回字段

```
info[]:
  id              记录ID
  name            机器人名称
  account_name    交易所账户名称
  exchange_name   交易所名称
  amt_type        类型 (1-现货 2-合约)
  strategy_name   策略名称
  run_time        运行时间（秒）
  net_value       净值
  initial_capital 总金额
  profit_rate     收益率
  status          0-未运行 1-实盘运行中 2-模拟运行 3-已停止 4-模拟已停止
  reserve_status  0-未预约 1-预约停止中 2-预约已终止
  is_info         是否可查看详情 (1-是 0-否)
  trade_status    1-交易中 2-待启动
  create_time     开始时间
  basic_unit      交易类型 (USDT-U本位 USD-币本位)

url:
  all_count       总条数
```

---

## 🎛️ 筛选功能设计

### CLI 参数 → API 参数映射

| 用户概念 | CLI 参数 | API 参数 | 取值 |
|---------|---------|---------|------|
| 运行状态 | `--status` | `search_status` | running(默认) / sim / stopped / deleted / all |
| 交易所 | `--exchange-ids` | `search_exchange` | 交易所账户 ID，逗号分隔；不传=全部 |
| 交易品种 | `--amt-type` | `search_amt_type` | spot / futures / all |
| 策略类型 | `--strategy-type` | `strategy_type` | 策略类型 ID；不传=全部 |
| 账号 | `--account-id` | `account_id` | 交易所账号 ID；不传=全部 |
| 合约方向 | `--direction` | `search_direction` | long / short / all |
| 交易对 | `--coin` | (通过 search_val 搜索) | 如 BTC, ETH |
| 名称 | `--search` | `search_val` | 机器人名称关键词 |

### 状态值映射

| CLI 传入 | API 值 | 含义 |
|----------|--------|------|
| `running` | 1 | 实盘运行中（**默认**） |
| `sim` | 2 | 模拟运行 |
| `stopped` | 3 | 已停止 |
| `deleted` | -1 | 已删除 |
| `all` | 不传 | 全部 |

### 交易品种映射

| CLI 传入 | API 值 | 含义 |
|----------|--------|------|
| `spot` | 1 | 现货 |
| `futures` | 2 | 合约 |
| `all` | 不传 | 全部 |

### 排序映射

| CLI 传入 | API sort_type | 含义 |
|----------|---------------|------|
| `latest` / **默认** | 1 | 最新记录（按创建时间降序） |
| `profit` | 2 | 收益率 |
| `runtime` | 3 | 运行时间 |
| `capital` | 4 | 投资额 |
| `nav` | 5 | 按净值 |
| `stop-time` | 6 | 按停止时间 |

### 默认值

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `status` | `running` | 默认只看实盘运行中 |
| `sort` | `latest` | 按创建时间，最新的在前 |
| `order` | `desc` | 降序 |
| 其他筛选 | 不传 | 传 `all` = 不传 = 全部 |

---

## 💻 CLI 接口

```bash
# 基本用法
cd skills/trade-bot && python3 scripts/trade_bot.py list --agent-id qc-xxx

# 筛选示例
python3 scripts/trade_bot.py list --agent-id qc-xxx --status running
python3 scripts/trade_bot.py list --agent-id qc-xxx --status running,sim
python3 scripts/trade_bot.py list --agent-id qc-xxx --exchange-ids 1,3
python3 scripts/trade_bot.py list --agent-id qc-xxx --amt-type futures --direction long
python3 scripts/trade_bot.py list --agent-id qc-xxx --search "DOGE马丁"
python3 scripts/trade_bot.py list --agent-id qc-xxx --strategy-type 1 --account-id 2

# 排序 + 分页
python3 scripts/trade_bot.py list --agent-id qc-xxx --sort profit --order desc --page 1 --limit 20

# 获取全部
python3 scripts/trade_bot.py list --agent-id qc-xxx --limit -1

# 组合筛选
python3 scripts/trade_bot.py list --agent-id qc-xxx \
  --status running \
  --amt-type futures \
  --direction long \
  --sort profit --order desc
```

---

## 📤 输出格式

```json
{
  "status": "ok",
  "total": 15,
  "page": 1,
  "limit": 10,
  "filters": {
    "status": [1],
    "amt_type": 2,
    "direction": "long"
  },
  "bots": [
    {
      "id": 123,
      "name": "DOGE马丁",
      "account_name": "币安主账户",
      "exchange_name": "Binance",
      "amt_type": 2,
      "strategy_name": "风霆_v4.3",
      "status": 1,
      "status_label": "实盘运行中",
      "profit_rate": 12.5,
      "net_value": 11250,
      "initial_capital": 10000,
      "run_time": 864000,
      "run_time_label": "10天",
      "direction": "long",
      "basic_unit": "USDT",
      "create_time": "2026-05-20 14:30:00"
    }
  ]
}
```

### 字段增强

脚本在 API 原始返回基础上增加：

| 增强字段 | 说明 |
|---------|------|
| `status_label` | 中文状态名（实盘运行中 / 模拟运行 / 已停止...） |
| `run_time_label` | 人类可读的运行时长（"3天5小时"） |
| `direction` | 根据策略推断做多/做空（如 API 有则透传） |
| `filters` | 回显当前筛选条件 |

---

## 🐍 函数签名

```python
# scripts/list_bots.py

import sys, os

# 日志模块路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'scripts', 'logging'))
from api_logger import log_http_request, log_error

BASE_URL = "https://www.fourieralpha.com/Mobile"

def run(
    token: str,
    status: str = "running",             # running|sim|stopped|deleted|all，默认 running
    exchange_ids: Optional[str] = None,   # 交易所账户ID，逗号分隔；不传=全部
    amt_type: Optional[str] = None,       # spot|futures|all；不传=全部
    strategy_type: Optional[int] = None,  # 策略类型ID；不传=全部
    account_id: Optional[int] = None,     # 交易所账号ID；不传=全部
    direction: Optional[str] = None,      # long|short|all；不传=全部
    search: Optional[str] = None,         # 名称搜索
    coin: Optional[str] = None,           # 币种
    sort: str = "latest",                 # 默认按创建时间排序
    order: str = "desc",                  # 默认降序（最新的在前）
    page: int = 1,
    limit: int = 10,
    agent_id: Optional[str] = None,       # 用于日志
) -> dict:
    """
    返回统一 JSON：
    {
        "status": "ok" | "error",
        "total": int,
        "page": int,
        "limit": int,
        "bots": [...],
        "filters": {...},
    }
    """
```

### 筛选逻辑

```python
def _build_search_status(status: str) -> Optional[str]:
    """将 CSV 状态名转为 API 的 CSV 状态值；all 或空 → 不传"""
    MAP = {"running": "1", "sim": "2", "stopped": "3", "deleted": "-1"}
    if not status or status == "all":
        return None
    return ",".join(MAP[s] for s in status.split(",") if s in MAP)

def _build_search_val(search: str, coin: str) -> Optional[str]:
    """合并名称搜索和币种搜索"""
    if search and coin:
        return f"{search} {coin}"
    return search or coin
```

### 📋 日志接入

所有脚本统一接入 `scripts/logging/api_logger.py`：

```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'scripts', 'logging'))
from api_logger import log_http_request, log_error

# 请求前记录
def run(token, ..., agent_id=None):
    url = f"{BASE_URL}/Trade/lists"
    params = {...}
    
    try:
        resp = requests.post(url, json=params, timeout=30)
        data = resp.json()
        # 请求成功 → 记录日志
        log_http_request(url, params, response=data, agent_id=agent_id)
        ...
    except Exception as e:
        # 请求失败 → 记录错误日志
        log_error(str(e), exception=e, context={"url": url}, agent_id=agent_id)
        return {"status": "error", "message": str(e)}
```

日志输出路径：`~/.quantclaw/logs/{agent_id}/{YYYY-MM-DD}.log`

### ⚠️ 交易所筛选前置步骤

`search_exchange` 和 `account_id` 参数需要交易所 ID。**调用 list 之前必须先获取交易所列表**：

```
Agent 流程：
1. 用户说"看看币安的机器人"
2. 先调 exchange-list 获取交易所账户列表 → 找到币安账户 ID
3. 用 `--exchange-ids <id>` 筛选机器人列表
```

```bash
# 步骤 1：获取交易所账户列表
python3 scripts/trade_bot.py exchange-list --agent-id qc-xxx

# 返回示例：
# [{"id": 1, "exchange_name": "Binance", "name": "主账户", "status": 2}, ...]

# 步骤 2：用交易所名称匹配 ID，查询机器人
python3 scripts/trade_bot.py list --agent-id qc-xxx --exchange-ids 1
```

> 交易所列表通过 `/User/exchange_lists` 获取，返回 `id`（账户ID）、`exchange_name`（交易所名称）、`name`（账户名）、`status`（1-未连接 2-已连接）。缓存到 `exchange-list` 子命令中复用。

---

## 🚨 Agent 使用规则（写入 SKILL.md）

1. **无需确认**：`list` 是 🟢 只读操作
2. **默认筛选**：
   - 不传 `--status` = 只看实盘运行中
   - 不传 `--sort` = 按创建时间，最新的在前
   - 不传其他筛选 = 全部
3. **状态对应关系**：
   - 用户说"运行中"/"实盘" → `--status running`（默认，可省略）
   - 用户说"模拟盘" → `--status sim`
   - 用户说"停止了"/"停止的" → `--status stopped`
   - 用户说"全部"/"所有" → `--status all`
4. **多状态查询**：用户说"看看运行中和模拟的" → `--status running,sim`
5. **排序**：用户说"按收益排" → `--sort profit`，"运行最久的" → `--sort runtime`，"最新的" → `--sort latest`（默认）
6. **全部筛选**：用户说"全部现货" → `--amt-type all`（或直接不传）