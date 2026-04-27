# 快速开始 - 回测查询

## ⚡ 重要更新

**所有脚本已支持自动获取 token，无需 `--token` 参数！**

## 🚀 正确用法

### 智能推荐（最常用）

```bash
python3 skills/backtest-query/smart_recommend.py \
  --coins "BTC,ETH" \
  --year 2024 \
  --workspace $(pwd) \
  --save-memory
```

### 基础查询

```bash
# 列出可用币种
python3 skills/backtest-query/query.py --list-coins

# 查询回测
python3 skills/backtest-query/query.py \
  --coin BTC \
  --strategy-type 11 \
  --sort 2
```

## ⚠️ 注意

- ❌ **不要使用** `--token` 参数，token 会自动获取
- ✅ **直接运行**脚本即可
- ✅ 脚本会从 `~/.quantclaw/users.json` 自动读取当前用户的 token

---

详细文档见：`SKILL.md`
