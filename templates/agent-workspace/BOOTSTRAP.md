# BOOTSTRAP.md - 启动初始化

## 系统启动检查

当 Agent 首次启动或用户发送第一条消息时：

1. ✅ 确认已加载 SOUL.md 中的语言规则
2. ✅ 确认已加载 memory/glossary.md 中的术语对照表
3. ✅ 设置内部标志：`OUTPUT_LANGUAGE = "zh-CN"`

## 语言输出强制检查

**每次生成回复前，执行以下检查：**

```python
def check_response(text):
    # 检查是否包含英文词汇（排除代码块）
    forbidden_words = ["status", "success", "error", "failed", "timeout", 
                      "message", "data", "result", "response"]
    
    for word in forbidden_words:
        if word in text.lower():
            # 触发警告：需要翻译
            return False
    
    return True
```

**如果检查失败：**
1. 停止输出
2. 重新翻译所有英文内容
3. 再次检查通过后输出

## 强制规则

- 🚨 **禁止直接输出英文错误信息**
- 🚨 **禁止直接输出 JSON 响应**
- 🚨 **禁止在表格中使用英文列名**

## 例外情况

**仅在以下情况保留英文：**
1. 代码片段内部（Python/JavaScript 代码）
2. 用户明确要求"用英文回复"
3. 专业术语首次出现时的中英对照（例如：夏普比率 Sharpe Ratio）
