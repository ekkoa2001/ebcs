import json
import re
from pathlib import Path
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


_ASSET_REF = re.compile(br'(?P<attr>(?:src|href)=")(?P<path>/[^"?]+\.(?:js|css))(?:\?[^"]*)?"')


def stamp_assets(body: bytes, web_root: Path) -> bytes:
    """Point every stylesheet and script at the current file, not a frozen query."""
    def repl(match: re.Match[bytes]) -> bytes:
        file = web_root / match.group("path").decode().lstrip("/")
        if not file.is_file():
            return match.group(0)
        version = str(file.stat().st_mtime_ns).encode()
        return match.group("attr") + match.group("path") + b"?v=" + version + b'"'
    return _ASSET_REF.sub(repl, body)


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
    rendered_body = handler.wfile.getvalue()
    # Keep the display name consistent for the legacy HTML shells as well as
    # the upgraded workspace.  EBCS is the compact form used where spaces are
    # not suitable, such as the visual eyebrow label.
    if request.method == "GET" and request.url.path in {"/", "/index.html", "/login.html", "/first-password.html", "/admin"}:
        rendered_body = rendered_body.replace(b"Ekko Script Web", b"Ekko Brand Content Strategy")
        rendered_body = rendered_body.replace(b"EkkoHub ", b"Ekko Brand Content Strategy ")
        rendered_body = rendered_body.replace(b"EKKO SCRIPT WEB", b"EBCS")
    # The legacy workspace is still the active front end.  Attach isolated UI
    # enhancement assets only to that workspace instead of editing the large
    # generated HTML document or changing any of its business scripts.
    if request.method == "GET" and request.url.path in {"/", "/index.html"} and b'id="homeView"' in rendered_body:
        # These assets are immutable in HTTP caches.  Derive their URL version
        # from their update timestamp so a CSS or JS fix is never hidden behind
        # an older, indefinitely cached release.
        web_root = Path(__file__).resolve().parents[2] / "web"
        def asset_version(relative_path: str) -> str:
            return str((web_root / relative_path).stat().st_mtime_ns)
        style_tag = f'<link rel="stylesheet" href="/assets/css/ui-upgrade.css?v={asset_version("assets/css/ui-upgrade.css")}">'.encode()
        script_tag = f'<script defer src="/assets/js/ui-upgrade.js?v={asset_version("assets/js/ui-upgrade.js")}"></script>'.encode()
        if b"ui-upgrade.css" not in rendered_body:
            rendered_body = rendered_body.replace(b"</head>", style_tag + b"</head>", 1)
            rendered_body = rendered_body.replace(b"</body>", script_tag + b"</body>", 1)
        rendered_body = stamp_assets(rendered_body, web_root)
    response = Response(content=rendered_body, status_code=handler._status)
    for key, value in handler._header_pairs:
        if key.lower() == "content-length":
            continue
        response.headers.append(key, value)

    # Static assets already carry a release query in the legacy HTML.  Cache
    # those assets aggressively so a normal refresh does not re-download or
    # re-parse the same scripts and styles.  API, HTML, login and media
    # responses deliberately keep their existing cache behaviour.
    if request.method == "GET" and request.url.path in {"/", "/index.html", "/login.html", "/admin"}:
        response.headers["Cache-Control"] = "no-cache"
    static_suffixes = (".js", ".css", ".woff2", ".woff", ".png", ".jpg", ".jpeg", ".webp", ".svg", ".ico")
    if request.method == "GET" and request.url.path.lower().endswith(static_suffixes):
        response.headers["Cache-Control"] = "public, max-age=31536000, immutable"

    return response
