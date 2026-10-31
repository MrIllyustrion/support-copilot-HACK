"""Пакетный прогон: python predict.py IN.jsonl OUT.jsonl  (поддерживает .gz)
Читает обращения в формате tickets_*.jsonl, пишет по строке на обращение:
{"ticket_id": ..., **ответ /triage}. В конце печатает сводку."""
import gzip, json, sys, time
from collections import Counter

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import core
from dedup import Deduper

def opener(path, mode):
    return gzip.open(path, mode + "t", encoding="utf-8") if path.endswith(".gz") else open(path, mode, encoding="utf-8")

def main(src, dst):
    n, human, dups, lat, cats = 0, 0, 0, [], Counter()
    deduper = Deduper()
    with opener(src, "r") as fin, open(dst, "w", encoding="utf-8") as fout:
        for line in fin:
            line = line.strip()
            if not line:
                continue
            t = json.loads(line)
            msgs = [{"role": m.get("role"), "text": m.get("text", "")} for m in t.get("messages", [])]
            t0 = time.perf_counter()
            kind, imgs = t.get("kind", "report"), int(t.get("images_count", 0) or 0)
            res = core.triage(kind, msgs, imgs)
            ptext = " ".join(m["text"] for m in msgs if m["role"] == "player")
            if not res["is_spam_or_duplicate"] and deduper.check(
                    t.get("reporter_hash"), t.get("created_at"), ptext, res["category"]):
                res = core.triage(kind, msgs, imgs, dup=True)
                dups += 1
            lat.append(time.perf_counter() - t0)
            res["ticket_id"] = t.get("ticket_id")
            fout.write(json.dumps(res, ensure_ascii=False) + "\n")
            n += 1
            human += res["needs_human"]
            cats[res["category"]] += 1
    lat.sort()
    p95 = lat[int(0.95 * (len(lat) - 1))] if lat else 0
    print(f"тикетов: {n}")
    if n:
        print(f"нужен человек: {human / n:.1%}")
        print(f"дубликатов: {dups}")
        print(f"латентность p95: {p95 * 1000:.2f} мс")
        print("стоимость на тикет: 0.000 $ (без внешних LLM-API)")
        print("категории:", dict(cats))

if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("usage: python predict.py IN.jsonl OUT.jsonl")
    main(sys.argv[1], sys.argv[2])
