"""Small HTTP inference service for the saved PolluTrace models (standard library server).

  python pipeline/serve.py --models outputs/models --port 8100

GET  /health                -> {"status":"ok","cities":[...]}
POST /predict               -> next-day PM2.5 from the last 30+ days of readings
     {"city":"Delhi","rows":[{"date":"2023-03-01","PM25":80,"PM10":150,"NO2":40,"NOx":50,"SO2":10,"CO":1.2,"Ozone":30}, ...]}

Bind address defaults to 127.0.0.1 and has no authentication: put the Go API in front of it.
"""
from __future__ import annotations

import argparse
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from common import CITIES
from predict import InputError, load_bundle, predict_rows

BUNDLES: dict = {}
MAX_BODY = 1_000_000


class H(BaseHTTPRequestHandler):
    def _send(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):  # quiet
        pass

    def do_GET(self):
        if self.path == "/health":
            self._send(200, {"status": "ok", "cities": sorted(BUNDLES)})
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self):
        if self.path != "/predict":
            return self._send(404, {"error": "not found"})
        try:
            n = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            return self._send(400, {"error": "bad Content-Length"})
        if n <= 0 or n > MAX_BODY:
            return self._send(400, {"error": "body missing or too large"})
        try:
            req = json.loads(self.rfile.read(n))
        except Exception:
            return self._send(400, {"error": "body is not valid JSON"})
        if not isinstance(req, dict):
            return self._send(400, {"error": "body must be a JSON object"})
        city = req.get("city")
        if city not in BUNDLES:
            return self._send(400, {"error": f"unknown city; choose one of {sorted(BUNDLES)}"})
        try:
            self._send(200, {"city": city, **predict_rows(req.get("rows"), *BUNDLES[city])})
        except InputError as e:
            self._send(422, {"error": str(e)})
        except Exception as e:  # model failure, not the caller's fault
            self._send(500, {"error": "prediction failed", "detail": type(e).__name__})


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", default="outputs/models")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=int(os.environ.get("INFERENCE_PORT", "8100")))
    a = ap.parse_args()
    for c in CITIES:
        try:
            BUNDLES[c] = load_bundle(a.models, c)
        except Exception as e:
            print(f"skipping {c}: {type(e).__name__}: {e}", flush=True)
    if not BUNDLES:
        raise SystemExit("no models found in " + a.models)
    print(f"serving {sorted(BUNDLES)} on {a.host}:{a.port}", flush=True)
    ThreadingHTTPServer((a.host, a.port), H).serve_forever()
