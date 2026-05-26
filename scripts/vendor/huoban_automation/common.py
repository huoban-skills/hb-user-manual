#!/usr/bin/env python3
"""Shared helpers for Huoban automation skills."""

from __future__ import annotations

import json
import os
import uuid
from typing import Any, Dict, Optional

try:
    import requests as _requests
    _USE_REQUESTS = True
except ImportError:
    import urllib.error
    import urllib.request
    _USE_REQUESTS = False

ENV_KEYS = {
    "HB_API_KEY": "api_key",
    "HB_ACCESS_TOKEN": "access_token",
    "HB_TENANT_ID": "tenant_id",
    "HB_TOKEN_COMPANY": "token_company",
    "HB_DEFAULT_SPACE_ID": "default_space_id",
}

PAAS_BASE = "https://api.huoban.com/paas/automation"
OPENAPI_BASE = "https://api.huoban.com/openapi/v1"


def read_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def load_config_from_env() -> Dict[str, Any]:
    cfg: Dict[str, Any] = {
        "api_key": "",
        "access_token": "",
        "tenant_id": "",
        "token_company": "",
        "default_space_id": 0,
    }
    for env_key, cfg_key in ENV_KEYS.items():
        value = os.environ.get(env_key, "")
        if value:
            if cfg_key == "default_space_id":
                cfg[cfg_key] = int(value)
            else:
                cfg[cfg_key] = value
    return cfg


def mask_secret(value: Any, keep: int = 12) -> str:
    text = str(value or "")
    if not text:
        return ""
    if len(text) <= keep:
        return text
    return f"{text[:keep]}..."


def check_session_config(cfg: Dict[str, Any]) -> bool:
    return bool(cfg.get("access_token") and cfg.get("tenant_id") and cfg.get("token_company"))


def check_apikey(cfg: Dict[str, Any]) -> bool:
    return bool(cfg.get("api_key"))


def build_paas_headers(cfg: Dict[str, Any]) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {cfg['access_token']}",
        "Content-Type": "application/json",
        "x-huoban-client-id": "1",
        "x-huoban-language": "zh-CN",
        "x-huoban-tenant-id": str(cfg["tenant_id"]),
        "x-huoban-token-company": cfg["token_company"],
        "x-huoban-request-id": uuid.uuid4().hex,
    }


def build_openapi_headers(cfg: Dict[str, Any]) -> Dict[str, str]:
    return {
        "Open-Authorization": f"Bearer {cfg['api_key']}",
        "Content-Type": "application/json",
    }


def http_json(
    method: str,
    url: str,
    headers: Dict[str, str],
    payload: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    body = json.dumps(payload, ensure_ascii=False) if payload is not None else None
    if _USE_REQUESTS:
        try:
            resp = _requests.request(
                method,
                url,
                headers=headers,
                data=body.encode("utf-8") if body is not None else None,
                timeout=30,
            )
            try:
                return resp.json()
            except Exception:
                return {"error": True, "status": resp.status_code, "message": resp.text}
        except Exception as exc:
            return {"error": True, "message": str(exc)}
    else:
        import urllib.error, urllib.request
        data = body.encode("utf-8") if body is not None else None
        request = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8")
            try:
                return json.loads(raw)
            except Exception:
                return {"error": True, "status": exc.code, "message": raw}
        except Exception as exc:
            return {"error": True, "message": str(exc)}
