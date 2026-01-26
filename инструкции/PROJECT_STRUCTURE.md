# Структура проекта Complex Flag Scanner

## Файлы и директории

```
complex_flag_scanner/
├── __init__.py                    # Инициализация пакета
├── README.md                      # Основная документация
├── INSTALL.md                     # Инструкция по установке
├── PROJECT_STRUCTURE.md           # Этот файл
├── requirements.txt               # Зависимости Python
├── Dockerfile                     # Docker образ
├── docker-compose.yml             # Docker Compose конфигурация
├── .gitignore                     # Git ignore правила
│
├── scanners/                      # Модули сканеров
│   ├── __init__.py               # Инициализация модуля сканеров
│   ├── bullish_flag_scanner.py   # Сканер бычьего флага (лонг)
│   ├── bearish_flag_scanner.py   # Сканер медвежьего флага (шорт)
│   └── combined_scanner.py       # Адаптер для совместимости
│
├── dashboard.py                   # Streamlit дашборд
├── service.py                     # Фоновый сервис для сканирования
└── plot.py                        # Скрипт для построения графиков

```

## Описание компонентов

### Сканеры (scanners/)
- **bullish_flag_scanner.py** - Поиск бычьих паттернов флаг (сигнал на покупку)
- **bearish_flag_scanner.py** - Поиск медвежьих паттернов флаг (сигнал на продажу)
- **combined_scanner.py** - Адаптер, объединяющий оба сканера для совместимости

### Основные скрипты
- **dashboard.py** - Интерактивный дашборд на Streamlit для просмотра результатов
- **service.py** - Фоновый сервис, который периодически сканирует рынок
- **plot.py** - Утилита для построения графиков с отмеченными точками паттернов

## Зависимости

Проект требует:
- Python 3.10+
- t-tech-investments (библиотека для работы с Tinkoff Invest API)
- pandas, numpy (обработка данных)
- plotly (построение графиков)
- streamlit (дашборд)

См. requirements.txt для полного списка зависимостей.
