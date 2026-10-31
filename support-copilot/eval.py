"""Оценка и отчёт.
python eval.py PRED.jsonl VALID_LABELED.jsonl [REPORT.md]

PRED - результат predict.py. VALID_LABELED - валидационный файл, где у обращений заполнены
category и priority (ключи как в схеме обращения). Считает:
  - accuracy по категории и macro-F1 по приоритету (если разметка есть);
  - долю цитат, которых нет в правилах (должна быть 0);
  - долю needs_human, долю спама/дублей, p95 латентности не считает (см. predict.py);
и пишет report.md с примерами черновиков по языкам."""
import gzip, json, sys
from collections import Counter, defaultdict

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import core

def read(path):
    op = gzip.open if path.endswith(".gz") else open
    with op(path, "rt", encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]

def macro_f1(y_true, y_pred):
    labels = sorted(set(y_true) | set(y_pred))
    f1s = []
    for c in labels:
        tp = sum(t == c and p == c for t, p in zip(y_true, y_pred))
        fp = sum(t != c and p == c for t, p in zip(y_true, y_pred))
        fn = sum(t == c and p != c for t, p in zip(y_true, y_pred))
        pr = tp / (tp + fp) if tp + fp else 0.0
        rc = tp / (tp + fn) if tp + fn else 0.0
        f1s.append(2 * pr * rc / (pr + rc) if pr + rc else 0.0)
    return sum(f1s) / len(f1s) if f1s else 0.0

def main(pred_path, gold_path, out_path="report.md"):
    pred = {p["ticket_id"]: p for p in read(pred_path)}
    gold = {g["ticket_id"]: g for g in read(gold_path)}
    ids = [i for i in pred if i in gold]
    n = len(pred)

    lab = [i for i in ids if gold[i].get("category") and gold[i].get("priority")]
    acc = sum(gold[i]["category"] == pred[i]["category"] for i in lab) / len(lab) if lab else None
    f1 = macro_f1([gold[i]["priority"] for i in lab], [pred[i]["priority"] for i in lab]) if lab else None

    bad_cites = sum(1 for p in pred.values() for r in p["draft_reply"]["cited"] if r not in core.RULES)
    human = sum(p["needs_human"] for p in pred.values()) / n if n else 0
    spam_dup = sum(p["is_spam_or_duplicate"] for p in pred.values()) / n if n else 0
    langs = Counter(p["lang"] for p in pred.values())

    rows = [
        "# Отчёт: Support Copilot", "",
        f"Обращений в прогоне: {n}", "",
        "## Метрики", "",
        "| Показатель | Значение |", "|---|---|",
        f"| Accuracy по категории | {acc:.3f} |" if acc is not None else "| Accuracy по категории | нет разметки category/priority в файле |",
        f"| Macro-F1 по приоритету | {f1:.3f} |" if f1 is not None else "| Macro-F1 по приоритету | нет разметки |",
        f"| Цитат несуществующих пунктов | {bad_cites} |",
        f"| Доля needs_human | {human:.1%} |",
        f"| Доля спама и дублей | {spam_dup:.1%} |",
        "| Стоимость на тикет | 0 $ (без внешних LLM) |",
        "| Латентность | см. вывод predict.py (p95, мс) |", "",
        "Языки: " + ", ".join(f"{k}: {v}" for k, v in langs.most_common()), "",
    ]
    if lab:
        conf = Counter((gold[i]["category"], pred[i]["category"]) for i in lab if gold[i]["category"] != pred[i]["category"])
        rows += ["## Частые ошибки категории (эталон -> прогноз)", ""]
        rows += [f"- {a} -> {b}: {c}" for (a, b), c in conf.most_common(10)] + [""]

    rows += ["## Примеры черновиков", ""]
    by_lang = defaultdict(list)
    for i, p in pred.items():
        by_lang[p["draft_reply"]["lang"]].append(i)
    for lang in ("ru", "kk", "uz", "en"):
        for i in by_lang.get(lang, [])[:2]:
            q = " ".join(m.get("text", "") for m in gold.get(i, {}).get("messages", []) if m.get("role") == "player")
            rows += [f"**{lang}**, {pred[i]['category']}, {pred[i]['priority']}",
                     f"> Обращение: {q[:200]}" if q else "",
                     f"> Черновик: {pred[i]['draft_reply']['text']}", ""]
    open(out_path, "w", encoding="utf-8").write("\n".join(rows))
    print("\n".join(rows[:16]))
    print(f"отчёт записан в {out_path}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit("usage: python eval.py PRED.jsonl VALID_LABELED.jsonl [REPORT.md]")
    main(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "report.md")
