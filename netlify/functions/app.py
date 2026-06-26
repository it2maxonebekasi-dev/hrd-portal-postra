import sys, os, json, base64, io

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app import create_app
flask_app = create_app()

def handler(event, context):
    http_method  = event.get("httpMethod", "GET")
    path         = event.get("path", "/")
    query_string = event.get("queryStringParameters") or {}
    headers_in   = event.get("headers") or {}
    body_raw     = event.get("body") or ""
    is_b64       = event.get("isBase64Encoded", False)

    body_bytes = base64.b64decode(body_raw) if is_b64 else (body_raw.encode("utf-8") if isinstance(body_raw, str) else body_raw)
    qs = "&".join(f"{k}={v}" for k, v in query_string.items()) if query_string else ""

    environ = {
        "REQUEST_METHOD"  : http_method,
        "PATH_INFO"       : path,
        "QUERY_STRING"    : qs,
        "CONTENT_LENGTH"  : str(len(body_bytes)),
        "CONTENT_TYPE"    : headers_in.get("content-type", ""),
        "SERVER_NAME"     : headers_in.get("host", "localhost"),
        "SERVER_PORT"     : "443",
        "SERVER_PROTOCOL" : "HTTP/1.1",
        "wsgi.input"      : io.BytesIO(body_bytes),
        "wsgi.errors"     : sys.stderr,
        "wsgi.url_scheme" : "https",
        "wsgi.multithread": False,
        "wsgi.multiprocess": False,
        "wsgi.run_once"   : False,
    }

    for key, value in headers_in.items():
        key_upper = key.upper().replace("-", "_")
        if key_upper == "CONTENT_TYPE":
            environ["CONTENT_TYPE"] = value
        elif key_upper == "CONTENT_LENGTH":
            environ["CONTENT_LENGTH"] = value
        else:
            environ[f"HTTP_{key_upper}"] = value

    response_started = {}
    response_body = []

    def start_response(status, response_headers, exc_info=None):
        response_started["status"] = status
        response_started["headers"] = dict(response_headers)

    result = flask_app(environ, start_response)
    for chunk in result:
        response_body.append(chunk)

    body_out = b"".join(response_body)
    status_code = int(response_started["status"].split(" ", 1)[0])
    resp_headers = response_started.get("headers", {})

    content_type = resp_headers.get("Content-Type", "")
    binary_types = ("image/", "application/pdf", "application/octet-stream", "font/")
    is_binary = any(content_type.startswith(bt) for bt in binary_types)

    if is_binary:
        return {"statusCode": status_code, "headers": resp_headers, "body": base64.b64encode(body_out).decode("utf-8"), "isBase64Encoded": True}
    else:
        return {"statusCode": status_code, "headers": resp_headers, "body": body_out.decode("utf-8", errors="replace"), "isBase64Encoded": False}
