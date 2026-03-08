# table_gen

Локальный API-first каркас `Phase 1` для конвейера подготовки `content pack`.

Текущее состояние:
- FastAPI API для полного happy-path от `job` до `publish`.
- Backend adapter layer (`mock`, `comfyui`) с конфигом через env.
- Сборка `content pack` в локальный storage.
- Валидация `manifest.json` по `JSON Schema` перед публикацией.
- Векторные артефакты pack: `vector/master.svg` и `vector/layers/*.svg`.
- Smoke-тест happy-path через `pytest`.

## Запуск без Docker

```bash
python -m venv .venv
. .venv/Scripts/activate  # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -e .
uvicorn app.main:app --reload
```

API будет доступен на `http://localhost:8000`, Swagger UI на `http://localhost:8000/docs`.
Frontend страница будет доступна на `http://localhost:8000/`.

## Запуск через Docker Compose

```bash
docker compose up --build
```

Конфигурация вынесена в [`.env`](/c:/.projects/table_gen/.env).  
Перед запуском проверь минимум:
- `TABLE_GEN_SESSION_GENERATE_BACKEND`
- `TABLE_GEN_NANO_BANANA_PRO_BASE_URL`
- `TABLE_GEN_NANO_BANANA_PRO_API_KEY`
- `TABLE_GEN_NANO_BANANA_PRO_MODEL`
- `TABLE_GEN_NANO_BANANA_PRO_ASPECT_RATIO`
- `TABLE_GEN_NANO_BANANA_PRO_IMAGE_SIZE`
- `TABLE_GEN_COMFYUI_BASE_URL`
- `TABLE_GEN_COMFYUI_WORKFLOW_HOST_PATH`

Контейнеры:
- `api` (orchestrator) - `http://localhost:8000`
- `frontend` - `http://localhost:8080`
- `step-generate` - `http://localhost:8001`
- `step-vectorize` - `http://localhost:8002`
- `step-palette` - `http://localhost:8003`

Env переменные:
- `TABLE_GEN_DEFAULT_BACKEND` (`mock` по умолчанию)
- `TABLE_GEN_COMFYUI_BASE_URL` (`http://localhost:8188` по умолчанию)
- `TABLE_GEN_COMFYUI_WORKFLOW_PATH` (обязателен для backend `comfyui`)
- `TABLE_GEN_COMFYUI_TIMEOUT_SECONDS` (по умолчанию `30`)
- `TABLE_GEN_COMFYUI_POLL_INTERVAL_SECONDS` (по умолчанию `1.0`)
- `TABLE_GEN_COMFYUI_POLL_MAX_ATTEMPTS` (по умолчанию `120`)

## Минимальный happy-path API

1. `POST /jobs` - создать job.
2. `GET /library/items` - список готовых pack из локальной библиотеки.
3. `POST /jobs/{job_id}/generate` - получить shortlist.
4. `POST /jobs/{job_id}/selection/composition` - выбрать композицию.
5. `POST /jobs/{job_id}/selection/palette` - выбрать палитру.
6. `POST /jobs/{job_id}/build` - собрать `content pack`.
7. `GET /packs/{pack_id}/validate` - проверить manifest по schema.
8. `POST /packs/{pack_id}/publish` - опубликовать в `runtime_cache`.

Сформированные файлы сохраняются локально в `data/`.

## ComfyUI backend

Для запуска генерации через ComfyUI:
- укажи в `POST /jobs` поле `"generator_backend": "comfyui"`;
- задай `TABLE_GEN_COMFYUI_WORKFLOW_PATH` на JSON workflow-файл ComfyUI API format;
- убедись, что ComfyUI доступен по `TABLE_GEN_COMFYUI_BASE_URL`.

## CLI workflow (terminal-first)

Интерактивный сценарий:

```bash
python -m app.cli
```

Сценарий включает:
- выбор `library` или `generate`;
- выбор композиции;
- выбор палитры из пресетов;
- сборку/валидацию/публикацию pack.

На выходе выводятся `job_id`, `pack_id`, путь к `master.svg` и пути color-layer SVG.

## Web frontend (functional)

Минимальный frontend без дизайна доступен по адресу:

```bash
http://localhost:8080/
```

Через страницу можно пройти весь workflow:
- шаг 1: создать сессию и выбрать `library` или `generate`;
- library path: выбрать pack из библиотеки и сразу получить `ready_for_runtime`;
- generate path: ввести prompt, получить 4 варианта, выбрать 1;
- далее автоматически: vectorize + генерация 3 палитровых вариантов;
- выбрать финальный вариант -> `ready_for_runtime` + publish в library.

## TouchDesigner stub

Заготовка пакетного скрипта:

```bash
python tools/touchdesigner_pack_stub.py data/runtime_cache/<pack_id>
```

## Тесты

```bash
pytest -q
```
