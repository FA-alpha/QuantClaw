# QuantClaw 回测技能 v2.0
### 停止阅读该文件,因该文件目前尚在开发中
### 🔑 重要: UserToken 获取方法

#### UserToken 获取规则
1. 使用 jq 工具从 ~/.quantclaw/users.json 获取
2. 必须传入当前机器人的 agentID
3. 获取失败时需要重试机制

```bash
# UserToken 获取示例
USERTOKEN=$(cat ~/.quantclaw/users.json | jq -r --arg agent_id "当前机器人agentID" '.users[] | select(.agentId == $agent_id) | .token')
```

#### 获取流程
1. 先获取当前机器人的 agentID
2. 通过 agentID 查询对应的 UserToken
3. 检查 UserToken 是否为空
   - 如果为空，等待2秒后重试
   - 最大重试次数为5次
4. 重试5次仍失败，通知用户

#### 注意事项
- UserToken 是唯一的用户认证凭证
- 所有接口调用必须使用此 UserToken
- 不要与其他 Token 概念混淆

## 回测流程

### 第一步：确认回测目标
- 根据用户输入或上下文确定回测目标
- 处理不同程度的模糊描述
  - 精确到具体策略ID
  - 精确到策略组ID
  - 模糊描述（如"最新的风霆V4策略"）

#### 判断目标类型
- 具体策略：已明确策略ID
- 具体策略组：已明确策略组ID
- 模糊描述：需进入策略查找步骤

### 第二步：策略查找
- 仅在用户未明确指定策略/策略组时启用
- 策略组查找：调用 `Strategy/group_lists` 接口
- 策略查找：调用 `Strategy/lists` 接口

#### 查找策略组规则
- 未指定具体名称：默认查询全部
- 指定策略组名称：使用 `search_val` 或 `search_name` 参数
- 可选筛选：状态、分页等

#### 查找策略规则
- 时间相关筛选：不传 `search_val`
- 策略名称筛选：传入具体名称
- 可选筛选：币种、交易类型、状态等

### 第三步：确认回测策略
- 从查找结果中确认最终回测策略
- 用户确认或系统智能推荐
- 检查策略可用性和适用性