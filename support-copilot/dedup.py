"""Дедупликация: один игрок, одна проблема, несколько тикетов за короткое время.
Дубль = тот же reporter_hash и (похожий текст по Jaccard или та же категория) в окне WINDOW секунд."""
import re
from datetime import datetime

WINDOW = 3600       # окно, секунд
SIM = 0.6           # порог схожести текстов

def _tokens(text: str) -> set:
    return {w[:6] for w in re.findall(r"\w+", (text or "").lower()) if len(w) > 2}

def _ts(s):
    try:
        return datetime.fromisoformat(s).timestamp()
    except Exception:
        return None

class Deduper:
    def __init__(self, window: int = WINDOW, sim: float = SIM):
        self.window, self.sim = window, sim
        self.seen = {}   # reporter_hash -> [(ts, tokens, category)]

    def check(self, reporter, created_at, text, category) -> bool:
        """Возвращает True, если обращение дублирует недавнее. Всегда запоминает обращение."""
        if not reporter:
            return False
        ts = _ts(created_at)
        if ts is None:
            ts = float(len(self.seen.get(reporter, [])))  # без времени: считаем подряд идущими
            window = float("inf")
        else:
            window = self.window
        toks = _tokens(text)
        dup = False
        for pts, ptoks, pcat in self.seen.get(reporter, []):
            if abs(ts - pts) > window:
                continue
            union = toks | ptoks
            jac = len(toks & ptoks) / len(union) if union else 0.0
            if jac >= self.sim or (pcat == category and category not in ("report.other", "complaint.other")):
                dup = True
                break
        self.seen.setdefault(reporter, []).append((ts, toks, category))
        return dup
