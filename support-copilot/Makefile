.PHONY: install serve serve-fastapi predict eval
IN ?= tickets.jsonl
OUT ?= pred.jsonl
GOLD ?= tickets_valid_labeled.jsonl
REPORT ?= report.md

# установка нужна только для варианта на FastAPI; основной сервер работает без неё
install:
	pip install -r requirements.txt

serve:
	python server.py 8000

serve-fastapi:
	uvicorn app:app --port 8000

predict:
	python predict.py $(IN) $(OUT)

# метрики и отчёт: make predict IN=<файл с разметкой> OUT=pred.jsonl && make eval GOLD=<тот же файл>
eval:
	python eval.py $(OUT) $(GOLD) $(REPORT)
