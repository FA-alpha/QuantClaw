#!/usr/bin/env python3
"""
API 通用请求模块 — fourieralpha 平台 HTTP 请求封装

统一管理：
  - BASE_URL / POST 请求
  - 日志记录（通过 scripts/logging）
  - 鉴权检查
  - 错误处理

所有 skill 脚本应该通过此模块发请求，不再各自裸调 requests。
"""
import sys
import os
import requests
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.logging import log_http_request, log_error

BASE_URL = "https://www.fourieralpha.com/Mobile"


def api_post(
    path: str,
    params: dict,
    agent_id: Optional[str] = None,
    timeout: int = 30,
) -> dict:
    """
    通用 POST 请求，统一日志 + 错误处理。

    成功返回 API 原始 dict；
    网络/脚本异常返回 {"_error": "..."}

    Usage:
        data = api_post("/Trade/lists", {"usertoken": t, ...}, agent_id="qc-xxx")
        if data.get("_error"):
            # handle error
    """
    url = f"{BASE_URL}{path}"
    try:
        resp = requests.post(url, data=params, timeout=timeout)
        result = resp.json()
        log_http_request(url, params, response=result, agent_id=agent_id)
        return result
    except requests.RequestException as e:
        log_error(str(e), exception=e, context={"url": url}, agent_id=agent_id)
        return {"_error": f"网络请求异常: {str(e)}"}
    except Exception as e:
        log_error(str(e), exception=e, context={"url": url}, agent_id=agent_id)
        return {"_error": f"脚本异常: {str(e)}"}


def check_auth(data: dict) -> tuple:
    """
    检查 API 鉴权状态。

    Returns:
        (ok: bool, message: str)

    Usage:
        ok, msg = check_auth(data)
        if not ok:
            return {"status": "error", "message": msg}
    """
    if data.get("_error"):
        return False, data["_error"]
    if data.get("status") == 0:
        info = data.get("info", "未知错误")
        info_str = str(info)
        # version 字段缺失视为兼容性问题，不报错
        if "Column not found" in info_str and "version" in info_str:
            return True, ""
        return False, info_str
    return True, ""


def check_status(data: dict) -> bool:
    """
    检查 API 业务状态（status == 1）。

    返回 True 表示业务成功。
    """
    return data.get("status") == 1