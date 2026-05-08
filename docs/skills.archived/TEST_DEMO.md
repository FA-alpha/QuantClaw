# 测试演示说明

## 📋 测试准备

### 1. 获取 Token

**方法A：如果服务已运行**
```bash
# 检查服务状态
curl http://localhost:8000/api/health

# 注册获取 token（如果是新用户）
curl http://localhost:8000/api/register
```

**方法B：使用现有 token**
如果你已经有 token，直接使用即可。

**方法C：从 Agent 工作区获取**
```bash
# 如果之前通过 webchat 交互过，token 应该在记忆中
grep -r "qc_" /home/ubuntu/quantclaw/memory/ 2>/dev/null || echo "未找到 token"
```

---

## 🚀 快速开始

### 测试 1: 验证技能脚本可执行

```bash
cd /home/ubuntu/work/QuantClaw/skills/backtest-query

# 查看帮助
python3 smart_recommend.py --help
```

**预期输出**：
```
usage: smart_recommend.py [-h] --token TOKEN [--coins COINS] ...
```

---

### 测试 2: 运行自动化测试（需要 token）

```bash
cd /home/ubuntu/work/QuantClaw/skills/backtest-query

# 使用你的 token
./test_smart_recommend.sh qc_YOUR_TOKEN_HERE
```

**测试流程**：
1. ✅ 基础查询（验证 API）
2. ✅ 快速推荐（探索模式）
3. ✅ 指定币种推荐
4. ✅ 完整推荐（含详情）
5. ✅ JSON 输出格式

---

### 测试 3: 手动单步测试

#### 步骤 1: 查询可用币种

```bash
python3 query.py --token qc_YOUR_TOKEN --list-coins
```

#### 步骤 2: 查询可用策略类型

```bash
python3 query.py --token qc_YOUR_TOKEN --list-strategies
```

#### 步骤 3: 完全开放式推荐（验证参数自动补全）

```bash
python3 smart_recommend.py \
  --token qc_YOUR_TOKEN \
  --group-size 2 \
  --top-n 2 \
  --no-detail
```

**关键验证点**：
- 应显示"未指定币种，使用默认主流币种: BTC, ETH, SOL"
- 应显示"未指定策略类型，查询多种类型"
- 应查询 3币种 × 3策略 = 9次

---

## 🎯 测试目标清单

### 功能测试

- [ ] **参数自动补全**
  - [ ] 不传 `--coins` 时使用默认币种
  - [ ] 不传 `--strategy-type` 时查询多种类型
  - [ ] 不传时间时使用默认"最近1年"

- [ ] **查询功能**
  - [ ] 可以查询可用币种
  - [ ] 可以查询可用策略类型
  - [ ] 可以查询可用时间段

- [ ] **推荐功能**
  - [ ] 快速模式（--no-detail）
  - [ ] 完整模式（获取详情）
  - [ ] 筛选条件（min-sharpe, max-drawdown）
  - [ ] 指定币种
  - [ ] 指定策略类型

- [ ] **输出功能**
  - [ ] 文本格式（默认）
  - [ ] JSON 格式（--format json）
  - [ ] 静默模式（--quiet）

- [ ] **记忆功能**
  - [ ] 保存到记忆文件（--save-memory）
  - [ ] 记忆文件格式正确

### 算法验证

- [ ] **评分算法**
  - [ ] 评分范围 0-100
  - [ ] 评分降序排列
  - [ ] 高分组合符合预期（高夏普、低回撤、低相关性）

- [ ] **相关性计算**
  - [ ] 相关性范围 -1 到 1
  - [ ] 低相关性组合评分更高

- [ ] **回撤错位分析**
  - [ ] 回撤重叠比例合理
  - [ ] 重叠低的组合评分更高

---

## 📊 预期结果示例

### 快速推荐输出

```
ℹ️  未指定币种，使用默认主流币种: BTC, ETH, SOL
ℹ️  未指定策略类型，查询多种类型: 风霆/网格/鲲鹏
ℹ️  未指定时间范围，使用默认：最近1年 (ai_time_id=5)

🔍 查询 BTC / 策略类型 11...
✅ BTC / 策略类型 11 找到 10 个策略
🔍 查询 BTC / 策略类型 7...
✅ BTC / 策略类型 7 找到 8 个策略
...

✅ 找到 2 个推荐组合

============================================================
🏆 推荐组合 #1 (评分: 78.5/100)
============================================================

📋 策略列表:
   1. BTC风霆做多v2
      币种: BTC | 年化: 32.5% | 夏普: 2.1 | 回撤: 11.2%
   ...

📊 组合分析:
   相关性: 0.32 (越低越好，<0.5为佳)
   组合夏普: 2.00
   ...

💡 推荐理由: 相关性较低(0.32)、高夏普率(2.00)
============================================================
```

---

## 🐛 故障排查

### 问题 1: 找不到 Python 命令

```bash
# 检查 Python 版本
python3 --version

# 如果没有，安装
sudo apt update && sudo apt install python3 python3-pip
```

### 问题 2: 缺少依赖

```bash
# 安装依赖
cd /home/ubuntu/work/QuantClaw/skills/backtest-query
pip3 install -r requirements.txt
```

### 问题 3: Token 无效

```bash
# 检查服务是否运行
curl http://localhost:8000/api/health

# 查看服务日志
tail -100 /tmp/quantclaw-server.log

# 重新启动服务
screen -r quantclaw  # 或查看启动脚本
```

### 问题 4: API 调用失败

```bash
# 测试 API 可达性
curl -X POST http://localhost:8000/api/backtest/list \
  -H "Content-Type: application/json" \
  -d '{"token": "qc_YOUR_TOKEN"}'

# 如果 404，检查服务端路由配置
```

---

## 📝 测试记录模板

测试日期: ___________
测试人: ___________
Token: qc___________

| 测试项 | 结果 | 备注 |
|--------|------|------|
| 脚本可执行 | ☐ 通过 ☐ 失败 | |
| 基础查询 | ☐ 通过 ☐ 失败 | |
| 参数自动补全 | ☐ 通过 ☐ 失败 | |
| 快速推荐 | ☐ 通过 ☐ 失败 | |
| 完整推荐 | ☐ 通过 ☐ 失败 | |
| JSON 输出 | ☐ 通过 ☐ 失败 | |
| 记忆保存 | ☐ 通过 ☐ 失败 | |
| 评分算法 | ☐ 通过 ☐ 失败 | |
| 相关性计算 | ☐ 通过 ☐ 失败 | |

---

## 🎉 测试完成后

1. **查看记忆文件**
   ```bash
   cat /home/ubuntu/quantclaw/memory/portfolio_history.md
   ```

2. **验证 Git 提交**
   ```bash
   cd /home/ubuntu/work/QuantClaw
   git log --oneline -5
   ```

3. **清理测试数据（可选）**
   ```bash
   # 清理记忆文件中的测试记录
   # 或保留作为演示数据
   ```

---

**下一步**：
- 如果测试通过，可以开始实际使用
- 如果测试失败，查看故障排查部分或反馈问题
