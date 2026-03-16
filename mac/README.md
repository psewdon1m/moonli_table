# moonli_table mac runtime (vectorize + segment only)

Минимальный локальный стек для Mac:

- `step-vectorize`
- `step-segment`
- `pipeline-api` (единая точка триггера для TouchDesigner)

## 1) Структура данных (важно для интеграции)

Этот стек использует bind mount:

- локальная папка `mac/io` -> контейнерная `/app/data`

Создайте папки:

```bash
cd ~/desktop/engine/moonli_table/mac
mkdir -p io/incoming io/sessions
```

TouchDesigner должен сохранять сгенерированные изображения в:

- `~/desktop/engine/moonli_table/mac/io/incoming`

## 2) Запуск

```bash
cd ~/desktop/engine/moonli_table/mac
docker compose up -d --build
```

Проверка:

```bash
curl http://localhost:8011/health
curl http://localhost:8002/health
curl http://localhost:8004/health
```

## 3) Как связать с TouchDesigner

### Рекомендуемый вариант (без upload, быстрее и стабильнее)

1. В TouchDesigner генерация делает PNG/JPG и сохраняет файл в:
   `~/desktop/engine/moonli_table/mac/io/incoming/<name>.png`
2. TouchDesigner отправляет trigger в `pipeline-api`:

```bash
curl -X POST http://localhost:8011/process/local \
  -H "Content-Type: application/json" \
  -d '{
    "local_path":"incoming/frame_001.png",
    "session_id":"sess_td_001",
    "candidate_id":"cand_td_001",
    "layer_count":6
  }'
```

3. В ответ получаете:
   - `master_svg_path`
   - `segment_dir`
   - `master_svg_uri`

`master_svg_uri` можно открыть по HTTP:

- `http://localhost:8011` + `master_svg_uri`

### Вариант с upload файла (если не хотите писать в shared folder)

```bash
curl -X POST http://localhost:8011/process \
  -F "file=@/absolute/path/to/frame_001.png" \
  -F "session_id=sess_td_001" \
  -F "candidate_id=cand_td_001" \
  -F "layer_count=6"
```

### Вариант по URL

```bash
curl -X POST http://localhost:8011/process/url \
  -H "Content-Type: application/json" \
  -d '{
    "image_url":"https://example.com/frame_001.png",
    "session_id":"sess_td_001",
    "candidate_id":"cand_td_001",
    "layer_count":6
  }'
```

## 4) Отмашка в TouchDesigner о завершении

По умолчанию trigger синхронный:

- TD отправляет запрос
- TD получает JSON-ответ со статусом `completed`

Если нужен push-callback, передайте `callback_url`:

- `process/local`: поле `callback_url`
- `process/url`: поле `callback_url`
- `process` (multipart): `callback_url` form field

`pipeline-api` отправит туда JSON-результат после окончания обработки.

## 5) Формат ответа

```json
{
  "status": "completed",
  "session_id": "sess_td_001",
  "candidate_id": "cand_td_001",
  "source_uri": "/app/data/incoming/frame_001.png",
  "prepared_image_path": "/app/data/sessions/sess_td_001/vectorize/base_xxxxxxxx/base_cand_td_001/prepared_rgba.png",
  "segment_dir": "/app/data/sessions/sess_td_001/segment",
  "master_svg_path": "/app/data/sessions/sess_td_001/segment/base_yyyyyyyy/vector/master.svg",
  "master_svg_uri": "/data/sessions/sess_td_001/segment/base_yyyyyyyy/vector/master.svg",
  "layer_count": 6
}
```

## 6) Practical notes

- `layer_count` ограничен `2..6`.
- Лучший вход: PNG (желательно с прозрачным фоном).
- Выходные SVG и слои лежат в `mac/io/sessions/...`.
