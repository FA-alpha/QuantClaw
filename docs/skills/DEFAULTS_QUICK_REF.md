# 默认参数快速参考

## 📍 配置文件位置

**文件**: `skills/backtest-query/defaults.py`  
**配置区域**: 第 17-27 行

---

## ⚙️ 当前配置（默认）

```python
# 币种配置
COIN_COUNT = None          # None=全部
COIN_TYPE_FILTER = "CRYPTO"  # 只要虚拟币
COIN_FALLBACK = ["BTC", "ETH", "SOL"]

# 策略配置
STRATEGY_COUNT = 3         # 前3个
STRATEGY_FALLBACK = [11, 7, 1]

# 时间配置
TIME_INDEX = 0             # 第1个
TIME_FALLBACK = "5"

# 缓存
ENABLE_CACHE = True        # 启用全局缓存
```

---

## 📊 当前效果

| 参数 | 配置 | 实际获取 |
|------|------|---------|
| 币种 | `CRYPTO` | 13个虚拟币（全部） |
| 策略 | 前3个 | [11, 8, 7] |
| 时间 | 第1个 | 16（2025年震荡） |

---

## 🎛️ 常用配置场景

### 只推荐虚拟币（默认）✅
```python
COIN_TYPE_FILTER = "CRYPTO"
```

### 只推荐美股
```python
COIN_TYPE_FILTER = "US"
```

### 全部币种（虚拟币+美股）
```python
COIN_TYPE_FILTER = None
```

### 只要前5个虚拟币
```python
COIN_COUNT = 5
COIN_TYPE_FILTER = "CRYPTO"
```

---

## 🔍 币种类型说明

| Type | 说明 | 数量 | 示例 |
|------|------|------|------|
| `CRYPTO` | 虚拟币 | 13个 | BTC, ETH, SOL, DOGE, XRP, ADA... |
| `US` | 美股 | 19个 | AAPL, TSLA, NVDA, MSFT, GOOGL... |

**美股包含**：
- ETF（SPXL, TQQQ, SOXL等）
- 个股（AAPL, TSLA, NVDA等）

---

## 🚀 快速修改指南

### 步骤1：编辑配置
```bash
vim /home/ubuntu/work/QuantClaw/skills/backtest-query/defaults.py
```

### 步骤2：修改配置（第17-27行）
```python
COIN_TYPE_FILTER = "US"  # 改为美股
```

### 步骤3：保存并测试
```bash
python3 smart_recommend.py --token xxx --no-detail
```

### 步骤4：验证输出
```
ℹ️  使用默认币种（类型=US）: SPXL, TQQQ, ... (19个)
```

---

## 📖 详细文档

- **配置指南**: `DEFAULTS_CONFIG.md`
- **算法详解**: `docs/skills/SMART_RECOMMEND_ALGORITHM.md`
- **测试指南**: `TEST.md`

---

**一个文件，全局配置！** 🎯
