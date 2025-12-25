# Сканер сложного флага (Complex Flag Scanner)

Проект для поиска и анализа паттернов "Флаг" со структурой 0-1-2-3-4 на финансовых рынках.

## Описание

Сканер ищет два типа паттернов:
- **Бычий флаг** (Bullish Flag) - сигнал на покупку (лонг)
- **Медвежий флаг** (Bearish Flag) - сигнал на продажу (шорт)

## Структура проекта

```
complex_flag_scanner/
├── scanners/
│   ├── __init__.py               # Инициализация модуля
│   ├── bullish_flag_scanner.py   # Сканер бычьего флага
│   ├── bearish_flag_scanner.py   # Сканер медвежьего флага
│   └── combined_scanner.py       # Адаптер для совместимости
├── dashboard.py                   # Streamlit дашборд
├── service.py                     # Фоновый сервис для сканирования
├── plot.py                        # Скрипт для построения графиков
├── requirements.txt               # Зависимости Python
├── Dockerfile                     # Docker образ
├── docker-compose.yml            # Docker Compose конфигурация
└── README.md                      # Этот файл
```

## Зависимости

Проект требует наличия библиотеки `t-tech-investments` для работы с API Tinkoff Invest.

**Важно:** Убедитесь, что у вас есть доступ к библиотеке `t-tech-investments` или установите её из соответствующего источника.

## Установка

1. Установите зависимости:
```bash
pip install -r requirements.txt
```

2. Создайте файл `.env` с токеном Tinkoff Invest API:
```
TINKOFF_INVEST_TOKEN=your_token_here
```

## Использование

### Запуск дашборда

```bash
streamlit run dashboard.py --server.port=8501
```

Дашборд будет доступен по адресу: http://localhost:8501

### Запуск фонового сервиса

```bash
python service.py
```

### Построение графиков для анализа

```bash
python plot.py
```

Или используйте функции из модуля:
```python
from plot import plot_bullish_flag, plot_bearish_flag

plot_bullish_flag('VKCO', 'TQBR', days_back=10, output_file='output.html')
plot_bearish_flag('VKCO', 'TQBR', days_back=10, output_file='output.html')
```

### Использование сканеров

```python
from scanners.bullish_flag_scanner import BullishFlagScanner
from scanners.bearish_flag_scanner import BearishFlagScanner
import os
from dotenv import load_dotenv

load_dotenv()
token = os.environ.get('TINKOFF_INVEST_TOKEN')

# Бычий флаг
bullish_scanner = BullishFlagScanner(token)
df = bullish_scanner.get_candles_df('VKCO', 'TQBR', days_back=10)
patterns = bullish_scanner.analyze(df, debug=True)

# Медвежий флаг
bearish_scanner = BearishFlagScanner(token)
df = bearish_scanner.get_candles_df('VKCO', 'TQBR', days_back=10)
patterns = bearish_scanner.analyze(df, debug=True)
```

## Docker

Запуск через Docker Compose:

```bash
docker-compose up -d
```

Это запустит:
- Дашборд на порту 8501
- Фоновый сервис сканирования

## Паттерн 0-1-2-3-4

### Бычий флаг:
- **T0**: Начало флагштока (Low)
- **T1**: Вершина флагштока (High)
- **T2**: Первый откат (Low)
- **T3**: Второй пик (High, <= T1)
- **T4**: Второй откат (Low, >= T0 + 50% флагштока)
- **Пробой**: Цена пробивает линию сопротивления T1-T3 вверх

### Медвежий флаг:
- **T0**: Начало падения (High)
- **T1**: Низ флагштока (Low)
- **T2**: Первый откат (High)
- **T3**: Второй минимум (Low, >= T1)
- **T4**: Второй откат (High, <= T2)
- **Пробой**: Цена пробивает линию поддержки T1-T3 вниз

## Лицензия

MIT
