"""Test T5 (FR6): how check_url / check_broken_links classify different link outcomes.

Run from the project folder (the one that contains broken_links.py):
    python link_status_test.py

It starts a tiny web server on this computer, so no real website is contacted
(except one deliberately invalid name used for the DNS-failure case).
"""
import os, sys, socket, threading, time, logging
sys.path.insert(0, os.getcwd())
os.environ["NO_PROXY"] = "*"; os.environ["no_proxy"] = "*"
for k in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
    os.environ.pop(k, None)
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import broken_links as b
# Note: on Windows a refused connection to a closed local port is retried for about 2 seconds
# before it fails, so the timeout below must be longer than that.

class Quiet(ThreadingHTTPServer):
    daemon_threads = True
    request_queue_size = 50
    def handle_error(self, request, client_address):  # hide harmless "client gave up" noise
        pass

class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_GET(self):
        if self.path == "/slow": time.sleep(6)
        code = {"/ok": 200, "/nf": 404, "/forbid": 403, "/many": 429, "/slow": 200}.get(self.path, 200)
        self.send_response(code); self.end_headers()
        try: self.wfile.write(b"x")
        except Exception: pass

srv = Quiet(("127.0.0.1", 0), H); port = srv.server_port
threading.Thread(target=srv.serve_forever, daemon=True).start()
s = socket.socket(); s.bind(("127.0.0.1", 0)); closed = s.getsockname()[1]; s.close()
hang = socket.socket(); hang.bind(("127.0.0.1", 0)); hang.listen(50); hp = hang.getsockname()[1]
held = []  # connections the "no reply" server accepts but never answers
def _hold():
    while True:
        try: held.append(hang.accept()[0])
        except Exception: return
threading.Thread(target=_hold, daemon=True).start()

cases = [  # (name, url, expected status)
    ("200 OK",                f"http://127.0.0.1:{port}/ok",     "ok"),
    ("404 Not Found",         f"http://127.0.0.1:{port}/nf",     "broken"),
    ("403 Forbidden",         f"http://127.0.0.1:{port}/forbid", "inconclusive"),
    ("429 Too Many Requests", f"http://127.0.0.1:{port}/many",   "inconclusive"),
    ("Slow reply (timeout)",  f"http://127.0.0.1:{port}/slow",   "inconclusive"),
    ("No reply (timeout)",    f"http://127.0.0.1:{hp}/x",        "inconclusive"),
    ("Connection refused",    f"http://127.0.0.1:{closed}/x",    "broken"),
    ("DNS failure",           "http://no-such-host.invalid/x",   "broken"),
]
bad = 0
print(f"{'Case':24s}{'Expected':14s}{'Got':14s}Result")
for name, url, exp in cases:
    got, detail = b.check_url(url, timeout=3)
    ok = got == exp; bad += (not ok)
    print(f"{name:24s}{exp:14s}{got:14s}{'PASS' if ok else 'FAIL'}   ({detail[:60]})")

r = b.check_broken_links(urls=[c[1] for c in cases], timeout=3)
exp_score = 3 / 4   # 3 broken out of 4 conclusive links; the 4 inconclusive are left out
ok = abs(r["score"] - exp_score) < 1e-9 and r["total"] == 4
bad += (not ok)
for k in ("broken","inconclusive"):
    for x in r[k]: print(f"   {k}: {x['url'].split('127.0.0.1:')[-1]}  {x['reason'][:50]}")
print(f"\nAll 8 links together: total={r['total']} broken={len(r['broken'])} "
      f"inconclusive={len(r['inconclusive'])} score={r['score']}  (expected 0.75)  {'PASS' if ok else 'FAIL'}")

r2 = b.check_broken_links(urls=[cases[4][1], cases[5][1]], timeout=3)
ok = r2["score"] == "not_applicable" or r2.get("status") == "not_applicable" or r2["score"] is None
bad += (not ok)
print(f"Only timeouts: result={r2['score']}  (expected not_applicable)  {'PASS' if ok else 'FAIL'}")
print("\nOVERALL:", "ALL PASSED" if bad == 0 else f"{bad} FAILED")
