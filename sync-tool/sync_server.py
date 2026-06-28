#!/usr/bin/env python3
"""
Local sync server for Card Notes & Pay.

Serves the app's static files AND a /api/sync endpoint that, on demand, reads
your Gmail statements, parses them, and returns the import JSON. The app's Sync
button calls /api/sync so one tap reads the latest mail — no manual file import.

Run:   python3 sync_server.py
Then open the printed URL:
  - on this Mac:  http://localhost:8787
  - on your phone (same Wi-Fi):  http://<your-mac-ip>:8787

Everything stays on your Mac. config.json holds your birthdate (to derive the
PDF passwords) and the app folder path.
"""
import json, os, socket, subprocess, sys, threading
from datetime import datetime
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
CFG = json.load(open(HERE / "config.json"))
APP_DIR = CFG.get("app_dir") or str(HERE.parent)  # default: the app folder one level up
PORT = int(CFG.get("port", 8787))
DOB = CFG["dob"]
SINCE = CFG.get("since", "2026/01/01")
DOWNLOAD = Path(os.path.expanduser("~/Downloads/cardpay-mydata.json"))

_lock = threading.Lock()


STATEMENTS = HERE / "statements"


def is_first_sync():
    return not (STATEMENTS / "_emails.json").exists()


def run_sync():
    """Run fetch + parse; return (ok, payload_or_error).

    First sync: fetch the full history (config 'since').
    Later syncs: fetch only the current month — fast — while the parser still
    rebuilds the complete dataset from all statements accumulated on disk.
    """
    env = dict(os.environ, CARDPAY_DOB=DOB, CARDPAY_NO_BROWSER="1")
    first = is_first_sync()
    since = SINCE if first else datetime.now().strftime("%Y/%m/01")
    print(f"[sync] mode={'FULL (first run)' if first else 'current month'} since={since}")
    try:
        f = subprocess.run([sys.executable, str(HERE / "fetch_statements.py"),
                            "--since", since], cwd=HERE, env=env,
                           capture_output=True, text=True, timeout=180)
        if f.returncode != 0:
            return False, (f.stdout + f.stderr)[-500:]
        p = subprocess.run([sys.executable, str(HERE / "parse_statements.py")],
                           cwd=HERE, env=env, capture_output=True, text=True, timeout=120)
        if p.returncode != 0:
            return False, (p.stdout + p.stderr)[-500:]
        return True, json.loads(DOWNLOAD.read_text())
    except subprocess.TimeoutExpired:
        return False, "Timed out talking to Gmail."
    except Exception as e:
        return False, str(e)


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=APP_DIR, **k)

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")

    def _json(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self._cors()
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204); self._cors(); self.end_headers()

    def do_POST(self):
        if self.path.rstrip("/") == "/api/sync":
            return self.handle_sync()
        self.send_error(404)

    def do_GET(self):
        p = self.path.split("?")[0].rstrip("/")
        if p == "/api/ping":
            return self._json(200, {"ok": True, "service": "cardpay-sync"})
        if p == "/api/sync":
            return self.handle_sync()
        return super().do_GET()

    def handle_sync(self):
        if not _lock.acquire(blocking=False):
            return self._json(429, {"ok": False, "error": "A sync is already running."})
        try:
            print("[sync] reading Gmail…")
            ok, payload = run_sync()
            if ok:
                n = len(payload.get("spending", []))
                print(f"[sync] done — {len(payload.get('cards', []))} cards, {n} card-months")
                self._json(200, payload)
            else:
                print("[sync] failed:", payload)
                self._json(500, {"ok": False, "error": payload})
        finally:
            _lock.release()

    def log_message(self, *a):
        pass  # quiet


def lan_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80)); ip = s.getsockname()[0]; s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def main():
    if not (HERE / "token.json").exists():
        print("⚠  No token.json yet — run ./sync.sh once to authorize Gmail first.")
    srv = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    ip = lan_ip()
    print("\n  Card Notes & Pay — local sync server")
    print(f"  ▶ On this Mac:   http://localhost:{PORT}")
    print(f"  ▶ On your phone: http://{ip}:{PORT}   (same Wi-Fi)")
    print("  Open that URL and tap 🔄 Sync to read the latest statements.")
    print("  Ctrl+C to stop.\n")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped.")


if __name__ == "__main__":
    main()
