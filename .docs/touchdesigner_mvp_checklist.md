# Чек-лист MVP импорта в TouchDesigner

Цель: подтвердить, что собранный `content pack` импортируется и исполняется в TouchDesigner без ручного изменения структуры пакета.

## 1. Подготовка пакета

- Создать job через `POST /jobs`.
- Получить shortlist через `POST /jobs/{job_id}/generate`.
- Выбрать композицию через `POST /jobs/{job_id}/selection/composition`.
- Выбрать палитру (1..6 цветов) через `POST /jobs/{job_id}/selection/palette`.
- Собрать pack через `POST /jobs/{job_id}/build`.
- Проверить schema через `GET /packs/{pack_id}/validate` (`valid = true`).
- Опубликовать в runtime cache через `POST /packs/{pack_id}/publish`.

## 2. Проверка структуры файлов

В опубликованном каталоге pack должны быть:
- `manifest.json`
- `palette.json`
- `assets/preview.txt`
- `layers/step_XX_mask.txt`
- `cumulative/step_XX_state.txt`

Количество `step_*` должно совпадать с количеством цветов в палитре.

## 3. Проверка контракта в TouchDesigner

- Runtime читает `manifest.json` без ошибок парсинга.
- Runtime корректно подхватывает список шагов (`steps[]`).
- Для каждого шага доступны:
  - путь к `layer_mask`
  - путь к `cumulative_state`
  - цвет шага
- Навигация `next/back/repeat` отрабатывает без падений.

## 4. Критерии прохождения MVP

- Импорт выполнен без ручной правки структуры файлов.
- Пошаговый сценарий рисования воспроизводится в TouchDesigner.
- Один и тот же формат pack применим для generated-потока.
- `manifest` остается валидным по schema v1.

## 5. Логи и артефакты подтверждения

- Сохранить `job_id`, `pack_id`, timestamp проверки.
- Сохранить копию `manifest.json` проверенного пакета.
- Зафиксировать результат проверки в `.docs/CHANGELOGE.md`.

