# CHANGELOGE

## 2026-03-06

### Added
- Базовый API-first прототип на FastAPI для `Phase 1`.
- Локальное хранение jobs и packs в `data/`.
- Endpoints:
  - `POST /jobs`
  - `GET /jobs/{job_id}`
  - `POST /jobs/{job_id}/generate`
  - `GET /jobs/{job_id}/shortlist`
  - `POST /jobs/{job_id}/selection/composition`
  - `POST /jobs/{job_id}/selection/palette`
  - `POST /jobs/{job_id}/build`
  - `GET /packs/{pack_id}/validate`
  - `POST /packs/{pack_id}/publish`
  - `GET /health`
- Backend adapter layer:
  - `mock` backend
  - `comfyui` adapter contract (phase-1 placeholder generation with predictable URIs)
- JSON Schema `manifest_v1.json` + runtime validation before publish.
- Dockerfile and docker-compose for local startup.
- Happy-path test `tests/test_happy_path.py`.

### Notes
- На момент первой сборки в окружении не было `python`/`py` в PATH; это устранено в блоке `validation update`.
- Целевой критерий MVP (подтвержденный импорт в TouchDesigner) остается следующим обязательным шагом.

## 2026-03-06 (validation update)

### Environment
- Установлен Python 3.12.10 для пользователя `pc`.
- Установлен `py launcher`.
- Обновлен пользовательский `PATH` с директориями Python и Launcher.

### Verification
- Выполнен `pytest -q`: `1 passed`.

## 2026-03-06 (comfyui adapter update)

### Added
- Реализован реальный adapter flow для ComfyUI backend:
  - `POST /prompt` submit workflow;
  - polling `GET /history/{prompt_id}`;
  - extraction image outputs в candidate URI через `/view`.
- Добавлены env-настройки ComfyUI:
  - `TABLE_GEN_COMFYUI_WORKFLOW_PATH`
  - `TABLE_GEN_COMFYUI_TIMEOUT_SECONDS`
  - `TABLE_GEN_COMFYUI_POLL_INTERVAL_SECONDS`
  - `TABLE_GEN_COMFYUI_POLL_MAX_ATTEMPTS`
- Добавлена обработка ошибок генерации в API (`400` для бизнес-ошибок, `502` для backend failures).
- Добавлены тесты ComfyUI адаптера:
  - успешное извлечение кандидатов из history outputs;
  - ошибка при отсутствии workflow path.

### Verification
- Выполнен `pytest -q`: `3 passed`.

## 2026-03-07 (cli + svg layers update)

### Added
- Реализован terminal-first CLI оркестратор `python -m app.cli`:
  - выбор `library` или `generate`;
  - выбор композиции;
  - выбор палитры из пресетов;
  - сборка/валидация/публикация pack и печать артефактов.
- Реализован векторный выход pack:
  - `vector/master.svg`
  - `vector/layers/{color_hex}.svg`
- В `manifest.json` и schema добавлена обязательная секция `vector_assets`:
  - `master_svg`
  - `color_layers[]` (`color`, `path`)
- Добавлен API endpoint `GET /library/items` для чтения локальной библиотеки.
- Добавлена заготовка пакетного скрипта для TouchDesigner:
  - `tools/touchdesigner_pack_stub.py`

### Tests
- Добавлены unit/integration/failure тесты:
  - `tests/test_vectorizer.py`
  - `tests/test_manifest_schema.py`
  - `tests/test_palette_presets.py`
  - `tests/test_cli_flow.py`
  - `tests/test_library_endpoint.py`
- Обновлен happy-path тест под `vector_assets`.

### Verification
- Выполнен `pytest -q`: `10 passed`.

## 2026-03-08 (session workflow + split containers)

### Added
- Session-driven orchestration для пользовательского потока:
  - `created -> mode_selected -> ... -> ready_for_runtime`
- Новые API endpoint'ы:
  - `POST /sessions`
  - `GET /sessions/{session_id}`
  - `POST /sessions/{session_id}/mode`
  - `POST /sessions/{session_id}/library/select`
  - `POST /sessions/{session_id}/generate/start`
  - `POST /sessions/{session_id}/generate/select`
  - `POST /sessions/{session_id}/variant/select`
  - `GET /palettes/session`
- Generate-path логика:
  - prompt + color range (жестко 2..6);
  - генерация 4 candidates через step-generate;
  - выбор 1 кандидата;
  - vectorize step;
  - build 3 palette variants;
  - выбор финала и перевод в `ready_for_runtime`.
- Library-path логика:
  - выбор готового pack и немедленный перевод сессии в `ready_for_runtime`.
- Frontend переработан в пошаговый wizard-поток.
- Контейнеризация разделена:
  - `frontend`, `api`, `step-generate`, `step-vectorize`, `step-palette`.

### Verification
- Выполнен `pytest -q`: `11 passed`.
