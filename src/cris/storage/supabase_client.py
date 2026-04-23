from __future__ import annotations

from typing import Any

from supabase import Client, create_client

from src.cris.config import get_settings


def get_supabase_client() -> Client | None:
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_key:
        return None
    return create_client(settings.supabase_url, settings.supabase_key)


def upsert_rows(table: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    client = get_supabase_client()
    if client is None:
        return {"status": "skipped", "reason": "Supabase credentials not configured"}
    try:
        response = client.table(table).upsert(rows).execute()
        return {"status": "ok", "data": getattr(response, "data", None)}
    except Exception as exc:
        return {"status": "error", "reason": str(exc), "data": None}


def select_rows(table: str, columns: str = "*", limit: int | None = None) -> dict[str, Any]:
    client = get_supabase_client()
    if client is None:
        return {"status": "skipped", "reason": "Supabase credentials not configured", "data": []}

    try:
        query = client.table(table).select(columns)
        if limit is not None:
            query = query.limit(limit)
        response = query.execute()
        return {"status": "ok", "data": getattr(response, "data", [])}
    except Exception as exc:
        return {"status": "error", "reason": str(exc), "data": []}


def get_supabase_status() -> dict[str, Any]:
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_key:
        return {
            "status": "not_configured",
            "message": "Supabase URL or key is missing in .env",
            "tables": {},
        }

    tables_to_check = ["fir_documents", "fir_feature_rows", "fir_relationship_edges"]
    table_status: dict[str, str] = {}
    overall = "connected"
    message = "Supabase is reachable and the core CRIS tables are available."

    for table in tables_to_check:
        response = select_rows(table, columns="doc_id" if table != "fir_relationship_edges" else "edge_id", limit=1)
        table_status[table] = response["status"]
        if response["status"] == "error":
            overall = "schema_issue"
            message = response.get("reason", "Supabase is reachable but table access failed.")

    return {
        "status": overall,
        "message": message,
        "tables": table_status,
    }


def rpc(function_name: str, params: dict[str, Any]) -> dict[str, Any]:
    client = get_supabase_client()
    if client is None:
        return {"status": "skipped", "reason": "Supabase credentials not configured", "data": []}
    try:
        response = client.rpc(function_name, params).execute()
        return {"status": "ok", "data": getattr(response, "data", [])}
    except Exception as exc:
        return {"status": "error", "reason": str(exc), "data": []}
