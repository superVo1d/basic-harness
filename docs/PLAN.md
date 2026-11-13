# PLAN — agent_loop

Личный проект. `[x]` готово, `[~]` частично, `[ ]` не начато.
Референс — Hermes (`~/Developer/hermes-agent`). **Обновлено:** 2026-11-13.

---

## Итог: работающий агент (Этапы 0–8)

Один клик по CLI: `python -m agent [--session_id X]` → цель через `/goal`, тулы, компактация, авто-доведение до `done`.

**Что есть:**
- `config.py` — `BASE_PATH`, `Settings` (`.env`): `max_context_size`, `protect_last_n`, `tavily_api_key`. ✅
- `logging_setup.py` — файл в `<root>/logs`, `level=INFO`. ✅
- `session.py` — полный `history` (append-only) + `summary`/`summary_upto`/`last_input_tokens`/`goal`, JSON в `<root>/data/sessions`, `latest_session_id`. ✅
- `cli.py` / `__main__.py` — REPL, `--session_id`/resume-latest, `/new`, `/goal`, `exit`, многострочный ввод, авто-save. ✅
- `registry.py` + `utils.py` — `@tool`, `tool_schemas()`, `call_tool()` (JSON-ошибки, `run_sync` мост для async). ✅
- `prompt.py` — Identity + Finishing + Parallel + Execution discipline + Tool-use. ✅
- `tools/` — `todo_list`, `web_search`, `web_extract` (Tavily), `vision_analyze` (Responses `input` с `role=user`). ✅
- `compression.py` — компактация: триггер по всей истории (`est > 0.6*window`), protect-хвост, summarizer + fail-soft, лог решения. ✅
- `goal.py` + `loop.run_agent` — Ralph loop: турн → судья (JSON из фенсов парсится) → continuation → …, стоп по `done/blocked/wait`, сброс `goal`, `budget=20`. ✅

---

## На заметку (не блокеры)

- [ ] **Таймаут клиента:** задать `OpenAI(..., timeout=60)` в `inference.py` — иначе зависший сервер подвешивает турн (был случай).
- [ ] **`JUDGE_MODEL`:** вынести судью на отдельную (дешёвую/стабильную) модель вместо основной.
- [ ] **todo-дубли:** при пере-планировании модель заводит новые id и merge копит пункты — подсказать в описании тула «используй те же id».
- [ ] **`_estimate_tokens`** считает только `content:str` (tool-строки/картинки не учитывает).
- [ ] **Компрессия без LLM-fallback:** если summarizer недоступен — просто не сжимаем (безопасно, но нет детерминированной сводки).
- [ ] **Чистка:** удалить мусорный каталог `agent/utils/` (пустой `async_bri`); `*.egg-info/` в `.gitignore`. ✅
- [ ] **`ddgs`** в зависимостях не используется (выбран Tavily) — убрать.

---

## Этап 9 (следующий). Хранилище в SQLite — `[ ]`

- [ ] `sessions` / `messages` вместо JSON-файлов; запись хода **до** побочных эффектов инструментов.
- [ ] `session_search` (FTS5) — recall по прошлым беседам.
- [ ] Сохранять `summary`/`summary_upto`/`last_input_tokens`/`goal`.
- [ ] Обернуть за интерфейсом `SessionStore` (`load/save/list/search`), чтобы позже можно было сменить бэкенд.
- **DoD:** перезапуск → история и сессии на месте; поиск по прошлым беседам работает.

---

## Этап 6 (опционально). `clarify` — `[ ]`

- [ ] `tools/clarify.py`: 1–5 вопросов, choices ≤4, callback от CLI (`input()`); без callback → `{"error":"unavailable"}`.

---

## Сценарии приёмки

- **S1 multi-turn** — контекст в сессии. ✅
- **S2 persistence** — перезапуск с тем же id → история на месте. ✅
- **S3 tools** — `todo_list` (replace→merge→read). ✅
- **S4 web** — `web_search` → ответ со ссылками (проверено вживую). ✅
- **S5 vision** — `vision_analyze` (формат `input` починен; нужна vision-модель в `VISION_MODEL`). `[~]`
- **S6 compression** — `compacted N messages` в логе, `history` не короче. ✅
- **S7 goal** — авто-доведение до `done`, сброс цели. ✅
- **S8 negative** — «привет» → без вызовов тулов. `[~]`

---

## Порядок

9 SQLite (+recall) → на заметку (таймаут, JUDGE_MODEL, dedupe) → 6 clarify (опц.).
