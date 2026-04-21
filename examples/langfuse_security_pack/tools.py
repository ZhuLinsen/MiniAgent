"""Langfuse tools for AI data security threat analysis."""
###
# conda activate miniagent
# python -m miniagent --config examples/langfuse_security_pack/profile.json
# - MiniAgent LLM: LLM_API_KEY、LLM_MODEL，有些供应商还要 LLM_API_BASE
# - Langfuse: LANGFUSE_PUBLIC_KEY、LANGFUSE_SECRET_KEY，自托管通常还要 LANGFUSE_BASE_URL
# - 腾讯云 CLS: TENCENTCLOUD_SECRET_ID、TENCENTCLOUD_SECRET_KEY、TENCENTCLOUD_REGION
###

from __future__ import annotations

import json
import os
import re
import time
from datetime import datetime
from typing import Any, Dict, List

from miniagent.tools import register_tool

_MAX_LIMIT = 200
_DEFAULT_FIELDS = "core,basic"
_TENCENT_CLOUD_SECRET_ID = ""
_TENCENT_CLOUD_SECRET_KEY = ""
_TENCENT_CLOUD_REGION = ""
_SENSITIVE_PATTERNS = [
    re.compile(r"(?i)(authorization\s*[:=]\s*bearer\s+)[^\s\"']+"),
    re.compile(r"(?i)((api[_-]?key|secret|password|token|access[_-]?token)\s*[:=]\s*[\"']?)[^\s,\"']+"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{8,}\b"),
    re.compile(r"\bpk-[A-Za-z0-9_-]{8,}\b"),
]


def _to_plain(value: Any) -> Any:
    """Convert SDK response objects into plain Python structures."""

    if value is None:
        return None
    if hasattr(value, "to_json_string"):
        try:
            return json.loads(value.to_json_string())
        except Exception:
            pass
    if hasattr(value, "ToJsonString"):
        try:
            return json.loads(value.ToJsonString())
        except Exception:
            pass
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if hasattr(value, "dict"):
        return value.dict()
    if isinstance(value, dict):
        return {key: _to_plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_plain(item) for item in value]
    return value


def _dedupe_csv(value: str) -> str:
    """Normalize comma-separated field lists."""

    seen = set()
    items: List[str] = []
    for part in value.split(","):
        item = part.strip()
        if item and item not in seen:
            seen.add(item)
            items.append(item)
    return ",".join(items)


def _redact_text(text: str) -> str:
    """Mask likely secrets before returning data to the model."""

    masked = text
    for pattern in _SENSITIVE_PATTERNS:
        def _replace(match: re.Match[str]) -> str:
            # Preserve any safe prefix captured by the pattern; otherwise replace
            # the matched secret token outright.
            if match.lastindex:
                return f"{match.group(1)}[REDACTED]"
            return "[REDACTED]"

        masked = pattern.sub(_replace, masked)
    return masked


def _redact_value(value: Any) -> Any:
    """Recursively redact strings inside nested SDK payloads."""

    if isinstance(value, str):
        return _redact_text(value)
    if isinstance(value, dict):
        return {key: _redact_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_redact_value(item) for item in value]
    return value


def _extract_items(payload: Any) -> List[Dict[str, Any]]:
    """Extract observation data from v2 or legacy payload shapes."""

    if isinstance(payload, dict):
        data = payload.get("data")
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return [data]
    if isinstance(payload, list):
        return payload
    return []


def _extract_meta(payload: Any) -> Dict[str, Any]:
    """Extract pagination metadata from SDK responses."""

    if isinstance(payload, dict):
        meta = payload.get("meta")
        if isinstance(meta, dict):
            return meta
    return {}


def _parse_time_ms(value: Any) -> int:
    """Parse epoch seconds/milliseconds or ISO8601 text into milliseconds."""

    if isinstance(value, (int, float)):
        timestamp = int(value)
        return timestamp if timestamp >= 10**12 else timestamp * 1000

    text = str(value).strip()
    if not text:
        raise ValueError("time value is empty")

    if re.fullmatch(r"\d+", text):
        timestamp = int(text)
        return timestamp if len(text) >= 13 else timestamp * 1000

    normalized = text.replace("Z", "+00:00")
    dt = datetime.fromisoformat(normalized)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.now().astimezone().tzinfo)
    return int(dt.timestamp() * 1000)


def _unwrap_response(payload: Any) -> Any:
    """Unwrap Tencent Cloud SDK payloads that still include the Response shell."""

    if isinstance(payload, dict):
        response = payload.get("Response")
        if isinstance(response, dict):
            return response
    return payload


@register_tool
def langfuse_fetch_logs(
    trace_id: str = "",
    session_id: str = "",
    user_id: str = "",
    name: str = "",
    observation_type: str = "",
    level: str = "",
    from_start_time: str = "",
    to_start_time: str = "",
    limit: int = 20,
    cursor: str = "",
    fields: str = "",
    parse_io_as_json: bool = False,
    redact_sensitive: bool = True,
) -> Dict[str, Any]:
    """Fetch Langfuse observations for AI data-security threat analysis.

    Args:
        trace_id: Filter by trace ID.
        session_id: Filter by session ID.
        user_id: Filter by user ID.
        name: Filter by observation name.
        observation_type: GENERATION, SPAN, or EVENT.
        level: DEBUG, DEFAULT, WARNING, or ERROR.
        from_start_time: ISO8601 start time inclusive.
        to_start_time: ISO8601 end time exclusive.
        limit: Max observations to fetch. Values above 200 are clamped.
        cursor: Cursor from a previous result page.
        fields: Comma-separated field groups such as core,basic,io,metadata,usage.
        parse_io_as_json: Ask the SDK to parse JSON input/output when supported.
        redact_sensitive: Redact likely credentials before returning data.

    Returns:
        Structured result with warnings, query metadata, and observation items.
    """

    warnings: List[str] = []
    try:
        from langfuse import get_client
    except ImportError:
        return {
            "ok": False,
            "error": (
                "langfuse package is not installed. Install it in this external "
                "business pack environment instead of MiniAgent core."
            ),
            "warnings": [
                "developer_action_required: pip install langfuse",
                "design_note: keep Langfuse as an optional dependency in the external pack",
            ],
        }

    base_url = os.getenv("LANGFUSE_BASE_URL", "").strip()
    if not base_url:
        warnings.append(
            "developer_warning: LANGFUSE_BASE_URL is not explicitly set; self-hosted deployments should always set it"
        )
        base_url = "https://cloud.langfuse.com"
        warnings.append("default_applied: fallback base_url=https://cloud.langfuse.com")

    normalized_fields = _dedupe_csv(fields)
    if not normalized_fields:
        normalized_fields = _DEFAULT_FIELDS
        warnings.append("default_applied: fields=core,basic")

    if limit <= 0:
        limit = 20
        warnings.append("default_applied: limit=20 because a non-positive value was passed")
    elif limit > _MAX_LIMIT:
        limit = _MAX_LIMIT
        warnings.append("limit_clamped: limit reduced to 200 to avoid over-broad log retrieval")

    if redact_sensitive:
        warnings.append("privacy_guard: redact_sensitive=True")

    if not any([
        trace_id,
        session_id,
        user_id,
        name,
        observation_type,
        level,
        from_start_time,
        to_start_time,
    ]):
        warnings.append(
            "no_filter_warning: no explicit filter was provided; this may retrieve broad project-wide log data"
        )

    langfuse = get_client()
    if not langfuse.auth_check():
        return {
            "ok": False,
            "error": "Langfuse auth_check failed",
            "warnings": warnings + [
                "developer_action_required: verify LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, and LANGFUSE_BASE_URL"
            ],
        }

    query: Dict[str, Any] = {
        "trace_id": trace_id or None,
        "session_id": session_id or None,
        "user_id": user_id or None,
        "name": name or None,
        "type": observation_type or None,
        "level": level or None,
        "from_start_time": from_start_time or None,
        "to_start_time": to_start_time or None,
        "limit": limit,
        "cursor": cursor or None,
        "fields": normalized_fields,
        "parse_io_as_json": parse_io_as_json,
    }
    query = {key: value for key, value in query.items() if value not in (None, "", [])}

    payload: Any = None
    meta: Dict[str, Any] = {}
    items: List[Dict[str, Any]] = []
    v2_error = None

    observations_api = getattr(getattr(langfuse, "api", None), "observations", None)
    if observations_api is not None:
        try:
            payload = _to_plain(observations_api.get_many(**query))
            items = _extract_items(payload)
            meta = _extract_meta(payload)
        except Exception as exc:  # pragma: no cover - depends on SDK/server version
            v2_error = exc

    if not items:
        legacy_api_root = getattr(getattr(langfuse, "api", None), "legacy", None)
        legacy_observations = getattr(legacy_api_root, "observations_v1", None)
        if legacy_observations is not None:
            legacy_query = {
                key: value
                for key, value in query.items()
                if key not in {"fields", "cursor", "parse_io_as_json"}
            }
            try:
                payload = _to_plain(legacy_observations.get_many(**legacy_query))
                items = _extract_items(payload)
                meta = _extract_meta(payload)
                warnings.append(
                    "fallback_applied: observation query used legacy observations_v1 compatibility mode"
                )
            except Exception as exc:  # pragma: no cover - depends on SDK/server version
                if v2_error is not None:
                    return {
                        "ok": False,
                        "error": (
                            "langfuse query failed on both v2 and legacy endpoints: "
                            f"v2={v2_error}; legacy={exc}"
                        ),
                        "warnings": warnings,
                    }
                return {
                    "ok": False,
                    "error": f"langfuse legacy query failed: {exc}",
                    "warnings": warnings,
                }
        elif v2_error is not None:
            return {
                "ok": False,
                "error": f"langfuse observations query failed: {v2_error}",
                "warnings": warnings + [
                    "developer_notice: current SDK/server may not expose a compatible legacy observations API"
                ],
            }

    if redact_sensitive:
        items = _redact_value(items)

    if not items:
        warnings.append(
            "empty_result_notice: empty results may mean ingestion delay, narrow filters, unsupported self-hosted API features, or missing langfuse.flush() on the producer side"
        )

    return {
        "ok": True,
        "source": "langfuse",
        "resource": "observations",
        "warnings": warnings,
        "query": query,
        "base_url": base_url,
        "count": len(items),
        "next_cursor": meta.get("cursor"),
        "items": items,
    }


@register_tool
def tencent_cls_fetch_logs(
    topic_id: str,
    query_string: str = "*",
    from_time: str = "",
    to_time: str = "",
    region: str = "",
    limit: int = 20,
    offset: int = 0,
    context: str = "",
    sort: str = "desc",
    high_light: bool = False,
    query_syntax: int = 1,
    use_new_analysis: bool = True,
    redact_sensitive: bool = True,
    secret_id: str = "",
    secret_key: str = "",
) -> Dict[str, Any]:
    """Fetch Tencent Cloud CLS logs through the official Python SDK.

    Args:
        topic_id: CLS topic ID.
        query_string: CLS query string. Use * or an empty string to fetch all logs.
        from_time: Start time as epoch seconds, epoch milliseconds, or ISO8601.
        to_time: End time as epoch seconds, epoch milliseconds, or ISO8601.
        region: Tencent Cloud region such as ap-guangzhou.
        limit: Max logs to fetch. CLS SearchLog allows up to 1000.
        offset: Pagination offset. Ignored when context is provided.
        context: CLS pagination cursor returned by a previous query.
        sort: asc or desc.
        high_light: Whether to return highlighted matches.
        query_syntax: 0 for Lucene, 1 for CQL.
        use_new_analysis: Prefer the newer analysis response format.
        redact_sensitive: Redact likely credentials before returning data.
        secret_id: Optional override for Tencent Cloud SecretId.
        secret_key: Optional override for Tencent Cloud SecretKey.

    Returns:
        Structured CLS query result with warnings and log items.
    """

    warnings: List[str] = []

    try:
        from tencentcloud.common import credential
        from tencentcloud.common.exception.tencent_cloud_sdk_exception import (
            TencentCloudSDKException,
        )
        from tencentcloud.common.profile.client_profile import ClientProfile
        from tencentcloud.common.profile.http_profile import HttpProfile
        from tencentcloud.cls.v20201016 import cls_client, models
    except ImportError:
        return {
            "ok": False,
            "error": (
                "Tencent Cloud CLS SDK is not installed. Install the official SDK packages "
                "in this external business pack environment."
            ),
            "warnings": [
                "developer_action_required: pip install --upgrade tencentcloud-sdk-python-common tencentcloud-sdk-python-cls",
                "alternative_install: pip install --upgrade tencentcloud-sdk-python",
            ],
        }

    effective_secret_id = (
        secret_id.strip()
        or os.getenv("TENCENTCLOUD_SECRET_ID", "").strip()
        or _TENCENT_CLOUD_SECRET_ID.strip()
    )
    effective_secret_key = (
        secret_key.strip()
        or os.getenv("TENCENTCLOUD_SECRET_KEY", "").strip()
        or _TENCENT_CLOUD_SECRET_KEY.strip()
    )
    effective_region = (
        region.strip()
        or os.getenv("TENCENTCLOUD_REGION", "").strip()
        or _TENCENT_CLOUD_REGION.strip()
    )

    if not effective_secret_id or not effective_secret_key:
        return {
            "ok": False,
            "error": "Tencent Cloud credentials are missing",
            "warnings": [
                "developer_action_required: set TENCENTCLOUD_SECRET_ID and TENCENTCLOUD_SECRET_KEY",
                "visible_fill_in_spot: you can also fill _TENCENT_CLOUD_SECRET_ID and _TENCENT_CLOUD_SECRET_KEY in examples/langfuse_security_pack/tools.py",
            ],
        }

    if not effective_region:
        return {
            "ok": False,
            "error": "Tencent Cloud region is missing",
            "warnings": [
                "developer_action_required: pass region, set TENCENTCLOUD_REGION, or fill _TENCENT_CLOUD_REGION in examples/langfuse_security_pack/tools.py",
            ],
        }

    topic_id = topic_id.strip()
    if not topic_id:
        return {
            "ok": False,
            "error": "topic_id is required",
            "warnings": warnings,
        }

    now_ms = int(time.time() * 1000)
    if not to_time:
        to_ms = now_ms
        warnings.append("default_applied: to_time=now")
    else:
        try:
            to_ms = _parse_time_ms(to_time)
        except ValueError as exc:
            return {
                "ok": False,
                "error": f"invalid to_time: {exc}",
                "warnings": warnings,
            }

    if not from_time:
        from_ms = to_ms - 3600 * 1000
        warnings.append("default_applied: from_time=last_1h")
    else:
        try:
            from_ms = _parse_time_ms(from_time)
        except ValueError as exc:
            return {
                "ok": False,
                "error": f"invalid from_time: {exc}",
                "warnings": warnings,
            }

    if from_ms >= to_ms:
        return {
            "ok": False,
            "error": "from_time must be earlier than to_time",
            "warnings": warnings,
        }

    if not query_string.strip():
        query_string = "*"
        warnings.append("default_applied: query_string=*")

    if limit <= 0:
        limit = 20
        warnings.append("default_applied: limit=20 because a non-positive value was passed")
    elif limit > 1000:
        limit = 1000
        warnings.append("limit_clamped: limit reduced to 1000 to match CLS SearchLog limits")

    if offset < 0:
        offset = 0
        warnings.append("default_applied: offset=0 because a negative value was passed")

    sort = sort.lower().strip() or "desc"
    if sort not in {"asc", "desc"}:
        sort = "desc"
        warnings.append("default_applied: sort=desc because an invalid value was passed")

    if query_syntax not in {0, 1}:
        query_syntax = 1
        warnings.append("default_applied: query_syntax=1 because an invalid value was passed")

    if context and offset:
        offset = 0
        warnings.append("request_normalized: offset ignored because CLS Context and Offset cannot be used together")

    if redact_sensitive:
        warnings.append("privacy_guard: redact_sensitive=True")

    request_payload: Dict[str, Any] = {
        "TopicId": topic_id,
        "From": from_ms,
        "To": to_ms,
        "QueryString": query_string,
        "Limit": limit,
        "Sort": sort,
        "HighLight": high_light,
        "UseNewAnalysis": use_new_analysis,
        "QuerySyntax": query_syntax,
    }
    if context:
        request_payload["Context"] = context
    else:
        request_payload["Offset"] = offset

    try:
        cred = credential.Credential(effective_secret_id, effective_secret_key)
        http_profile = HttpProfile()
        http_profile.endpoint = "cls.tencentcloudapi.com"
        client_profile = ClientProfile()
        client_profile.httpProfile = http_profile
        client = cls_client.ClsClient(cred, effective_region, client_profile)

        request = models.SearchLogRequest()
        request.from_json_string(json.dumps(request_payload))
        response = client.SearchLog(request)
        payload = _unwrap_response(_to_plain(response))
    except TencentCloudSDKException as exc:
        return {
            "ok": False,
            "error": f"tencent cls SearchLog failed: {exc}",
            "warnings": warnings,
            "query": request_payload,
            "region": effective_region,
        }

    if redact_sensitive:
        payload = _redact_value(payload)

    results: List[Any] = []
    if isinstance(payload, dict):
        raw_results = payload.get("Results")
        if isinstance(raw_results, list):
            results = raw_results

    if not results:
        warnings.append(
            "empty_result_notice: empty results may mean narrow filters, wrong topic_id or region, ingestion delay, or an exhausted CLS context cursor"
        )

    return {
        "ok": True,
        "source": "tencent_cls",
        "resource": "SearchLog",
        "warnings": warnings,
        "region": effective_region,
        "topic_id": topic_id,
        "query": request_payload,
        "count": len(results),
        "list_over": payload.get("ListOver") if isinstance(payload, dict) else None,
        "next_context": payload.get("Context") if isinstance(payload, dict) else None,
        "analysis": payload.get("Analysis") if isinstance(payload, dict) else None,
        "columns": (
            payload.get("Columns") or payload.get("ColNames")
            if isinstance(payload, dict)
            else None
        ),
        "analysis_records": payload.get("AnalysisRecords") if isinstance(payload, dict) else None,
        "request_id": payload.get("RequestId") if isinstance(payload, dict) else None,
        "items": results,
    }
