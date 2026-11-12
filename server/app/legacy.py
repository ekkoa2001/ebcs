import json
from email.parser import BytesParser
from email.policy import HTTP
from io import BytesIO

from starlette.requests import Request
from starlette.responses import Response

import server
import team_server


class BoundServer:
    def __init__(self):
        from app.config import settings
        self.allowed_hosts = set(settings["allowed_hosts"])
        self.secure = settings["secure"]


class LegacyHandler(team_server.Handler):
    def __init__(self, request: Request, body: bytes, path: str):
        self.client_address = (request.client.host if request.client else "127.0.0.1", 0)
        self.path = path
        self.command = request.method
        self.server = BoundServer()
        self.request_version = "HTTP/1.1"
        self.rfile = BytesIO(body)
        self.wfile = BytesIO()
        raw_headers = "".join(f"{key}: {value}\r\n" for key, value in request.headers.items()).encode() + b"\r\n"
        self.headers = BytesParser(policy=HTTP).parsebytes(raw_headers)
        self._status = 200
        self._header_pairs = []

    def send_response(self, code, message=None):
        self._status = code

    def send_header(self, keyword, value):
        self._header_pairs.append((keyword, value))

    def end_headers(self):
        return None

    def log_message(self, fmt, *args):
        return None


def _path_of(request: Request, override: str | None) -> str:
    if override:
        return override
    path = request.url.path
    if request.url.query:
        path += "?" + request.url.query
    return path


async def dispatch(request: Request, path: str | None = None) -> Response:
    body = await request.body()
    handler = LegacyHandler(request, body, _path_of(request, path))
    meta = {"ip": handler.client_address[0], "ua": request.headers.get("user-agent", ""), "module": "v1"}
    token = server.REQUEST_META.set(meta)
    try:
        if request.method == "GET":
            handler.do_GET()
        elif request.method == "POST":
            handler.do_POST()
        else:
            return Response(json.dumps({"error": "未找到"}, ensure_ascii=False), status_code=404, media_type="application/json")
    finally:
        server.REQUEST_META.reset(token)
    response = Response(content=handler.wfile.getvalue(), status_code=handler._status)
    for key, value in handler._header_pairs:
        if key.lower() == "content-length":
            continue
        response.headers.append(key, value)
    return response
