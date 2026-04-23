#!/bin/bash
# 同步模板到现有用户工作区

TEMPLATE_DIR="${TEMPLATE_DIR:-$HOME/work/QuantClaw/templates/agent-workspace}"
WORKSPACE_BASE="${WORKSPACE_BASE:-$HOME/quantclaw-users}"

if [ ! -d "$TEMPLATE_DIR" ]; then
    echo "❌ 模板目录不存在: $TEMPLATE_DIR"
    exit 1
fi

if [ ! -d "$WORKSPACE_BASE" ]; then
    echo "⚠️  用户工作区不存在: $WORKSPACE_BASE"
    echo "    没有需要更新的用户"
    exit 0
fi

echo "📋 同步模板到现有用户工作区"
echo "   模板: $TEMPLATE_DIR"
echo "   用户: $WORKSPACE_BASE"
echo ""

# 统计
updated=0
failed=0

# 遍历所有用户工作区
for user_workspace in "$WORKSPACE_BASE"/qc-*; do
    if [ ! -d "$user_workspace" ]; then
        continue
    fi
    
    user_id=$(basename "$user_workspace")
    echo "🔄 更新: $user_id"
    
    # 备份现有文件
    backup_dir="$user_workspace/.backup-$(date +%Y%m%d-%H%M%S)"
    mkdir -p "$backup_dir"
    
    # 复制所有 .md 模板文件
    for template_file in "$TEMPLATE_DIR"/*.md; do
        if [ -f "$template_file" ]; then
            filename=$(basename "$template_file")
            target="$user_workspace/$filename"
            
            # 备份现有文件
            if [ -f "$target" ]; then
                cp "$target" "$backup_dir/" 2>/dev/null
            fi
            
            # 复制新模板
            if cp "$template_file" "$target" 2>/dev/null; then
                echo "   ✅ $filename"
            else
                echo "   ❌ $filename (失败)"
                ((failed++))
            fi
        fi
    done
    
    echo "   💾 备份: $backup_dir"
    ((updated++))
    echo ""
done

echo "📊 完成"
echo "   更新用户: $updated"
echo "   失败: $failed"

if [ $updated -eq 0 ]; then
    echo ""
    echo "ℹ️  没有找到需要更新的用户工作区"
fi
