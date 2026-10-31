"""HTTP-сервис без внешних зависимостей (только стандартная библиотека Python 3.8+).
Запуск: python server.py [порт]   (по умолчанию 8000)
POST /triage - контракт кейса, GET /health - проверка, GET / - веб-интерфейс."""
import json
import os
import sys
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import core
from dedup import Deduper

deduper = Deduper()

HTML_PAGE = """<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Support Copilot — Панель управления</title>
  <style>
    :root {
      --bg: #0b0f19;
      --card-bg: #151c2e;
      --card-border: #232d45;
      --accent: #6366f1;
      --accent-hover: #4f46e5;
      --text: #f8fafc;
      --text-muted: #94a3b8;
      --success: #10b981;
      --warning: #f59e0b;
      --danger: #ef4444;
      --info: #06b6d4;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
      background: var(--bg);
      color: var(--text);
      min-height: 100vh;
      padding: 24px 16px;
      line-height: 1.5;
    }
    .container {
      max-width: 900px;
      margin: 0 auto;
    }
    header {
      margin-bottom: 24px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 12px;
      border-bottom: 1px solid var(--card-border);
      padding-bottom: 16px;
    }
    .brand h1 {
      font-size: 24px;
      font-weight: 700;
      display: flex;
      align-items: center;
      gap: 10px;
    }
    .brand p {
      color: var(--text-muted);
      font-size: 14px;
      margin-top: 4px;
    }
    .status-badge {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      background: rgba(16, 185, 129, 0.15);
      color: #34d399;
      border: 1px solid rgba(16, 185, 129, 0.3);
      padding: 6px 14px;
      border-radius: 9999px;
      font-size: 13px;
      font-weight: 500;
    }
    .status-dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: #10b981;
      box-shadow: 0 0 8px #10b981;
    }
    .card {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 12px;
      padding: 20px;
      margin-bottom: 20px;
      box-shadow: 0 8px 24px rgba(0,0,0,0.25);
    }
    .presets-label {
      font-size: 13px;
      color: var(--text-muted);
      margin-bottom: 8px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }
    .presets {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      margin-bottom: 20px;
    }
    .preset-btn {
      background: #1e293b;
      color: #cbd5e1;
      border: 1px solid var(--card-border);
      border-radius: 8px;
      padding: 6px 12px;
      font-size: 13px;
      cursor: pointer;
      transition: all 0.2s;
    }
    .preset-btn:hover {
      background: var(--accent);
      color: #fff;
      border-color: var(--accent);
    }
    .form-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 16px;
      margin-bottom: 16px;
    }
    .form-group {
      display: flex;
      flex-direction: column;
      gap: 6px;
    }
    .form-group label {
      font-size: 13px;
      color: var(--text-muted);
      font-weight: 500;
    }
    input, select, textarea {
      background: #0f172a;
      border: 1px solid var(--card-border);
      color: var(--text);
      padding: 10px 12px;
      border-radius: 8px;
      font-size: 14px;
      outline: none;
      transition: border-color 0.2s;
    }
    input:focus, select:focus, textarea:focus {
      border-color: var(--accent);
    }
    textarea {
      min-height: 100px;
      resize: vertical;
      font-family: inherit;
    }
    .btn-submit {
      background: var(--accent);
      color: white;
      border: none;
      padding: 12px 24px;
      border-radius: 8px;
      font-size: 15px;
      font-weight: 600;
      cursor: pointer;
      width: 100%;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      transition: background 0.2s;
    }
    .btn-submit:hover {
      background: var(--accent-hover);
    }
    .btn-submit:disabled {
      opacity: 0.6;
      cursor: not-allowed;
    }
    .results {
      display: none;
      margin-top: 24px;
    }
    .badges-row {
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
      margin-bottom: 16px;
    }
    .badge {
      padding: 6px 12px;
      border-radius: 6px;
      font-size: 13px;
      font-weight: 600;
    }
    .badge-p0 { background: #fee2e2; color: #991b1b; }
    .badge-p1 { background: #ffedd5; color: #9a3412; }
    .badge-p2 { background: #fef3c7; color: #92400e; }
    .badge-p3 { background: #e0e7ff; color: #3730a3; }
    .badge-cat { background: #334155; color: #f1f5f9; }
    .badge-lang { background: #0369a1; color: #e0f2fe; }
    .badge-spam { background: #dc2626; color: white; }
    .banner {
      padding: 14px;
      border-radius: 8px;
      margin-bottom: 16px;
      font-size: 14px;
    }
    .banner-danger {
      background: rgba(239, 68, 68, 0.15);
      border: 1px solid rgba(239, 68, 68, 0.3);
      color: #fca5a5;
    }
    .banner-success {
      background: rgba(16, 185, 129, 0.15);
      border: 1px solid rgba(16, 185, 129, 0.3);
      color: #6ee7b7;
    }
    .reply-box {
      background: #0f172a;
      border: 1px solid var(--card-border);
      border-radius: 8px;
      padding: 14px;
      font-size: 14px;
      margin-top: 10px;
      white-space: pre-wrap;
      position: relative;
    }
    .copy-btn {
      position: absolute;
      top: 8px;
      right: 8px;
      background: #1e293b;
      color: #cbd5e1;
      border: 1px solid var(--card-border);
      padding: 4px 8px;
      border-radius: 6px;
      font-size: 12px;
      cursor: pointer;
    }
    .copy-btn:hover {
      background: var(--accent);
      color: #fff;
    }
    details {
      margin-top: 16px;
      font-size: 13px;
    }
    summary {
      cursor: pointer;
      color: var(--text-muted);
      padding: 6px 0;
    }
    pre {
      background: #0f172a;
      padding: 12px;
      border-radius: 8px;
      overflow-x: auto;
      color: #cbd5e1;
      margin-top: 8px;
      border: 1px solid var(--card-border);
    }
    .facts-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 12px;
      margin-bottom: 16px;
    }
    .fact-item {
      background: #0f172a;
      padding: 10px 14px;
      border-radius: 8px;
      border: 1px solid var(--card-border);
    }
    .fact-item .label {
      font-size: 12px;
      color: var(--text-muted);
    }
    .fact-item .val {
      font-size: 14px;
      font-weight: 600;
      margin-top: 2px;
    }
  </style>
</head>
<body>
  <div class="container">
    <header>
      <div class="brand">
        <h1>🛡️ Support Copilot</h1>
        <p>Ассистент поддержки и автоматической сортировки обращений</p>
      </div>
      <div class="status-badge">
        <span class="status-dot"></span>
        <span>Онлайн (<span id="rule-count">3</span> правил)</span>
      </div>
    </header>

    <div class="card">
      <div class="presets-label">Готовые примеры обращений (нажмите для проверки):</div>
      <div class="presets">
        <button type="button" class="preset-btn" onclick="applyPreset('insult')">💬 Оскорбления</button>
        <button type="button" class="preset-btn" onclick="applyPreset('cheat')">⚡ Читы / Аимбот</button>
        <button type="button" class="preset-btn" onclick="applyPreset('payment')">💳 Донат / Платёж</button>
        <button type="button" class="preset-btn" onclick="applyPreset('hack')">🔒 Взлом аккаунта</button>
        <button type="button" class="preset-btn" onclick="applyPreset('spam')">🚫 Спам / Ссылка</button>
      </div>

      <form id="triage-form" onsubmit="submitForm(event)">
        <div class="form-grid">
          <div class="form-group">
            <label for="kind">Тип обращения:</label>
            <select id="kind">
              <option value="complaint">Жалоба на игрока (complaint)</option>
              <option value="report">Вопрос / Репорт (report)</option>
            </select>
          </div>
          <div class="form-group">
            <label for="reporter">Хэш игрока (reporter_hash):</label>
            <input type="text" id="reporter" value="user_77a" placeholder="user_123">
          </div>
          <div class="form-group">
            <label for="attachments">Количество вложений (скрины):</label>
            <input type="number" id="attachments" value="1" min="0" max="10">
          </div>
        </div>

        <div class="form-group" style="margin-bottom: 16px;">
          <label for="text">Текст обращения игрока:</label>
          <textarea id="text" placeholder="Введите текст обращения...">Игрок Arman_Petrov оскорблял меня и моих родственников в общем чате, скрины приложил, нарушен пункт 2.1 ОП</textarea>
        </div>

        <button type="submit" id="submit-btn" class="btn-submit">
          <span>🚀 Проанализировать обращение</span>
        </button>
      </form>
    </div>

    <div id="results" class="card results">
      <h2 style="font-size: 18px; margin-bottom: 14px;">Результаты анализа:</h2>
      
      <div class="badges-row" id="badges-container"></div>
      <div id="human-banner" class="banner"></div>

      <div class="facts-grid">
        <div class="fact-item">
          <div class="label">Никнейм нарушителя:</div>
          <div class="val" id="res-nick">—</div>
        </div>
        <div class="fact-item">
          <div class="label">Доказательства:</div>
          <div class="val" id="res-evidence">—</div>
        </div>
        <div class="fact-item">
          <div class="label">Пункты правил:</div>
          <div class="val" id="res-rules">—</div>
        </div>
        <div class="fact-item">
          <div class="label">Уверенность (confidence):</div>
          <div class="val" id="res-conf">—</div>
        </div>
      </div>

      <div style="margin-top: 16px;">
        <div style="font-size: 13px; font-weight: 600; color: var(--text-muted); text-transform: uppercase;">Черновик ответа игроку:</div>
        <div class="reply-box">
          <button class="copy-btn" onclick="copyReply()">Копировать</button>
          <div id="res-reply-text"></div>
        </div>
      </div>

      <div id="cited-rules-box" style="margin-top: 14px; font-size: 13px; display: none;">
        <span style="color: var(--text-muted);">Процитированные правила:</span>
        <div id="cited-rules-list" style="margin-top: 6px;"></div>
      </div>

      <details>
        <summary>Показать полный JSON ответ сервера</summary>
        <pre><code id="res-raw"></code></pre>
      </details>
    </div>
  </div>

  <script>
    const PRESETS = {
      insult: {
        kind: 'complaint',
        reporter: 'user_01',
        attachments: 2,
        text: 'Arman_Petrov оскорблял меня и мою семью в чате, скрины есть, 2.1 ОП'
      },
      cheat: {
        kind: 'complaint',
        reporter: 'user_02',
        attachments: 1,
        text: 'Игрок Vanya_Ivanov летает на машине со спидхаком и стреляет сквозь стены'
      },
      payment: {
        kind: 'report',
        reporter: 'user_03',
        attachments: 1,
        text: 'Задонатил 500 рублей 30 минут назад, деньги с карты списались, но донат на аккаунт не пришёл, чек прикрепил'
      },
      hack: {
        kind: 'report',
        reporter: 'user_04',
        attachments: 0,
        text: 'Украли аккаунт, поменяли пароль и почту, помогите вернуть пожалуйста'
      },
      spam: {
        kind: 'report',
        reporter: 'spammer_99',
        attachments: 0,
        text: 'Бесплатные вирты и донат для Grand Mobile забирай тут: https://free-donate-scam.ru'
      }
    };

    function applyPreset(key) {
      const p = PRESETS[key];
      if (!p) return;
      document.getElementById('kind').value = p.kind;
      document.getElementById('reporter').value = p.reporter;
      document.getElementById('attachments').value = p.attachments;
      document.getElementById('text').value = p.text;
      submitForm();
    }

    // Загрузка статистики health
    fetch('/health')
      .then(r => r.json())
      .then(d => {
        if (d && d.rules !== undefined) {
          document.getElementById('rule-count').textContent = d.rules;
        }
      })
      .catch(() => {});

    async function submitForm(e) {
      if (e) e.preventDefault();
      const btn = document.getElementById('submit-btn');
      btn.disabled = true;
      btn.innerHTML = '<span>⏳ Анализ...</span>';

      const payload = {
        kind: document.getElementById('kind').value,
        reporter_hash: document.getElementById('reporter').value.trim(),
        created_at: new Date().toISOString(),
        messages: [{
          role: 'player',
          text: document.getElementById('text').value,
          attachments: parseInt(document.getElementById('attachments').value, 10) || 0
        }]
      };

      try {
        const resp = await fetch('/triage', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        const data = await resp.json();
        renderResults(data);
      } catch (err) {
        alert('Ошибка при связи с сервером: ' + err.message);
      } finally {
        btn.disabled = false;
        btn.innerHTML = '<span>🚀 Проанализировать обращение</span>';
      }
    }

    function renderResults(res) {
      const resultsDiv = document.getElementById('results');
      resultsDiv.style.display = 'block';

      // Badges
      const badges = document.getElementById('badges-container');
      badges.innerHTML = '';

      const pColors = { p0: 'badge-p0', p1: 'badge-p1', p2: 'badge-p2', p3: 'badge-p3' };
      badges.innerHTML += `<span class="badge ${pColors[res.priority] || 'badge-p3'}">Приоритет: ${res.priority.toUpperCase()}</span>`;
      badges.innerHTML += `<span class="badge badge-cat">Категория: ${res.category}</span>`;
      badges.innerHTML += `<span class="badge badge-lang">Язык: ${res.lang.toUpperCase()}</span>`;
      if (res.is_spam_or_duplicate) {
        badges.innerHTML += `<span class="badge badge-spam">⚠️ Спам или дубликат</span>`;
      }

      // Human banner
      const banner = document.getElementById('human-banner');
      if (res.needs_human) {
        banner.className = 'banner banner-danger';
        banner.innerHTML = `<strong>⚠️ Требуется проверка администратором!</strong><br>Причины: ${res.reasons.join(', ')}`;
      } else {
        banner.className = 'banner banner-success';
        banner.innerHTML = `<strong>✅ Можно ответить автоматически</strong> (вмешательство человека не требуется)`;
      }

      // Facts
      const ext = res.extracted || {};
      document.getElementById('res-nick').textContent = ext.nickname || 'Не указан';
      document.getElementById('res-evidence').textContent = ext.has_evidence ? 'Есть доказательства' : 'Нет доказательств';
      document.getElementById('res-rules').textContent = (ext.rule_refs && ext.rule_refs.length) ? ext.rule_refs.join(', ') : 'Не указаны';
      document.getElementById('res-conf').textContent = res.confidence ? (res.confidence * 100).toFixed(0) + '%' : '100%';

      // Reply
      const reply = res.draft_reply || {};
      document.getElementById('res-reply-text').textContent = reply.text || '—';

      // Cited rules
      const citedBox = document.getElementById('cited-rules-box');
      const citedList = document.getElementById('cited-rules-list');
      if (reply.cited && reply.cited.length) {
        citedBox.style.display = 'block';
        citedList.innerHTML = reply.cited.map(c => `<div style="padding: 4px 0; color: #a5b4fc;">• Пункт ${c}</div>`).join('');
      } else {
        citedBox.style.display = 'none';
      }

      // Raw json
      document.getElementById('res-raw').textContent = JSON.stringify(res, null, 2);

      resultsDiv.scrollIntoView({ behavior: 'smooth' });
    }

    function copyReply() {
      const text = document.getElementById('res-reply-text').textContent;
      navigator.clipboard.writeText(text).then(() => {
        alert('Текст черновика скопирован в буфер обмена!');
      });
    }
  </script>
</body>
</html>
"""

def handle_triage(body: dict) -> dict:
    kind = body.get("kind", "report")
    msgs = [
        {
            "role": m.get("role", "player"),
            "text": m.get("text", "") or "",
            "attachments": int(m.get("attachments", 0) or 0),
        }
        for m in body.get("messages", [])
    ]
    res = core.triage(kind, msgs)
    ptext = " ".join(m["text"] for m in msgs if m["role"] == "player")
    if not res["is_spam_or_duplicate"] and deduper.check(
        body.get("reporter_hash"), body.get("created_at"), ptext, res["category"]
    ):
        res = core.triage(kind, msgs, dup=True)
    return res

class Handler(BaseHTTPRequestHandler):
    def _send_bytes(self, code: int, data: bytes, content_type: str):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(data)

    def _send(self, code: int, obj: dict):
        data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self._send_bytes(code, data, "application/json; charset=utf-8")

    def _send_html(self, code: int, html_str: str):
        self._send_bytes(code, html_str.encode("utf-8"), "text/html; charset=utf-8")

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        path = self.path.split("?")[0]
        if path in ("/", "/index.html", "/docs"):
            self._send_html(200, HTML_PAGE)
        elif path == "/health":
            self._send(200, {"ok": True, "rules": len(core.RULES)})
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self):
        path = self.path.split("?")[0]
        if path != "/triage":
            return self._send(404, {"error": "not found"})
        try:
            n = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(n).decode("utf-8"))
            if not isinstance(body.get("messages"), list):
                return self._send(422, {"error": "messages must be a list"})
            self._send(200, handle_triage(body))
        except (ValueError, UnicodeDecodeError):
            self._send(400, {"error": "invalid JSON"})

    def log_message(self, *a):
        pass

def open_browser(port: int):
    time.sleep(0.7)
    try:
        webbrowser.open(f"http://localhost:{port}/")
    except Exception:
        pass

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    threading.Thread(target=open_browser, args=(port,), daemon=True).start()
    print("=" * 60)
    print(" Support Copilot успешно запущен!")
    print(f" Веб-интерфейс:     http://localhost:{port}/")
    print(f" Интерактивные docs: http://localhost:{port}/docs")
    print(f" Проверка здоровья: http://localhost:{port}/health")
    print(f" Загружено правил:  {len(core.RULES)}")
    print("=" * 60)
    print(" Браузер откроется автоматически через секунду...")
    print(" Чтобы остановить сервер, нажмите Ctrl + C")
    try:
        ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()
    except KeyboardInterrupt:
        print("\nСервер остановлен.")
