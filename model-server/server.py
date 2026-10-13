"""Kyuma model-server — Phase 05.

Keeps Qwen2.5-1.5B-Instruct (Q4_K_M, Phase 06 bake-off winner) resident in
llama-server (GPU offload) and exposes the tiny API the harness speaks:

  POST /decide {sentence: str} -> Exec {action, args}  (200) or {error} (4xx/5xx)
  GET  /health -> {loaded, device, vram_mb, model, backend}

Single process: this wrapper spawns llama-server as a child and proxies to its
OpenAI-compatible endpoint with GBNF-constrained JSON (json_schema), temp 0.
Qwen2.5-Instruct has no thinking mode; the `/no_think` suffix + `<think>`
strip are kept harmlessly so `--model models/Qwen3-0.6B-Q4_K_M.gguf`
(backup) still runs thinking-free. Each /decide
is stateless (no chat history), so context never grows stale — that is the
context reset. CPU fallback: --device cpu (n_gpu_layers=0); still answers.

Stdlib only. Start:  .venv/bin/python model-server/server.py [--port 8080]
Stop: Ctrl-C (child llama-server is terminated).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, REPO)  # harness.contracts
from harness.contracts import ACTIONS, Exec  # noqa: E402

DEFAULT_MODEL = os.path.join(REPO, "models", "qwen2.5-1.5b-instruct-q4_k_m.gguf")
BACKUP_MODEL = os.path.join(REPO, "models", "Qwen3-0.6B-Q4_K_M.gguf")
VENDOR_DIR = os.path.join(HERE, "vendor")

SYSTEM_PROMPT = (
    "You are Kyuma, a desktop voice-command parser. "
    "Output ONLY one JSON object, no other text. "
    "Never explain, never think out loud."
)

JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "action": {"type": "string", "enum": list(ACTIONS)},
        "args": {"type": "object"},
    },
    "required": ["action", "args"],
    "additionalProperties": False,
}


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def find_llama_server(explicit: str | None) -> str:
    if explicit and os.path.isfile(explicit):
        return explicit
    env = os.environ.get("LLAMA_SERVER")
    if env and os.path.isfile(env):
        return env
    hit = shutil.which("llama-server")
    if hit:
        return hit
    for root, _, files in os.walk(VENDOR_DIR):
        if "llama-server" in files:
            p = os.path.join(root, "llama-server")
            os.chmod(p, 0o755)
            return p
    raise FileNotFoundError("llama-server binary not found (vendor/ or PATH)")


def vram_used_mb() -> int | None:
    try:
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
            timeout=10, text=True,
        )
        return int(out.strip().splitlines()[0])
    except Exception:
        return None


def strip_think(text: str) -> str:
    return re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()


def _child_env() -> dict[str, str]:
    """-child env with vendor CUDA runtime libs visible (no system install)."""
    env = dict(os.environ)
    libdirs = []
    for root, _, files in os.walk(VENDOR_DIR):
        if any(f.startswith("libcudart.so") for f in files):
            libdirs.append(root)
    if libdirs:
        env["LD_LIBRARY_PATH"] = os.pathsep.join(
            libdirs + [env["LD_LIBRARY_PATH"]] if env.get("LD_LIBRARY_PATH") else libdirs
        )
    return env


class Backend:
    """Owns the llama-server child process."""

    def __init__(self, model: str, device: str, ctx_size: int, binary: str):
        self.port = free_port()
        cmd = [
            binary, "-m", model,
            "--host", "127.0.0.1", "--port", str(self.port),
            "--ctx-size", str(ctx_size),
            "--n-gpu-layers", "0" if device == "cpu" else "99",
            "--threads", str(os.cpu_count() or 4),
            "--log-disable",
        ]
        self.proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL,
                                       stderr=subprocess.DEVNULL, env=_child_env())
        self.device = "cpu" if device == "cpu" else "cuda"
        self.model = os.path.basename(model)
        self.loaded = False
        self._wait_ready()

    def _wait_ready(self, timeout: float = 180.0) -> None:
        url = f"http://127.0.0.1:{self.port}/health"
        t0 = time.time()
        while time.time() - t0 < timeout:
            if self.proc.poll() is not None:
                raise RuntimeError("llama-server exited during load")
            try:
                with urllib.request.urlopen(url, timeout=5) as r:
                    if r.status == 200 and json.load(r).get("status") == "ok":
                        self.loaded = True
                        return
            except Exception:
                time.sleep(1.0)
        raise TimeoutError("llama-server did not become ready")

    def chat_decide(self, sentence: str, timeout: float = 60.0) -> dict:
        body = {
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"{sentence} /no_think"},
            ],
            "temperature": 0,
            "max_tokens": 128,
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": "exec", "schema": JSON_SCHEMA},
            },
        }
        req = urllib.request.Request(
            f"http://127.0.0.1:{self.port}/v1/chat/completions",
            data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as r:
            payload = json.load(r)
        content = payload["choices"][0]["message"]["content"]
        return json.loads(strip_think(content))

    def stop(self) -> None:
        self.proc.terminate()
        try:
            self.proc.wait(timeout=15)
        except subprocess.TimeoutExpired:
            self.proc.kill()


BACKEND: Backend | None = None
DECIDES = 0


class Handler(BaseHTTPRequestHandler):
    server_version = "KyumaModelServer/05"

    def _send(self, code: int, obj: dict) -> None:
        data = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:  # noqa: N802
        if self.path != "/health":
            return self._send(404, {"error": "unknown path"})
        assert BACKEND is not None
        self._send(200, {
            "loaded": BACKEND.loaded,
            "device": BACKEND.device,
            "vram_mb": vram_used_mb(),
            "model": BACKEND.model,
            "backend": "llama-server",
            "decides": DECIDES,  # monotonic: a reload would reset it
        })

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/decide":
            return self._send(404, {"error": "unknown path"})
        assert BACKEND is not None
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length) or b"{}")
        except (ValueError, OSError):
            return self._send(400, {"error": "invalid JSON body"})
        sentence = body.get("sentence")
        if not isinstance(sentence, str) or not sentence.strip():
            return self._send(400, {"error": "sentence must be a non-empty string"})
        try:
            obj = BACKEND.chat_decide(sentence.strip())
            Exec.from_dict(obj)  # contract second gate before counting
            global DECIDES
            DECIDES += 1
            self._send(200, obj)
        except (ValueError, TypeError, KeyError) as e:
            # Contract second gate: backend emitted non-Exec JSON.
            self._send(502, {"error": f"backend output failed Exec validation: {e}"})
        except Exception as e:  # noqa: BLE001 — server must stay up
            self._send(502, {"error": f"backend failure: {e}"})

    def log_message(self, *a: object) -> None:
        pass


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="Kyuma model-server (Phase 05)")
    ap.add_argument("--port", type=int, default=8080)
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--device", choices=("auto", "cpu"), default="auto")
    ap.add_argument("--ctx-size", type=int, default=2048)
    ap.add_argument("--llama-server", default=None)
    args = ap.parse_args(argv)

    global BACKEND
    BACKEND = Backend(args.model, args.device, args.ctx_size,
                      find_llama_server(args.llama_server))
    srv = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(json.dumps({"listening": srv.server_address[1],
                      "device": BACKEND.device, "model": BACKEND.model}), flush=True)
    # SIGTERM (pkill, CI teardown) must also reap the llama-server child.
    # shutdown() deadlocks when called from the serve_forever thread itself
    # (which is where signal handlers run), so hand it to a daemon thread.
    signal.signal(signal.SIGTERM,
                  lambda *_: threading.Thread(target=srv.shutdown, daemon=True).start())
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.server_close()
        BACKEND.stop()


if __name__ == "__main__":
    main()
