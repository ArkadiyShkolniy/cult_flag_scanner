# Структура проекта Trading Bot

## Основные директории

### `/trading_bot/` - Модуль торгового бота
- `trade_manager.py` - Управление сделками, расчет объема, ML-фильтрация
- `trade_strategy.py` - Логика входа в позиции (EMA Squeeze, Parallel Lines)
- `trading_dashboard.py` - Streamlit дашборд для визуализации
- `parallel_entry_strategy.py` - Стратегия параллельного входа
- `pattern_tracker.py` - Отслеживание паттернов

### `/scanners/` - Сканеры паттернов
- `bullish_flag_scanner.py` - Сканер бычьего флага
- `bearish_flag_scanner.py` - Сканер медвежьего флага
- `combined_scanner.py` - Объединенный сканер
- `hybrid_scanner.py` - Гибридный сканер

### `/neural_network/` - ML модели
- Модели для фильтрации сделок
- Скрипты для обучения

## Основные файлы

- `service.py` - Фоновый сервис сканирования
- `config.py` - Конфигурация
- `requirements.txt` - Зависимости
- `docker-compose.yml` - Docker конфигурация
