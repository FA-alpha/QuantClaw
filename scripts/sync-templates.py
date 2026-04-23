#!/usr/bin/env python3
"""
同步模板到现有用户工作区

用法:
    python sync-templates.py                    # 更新所有 .md 文件
    python sync-templates.py --files SOUL.md    # 只更新指定文件
    python sync-templates.py --dry-run          # 预览不实际执行
    python sync-templates.py --exclude USER.md  # 排除特定文件
"""

import os
import sys
import shutil
import argparse
from pathlib import Path
from datetime import datetime

# 默认路径
DEFAULT_TEMPLATE_DIR = Path.home() / 'work/QuantClaw/templates/agent-workspace'
DEFAULT_WORKSPACE_BASE = Path.home() / 'quantclaw-users'


def backup_file(file_path: Path, backup_dir: Path) -> bool:
    """备份单个文件"""
    try:
        backup_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(file_path, backup_dir / file_path.name)
        return True
    except Exception as e:
        print(f"   ⚠️  备份失败: {e}")
        return False


def sync_templates(template_dir: Path, workspace_base: Path, 
                   files: list = None, exclude: list = None, 
                   dry_run: bool = False) -> dict:
    """
    同步模板到用户工作区
    
    Args:
        template_dir: 模板目录
        workspace_base: 用户工作区基础路径
        files: 指定要更新的文件（None = 全部）
        exclude: 要排除的文件
        dry_run: 预览模式
    
    Returns:
        dict: 统计信息
    """
    stats = {
        'users_updated': 0,
        'files_updated': 0,
        'files_failed': 0,
        'users_skipped': 0
    }
    
    if not template_dir.exists():
        print(f"❌ 模板目录不存在: {template_dir}")
        return stats
    
    if not workspace_base.exists():
        print(f"⚠️  用户工作区不存在: {workspace_base}")
        print(f"    没有需要更新的用户")
        return stats
    
    # 获取模板文件列表
    if files:
        template_files = [template_dir / f for f in files if (template_dir / f).exists()]
    else:
        template_files = list(template_dir.glob('*.md'))
    
    # 应用排除规则
    if exclude:
        template_files = [f for f in template_files if f.name not in exclude]
    
    if not template_files:
        print("❌ 没有找到需要同步的模板文件")
        return stats
    
    print(f"📋 同步模板到现有用户工作区")
    print(f"   模板: {template_dir}")
    print(f"   用户: {workspace_base}")
    print(f"   文件: {', '.join(f.name for f in template_files)}")
    if dry_run:
        print(f"   ⚠️  预览模式（不会实际修改）")
    print()
    
    # 遍历所有用户工作区
    user_workspaces = sorted(workspace_base.glob('qc-*'))
    
    if not user_workspaces:
        print("ℹ️  没有找到用户工作区")
        return stats
    
    for user_workspace in user_workspaces:
        if not user_workspace.is_dir():
            continue
        
        user_id = user_workspace.name
        print(f"🔄 更新: {user_id}")
        
        # 创建备份目录
        timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        backup_dir = user_workspace / f'.backup-{timestamp}'
        
        files_updated_count = 0
        
        # 复制模板文件
        for template_file in template_files:
            filename = template_file.name
            target = user_workspace / filename
            
            # 备份现有文件
            if target.exists() and not dry_run:
                backup_file(target, backup_dir)
            
            # 复制新模板
            try:
                if dry_run:
                    print(f"   [预览] {filename}")
                    files_updated_count += 1
                else:
                    shutil.copy2(template_file, target)
                    print(f"   ✅ {filename}")
                    files_updated_count += 1
                    stats['files_updated'] += 1
            except Exception as e:
                print(f"   ❌ {filename} (失败: {e})")
                stats['files_failed'] += 1
        
        if not dry_run and files_updated_count > 0:
            print(f"   💾 备份: {backup_dir}")
        
        if files_updated_count > 0:
            stats['users_updated'] += 1
        else:
            stats['users_skipped'] += 1
        
        print()
    
    return stats


def main():
    parser = argparse.ArgumentParser(description='同步模板到现有用户工作区')
    parser.add_argument('--template-dir', type=Path, default=DEFAULT_TEMPLATE_DIR,
                        help=f'模板目录 (默认: {DEFAULT_TEMPLATE_DIR})')
    parser.add_argument('--workspace-base', type=Path, default=DEFAULT_WORKSPACE_BASE,
                        help=f'用户工作区基础路径 (默认: {DEFAULT_WORKSPACE_BASE})')
    parser.add_argument('--files', nargs='+', metavar='FILE',
                        help='指定要更新的文件（如 SOUL.md AGENTS.md）')
    parser.add_argument('--exclude', nargs='+', metavar='FILE',
                        help='排除的文件（如 USER.md）')
    parser.add_argument('--dry-run', action='store_true',
                        help='预览模式，不实际修改文件')
    
    args = parser.parse_args()
    
    stats = sync_templates(
        template_dir=args.template_dir,
        workspace_base=args.workspace_base,
        files=args.files,
        exclude=args.exclude,
        dry_run=args.dry_run
    )
    
    print("📊 完成")
    print(f"   更新用户: {stats['users_updated']}")
    print(f"   更新文件: {stats['files_updated']}")
    if stats['files_failed'] > 0:
        print(f"   失败: {stats['files_failed']}")
    if stats['users_skipped'] > 0:
        print(f"   跳过: {stats['users_skipped']}")
    
    if args.dry_run:
        print()
        print("⚠️  预览模式完成，使用 --dry-run 参数实际执行")


if __name__ == '__main__':
    main()
