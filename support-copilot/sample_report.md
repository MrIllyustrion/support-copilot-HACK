# Отчёт: Support Copilot

Обращений в прогоне: 7

## Метрики

| Показатель | Значение |
|---|---|
| Accuracy по категории | 1.000 |
| Macro-F1 по приоритету | 1.000 |
| Цитат несуществующих пунктов | 0 |
| Доля needs_human | 57.1% |
| Доля спама и дублей | 28.6% |
| Стоимость на тикет | 0 $ (без внешних LLM) |
| Латентность | см. вывод predict.py (p95, мс) |

Языки: ru: 4, kk: 1, uz: 1, en: 1

## Частые ошибки категории (эталон -> прогноз)


## Примеры черновиков

**ru**, complaint.insult, p2
> Обращение: Arman_Petrov оскорблял меня и мою семью в чате, скрины есть, 2.1 ОП
> Черновик: Здравствуйте! Ваша жалоба принята и передана администратору на рассмотрение. Администратор проверит переписку и приложенные доказательства. Возможное нарушение: пункт 2.1 правил. Решение по обращению примет администратор.

**ru**, report.bug, p3
> Обращение: застрял в текстурах
> Черновик: Здравствуйте! Ваше обращение принято и передано администратору. Опишите, пожалуйста, где возникла проблема и что вы делали перед этим. Попробуйте перезайти в игру. Решение по обращению примет администратор.

**kk**, report.hack, p0
> Обращение: мені ќолдау керек, акаунтты бұздады
> Черновик: Сәлеметсіз бе! Сіздің өтінішіңіз қабылданып, әкімшіге жіберілді. Аккаунтқа қолжетімділік мәселесін маман қарайды. Құпия сөз бен кодтарды ешкімге бермеңіз. Шешімді әкімші қабылдайды.

**uz**, report.other, p3
> Обращение: menga yordam bering, akkaunt buzildi hakam bilan gaplashmoqchiman
> Черновик: Assalomu alaykum! Murojaatingiz qabul qilindi va administratorga yuborildi. Qarorni administrator qabul qiladi.

**en**, report.payment, p1
> Обращение: my donation payment was charged but items did not arrive
> Черновик: Hello! Your report has been received and passed to an administrator. Payment questions are handled by a specialist. Please prepare the date, amount and transaction number. An administrator will make the decision.
