#!/usr/bin/env python3
"""批量采集伙伴云工作区的表结构和自动化配置，输出结构化 JSON。"""

from __future__ import annotations

import json
import os
import sys

# 内置最小 Huoban automation API 客户端，保证不安装 hb-automation 也能运行备用采集脚本。
VENDOR_SCRIPTS = os.path.join(
    os.path.dirname(__file__),
    "vendor", "huoban_automation",
)
sys.path.insert(0, os.path.abspath(VENDOR_SCRIPTS))

from common import ENV_KEYS, load_config_from_env  # noqa: E402
from client import (  # noqa: E402
    list_tables,
    get_table_fields,
    list_automations,
    filter_automations,
    extract_layout_items,
    get_automation,
)


def _arg(flag: str) -> str | None:
    try:
        return sys.argv[sys.argv.index(flag) + 1]
    except (ValueError, IndexError):
        return None


def collect_fields(cfg, table_id):
    """采集表字段结构，提取关键信息。"""
    result = get_table_fields(cfg, table_id)
    # API 返回: {code, message, data: {table: {fields: [...]}}}
    table_data = result.get("data", {}).get("table", {})
    raw_fields = table_data.get("fields", [])

    fields = []
    relations = []
    for f in raw_fields:
        field_type = f.get("field_type", "")
        field_info = {
            "field_id": f.get("field_id"),
            "name": f.get("name", ""),
            "field_type": field_type,
            "required": f.get("required", False),
            "description": f.get("description", ""),
        }
        # 关联字段额外提取目标表
        if field_type == "relation":
            config = f.get("config", {})
            rel_table_id = config.get("table_id") or config.get("relation_table_id")
            field_info["relation_table_id"] = rel_table_id
            relations.append({
                "field_name": f.get("name", ""),
                "target_table_id": rel_table_id,
            })
        # 选项字段提取选项值
        if field_type in ("option", "category"):
            options = f.get("config", {}).get("options", [])
            field_info["options"] = [o.get("name", "") for o in options]
        fields.append(field_info)
    return fields, relations


def collect_automations(cfg, table_id, space_id):
    """采集表上的所有自动化（按钮、数据触发、调用触发等）。"""
    try:
        result = list_automations(cfg, table_id, space_id)
        items = extract_layout_items(result)
        automations = []
        for item in items:
            auto_id = item.get("automation_id") or item.get("button_id")
            auto_type = item.get("type", "")
            auto_name = item.get("name", "")
            automations.append({
                "automation_id": auto_id,
                "type": auto_type,
                "name": auto_name,
                "enabled": item.get("enabled", True),
            })
        return automations
    except Exception as e:
        return [{"error": str(e)}]


def collect_automation_detail(cfg, automation_id):
    """获取单条自动化的完整配置（节点详情）。"""
    try:
        result = get_automation(cfg, str(automation_id))
        data = result.get("data", result)
        nodes = data.get("nodes", [])
        simplified_nodes = []
        for node in nodes:
            n = {
                "node_id": node.get("node_id"),
                "node_type": node.get("node_type", ""),
                "name": node.get("name", ""),
            }
            # 提取跨表写入信息
            if node.get("node_type") in ("create_item", "update_item"):
                n["target_table_id"] = node.get("table_id")
            simplified_nodes.append(n)
        return simplified_nodes
    except Exception as e:
        return [{"error": str(e)}]


def main():
    space_id_str = _arg("--space")
    output_path = _arg("--output") or "meta_output.json"
    detail = "--detail" in sys.argv
    # 可选：只采集指定表名（逗号分隔）
    table_filter = _arg("--tables")
    filter_names = [n.strip() for n in table_filter.split(",")] if table_filter else []

    cfg = load_config_from_env()
    missing = [env_key for env_key, cfg_key in ENV_KEYS.items()
               if cfg_key != "default_space_id" and not cfg.get(cfg_key)]
    if missing:
        print(f"[ERR] missing environment variables: {', '.join(missing)}", file=sys.stderr)
        sys.exit(1)

    space_id = int(space_id_str) if space_id_str else int(cfg.get("default_space_id", 0))
    if not space_id:
        print("[ERR] no space_id provided and HB_DEFAULT_SPACE_ID is not set", file=sys.stderr)
        sys.exit(1)

    # 1. 拉取所有表
    print(f"[1/3] 拉取工作区 {space_id} 的表清单...", file=sys.stderr)
    tables_result = list_tables(cfg, space_id)
    # API 返回结构: {code, message, data: {tables: [...]}}
    data = tables_result.get("data", tables_result)
    tables = data.get("tables", [])
    print(f"  找到 {len(tables)} 张表", file=sys.stderr)

    # 建立 table_id -> name 映射（全量，用于解析关联目标）
    id_to_name = {}
    for t in tables:
        table_id = t.get("table_id")
        table_name = t.get("name", "")
        id_to_name[table_id] = table_name
        # 兼容字符串和数字 ID
        id_to_name[str(table_id)] = table_name

    # 按名称过滤
    if filter_names:
        tables = [t for t in tables if t.get("name", "") in filter_names]
        print(f"  过滤后 {len(tables)} 张表", file=sys.stderr)

    all_tables = []

    # 2. 逐表采集
    for i, t in enumerate(tables):
        table_id = t.get("table_id")
        table_name = t.get("name", "")
        print(f"[2/3] ({i+1}/{len(tables)}) 采集 {table_name} ...", file=sys.stderr)

        fields, relations = collect_fields(cfg, table_id)
        automations = collect_automations(cfg, table_id, space_id)

        # 关联字段的目标表名
        for rel in relations:
            target_id = rel.get("target_table_id")
            rel["target_table_name"] = id_to_name.get(str(target_id), id_to_name.get(target_id, f"unknown({target_id})"))

        table_meta = {
            "table_id": table_id,
            "table_name": table_name,
            "fields": fields,
            "relations": relations,
            "automations": automations,
        }

        # 可选：采集自动化详情（节点级别）
        if detail and automations:
            for auto in automations:
                if isinstance(auto, dict) and "error" not in auto:
                    auto_id = auto.get("automation_id")
                    if auto_id:
                        auto["nodes"] = collect_automation_detail(cfg, auto_id)

        all_tables.append(table_meta)

    # 3. 输出
    output = {
        "space_id": space_id,
        "table_count": len(all_tables),
        "tables": all_tables,
        "table_id_map": {str(k): v for k, v in id_to_name.items()},
    }

    print(f"[3/3] 写入 {output_path}", file=sys.stderr)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"Done. {len(all_tables)} tables collected.", file=sys.stderr)


if __name__ == "__main__":
    main()
