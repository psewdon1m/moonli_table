Документ разработки: инженерное ТЗ конвейера подготовки визуального контента для интерактивного рисовального стола
1. Область системы
1.1. Назначение

Система предназначена для подготовки визуального контента для интерактивного рисовального стола.

На входе система получает:

тему, параметры генерации или выбор из библиотеки;

профиль сложности;

ограничения по цветам;

параметры конкретного стола.

На выходе система формирует versioned content pack, который исполняется в TouchDesigner.

1.2. Границы системы

Внутри системы:

генерация черно-белых композиций;

нормализация изображений;

отбор пригодных кандидатов;

выбор композиции;

выбор палитры;

автоматическое назначение палитры;

сегментация на цветовые слои;

сборка content pack;

публикация и хранение в библиотеке.

Вне системы:

кнопочная логика стола;

управление водой;

проигрывание шагов пользователю;

проекционная калибровка;

локальный UI сессии на столе.

1.3. Архитектурный принцип

Production pipeline работает отдельно от runtime стола.
TouchDesigner только исполняет готовый пакет.

2. Архитектура верхнего уровня
2.1. Подсистемы
A. Pipeline Core

Центральный backend на Python.
Отвечает за orchestration, обработку изображений, валидацию, сборку пакетов, библиотеку и публикацию.

B. Generation Backend

Подсистема генерации изображений.
Основной вариант: ComfyUI / ComfyUI Cloud.
Дополнительные backend’ы: OpenAI, Firefly, иные совместимые генераторы.

C. Content Library

Хранилище готовых и промежуточных пакетов, превью, статусов, версий и метаданных.

D. Runtime Delivery Layer

Механизм публикации и доставки готовых пакетов в локальное тестовое окружение и на реальные столы.

E. TouchDesigner Runtime

Исполняет content pack, читает manifest, строит анимацию шага, обслуживает пользовательскую сессию.

2.2. Среда развертывания

Основная серверная часть системы разрабатывается и поставляется в Docker-окружении.

Docker является базовым стандартом для:

локальной разработки;

тестирования;

staging;

production-развертывания pipeline-сервисов.

Контейнеризация распространяется в первую очередь на:

Pipeline Core;

API layer;

workers;

Content Library / registry;

вспомогательные сервисы;

optional n8n, если он будет использоваться.

TouchDesigner runtime на столе может оставаться нативным приложением на mac mini и не обязан быть частью Docker-контура.

ComfyUI может запускаться:

либо отдельно локально;

либо через ComfyUI Cloud;

либо, при необходимости, в отдельном контейнере.

3. Технологический стек
3.1. Базовый стек

Python — ядро конвейера;

Docker — основной способ сборки и развертывания backend-сервисов;

ComfyUI / ComfyUI Cloud — основной generation backend;

TouchDesigner — runtime на столе;

JSON-driven content pack — единый контракт поставки контента.

3.2. Дополнительный стек

OpenAI / Firefly — опциональные генерационные backend’ы;

n8n — опциональный orchestration-layer для очередей, админских workflow и интеграций;

object storage / file storage — хранение пакетов и ассетов;

queue/broker — при переходе к серверному multi-job режиму.

3.3. Инфраструктурный принцип

Система должна быть собрана так, чтобы backend-часть можно было запускать:

локально через docker compose;

на сервере в контейнерной среде;

в облаке без изменения формата content pack.

4. Продуктовая модель
4.1. Режимы работы
Режим 1. Выбор из библиотеки

Пользователь выбирает:

готовую композицию;

палитру.

Режим 2. Генерация нового изображения

Пользователь:

задает тему;

получает shortlist черно-белых композиций;

выбирает композицию;

выбирает палитру;

получает готовый пакет для рисования.

4.2. Базовый приоритет

Основной режим продукта — библиотека проверенных работ.
Генерация нового изображения — дополнительный режим.

4.3. Пополнение библиотеки

Удачные пользовательские изображения могут быть переведены в библиотеку, если:

прошли автоматическую валидацию;

были реально выбраны;

использовались в сессии;

не показали эксплуатационных проблем.

5. Формальные определения
5.1. Композиция

Черно-белый базовый рисунок без палитры, пригодный для последующей раскраски и сегментации.

5.2. Палитра

Набор от 1 до 6 цветов, допустимых для данной композиции.

5.3. Цветовой слой

Совокупность всех областей рисунка, закрашиваемых одним цветом.

5.4. Этап

Один шаг пользовательского рисования.
В текущей логике:

1 этап = 1 цветовой слой

5.5. Content Pack

Независимый versioned набор файлов и JSON-метаданных, который полностью описывает один готовый рисунок для исполнения на столе.

5.6. Generation Profile

Технический профиль генерации, который задает ограничения и требования к изображению до запуска генерации.

6. Основные требования
6.1. Функциональные требования

Система должна:

принимать запрос на генерацию или выбор из библиотеки;

генерировать несколько черно-белых кандидатов;

нормализовать и фильтровать кандидатов;

выдавать shortlist пригодных вариантов;

фиксировать выбор композиции;

фиксировать выбор палитры;

раскладывать палитру по композиции;

сегментировать итоговое изображение на цветовые слои;

формировать JSON-driven content pack;

публиковать пакет в библиотеку или runtime cache;

переиспользовать удачные пакеты как библиотечные элементы.

6.2. Нефункциональные требования

Система должна быть:

модульной;

воспроизводимой;

версионируемой;

контейнеризуемой;

расширяемой по backend’ам;

независимой от конкретного генератора;

безопасной для эксплуатации в публичной среде.

6.3. Требование к генерации

Основной упор делается на constrained generation, то есть на генерацию, которая изначально подчиняется ограничениям системы, а не на последующее исправление большого количества ошибок.

6.4. Требование к проверке

Этапы проверки и валидации сохраняются, но используются как страховочный и контрактный слой, а не как основной способ “чинить” плохую генерацию.

7. Ограничения контента
7.1. Цвета

минимум: 1 цвет;

максимум: 6 цветов.

7.2. Сложность

Рисунок должен быть пригоден для пользователя уровня музейной интерактивной установки, включая детей от 12 лет.

7.3. Геометрия

Композиция должна:

укладываться в безопасную рабочую зону;

не выходить в запрещенные зоны поверхности;

сохранять читаемость при проекции.

7.4. Временная пригодность

Рисунок должен быть проходим в типовой сессии около 20 минут.

7.5. Моторная пригодность

Рисунок должен:

иметь крупные и читаемые формы;

не содержать избыточного числа мелких изолированных зон;

быть удобным для поэтапного рисования по цветам.

8. Модули системы
8.1. request_intake
Назначение

Принимает входной запрос на подготовку контента.

Вход

mode: library | generate

theme

difficulty

max_colors

palette_mode

table_profile

session_profile

Выход

GenerationRequest

Ответственность

первичная валидация параметров;

создание job;

присвоение request_id.

8.2. generation_profile_builder
Назначение

Формирует технический профиль генерации.

Вход

GenerationRequest

системные правила

профиль стола

Выход

GenerationProfile

Ответственность

перевод пользовательского запроса в производственный профиль;

фиксация:

допустимого диапазона цветов;

safe margins;

target complexity;

target duration;

line density;

region constraints.

8.3. candidate_generator
Назначение

Генерирует набор черно-белых кандидатов.

Вход

GenerationProfile

backend id

workflow id

Выход

список CandidateImage

Ответственность

запуск генерации через ComfyUI backend;

поддержка альтернативных backend’ов;

сохранение provenance.

8.4. candidate_normalizer
Назначение

Приводит кандидат к производственному виду.

Вход

CandidateImage

GenerationProfile

Выход

NormalizedCandidate

Ответственность

ресайз;

центрирование;

применение safe zone;

очистка шума;

упрощение мелких элементов;

первичная оценка пригодности.

8.5. candidate_ranker
Назначение

Фильтрует и ранжирует нормализованные варианты.

Вход

список NormalizedCandidate

GenerationProfile

Выход

CandidateShortlist

Ответственность

отсев слабых вариантов;

score-based ranking;

формирование shortlist для пользователя.

8.6. library_selector
Назначение

Возвращает подходящие кандидаты из библиотеки.

Вход

theme

difficulty

max_colors

filters

Выход

список LibraryItem

Ответственность

поиск по тегам;

фильтрация по сложности и цветам;

выдача превью и метаданных.

8.7. composition_selector
Назначение

Фиксирует выбранную пользователем композицию.

Вход

candidate_id или library_item_id

session context

Выход

SelectedComposition

Ответственность

запись выбора;

загрузка ассетов выбранной композиции;

связь выбора с будущим pack.

8.8. palette_selector
Назначение

Фиксирует выбранную палитру.

Вход

palette_id

SelectedComposition

Выход

SelectedPalette

Ответственность

получение палитры;

проверка совместимости;

передача в этап color assignment.

8.9. palette_assignment
Назначение

Назначает цвета композиции.

Вход

SelectedComposition

SelectedPalette

GenerationProfile

Выход

ColoredComposition

Ответственность

распределение цветов по зонам;

контроль лимита 1..6 цветов;

снижение риска слияния соседних зон;

построение итоговой цветовой карты.

8.10. layer_segmenter
Назначение

Разбивает итоговый рисунок на цветовые слои.

Вход

ColoredComposition

Выход

SegmentationResult

Ответственность

построение маски каждого слоя;

определение последовательности шагов;

генерация cumulative states.

8.11. pack_builder
Назначение

Собирает итоговый content pack.

Вход

SelectedComposition

SelectedPalette

SegmentationResult

provenance

validation data

Выход

ContentPack

Ответственность

сборка файловой структуры;

генерация manifest;

генерация auxiliary assets;

versioning.

8.12. validator
Назначение

Проверяет структурную корректность пакета.

Вход

ContentPack

Выход

ValidationReport

Ответственность

проверка manifest schema;

проверка обязательных файлов;

проверка step/layer consistency;

проверка ссылок на assets.

8.13. publisher
Назначение

Публикует пакет в библиотеку и/или runtime cache.

Вход

ContentPack

ValidationReport

destination

Выход

PublishedPack

Ответственность

запись в registry;

присвоение статуса;

публикация на стол или в тестовое окружение.

8.14. library_promoter
Назначение

Переводит удачные пакеты в curated library.

Вход

pack id

usage metrics

approval rules

Выход

обновленный статус библиотечного элемента

Ответственность

анализ пригодности;

перевод в library_candidate или library.

9. Потоки данных
9.1. Поток генерации

GenerationRequest
→ GenerationProfile
→ CandidateImage[]
→ NormalizedCandidate[]
→ CandidateShortlist
→ SelectedComposition
→ SelectedPalette
→ ColoredComposition
→ SegmentationResult
→ ContentPack
→ ValidationReport
→ PublishedPack

9.2. Поток библиотеки

LibraryQuery
→ LibraryItem[]
→ SelectedComposition
→ SelectedPalette
→ ColoredComposition
→ SegmentationResult
→ ContentPack
→ ValidationReport
→ PublishedPack

10. Сущности данных
10.1. GenerationRequest
{
  "request_id": "req_001",
  "mode": "generate",
  "theme": "forest animal",
  "difficulty": "medium",
  "max_colors": 6,
  "palette_mode": "user_select",
  "table_profile_id": "table_default",
  "session_profile_id": "kids_20m"
}
10.2. GenerationProfile
{
  "profile_id": "gp_001",
  "request_id": "req_001",
  "canvas_width": 1920,
  "canvas_height": 1080,
  "safe_margin_px": 80,
  "max_colors": 6,
  "target_color_range": [1, 6],
  "target_complexity": "medium",
  "target_session_minutes": 20,
  "max_micro_regions": 12,
  "min_region_area_px": 2500,
  "line_style": "clean_outline"
}
10.3. CandidateImage
{
  "candidate_id": "cand_001",
  "profile_id": "gp_001",
  "backend": "comfyui",
  "workflow_id": "bw_outline_v3",
  "seed": 123456,
  "image_path": "candidates/cand_001.png",
  "preview_path": "candidates/cand_001_preview.png",
  "status": "generated"
}
10.4. NormalizedCandidate
{
  "candidate_id": "cand_001",
  "normalized_image_path": "normalized/cand_001.png",
  "normalization_version": "1.0.0",
  "quality_metrics": {
    "estimated_region_count": 5,
    "micro_region_count": 2,
    "edge_margin_ok": true,
    "readability_score": 0.84
  },
  "status": "normalized"
}
10.5. CandidateShortlist
{
  "shortlist_id": "sl_001",
  "request_id": "req_001",
  "candidate_ids": ["cand_001", "cand_004", "cand_007"],
  "ranking_version": "1.0.0"
}
10.6. SelectedComposition
{
  "selection_id": "selc_001",
  "source_type": "generated",
  "source_id": "cand_001",
  "composition_bw_path": "selected/composition_bw.png",
  "outline_master_path": "selected/outline_master.png"
}
10.7. SelectedPalette
{
  "selection_id": "selp_001",
  "palette_id": "palette_spring_01",
  "colors": ["#F4D35E", "#EE964B", "#F95738", "#0D3B66"]
}
10.8. ColoredComposition
{
  "colored_id": "col_001",
  "composition_id": "selc_001",
  "palette_id": "palette_spring_01",
  "composition_colored_path": "colored/composition_colored.png",
  "actual_colors": 4,
  "color_map": [
    {"region_id": "r1", "color": "#F4D35E"},
    {"region_id": "r2", "color": "#0D3B66"}
  ]
}
10.9. SegmentationResult
{
  "segmentation_id": "seg_001",
  "colored_id": "col_001",
  "step_count": 4,
  "layers": [
    {
      "step_index": 1,
      "color": "#F4D35E",
      "mask_path": "layers/layer_01_mask.png",
      "state_before_path": "states/state_00_base.png",
      "state_after_path": "states/state_01_done.png"
    }
  ]
}
10.10. ContentPack
{
  "pack_id": "pack_001",
  "version": "1.0.0",
  "root_path": "packs/pack_001/",
  "manifest_path": "packs/pack_001/manifest.json",
  "status": "packaged"
}
10.11. ValidationReport
{
  "pack_id": "pack_001",
  "schema_ok": true,
  "assets_ok": true,
  "steps_ok": true,
  "errors": [],
  "warnings": []
}
10.12. LibraryItem
{
  "library_item_id": "lib_001",
  "pack_id": "pack_001",
  "title": "Forest Fox",
  "theme": "forest",
  "difficulty": "medium",
  "estimated_duration_min": 18,
  "actual_colors": 4,
  "usage_count": 16,
  "started_count": 13,
  "completion_count": 9,
  "status": "library"
}
11. Структура content pack
content_pack/
  manifest.json
  generation_profile.json
  validation_report.json
  preview.png
  composition_bw.png
  composition_colored.png
  outline_master.png
  palette.json
  layers/
    layer_01_mask.png
    layer_02_mask.png
    ...
  states/
    state_00_base.png
    state_01_done.png
    state_02_done.png
    ...
  thumbs/
    thumb_sm.png
    thumb_md.png
12. Manifest schema
12.1. Обязательные поля manifest.json
{
  "id": "pack_001",
  "version": "1.0.0",
  "status": "approved",
  "source_type": "generated",
  "generator_backend": "comfyui",
  "workflow_id": "bw_outline_v3",
  "created_at": "2026-03-06T12:00:00Z",
  "theme": "forest fox",
  "difficulty": "medium",
  "estimated_duration_min": 18,
  "canvas_size": {"width": 1920, "height": 1080},
  "safe_zone": {"left": 80, "top": 80, "right": 80, "bottom": 80},
  "actual_colors": 4,
  "step_count": 4,
  "palette": {
    "palette_id": "palette_spring_01",
    "colors": ["#F4D35E", "#EE964B", "#F95738", "#0D3B66"]
  },
  "steps": [],
  "asset_paths": {},
  "provenance": {},
  "compatibility": {
    "runtime": "touchdesigner",
    "schema_version": "1.0.0"
  }
}
12.2. Поля элемента steps[]
{
  "step_index": 1,
  "color_id": "c1",
  "color_value": "#F4D35E",
  "layer_mask_path": "layers/layer_01_mask.png",
  "state_before_path": "states/state_00_base.png",
  "state_after_path": "states/state_01_done.png",
  "animation_mode": "fill_mask",
  "recommended_duration_sec": 12,
  "repeat_allowed": true
}
13. API endpoints
13.1. Общие принципы

API внутренний;

обмен в JSON;

долгие операции работают как jobs;

ассеты передаются через file paths или object storage references.

13.2. Jobs
POST /jobs

Создать новую задачу.

{
  "mode": "generate",
  "theme": "forest fox",
  "difficulty": "medium",
  "max_colors": 6,
  "palette_mode": "user_select"
}
GET /jobs/{job_id}

Получить состояние задачи.

{
  "job_id": "job_001",
  "status": "shortlist_ready",
  "current_stage": "candidate_ranker"
}
13.3. Генерация
POST /generation-profiles

Создать generation profile.

POST /candidates/generate

Запустить генерацию кандидатов.

{
  "profile_id": "gp_001",
  "backend": "comfyui",
  "workflow_id": "bw_outline_v3",
  "count": 6
}
POST /candidates/normalize

Нормализовать список кандидатов.

POST /candidates/rank

Ранжировать кандидатов.

GET /candidates/shortlist/{shortlist_id}

Получить shortlist.

13.4. Библиотека
GET /library/items

Получить элементы библиотеки.

GET /library/items/{library_item_id}

Получить подробности библиотечного элемента.

POST /library/promote

Продвинуть пакет в curated library.

{
  "pack_id": "pack_001"
}
13.5. Выбор
POST /selections/composition
{
  "source_type": "generated",
  "source_id": "cand_001"
}
POST /selections/palette
{
  "composition_selection_id": "selc_001",
  "palette_id": "palette_spring_01"
}
13.6. Сборка
POST /compositions/apply-palette

Применить палитру.

POST /segmentations

Выполнить сегментацию.

POST /packs/build
{
  "composition_selection_id": "selc_001",
  "palette_selection_id": "selp_001"
}
POST /packs/validate

Провести структурную проверку.

POST /packs/publish
{
  "pack_id": "pack_001",
  "destination": "local_runtime_cache"
}
13.7. Runtime delivery
GET /packs/{pack_id}/manifest

Получить manifest.

GET /packs/{pack_id}/assets

Получить список assets.

POST /runtime/sync

Синхронизировать пакет с runtime.

14. Контейнеризация и Docker-требования
14.1. Базовый принцип

Основная backend-часть системы собирается и разворачивается в Docker.

14.2. Обязательные Docker-компоненты

В контейнеры должны выноситься:

pipeline core;

API service;

job workers;

content library / registry service;

optional queue/broker;

optional n8n;

вспомогательные сервисы упаковки и публикации.

14.3. Допустимые исключения

Нативно могут работать:

TouchDesigner runtime на mac mini;

отдельный ComfyUI instance, если это удобнее для GPU/Cloud-конфигурации.

14.4. Требования к контейнерной сборке

каждый backend-сервис должен иметь Dockerfile;

локальный запуск должен поддерживаться через docker compose;

конфигурация должна выноситься в environment variables;

зависимости backend-сервисов не должны требовать ручной установки на host-машину;

dev/test/prod окружения должны быть максимально унифицированы.

14.5. Целевой Docker-контур

Минимальная контейнерная схема:

api

worker

library/registry

storage adapter

optional queue

optional admin/orchestrator

15. Статусы и state machine
15.1. Job statuses

queued

profile_ready

generation_running

generation_done

normalization_done

shortlist_ready

composition_selected

palette_selected

segmentation_done

packaged

validated

published

failed

15.2. Pack statuses

generated

normalized

validated

packaged

approved

used_on_table

started_by_user

library_candidate

library

archived

16. Логирование и трассировка
16.1. Для каждого job сохранять

request_id;

job_id;

stage transitions;

backend calls;

workflow id;

seed;

processing duration;

errors;

operator actions.

16.2. Для каждого pack сохранять

manifest version;

generator backend;

source ids;

palette;

segmentation version;

validation version;

publication history.

17. Ошибки и обработка сбоев
17.1. Категории ошибок

generation backend unavailable;

invalid profile;

no suitable candidates;

normalization failed;

palette assignment failed;

segmentation failed;

manifest build failed;

asset missing;

publish failed.

17.2. Правила обработки

ошибки генерации не должны повреждать библиотеку;

незавершенный pack не получает статус published;

частично собранные результаты остаются в промежуточном storage со статусом failed;

все ошибки логируются с request id и stage id.

18. Интеграция с TouchDesigner
18.1. Контракт runtime

TouchDesigner ожидает:

manifest.json;

palette.json;

layer masks;

cumulative states;

preview assets.

18.2. Ответственность runtime

чтение manifest;

отображение текущего шага;

repeat/back/next;

локальное хранение состояния сессии;

процедурная анимация из JSON-driven данных.

18.3. Runtime не делает

генерацию;

сегментацию;

пересборку пакета;

библиотечную логику;

production orchestration.

19. Roadmap
Phase 1 — локальный инженерный прототип
Scope

Python service в Docker

API в Docker

worker в Docker при необходимости

ComfyUI локально или отдельно

генерация 4–6 BW кандидатов

нормализация

shortlist

ручной выбор композиции

ручной выбор палитры

palette assignment

segmentation

manifest + assets

импорт в TouchDesigner

Deliverables

рабочий CLI/API;

schema manifest v1;

demo pack;

runtime import test.

Phase 2 — библиотека и publish flow
Scope

library storage

item statuses

usage metadata

publish endpoint

local runtime cache sync

начальная curated library

Deliverables

библиотека пакетов;

фильтрация по теме/сложности;

promotion flow.

Phase 3 — серверный запуск
Scope

перенос pipeline на отдельный сервер

object storage

job queue

доставка pack’ов на тестовые столы

стабильные фоновые jobs

переход от локального docker compose к серверному контейнерному разворачиванию

Deliverables

server deployment;

multi-job processing;

runtime sync;

контейнерная инфраструктура production-уровня.

Phase 4 — ComfyUI Cloud / external backends
Scope

переключаемые backend’ы

ComfyUI Cloud

optional OpenAI / Firefly routes

unified backend adapter layer

Deliverables

backend abstraction;

configurable generator selection;

provenance consistency.

Phase 5 — библиотека, аналитика, promotion rules
Scope

usage scoring

started/completed metrics

auto-promotion suggestions

content retirement rules

Deliverables

semi-automatic library curation;

quality-based ranking.

20. Приемочные критерии

Система считается принятой на инженерном уровне, если:

Новый job можно создать через API.

Система может сгенерировать shortlist кандидатов.

Система может собрать content pack без ручной раскладки файлов.

Manifest соответствует schema v1.

TouchDesigner может прочитать пакет без изменения структуры.

Один и тот же формат pack работает и для generated, и для library source.

Backend генерации можно заменить без изменения manifest schema.

У каждого pack есть provenance и version history.

Backend-часть может быть поднята в Docker-окружении.

Локальная разработка поддерживается через docker compose.

21. Итоговое решение

Утвержденная архитектура:

Python service — ядро конвейера;

Docker — основной стандарт сборки и развертывания backend-части;

ComfyUI / ComfyUI Cloud — основной генерационный backend;

OpenAI / Firefly — подключаемые внешние backend’ы;

TouchDesigner — runtime исполнения;

JSON-driven content pack — единый формат поставки.