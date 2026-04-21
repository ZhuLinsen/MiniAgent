"""Minimal HTTP control plane for the interactive MiniAgent CLI."""

from __future__ import annotations

import json
import os
import threading
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, Optional, Tuple
from urllib.parse import parse_qs, urlparse

from .logger import get_logger

logger = get_logger(__name__)


class AgentBusyError(RuntimeError):
    """Raised when the current MiniAgent session is already handling a request."""


def _normalize_host(host: str) -> str:
    """Trim brackets from IPv6 literals to simplify comparisons."""

    host = host.strip()
    if host.startswith("[") and host.endswith("]"):
        return host[1:-1]
    return host


def is_loopback_host(host: str) -> bool:
    """Return True when the host is a loopback-only address."""

    normalized = _normalize_host(host).lower()
    return normalized in {"127.0.0.1", "localhost", "::1"}


def parse_control_http_address(spec: str) -> Tuple[str, int]:
    """Parse ``[HOST:]PORT`` into a normalized host/port tuple."""

    raw = (spec or "").strip()
    if not raw:
        raise ValueError("control-http address cannot be empty")

    if raw.isdigit():
        port = int(raw)
        if not 0 <= port <= 65535:
            raise ValueError("control-http port must be between 0 and 65535")
        return "127.0.0.1", port

    if ":" not in raw:
        raise ValueError("control-http must be in PORT or HOST:PORT format")

    host, port_text = raw.rsplit(":", 1)
    host = host.strip() or "127.0.0.1"
    try:
        port = int(port_text)
    except ValueError as exc:
        raise ValueError("control-http port must be an integer") from exc

    if not 0 <= port <= 65535:
        raise ValueError("control-http port must be between 0 and 65535")
    return _normalize_host(host), port


@dataclass
class ControlPlaneHandle:
    """Running HTTP control plane server plus its background thread."""

    server: ThreadingHTTPServer
    thread: threading.Thread
    host: str
    port: int

    @property
    def address(self) -> str:
        return f"{self.host}:{self.port}"

    def close(self) -> None:
        """Stop the HTTP server and wait briefly for the background thread."""

        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)


class _ControlRequestHandler(BaseHTTPRequestHandler):
    """HTTP request handler for the MiniAgent control plane."""

    protocol_version = "HTTP/1.1"
    server: "_MiniAgentControlHTTPServer"

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
        logger.debug("control-http %s - " + format, self.client_address[0], *args)

    def _send_json(self, status_code: int, payload: Dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.close_connection = True
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(body)

    def _start_ndjson_stream(self) -> None:
        self.close_connection = True
        self.send_response(200)
        self.send_header("Content-Type", "application/x-ndjson; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.flush()

    def _write_ndjson_event(self, payload: Dict[str, Any]) -> bool:
        try:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8") + b"\n"
            self.wfile.write(body)
            self.wfile.flush()
            return True
        except (BrokenPipeError, ConnectionResetError, OSError):
            logger.warning("control-http stream client disconnected while writing events")
            return False

    def _send_error(self, status_code: int, error: str, message: str) -> None:
        self._send_json(status_code, {"ok": False, "error": error, "message": message})

    def _require_auth(self) -> bool:
        if self.path.startswith("/healthz"):
            return True

        token = self.server.control_token
        if not token:
            return True

        header = self.headers.get("Authorization", "")
        expected = f"Bearer {token}"
        if header == expected:
            return True

        self._send_error(401, "unauthorized", "missing or invalid bearer token")
        return False

    def _read_json_body(self) -> Optional[Dict[str, Any]]:
        content_length = self.headers.get("Content-Length", "").strip()
        if not content_length:
            self._send_error(400, "invalid_request", "missing Content-Length header")
            return None

        try:
            size = int(content_length)
        except ValueError:
            self._send_error(400, "invalid_request", "invalid Content-Length header")
            return None

        raw = self.rfile.read(size)
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._send_error(400, "invalid_request", "request body must be valid JSON")
            return None

        if not isinstance(payload, dict):
            self._send_error(400, "invalid_request", "request body must be a JSON object")
            return None
        return payload

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)

        if parsed.path == "/healthz":
            self._send_json(200, {"ok": True})
            return

        if not self._require_auth():
            return

        if parsed.path == "/v1/session":
            self._send_json(200, self.server.runtime.get_session_info())
            return

        if parsed.path == "/v1/history":
            query = parse_qs(parsed.query)
            limit_text = (query.get("limit") or ["20"])[0]
            try:
                limit = int(limit_text)
            except ValueError:
                self._send_error(400, "invalid_request", "history limit must be an integer")
                return

            if limit < 0:
                self._send_error(400, "invalid_request", "history limit must be non-negative")
                return

            self._send_json(200, {"ok": True, "messages": self.server.runtime.get_history(limit=limit)})
            return

        self._send_error(404, "not_found", f"unknown path: {parsed.path}")

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)

        if not self._require_auth():
            return

        if parsed.path == "/v1/interrupt":
            self._send_error(501, "not_implemented_yet", "interrupt support has not been implemented yet")
            return

        if parsed.path != "/v1/message":
            self._send_error(404, "not_found", f"unknown path: {parsed.path}")
            return

        payload = self._read_json_body()
        if payload is None:
            return

        text = payload.get("text", "")
        if not isinstance(text, str) or not text.strip():
            self._send_error(400, "invalid_request", "field 'text' is required")
            return

        mode = payload.get("mode")
        if mode not in (None, "text", "native"):
            self._send_error(400, "invalid_request", "field 'mode' must be 'text' or 'native'")
            return

        stream = bool(payload.get("stream", False))
        if stream:
            request_id = payload.get("request_id")
            if isinstance(request_id, str) and request_id:
                accepted_event = {"type": "request.accepted", "request_id": request_id}
                complete_ok_event = {"type": "request.complete", "ok": True, "request_id": request_id}
            else:
                request_id = None
                accepted_event = {"type": "request.accepted"}
                complete_ok_event = {"type": "request.complete", "ok": True}

            self._start_ndjson_stream()
            stream_open = True

            def _emit_stream_event(event: Dict[str, Any]) -> None:
                nonlocal stream_open
                if not stream_open:
                    return
                stream_open = self._write_ndjson_event(event)

            _emit_stream_event(accepted_event)

            try:
                self.server.runtime.process_message(
                    text.strip(),
                    mode=mode,
                    use_streaming=True,
                    capture_events=False,
                    event_callback=_emit_stream_event,
                )
            except AgentBusyError:
                _emit_stream_event({
                    "type": "error",
                    "error": "agent_busy",
                    "message": "the current MiniAgent session is already processing a request",
                })
                _emit_stream_event({
                    "type": "request.complete",
                    "ok": False,
                    **({"request_id": request_id} if request_id else {}),
                })
                return
            except Exception as exc:  # pragma: no cover - exercised through integration, not unit tests
                logger.error("control-http streaming message handling failed: %s", exc)
                _emit_stream_event({
                    "type": "error",
                    "error": "internal_error",
                    "message": str(exc),
                })
                _emit_stream_event({
                    "type": "request.complete",
                    "ok": False,
                    **({"request_id": request_id} if request_id else {}),
                })
                return

            _emit_stream_event(complete_ok_event)
            return

        request_id = payload.get("request_id")
        events = []
        if isinstance(request_id, str) and request_id:
            events.append({"type": "request.accepted", "request_id": request_id})
        else:
            request_id = None
            events.append({"type": "request.accepted"})

        try:
            result = self.server.runtime.process_message(
                text.strip(),
                mode=mode,
                use_streaming=False,
                capture_events=True,
            )
        except AgentBusyError:
            self._send_error(409, "agent_busy", "the current MiniAgent session is already processing a request")
            return
        except Exception as exc:  # pragma: no cover - exercised through integration, not unit tests
            logger.error("control-http message handling failed: %s", exc)
            self._send_error(500, "internal_error", str(exc))
            return

        events.extend(result["events"])
        if request_id:
            events.append({"type": "request.complete", "ok": True, "request_id": request_id})
        else:
            events.append({"type": "request.complete", "ok": True})

        self._send_json(
            200,
            {
                "ok": True,
                "request_id": request_id,
                "content": result["content"],
                "events": events,
            },
        )


class _MiniAgentControlHTTPServer(ThreadingHTTPServer):
    """Custom server type carrying MiniAgent runtime references."""

    daemon_threads = True

    def __init__(
        self,
        server_address: Tuple[str, int],
        runtime: Any,
        control_token: Optional[str],
    ):
        super().__init__(server_address, _ControlRequestHandler)
        self.runtime = runtime
        self.control_token = control_token


def start_control_server(runtime: Any, spec: str) -> ControlPlaneHandle:
    """Start the HTTP control plane in a daemon thread."""

    host, port = parse_control_http_address(spec)
    token = os.environ.get("MINIAGENT_CONTROL_TOKEN", "").strip() or None

    if token is None and not is_loopback_host(host):
        raise ValueError(
            "control-http on a non-loopback host requires MINIAGENT_CONTROL_TOKEN to be set"
        )

    server = _MiniAgentControlHTTPServer((host, port), runtime=runtime, control_token=token)
    real_host, real_port = server.server_address[:2]
    handle = ControlPlaneHandle(
        server=server,
        thread=threading.Thread(target=server.serve_forever, daemon=True),
        host=_normalize_host(str(real_host)),
        port=int(real_port),
    )
    handle.thread.start()
    return handle
