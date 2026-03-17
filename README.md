# Mail Import

Django-сервис для импорта рассылок из XLSX-файла с последующей отправкой писем.

## Стек

| Слой        | Технология              |
|-------------|-------------------------|
| Язык        | Python 3.11             |
| Фреймворк   | Django 4.2              |
| База данных | PostgreSQL 15           |
| XLSX        | openpyxl                |
| Контейнер   | Docker + docker-compose |
| Линтеры     | black, ruff, pre-commit |
| Тесты       | pytest + pytest-django  |

---

## Быстрый старт

git clone https://github.com/boshka22/jetland_testovoe2
```bash
cp .env.example .env
docker-compose up --build
```

---

## Импорт рассылок

```bash
docker-compose exec web python manage.py import_mailings /app/sest.xlsx
```

### Формат XLSX-файла

Первая строка — заголовки. Порядок колонок не важен.

| Колонка       | Описание                                      |
|---------------|-----------------------------------------------|
| `external_id` | Уникальный ID записи во внешней системе       |
| `user_id`     | ID пользователя (целое положительное число)   |
| `email`       | Email получателя                              |
| `subject`     | Тема письма                                   |
| `message`     | Текст письма                                  |

### Пример вывода

```
Importing: /data/mailings.xlsx

Импорт завершён: /data/mailings.xlsx
────────────────────────────────────────
Обработано строк:         1000
Создано:                   950
Пропущено (дубли):          30
Ошибок:                     20
Время:                    4м 23с
Batch ID:                   7
```

### Повторный импорт

`external_id` используется как идемпотентный ключ. При повторном запуске
с тем же файлом уже обработанные строки будут пропущены (`Пропущено`),
а не созданы повторно.

---

## Структура проекта

```
mail_import/
├── apps/
│   └── mailings/
│       ├── models.py           # ImportBatch, MailingRecord
│       ├── services.py         # iter_xlsx_rows, validate_row, MailingImportService
│       ├── email.py            # send_email (заглушка с sleep + logging)
│       ├── exceptions.py       # доменные исключения
│       ├── admin.py
│       ├── migrations/
│       ├── management/
│       │   └── commands/
│       │       └── import_mailings.py
│       └── tests/
├── config/
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── Dockerfile
├── docker-compose.yml
└── entrypoint.sh
```

---

## Тесты

```bash
docker-compose exec web pip install -r requirements/test.txt
docker-compose exec web pytest
```

---

## Линтеры

```bash
pip install -r requirements/lint.txt
pre-commit install
black .
ruff check .
```
