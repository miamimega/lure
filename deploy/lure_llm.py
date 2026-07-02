#!/usr/bin/env python3
"""
lure LLM proxy — the tiny backend behind the live demo at lure.fullpercent.io.

It exposes two endpoints that the demo page calls:
  GET  /health   -> {"ok": true, "model": "qwen3:4b"}
  POST /generate -> {"hooks": ["...", ...], "model": "qwen3:4b"}

It builds a direct-response prompt from the channel's winners / losers / rules,
calls a LOCAL Ollama model, parses the output into clean hooks, and refuses the
known losers. Stdlib only (no pip). Bound to localhost; nginx rate-limits in front.

Config via env:
  LURE_MODEL   default model tag              (default: qwen3:4b)
  OLLAMA_URL     Ollama base URL                (default: http://127.0.0.1:11434)
  LURE_PORT    port to listen on              (default: 8788)
  LURE_MAXTOK  max tokens per generation      (default: 260)
  LURE_RPM     per-IP requests/min rate limit (default: 12)
"""
import json, os, re, time, threading, urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from collections import defaultdict, deque

MODEL   = os.environ.get("LURE_MODEL", "qwen3:4b")
OLLAMA  = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")
PORT    = int(os.environ.get("LURE_PORT", "8788"))
MAXTOK  = int(os.environ.get("LURE_MAXTOK", "260"))
RPM     = int(os.environ.get("LURE_RPM", "12"))
HOST    = os.environ.get("LURE_HOST", "127.0.0.1")

CHANNEL_NAME = {"email": "email marketing", "meta_facebook": "Meta / Facebook ads",
                "google_ads": "Google Search ads (RSA headlines)", "affiliate": "affiliate / native ads"}

# one generation at a time keeps CPU inference from thrashing the shared box
GEN_LOCK = threading.Semaphore(1)
_hits = defaultdict(deque)  # ip -> timestamps


def _rate_ok(ip):
    now = time.time()
    q = _hits[ip]
    while q and now - q[0] > 60:
        q.popleft()
    if len(q) >= RPM:
        return False
    q.append(now)
    return True


def _ollama(path, payload=None, timeout=40):
    url = OLLAMA + path
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"},
                                 method="POST" if data else "GET")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def build_messages(seg, offer, winners, losers, rules, n):
    ch = CHANNEL_NAME.get(seg, "advertising")
    rules_txt = "\n".join("- " + r for r in (rules or [])[:6])
    win_txt = "\n".join("- " + w for w in (winners or [])[:8])
    lose_txt = ", ".join((losers or [])[:14])
    system = (
        f"You are a world-class direct-response copywriter. You write ad HOOKS "
        f"(the opening line or headline) for {ch}.\n\n"
        f"Channel rules:\n{rules_txt}\n\n"
        f"Lean into the SPIRIT of these proven winning patterns (do not copy them word for word):\n{win_txt}\n\n"
        f"NEVER use these losing phrases or anything close to them (they get rejected or flop): {lose_txt}.\n\n"
        f"Write exactly {n} distinct, ready-to-run hooks for the offer. Vary the mechanism "
        f"(question, number, contrarian, callout, benefit, curiosity, PAS). Each hook is ONE short line. "
        f"Output ONLY the hooks, one per line — no numbering, no quotes, no explanation, no preamble."
    )
    # Qwen3 is a hybrid "thinking" model; /no_think makes it answer directly (fast, no reasoning dump)
    user = f"Offer: {offer}" + (" /no_think" if MODEL.startswith("qwen3") else "")
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


_STRIP = re.compile(r"^\s*(?:\d+[\.\)]|[-*•])\s*")
_THINK = re.compile(r"<think>.*?</think>", re.S | re.I)
_BADLINE = re.compile(r"^(here are|sure|okay|got it|hooks?:|of course)", re.I)


def parse_hooks(text, losers, n):
    text = _THINK.sub("", text or "")
    out, seen = [], set()
    low_losers = [l.lower() for l in (losers or [])]
    for line in text.splitlines():
        s = _STRIP.sub("", line).strip().strip('"').strip("'").strip()
        if not s or len(s) < 6 or _BADLINE.match(s):
            continue
        low = s.lower()
        if low in seen or any(p and p in low for p in low_losers):
            continue
        seen.add(low)
        out.append(s)
        if len(out) >= n:
            break
    return out


class H(BaseHTTPRequestHandler):
    def _send(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass

    def do_GET(self):
        if self.path.rstrip("/") != "/health":
            return self._send(404, {"error": "not found"})
        try:
            tags = _ollama("/api/tags", timeout=5)
            names = [m.get("name", "") for m in tags.get("models", [])]
            ok = any(n == MODEL or n.split(":")[0] == MODEL.split(":")[0] for n in names)
            return self._send(200, {"ok": ok, "model": MODEL})
        except Exception:
            return self._send(200, {"ok": False, "model": MODEL})

    def do_POST(self):
        if self.path.rstrip("/") != "/generate":
            return self._send(404, {"error": "not found"})
        ip = self.headers.get("X-Forwarded-For", self.client_address[0]).split(",")[0].strip()
        if not _rate_ok(ip):
            return self._send(429, {"error": "slow down — rate limit"})
        try:
            ln = int(self.headers.get("Content-Length", "0"))
            body = json.loads(self.rfile.read(ln) or b"{}")
        except Exception:
            return self._send(400, {"error": "bad json"})

        offer = str(body.get("offer", "")).strip()[:120] or "your offer"
        seg = body.get("segment", "meta_facebook")
        n = max(3, min(10, int(body.get("n", 8))))
        losers = body.get("losers", [])
        msgs = build_messages(seg, offer, body.get("winners", []), losers, body.get("rules", []), n)

        if not GEN_LOCK.acquire(timeout=25):
            return self._send(503, {"error": "busy, try again"})
        try:
            resp = _ollama("/api/chat", {
                "model": MODEL, "messages": msgs, "stream": False, "think": False,
                "options": {"num_predict": MAXTOK, "temperature": 0.85, "top_p": 0.9},
            }, timeout=90)
        except Exception as e:
            return self._send(502, {"error": "model error", "detail": str(e)[:120]})
        finally:
            GEN_LOCK.release()

        content = (resp.get("message") or {}).get("content", "")
        hooks = parse_hooks(content, losers, n)
        if not hooks:
            return self._send(502, {"error": "no hooks", "raw": content[:200]})
        return self._send(200, {"hooks": hooks, "model": MODEL})


if __name__ == "__main__":
    print(f"lure-llm on :{PORT} -> {OLLAMA} model={MODEL} rpm={RPM}", flush=True)
    ThreadingHTTPServer((HOST, PORT), H).serve_forever()
