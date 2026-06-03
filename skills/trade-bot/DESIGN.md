# Trade-Bot 技能设计文档

## 📋 概述

"用户操作交易机器人"技能，允许 Agent 通过 API 管理 fourieralpha 平台的交易机器人。

---

## 🔒 安全确认机制（核心设计）

### 设计原则

> **所有涉及交易机器人的写操作（创建/停止/调整/加仓），代码层强制要求确认。**

### 实现方案：默认预览 + `--confirm` 两步模式

每个写操作默认只预览不执行，加 `--confirm` 才真正调用 API。

| 模式 | 触发方式 | 行为 |
|------|---------|------|
| 预览（默认） | 不加 `--confirm` | 输出 JSON `{"status":"preview",...}`，不调用 API |
| 执行 | 加 `--confirm` | 调用 API 并返回结果 |

> **为什么不是 `--dry-run`**：写操作 "不加 flag = 安全" 更可靠。Agent 必须**显式加 `--confirm`** 才能执行。漏加 = 安全，不加 = 无害。

**Agent 交互流程**：

```
用户："创建 DOGE 交易机器人"
     ↓
Agent: cd skills/trade-bot && python3 scripts/trade_bot.py apply --agent-id qc-xxx ...
     → JSON {"status":"preview", "action":"创建交易机器人", ...}
     ↓
Agent 展示预览给用户
     ↓
用户："确认"
     ↓
Agent: cd skills/trade-bot && python3 scripts/trade_bot.py apply --agent-id qc-xxx ... --confirm
     → JSON {"status":"executed", "bot_id": "123", ...}
```

### 操作危险等级

| 等级 | 操作 | 确认要求 |
|------|------|---------|
| 🟢 只读 | list, detail, check-status, balance, orders, exchange-list | 无需确认 |
| 🟡 可逆写 | 手动加仓、取消加仓 | 需确认 |
| 🔴 危险写 | 创建(实盘)、停止、调整保证金、策略更新 | **强制确认** |

### SKILL.md 强制规则

1. 所有 🔴🟡 操作，Agent **必须先不加 `--confirm`** 预览
2. 将预览 `summary` 展示给用户
3. 等待用户明确说"确认"/"好的"/"执行"等
4. 加上 `--confirm` 重新调用
5. 用户说"取消"/"不要"则终止

---

## 📁 文件结构

```
skills/trade-bot/
├── DESIGN.md                    ← 设计文档（本文件）
├── SKILL.md                     ← Agent 使用指南
└── scripts/                     ← 所有脚本（自包含，无外部依赖）
    │
    ├── trade_bot.py             ← 🔑 入口（argparse CLI，路由 + token 解析）
    ├── list_bots.py             ← 机器人列表查询（/Trade/lists）
    ├── leverage_bot.py          ← 杠杆率统计（/TradeStat/leverage_ratio）
    ├── exchange_list.py         ← 交易所账户列表（/User/exchange_lists）
    │
    ├── api_client.py            ← 🔧 通用 HTTP 请求封装
    ├── platform_data.py         ← 🔧 平台参考数据（币种/策略/时间，24h 缓存）
    └── qc_log/                  ← 🔧 统一日志模块（本地副本，避 stdlib logging 冲突）
        ├── __init__.py
        └── api_logger.py
```

### 内部模块说明

**`qc_log/`** — API 请求日志 & 错误日志
- 来源：`scripts/logging/api_logger.py`（本地副本，自包含）
- 目录名 `qc_log` 而非 `logging`，避免遮蔽 Python 标准库 `logging`（urllib3 依赖它）
- `log_http_request(url, params, response, agent_id)` — 记录 API 请求/响应到 `~/.quantclaw/logs/{agent_id}/{date}.log`
- `log_error(msg, exception, context, agent_id)` — 记录脚本错误（含 traceback）
- 自动清理 7 天前的旧日志

**`api_client.py`** — 通用 HTTP 请求封装
- `api_post(path, params, agent_id)` — 统一 POST 请求，内置日志 + 网络异常兜底
- `check_auth(data)` — 检查 API 鉴权状态，返回 `(ok, message)`
- `check_status(data)` — 检查业务状态（status == 1）
- 目的：消除各脚本重复的 `requests.post` + `log_http_request` + `try/except` 模式

**`platform_data.py`** — 平台级参考数据（带 24h 磁盘缓存）
- `get_coin_list(token)` → `/Strategy/coin_lists` — 可用币种列表
- `get_ai_time_list(token)` → `/Extend/ai_time_lists` — AI 回测时间列表
- `get_ai_strategy_list(token)` → `/Extend/ai_strategy_lists` — AI 策略类型列表
- `get_exchange_list(token, page, limit)` → `/User/exchange_lists` — 交易所账户（不缓存）
- 缓存目录：`~/.quantclaw/cache/{key}.json`，TTL 24h
- 依赖 `api_client`（`api_post` / `check_auth`）

### 架构约定
- `trade_bot.py` 是唯一入口，用 `argparse` 子命令路由（零外部 CLI 依赖）
- 每个功能脚本导出 `def run(...)`，由入口 import 调用，不做 `if __name__` 独立运行
- Token 解析统一在入口 `get_user_token_by_agent_id()` 完成
- 所有 import 均为本地引用（`from qc_log import ...` / `from api_client import ...`），不依赖项目根 `scripts/`
- skill 完全自包含，可独立复制/安装/分发

---

## 🎯 目标功能

### 🟢 只读操作（无需 `--confirm`）

| 子命令 | API | 说明 |
|--------|-----|------|
| `list` | `/Trade/lists` | 按状态/交易所/类型/排序查询 |
| `detail` | `/Trade/info` 或 `/Trade/new_info` | 运行数据、收益率、周期记录 |
| `check-status` | `/Trade/check_status` | 轮询浮动数据 |
| `balance` | `/Trade/balance_do` | 查询交易所账户余额 |
| `orders` | `/Trade/grid_lists` | 某周期的网格订单明细 |
| `exchange-list` | `/User/exchange_lists` | 用户绑定的交易所账户列表 |

### 🟡🔴 写操作（默认预览，需 `--confirm` 才执行）

| 子命令 | API | 危险等级 | 说明 |
|--------|-----|---------|------|
| `apply` | `/Trade/apply_do` | 🔴 实盘 / 🟡 模拟 | 创建交易机器人 |
| `stop` | `/Trade/status_do` | 🔴 | 停止/重启/预约停止 |
| `scale` | `/Trade/scale_do` | 🟡 | 手动加仓/取消加仓 |
| `margin` | `/Trade/margin_do` | 🔴 | 增加/减少保证金 |
| `update` | `/Trade/strategy_update_do` | 🔴 | 永久/本周期策略参数更新 |

---

## 🏗️ 布线 / 架构

### 入口文件骨架（trade_bot.py）

```python
#!/usr/bin/env python3
"""交易机器人管理 - typer CLI 入口"""
import json
import os
import typer
from pathlib import Path
from typing import Optional

SCRIPT_DIR = Path(__file__).parent
app = typer.Typer(help="交易机器人管理")

BASE_URL = "..."  # 从配置/环境变量读取

def get_user_token_by_agent_id(agent_id: str) -> Optional[str]:
    """从 ~/.quantclaw/users.json 查询 token"""
    users_file = os.path.expanduser("~/.quantclaw/users.json")
    if not os.path.exists(users_file):
        print(f'{{"status":"error","message":"users.json 不存在: {users_file}"}}')
        return None
    with open(users_file) as f:
        users = json.load(f)
    for u in users.get("users", []):
        if u.get("agentId") == agent_id:
            return u.get("token")
    print(f'{{"status":"error","message":"未找到 agentId={agent_id} 的 token"}}')
    return None


# ═══ 🟢 只读子命令 ═══

@app.command()
def list_bots(
    agent_id: str = typer.Option(..., "--agent-id"),
    status: Optional[int] = typer.Option(None, "--status"),
    search_val: Optional[str] = typer.Option(None, "--search"),
    search_exchange: Optional[str] = typer.Option(None, "--exchange-ids"),
    sort_type: int = typer.Option(1, "--sort-type"),
    page: int = typer.Option(1, "--page"),
    limit: int = typer.Option(10, "--limit"),
):
    """查询交易机器人列表"""
    from list_bots import run
    token = get_user_token_by_agent_id(agent_id)
    if not token: return
    result = run(token=token, status=status, search_val=search_val,
                 search_exchange=search_exchange, sort_type=sort_type,
                 page=page, limit=limit)
    print(json.dumps(result, ensure_ascii=False, indent=2))


@app.command()
def detail(
    agent_id: str = typer.Option(..., "--agent-id"),
    bot_id: int = typer.Option(..., "--bot-id"),
    new_api: bool = typer.Option(False, "--new-api"),
):
    """查询机器人详情（--new-api 使用 /Trade/new_info）"""
    from detail_bot import run
    token = get_user_token_by_agent_id(agent_id)
    if not token: return
    result = run(token=token, bot_id=bot_id, new_api=new_api)
    print(json.dumps(result, ensure_ascii=False, indent=2))


@app.command()
def check_status(
    agent_id: str = typer.Option(..., "--agent-id"),
    bot_id: int = typer.Option(..., "--bot-id"),
    grids_token: str = typer.Option(..., "--grids-token"),
):
    """轮询浮动数据"""
    from detail_bot import run_check_status
    token = get_user_token_by_agent_id(agent_id)
    if not token: return
    result = run_check_status(token=token, bot_id=bot_id, grids_token=grids_token)
    print(json.dumps(result, ensure_ascii=False, indent=2))


@app.command()
def balance(
    agent_id: str = typer.Option(..., "--agent-id"),
    account_id: int = typer.Option(..., "--account-id"),
    basic_unit: str = typer.Option("USDT", "--basic-unit"),
    coin: Optional[str] = typer.Option(None, "--coin"),
    strategy_id: Optional[str] = typer.Option(None, "--strategy-id"),
):
    """查询交易所账户余额"""
    from balance import run
    token = get_user_token_by_agent_id(agent_id)
    if not token: return
    result = run(token=token, account_id=account_id, basic_unit=basic_unit,
                 coin=coin, strategy_id=strategy_id)
    print(json.dumps(result, ensure_ascii=False, indent=2))


@app.command()
def exchange_list(
    agent_id: str = typer.Option(..., "--agent-id"),
    page: int = typer.Option(1, "--page"),
    limit: int = typer.Option(-1, "--limit"),
):
    """查询交易所账户列表"""
    from balance import run_exchange_list
    token = get_user_token_by_agent_id(agent_id)
    if not token: return
    result = run_exchange_list(token=token, page=page, limit=limit)
    print(json.dumps(result, ensure_ascii=False, indent=2))


@app.command()
def orders(
    agent_id: str = typer.Option(..., "--agent-id"),
    bot_id: int = typer.Option(..., "--bot-id"),
    grid_id: int = typer.Option(..., "--grid-id"),
):
    """查看周期网格订单明细"""
    from grid_orders import run
    token = get_user_token_by_agent_id(agent_id)
    if not token: return
    result = run(token=token, bot_id=bot_id, grid_id=grid_id)
    print(json.dumps(result, ensure_ascii=False, indent=2))


# ═══ 🔴🟡 写操作子命令（默认预览，加 --confirm 执行） ═══

@app.command()
def apply(
    agent_id: str = typer.Option(..., "--agent-id"),
    strategy_id: str = typer.Option(..., "--strategy-id"),
    name: str = typer.Option(..., "--name"),
    trade_type: int = typer.Option(..., "--trade-type"),
    account_id: int = typer.Option(..., "--account-id"),
    multiple_num: Optional[float] = typer.Option(None, "--leverage"),
    basic_unit: str = typer.Option("USDT", "--basic-unit"),
    backtest_date: Optional[str] = typer.Option(None, "--backtest-date"),
    auto_redeem: int = typer.Option(0, "--auto-redeem"),
    fst_capital: Optional[float] = typer.Option(None, "--fst-capital"),
    each_capital: Optional[float] = typer.Option(None, "--each-capital"),
    initial_capital: Optional[float] = typer.Option(None, "--initial-capital"),
    max_grid_size: Optional[int] = typer.Option(None, "--max-grid-size"),
    trade_buy_type: Optional[str] = typer.Option(None, "--trade-buy-type"),
    trade_model: Optional[str] = typer.Option(None, "--trade-model"),
    confirm: bool = typer.Option(False, "--confirm"),
):
    """创建交易机器人（默认预览模式，加 --confirm 执行）"""
    from apply_bot import run
    token = get_user_token_by_agent_id(agent_id)
    if not token: return
    result = run(
        token=token, strategy_id=strategy_id, name=name,
        trade_type=trade_type, account_id=account_id,
        multiple_num=multiple_num, basic_unit=basic_unit,
        backtest_date=backtest_date, auto_redeem=auto_redeem,
        fst_capital=fst_capital, each_capital=each_capital,
        initial_capital=initial_capital, max_grid_size=max_grid_size,
        trade_buy_type=trade_buy_type, trade_model=trade_model,
        confirm=confirm,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


@app.command()
def stop(
    agent_id: str = typer.Option(..., "--agent-id"),
    bot_id: int = typer.Option(..., "--bot-id"),
    save_type: int = typer.Option(..., "--save-type"),
    confirm: bool = typer.Option(False, "--confirm"),
):
    """停止/重启机器人 (save_type: 4-停止 5-停止当周期 6-预约停止 7-取消预约)"""
    from stop_bot import run
    token = get_user_token_by_agent_id(agent_id)
    if not token: return
    result = run(token=token, bot_id=bot_id, save_type=save_type, confirm=confirm)
    print(json.dumps(result, ensure_ascii=False, indent=2))


@app.command()
def scale(
    agent_id: str = typer.Option(..., "--agent-id"),
    bot_id: int = typer.Option(..., "--bot-id"),
    save_type: int = typer.Option(..., "--save-type"),
    price: Optional[float] = typer.Option(None, "--price"),
    amt: Optional[float] = typer.Option(None, "--amt"),
    order_id: Optional[str] = typer.Option(None, "--order-id"),
    confirm: bool = typer.Option(False, "--confirm"),
):
    """手动加仓/取消加仓 (save_type: 8-加仓 9-取消加仓)"""
    from scale_bot import run
    token = get_user_token_by_agent_id(agent_id)
    if not token: return
    result = run(token=token, bot_id=bot_id, save_type=save_type,
                 price=price, amt=amt, order_id=order_id, confirm=confirm)
    print(json.dumps(result, ensure_ascii=False, indent=2))


@app.command()
def margin(
    agent_id: str = typer.Option(..., "--agent-id"),
    bot_id: int = typer.Option(..., "--bot-id"),
    amt: float = typer.Option(..., "--amt"),
    save_type: int = typer.Option(..., "--save-type"),
    confirm: bool = typer.Option(False, "--confirm"),
):
    """调整保证金 (save_type: 6-增加 7-减少)"""
    from margin_bot import run
    token = get_user_token_by_agent_id(agent_id)
    if not token: return
    result = run(token=token, bot_id=bot_id, amt=amt,
                 save_type=save_type, confirm=confirm)
    print(json.dumps(result, ensure_ascii=False, indent=2))


@app.command()
def update(
    agent_id: str = typer.Option(..., "--agent-id"),
    bot_id: int = typer.Option(..., "--bot-id"),
    update_type: int = typer.Option(..., "--update-type"),
    rule: str = typer.Option(..., "--rule"),
    confirm: bool = typer.Option(False, "--confirm"),
):
    """策略参数更新 (update_type: 1-永久 2-当周期生效)"""
    from strategy_update import run
    token = get_user_token_by_agent_id(agent_id)
    if not token: return
    result = run(token=token, bot_id=bot_id, update_type=update_type,
                 rule=rule, confirm=confirm)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    app()
```

### 功能脚本模板（list_bots.py 示例 - 只读）

```python
"""查询交易机器人列表"""
import requests

BASE_URL = "..."  # 从配置/环境变量读取，或由入口传入

def run(token, status=None, search_val=None, search_exchange=None,
        sort_type=1, page=1, limit=10):
    """查询列表，始终返回 JSON"""
    params = {
        "usertoken": token,
        "page": page,
        "limit": limit,
        "sort_type": sort_type,
        "sort_desc_type": 1,
    }
    if status is not None:
        params["search_status"] = status
    if search_val:
        params["search_val"] = search_val
    if search_exchange:
        params["search_exchange"] = search_exchange

    resp = requests.post(f"{BASE_URL}/Trade/lists", json=params, timeout=30)
    return resp.json()
```

### 功能脚本模板（apply_bot.py 示例 - 写操作）

```python
"""创建交易机器人"""
import requests

BASE_URL = "..."

def run(token, strategy_id, name, trade_type, account_id, confirm=False, **kwargs):
    """
    confirm=False: 返回预览 JSON，不调 API
    confirm=True:  调用 /Trade/apply_do
    """
    params = {
        "usertoken": token,
        "strategy_id": strategy_id,
        "name": name,
        "trade_type": trade_type,
        "account_id": account_id,
    }
    # 过滤 None 值
    params.update({k: v for k, v in kwargs.items() if v is not None})

    if not confirm:
        trade_type_name = "实盘" if trade_type == 2 else "模拟盘"
        return {
            "status": "preview",
            "action": "创建交易机器人",
            "danger_level": "red" if trade_type == 2 else "yellow",
            "summary": {
                "名称": name,
                "策略ID": strategy_id,
                "类型": trade_type_name,
                "交易所账户ID": account_id,
                "参数": params,
            },
            "warning": "⚠️ 实盘操作，资金将真实交易" if trade_type == 2 else None,
        }

    resp = requests.post(f"{BASE_URL}/Trade/apply_do", json=params, timeout=30)
    data = resp.json()
    data["api_status"] = data.get("status")
    data["status"] = "executed" if data.get("status") == 1 else "failed"
    return data
```

### JSON 输出规范

```json
// 预览
{"status": "preview", "action": "...", "danger_level": "red|yellow", "summary": {...}}

// 执行成功
{"status": "executed", "api_status": 1, "bot_id": "...", ...}

// 执行失败
{"status": "failed", "api_status": 0, "message": "...", ...}
```

---

## 🔗 与其他技能的关系

> ⚠️ **trade-bot 职责边界**：聚焦于**已存在机器人的管理/监控/控制**。
> 创建机器人 (`/Trade/apply_do`) 由其他 skill（如 backtest-query）在策略推荐流程中触发，
> trade-bot 的 `apply_bot.py` 作为底层模块供其他 skill 复用。

```
backtest-query                      trade-bot
  │                                   │
  ├─ 推荐策略 → 用户说"实盘跑"       │
  │   └──→ apply_bot.run(confirm=True)  
  │                                   │
  └─ 创建完成后 ──────────────────→ 接管：监控/管理
                                        │
                                        ├─ list_bots      查看机器人列表
                                        ├─ detail_bot     查看运行详情
                                        ├─ stop_bot       停止/重启
                                        ├─ scale_bot      手动加仓
                                        ├─ margin_bot     调整保证金
                                        └─ strategy_update 策略参数更新
```

| 职责 | 归属 Skill |
|------|-----------|
| 策略推荐/创建策略组 | backtest-query |
| 回测 | start-backtest |
| 创建机器人 | backtest-query（调用 `apply_bot.run()`） |
| 管理/监控/控制机器人 | **trade-bot** ✅ |

---

## 📊 实现优先级

- **MVP**: `list_bots` + `detail_bot` + `balance` + `stop_bot` + `apply_bot.run()`
- **进阶**: `scale_bot` + `margin_bot` + `strategy_update` + `check_status` + `orders`

---

## ✅ 已确定

- [x] 确认机制：默认预览，显式 `--confirm` 执行
- [x] 创建机器人由其他 skill 调用，trade-bot 聚焦管理/监控
- [x] 目录结构：.md 放根目录，脚本统一 `scripts/`
- [x] Token：复用 `get_user_token_by_agent_id()` → `~/.quantclaw/users.json`
- [x] 入口架构：`trade_bot.py` typer CLI 路由 → 各功能脚本 `run()`
- [x] 一功能一脚本，入口统一分发

## ❓ 待确认

- [ ] MVP 范围可以吗？（列表/详情/余额/停止 + apply_bot 底层）