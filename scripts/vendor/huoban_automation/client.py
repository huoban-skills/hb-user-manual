#!/usr/bin/env python3
"""Shared automation API client helpers for Huoban skills."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from common import (
    OPENAPI_BASE,
    PAAS_BASE,
    build_openapi_headers,
    build_paas_headers,
    http_json,
)

CREATE_ENDPOINTS = {
    "button": "button",
    "call": "call",
    "item_trigger": "item_trigger",
}


def paas_request(
    method: str,
    url: str,
    cfg: Dict[str, Any],
    payload: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return http_json(method, url, build_paas_headers(cfg), payload)


def openapi_request(
    method: str,
    url: str,
    cfg: Dict[str, Any],
    payload: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return http_json(method, url, build_openapi_headers(cfg), payload)


def resolve_space_id(cfg: Dict[str, Any], space_id: Optional[int] = None) -> int:
    return int(space_id or cfg.get("default_space_id") or 0)


def create_automation(
    cfg: Dict[str, Any],
    automation_type: str,
    automation_body: Dict[str, Any],
) -> Dict[str, Any]:
    endpoint = CREATE_ENDPOINTS.get(automation_type, automation_type)
    return paas_request("POST", f"{PAAS_BASE}/{endpoint}", cfg, automation_body)


def list_automations(
    cfg: Dict[str, Any],
    table_id: int,
    space_id: Optional[int] = None,
) -> Dict[str, Any]:
    resolved_space = resolve_space_id(cfg, space_id)
    url = (
        f"https://api.huoban.com/paasapi/admin/space/{resolved_space}/source_type/automation/layout"
        f"?automation_table_id={table_id}"
    )
    return paas_request("GET", url, cfg)


def get_automation(cfg: Dict[str, Any], automation_id: str) -> Dict[str, Any]:
    return paas_request("GET", f"{PAAS_BASE}/{automation_id}", cfg)


def update_automation(
    cfg: Dict[str, Any],
    automation_id: str,
    automation_body: Dict[str, Any],
) -> Dict[str, Any]:
    body = dict(automation_body)
    body["automation_id"] = int(automation_id)
    return paas_request("PUT", f"{PAAS_BASE}/{automation_id}", cfg, body)


def delete_automation(cfg: Dict[str, Any], automation_id: str) -> Dict[str, Any]:
    return paas_request("DELETE", f"{PAAS_BASE}/{automation_id}", cfg)


def extract_layout_items(result: Dict[str, Any]) -> List[Dict[str, Any]]:
    layout = result.get("layout") or []
    if not layout:
        return []
    return layout[0].get("automation_list", [])


def filter_automations(result: Dict[str, Any], automation_type: str) -> List[Dict[str, Any]]:
    return [item for item in extract_layout_items(result) if item.get("type") == automation_type]


def extract_automation_id(result: Dict[str, Any]) -> Optional[Any]:
    data = result.get("data") or {}
    return data.get("automation_id") or data.get("button_id") or result.get("automation_id")


def list_tables(cfg: Dict[str, Any], space_id: Optional[int] = None) -> Dict[str, Any]:
    resolved_space = resolve_space_id(cfg, space_id)
    return openapi_request("POST", f"{OPENAPI_BASE}/table/list", cfg, {"space_id": str(resolved_space)})


def get_table_fields(cfg: Dict[str, Any], table_id: int) -> Dict[str, Any]:
    return openapi_request("POST", f"{OPENAPI_BASE}/table/{table_id}", cfg)


def edit_url(
    automation_type: str,
    space_id: Optional[int],
    table_id: Optional[int],
    automation_id: Optional[Any],
) -> Optional[str]:
    if not (space_id and table_id and automation_id):
        return None
    path_type = CREATE_ENDPOINTS.get(automation_type, automation_type)
    return (
        f"https://app.huoban.com/admin/spaces/{space_id}/tables/{table_id}"
        f"/automations/{path_type}/{automation_id}/edit"
    )
