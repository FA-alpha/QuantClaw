#!/usr/bin/env python3
"""
Agent 展示约束 — 通用模块

所有写操作脚本返回结果时必须附带 agent_display 字段，
明确告诉 Agent 该展示什么、不该做什么。

使用方法:
    from agent_display import blocked, prompt, preview, ok, error

    return blocked("金额超额", "...", rule="等用户重新输入", ...)
    return prompt("请输入金额", ...)
    return preview("手动加仓", ...)
    return ok("操作成功", ...)
    return error("网络错误", ...)
"""
from typing import Optional


def _build(
    status: str,
    title: str,
    lines: Optional[list] = None,
    user_prompt: str = "",
    blocked: bool = False,
    rule: str = "",
    **kwargs,
) -> dict:
    result = {
        "status": status,
        "agent_display": {
            "title": title,
            "lines": lines or [],
            "blocked": blocked,
            "rule": rule,
            "user_prompt": user_prompt,
        },
    }
    result.update(kwargs)
    return result


def blocked_result(
    title: str,
    reason: str,
    rule: str = "",
    user_prompt: str = "",
    **kwargs,
) -> dict:
    """操作被阻止：不可执行，Agent 必须等待用户处理"""
    return _build(
        status="blocked",
        title=title,
        lines=[reason],
        blocked=True,
        rule=rule or "该操作不可执行，不得尝试绕过或自行调整",
        user_prompt=user_prompt or "请检查后重新操作",
        **kwargs,
    )


def prompt_result(
    title: str,
    prompt_text: str,
    rule: str = "",
    **kwargs,
) -> dict:
    """需要用户输入：引导用户提供信息，Agent 不得代为决定"""
    return _build(
        status="prompt",
        title=title,
        lines=[prompt_text],
        blocked=True,
        rule=rule or "必须等待用户输入，不得代为决定或编造数据",
        user_prompt=prompt_text,
        **kwargs,
    )


def preview_result(
    title: str,
    detail_lines: list,
    rule: str = "",
    user_prompt: str = "",
    **kwargs,
) -> dict:
    """预览：展示操作详情，等待用户确认"""
    return _build(
        status="preview",
        title=title,
        lines=detail_lines,
        blocked=True,
        rule=rule or "必须等待用户确认后才执行，不得自行跳过确认步骤",
        user_prompt=user_prompt or "确认执行？回复「确认」或「取消」",
        **kwargs,
    )


def ok_result(
    title: str,
    detail_lines: Optional[list] = None,
    **kwargs,
) -> dict:
    """操作成功"""
    return _build(
        status="ok",
        title=title,
        lines=detail_lines or [],
        blocked=False,
        rule="",
        user_prompt="",
        **kwargs,
    )


def error_result(
    title: str,
    message: str,
    rule: str = "",
    **kwargs,
) -> dict:
    """错误：Agent 应展示错误信息，不得自行处理"""
    return _build(
        status="error",
        title=title,
        lines=[message],
        blocked=True,
        rule=rule or "该错误无法自动处理，请告知用户并等待指示",
        user_prompt="",
        **kwargs,
    )