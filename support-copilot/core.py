"""Ядро триажа: без внешних зависимостей (только стандартная библиотека).
Используется и HTTP-сервисом (app.py), и пакетным запуском (predict.py)."""
import json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))

# ---------- нормализация cp1251 (казахские буквы) ----------
KZ_MAP = str.maketrans({
    "ќ": "қ", "ґ": "ғ", "ѕ": "ң", "є": "ә", "ј": "ө", "ў": "ұ", "ї": "ү",
    "Ќ": "Қ", "Ґ": "Ғ", "Ѕ": "Ң", "Є": "Ә", "Ј": "Ө", "Ў": "Ұ", "Ї": "Ү",
})

def normalize(t: str) -> str:
    return (t or "").translate(KZ_MAP)

# ---------- определение языка ----------
KK_CH = set("қғңәөұүһӘҚҒҢӨҰҮҺ")
UZ_WORDS = {"va", "emas", "bilan", "menga", "men", "uchun", "bu", "yoq", "yo'q", "iltimos", "salom", "qanday", "hakam", "admin"}
EN_WORDS = {"the", "and", "is", "i", "you", "my", "he", "she", "please", "was", "with", "hello", "hi"}

def detect_lang(t: str) -> str:
    t = normalize(t)
    if not re.search(r"[A-Za-zА-Яа-яЁёӘәҒғҚқҢңӨөҰұҮүҺһІі]", t):
        return "und"
    if any(c in KK_CH for c in t):
        return "kk"
    ws = set(re.findall(r"[a-zа-яё'ʻ’]+", t.lower()))
    if re.search(r"[oOgG][ʻ‘’']", t) or len(ws & UZ_WORDS) >= 2:
        return "uz"
    lat = sum(c.isascii() and c.isalpha() for c in t)
    cyr = sum("а" <= c.lower() <= "я" or c.lower() == "ё" for c in t)
    if cyr >= lat and cyr > 0:
        return "ru"
    if len(ws & UZ_WORDS) >= 1 and len(ws & EN_WORDS) == 0:
        return "uz"
    return "en" if lat else "und"

# ---------- правила и поиск (RAG, лексический) ----------
def load_rules() -> dict:
    candidates = [os.environ.get("RULES_PATH", ""), os.path.join(HERE, "rules.json"),
                  os.path.join(HERE, "rules.sample.json")]
    path = next(p for p in candidates if p and os.path.exists(p))
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    out = {}
    def walk(n):
        if isinstance(n, dict):
            if "id" in n and "text" in n:
                out[str(n["id"])] = str(n["text"])
            for v in n.values():
                walk(v)
        elif isinstance(n, list):
            for v in n:
                walk(v)
    walk(data)
    return out

RULES = load_rules()
tok = lambda s: {w[:5] for w in re.findall(r"\w+", s.lower()) if len(w) > 2}
RULE_TOK = {k: tok(v) for k, v in RULES.items()}

def retrieve(text: str, k: int = 2, min_score: int = 1):
    q = tok(text)
    scored = sorted(((len(q & t), r) for r, t in RULE_TOK.items()), reverse=True)
    return [r for s, r in scored[:k] if s >= min_score]

# ---------- категория, приоритет, спам ----------
CATS = [
    ("report.payment", r"донат|оплат|платеж|платёж|списал|купил.*(не пришл|не получ)|возврат|деньги вернуть|tolov|payment|refund"),
    ("report.hack", r"взлом|угнал аккаунт|украли аккаунт|зашли в аккаунт|hacked|hack\b|аккаунт.*(взлом|украд)|бұзд|бұзып"),
    ("report.appeal", r"разбан|снять бан|обжалов|незаслуженно забан|забанили зря|unban|appeal"),
    ("complaint.insult", r"оскорб|мат\b|матер|унижа|insult|қорла|haqorat|haқорат"),
    ("complaint.cheat", r"чит|скрипт|аимбот|wallhack|баг.*использ|cheat|exploit"),
    ("complaint.scam", r"обман|кинул|развел|скам|мошенн|scam"),
    ("report.bug", r"застрял|текстур|баг|не работает|вылетает|лаг|crash|bug|stuck"),
]
SPAM = re.compile(r"(https?://|t\.me/|продам|куплю аккаунт|подписывайся|промокод)", re.I)
ALWAYS_HUMAN = {"report.payment", "report.hack", "report.appeal"}
PROMISE = re.compile(r"разбан|возврат|вернём|вернем|компенсац|refund|unban", re.I)

def classify(kind: str, text: str):
    t = text.lower()
    if SPAM.search(t) and len(t) < 300 and not re.search(r"\d\.\d", t):
        return "spam", 0.7
    for cat, pat in CATS:
        if re.search(pat, t):
            return cat, 0.8
    return (f"{kind}.other" if kind in ("complaint", "report") else "report.other"), 0.4

def priority(cat: str, text: str) -> str:
    t = text.lower()
    if cat == "report.hack" or re.search(r"угроз|суицид|взрыв|шантаж|doxx|слив данных", t):
        return "p0"
    if cat in ("report.payment", "complaint.scam", "complaint.cheat"):
        return "p1"
    if cat in ("complaint.insult", "report.appeal"):
        return "p2"
    return "p3"

# ---------- извлечение фактов ----------
NICK = re.compile(r"\b[A-Za-z][A-Za-z0-9]*_[A-Za-z][A-Za-z0-9_]*\b")
REF = re.compile(r"(?<![\d.])(\d{1,2}\.\d{1,2}(?:\.\d{1,2})?)(?![\d.])")
SERVER = re.compile(r"(?:сервер|server|srv)\s*[№#]?\s*(\w+)", re.I)
EVID = re.compile(r"скрин|видео|запис|доказат|screens?|proof|evidence|dalil|дәлел", re.I)

def extract(text: str, attachments: int, valid_rules) -> dict:
    nick = NICK.search(text)
    refs = [r for r in dict.fromkeys(REF.findall(text)) if r in valid_rules]
    srv = SERVER.search(text)
    return {
        "nickname": nick.group(0) if nick else None,
        "rule_refs": refs,
        "has_evidence": attachments > 0 or bool(EVID.search(text)),
        "server": srv.group(1) if srv else None,
    }

# ---------- шаблоны черновиков ----------
TPL = {
    "ru": {"hi": "Здравствуйте! ",
           "complaint": "Ваша жалоба принята и передана администратору на рассмотрение. ",
           "report": "Ваше обращение принято и передано администратору. ",
           "cite": "Возможное нарушение: пункт {r} правил. ",
           "noev": "Если есть скриншоты или видео, пожалуйста, приложите их. ",
           "human": "Решение по обращению примет администратор.",
           "spam": "Обращение не содержит вопроса по игре."},
    "kk": {"hi": "Сәлеметсіз бе! ",
           "complaint": "Сіздің шағымыңыз қабылданып, қарау үшін әкімшіге жіберілді. ",
           "report": "Сіздің өтінішіңіз қабылданып, әкімшіге жіберілді. ",
           "cite": "Ықтимал бұзушылық: ережелердің {r}-тармағы. ",
           "noev": "Скриншот не бейне болса, тіркеңіз. ",
           "human": "Шешімді әкімші қабылдайды.",
           "spam": "Өтініште ойынға қатысты сұрақ жоқ."},
    "uz": {"hi": "Assalomu alaykum! ",
           "complaint": "Shikoyatingiz qabul qilindi va ko'rib chiqish uchun administratorga yuborildi. ",
           "report": "Murojaatingiz qabul qilindi va administratorga yuborildi. ",
           "cite": "Mumkin bo'lgan buzilish: qoidalarning {r}-bandi. ",
           "noev": "Agar skrinshot yoki video bo'lsa, iltimos, biriktiring. ",
           "human": "Qarorni administrator qabul qiladi.",
           "spam": "Murojaatda o'yinga oid savol yo'q."},
    "en": {"hi": "Hello! ",
           "complaint": "Your complaint has been received and passed to an administrator for review. ",
           "report": "Your report has been received and passed to an administrator. ",
           "cite": "Possible violation: rule {r}. ",
           "noev": "If you have screenshots or video, please attach them. ",
           "human": "An administrator will make the decision.",
           "spam": "The message does not contain a game-related question."},
}

# ---------- тексты по категориям (без обещаний наказаний, разбанов, возвратов) ----------
CAT_TXT = {
    "ru": {
        "complaint.insult": "Администратор проверит переписку и приложенные доказательства. ",
        "complaint.cheat": "Администратор проверит подозрение на использование стороннего ПО. ",
        "complaint.scam": "Администратор проверит обстоятельства сделки. Сохраните переписку и скриншоты. ",
        "report.bug": "Опишите, пожалуйста, где возникла проблема и что вы делали перед этим. Попробуйте перезайти в игру. ",
        "report.payment": "Вопросы по платежам рассматривает специалист. Подготовьте дату, сумму и номер операции. ",
        "report.hack": "Вопросы доступа к аккаунту рассматривает специалист. Никому не сообщайте пароль и коды. ",
        "report.appeal": "Апелляции рассматривает специалист. Укажите ник и дату наказания. ",
        "dup": "Мы уже получили ваше обращение по этому вопросу, повторно отправлять его не нужно.",
    },
    "kk": {
        "complaint.insult": "Әкімші жазбаны және тіркелген дәлелдерді тексереді. ",
        "complaint.cheat": "Әкімші бөгде бағдарламаны қолдану күдігін тексереді. ",
        "complaint.scam": "Әкімші мәміле мән-жайын тексереді. Жазбаны және скриншоттарды сақтаңыз. ",
        "report.bug": "Мәселе қай жерде болғанын және алдында не істегеніңізді сипаттаңыз. Ойынға қайта кіріп көріңіз. ",
        "report.payment": "Төлем мәселесін маман қарайды. Күнін, соманы және операция нөмірін дайындаңыз. ",
        "report.hack": "Аккаунтқа қолжетімділік мәселесін маман қарайды. Құпия сөз бен кодтарды ешкімге бермеңіз. ",
        "report.appeal": "Апелляцияны маман қарайды. Ник пен жаза күнін көрсетіңіз. ",
        "dup": "Бұл мәселе бойынша өтінішіңізді алдық, қайта жіберудің қажеті жоқ.",
    },
    "uz": {
        "complaint.insult": "Administrator yozishmani va ilova qilingan dalillarni tekshiradi. ",
        "complaint.cheat": "Administrator begona dastur ishlatilganligi shubhasini tekshiradi. ",
        "complaint.scam": "Administrator bitim holatlarini tekshiradi. Yozishma va skrinshotlarni saqlang. ",
        "report.bug": "Muammo qayerda yuz berganini va undan oldin nima qilganingizni yozing. O'yinga qayta kirib ko'ring. ",
        "report.payment": "To'lov masalasini mutaxassis ko'rib chiqadi. Sana, summa va operatsiya raqamini tayyorlang. ",
        "report.hack": "Akkauntga kirish masalasini mutaxassis ko'rib chiqadi. Parol va kodlarni hech kimga bermang. ",
        "report.appeal": "Apellyatsiyani mutaxassis ko'rib chiqadi. Nik va jazo sanasini ko'rsating. ",
        "dup": "Bu masala bo'yicha murojaatingiz qabul qilingan, qayta yuborish shart emas.",
    },
    "en": {
        "complaint.insult": "An administrator will review the chat log and the attached evidence. ",
        "complaint.cheat": "An administrator will check the suspected use of third-party software. ",
        "complaint.scam": "An administrator will review the circumstances of the deal. Please keep the chat and screenshots. ",
        "report.bug": "Please describe where the problem happened and what you did before it. Try restarting the game. ",
        "report.payment": "Payment questions are handled by a specialist. Please prepare the date, amount and transaction number. ",
        "report.hack": "Account access issues are handled by a specialist. Never share your password or codes with anyone. ",
        "report.appeal": "Appeals are handled by a specialist. Please state your nickname and the date of the penalty. ",
        "dup": "We have already received your request on this issue, there is no need to send it again.",
    },
}

def draft(kind, lang, cat, facts, cited, dup=False):
    p = TPL.get(lang, TPL["ru"])
    c = CAT_TXT.get(lang, CAT_TXT["ru"])
    if dup:
        return p["hi"] + c["dup"]
    if cat == "spam":
        return p["hi"] + p["spam"]
    s = p["hi"] + p["complaint" if kind == "complaint" else "report"]
    s += c.get(cat, "")
    if cited:
        s += p["cite"].format(r=", ".join(cited))
    if not facts["has_evidence"] and kind == "complaint":
        s += p["noev"]
    return s + p["human"]  # никаких обещаний наказания, разбана или возврата


# ---------- привязка к taxonomy.json ----------
def load_category_map() -> dict:
    """category_map.json: {"внутренняя категория": "id из taxonomy.json"}. Нет файла - имена не меняются."""
    p = os.path.join(HERE, "category_map.json")
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    return {}

CATEGORY_MAP = load_category_map()
def public_category(cat: str) -> str:
    return CATEGORY_MAP.get(cat, cat)

# ---------- главная функция ----------
def triage(kind: str, messages: list, images_count: int = 0, dup: bool = False) -> dict:
    """messages: [{"role": "player", "text": "...", "attachments": 0}, ...]"""
    player = [m for m in messages if m.get("role") == "player"] or messages
    text = normalize("\n".join(m.get("text", "") or "" for m in player))
    attachments = max(images_count, sum(int(m.get("attachments", 0) or 0) for m in player))
    lang = detect_lang(text)
    cat, conf = classify(kind, text)
    facts = extract(text, attachments, RULES)

    cited = list(facts["rule_refs"])
    if not cited and cat not in ("spam", "report.bug") and not cat.endswith(".other"):
        cited = retrieve(text, k=1, min_score=1)
    cited = [r for r in cited if r in RULES]  # защита от галлюцинаций

    reasons, needs_human = [], False
    if cat in ALWAYS_HUMAN:
        needs_human = True
        reasons.append("платежи, апелляции и взлом всегда обрабатывает человек")
    if kind == "complaint" and cat != "spam":
        needs_human = True
        reasons.append("решение о наказании подтверждает администратор")
    if PROMISE.search(text):
        needs_human = True
        reasons.append("в обращении просьба о разбане, возврате или компенсации")
    if conf < 0.5:
        needs_human = True
        reasons.append("низкая уверенность классификации")
    if lang == "und":
        needs_human = True
        reasons.append("язык не определён")
    if dup:
        reasons.append("дубликат недавнего обращения этого игрока")

    dlang = lang if lang in TPL else "ru"
    return {
        "lang": lang,
        "category": public_category(cat),
        "priority": priority(cat, text) if cat != "spam" else "p3",
        "is_spam_or_duplicate": cat == "spam" or dup,
        "extracted": facts,
        "draft_reply": {"lang": dlang, "text": draft(kind, dlang, cat, facts, cited, dup), "cited": cited},
        "needs_human": needs_human,
        "confidence": round(conf, 2),
        "reasons": reasons,
    }
