"""HTTP-сервис: POST /triage, GET /health, GET / (веб-интерфейс).
Запуск: python app.py  или  uvicorn app:app --port 8000"""
import sys
import webbrowser

try:
    from fastapi import FastAPI
    from fastapi.responses import HTMLResponse
    from pydantic import BaseModel
    from typing import Optional
    import uvicorn
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False

import core
from dedup import Deduper
import server

if not FASTAPI_AVAILABLE:
    # Если fastapi не установлен, сразу используем встроенный сервер без зависимостей
    if __name__ == "__main__":
        server.main() if hasattr(server, "main") else os.system("python server.py 8000")
else:
    deduper = Deduper()

    class Msg(BaseModel):
        role: str = "player"
        text: str = ""
        attachments: int = 0

    class Req(BaseModel):
        kind: str = "report"
        messages: list[Msg]
        reporter_hash: Optional[str] = None
        created_at: Optional[str] = None

    app = FastAPI(title="Support Copilot")

    @app.get("/", response_class=HTMLResponse)
    def index():
        return server.HTML_PAGE

    @app.get("/health")
    def health():
        return {"ok": True, "rules": len(core.RULES)}

    @app.post("/triage")
    def triage(req: Req):
        msgs = [m.model_dump() for m in req.messages]
        res = core.triage(req.kind, msgs)
        ptext = " ".join(m["text"] for m in msgs if m["role"] == "player")
        if not res["is_spam_or_duplicate"] and deduper.check(
                req.reporter_hash, req.created_at, ptext, res["category"]):
            res = core.triage(req.kind, msgs, dup=True)
        return res

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    if FASTAPI_AVAILABLE:
        import threading, time
        def _open():
            time.sleep(0.7)
            try:
                webbrowser.open(f"http://localhost:{port}/")
            except Exception:
                pass
        threading.Thread(target=_open, daemon=True).start()
        print(f"Запуск Support Copilot на http://localhost:{port}/")
        uvicorn.run(app, host="0.0.0.0", port=port)
    else:
        from http.server import ThreadingHTTPServer
        ThreadingHTTPServer(("0.0.0.0", port), server.Handler).serve_forever()
