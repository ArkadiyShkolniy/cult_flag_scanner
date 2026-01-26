# Использование Docker контейнера

## ✅ Образ собран

Docker образ `complex-flag-scanner:latest` успешно собран.

## Запуск через Docker Compose

### 1. Убедитесь, что есть .env файл

Создайте файл `.env` в директории проекта:

```bash
cd /Users/arkadiyshkolniy/Documents/cult_trade/invest-python-main/complex_flag_scanner
echo "TINKOFF_INVEST_TOKEN=ваш_токен" > .env
```

### 2. Запустите контейнеры

```bash
docker-compose up -d
```

Это запустит:
- **Дашборд** на порту 8504: http://localhost:8504
- **Фоновый сервис** сканирования (без портов, работает в фоне)

### 3. Просмотр логов

```bash
# Логи дашборда
docker-compose logs -f complex-flag-dashboard

# Логи фонового сервиса
docker-compose logs -f complex-flag-worker
```

### 4. Остановка

```bash
docker-compose down
```

## Запуск только дашборда (без docker-compose)

```bash
docker run -d \
  --name complex-flag-dashboard \
  -p 8501:8501 \
  --env-file .env \
  -v $(pwd):/app \
  complex-flag-scanner:latest \
  streamlit run dashboard.py --server.port=8501 --server.address=0.0.0.0 --server.enableCORS=false --server.enableXsrfProtection=false
```

## Проверка работы

1. Откройте браузер: http://localhost:8504
2. Должен открыться дашборд сканера сложного флага

## Проблемы

### Порт 8503 уже занят

Измените порт в `docker-compose.yml`:
```yaml
ports:
  - "8504:8501"  # Внешний порт 8504, внутренний 8501
```

### Ошибка с .env файлом

Убедитесь, что файл `.env` существует и содержит:
```
TINKOFF_INVEST_TOKEN=ваш_токен_здесь
```

### Проверка контейнеров

```bash
docker-compose ps
docker ps | grep complex-flag
```
