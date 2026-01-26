# 🚀 Быстрый запуск всех компонентов

## Предварительные требования

1. **Установите зависимости Python:**
```bash
cd /home/ark/projects/trading_bot
pip3 install -r requirements.txt
```

2. **Убедитесь, что файл `.env` существует и содержит:**
```
TINKOFF_INVEST_TOKEN=your_token_here
TELEGRAM_BOT_TOKEN=your_telegram_token  # Опционально, для продакшена
TELEGRAM_CHAT_ID=your_chat_id           # Опционально, для продакшена
```

## Запуск всех компонентов

### Вариант 1: Использование скрипта (рекомендуется)

```bash
cd /home/ark/projects/trading_bot
./start_all.sh
```

### Вариант 2: Ручной запуск

#### 1. 🎨 Инструмент для разметки паттернов
```bash
cd /home/ark/projects/trading_bot
streamlit run neural_network/labeling_dashboard.py --server.port=8505 --server.address=0.0.0.0
```
**Доступ:** http://localhost:8505

#### 2. 🤖 Торговый робот для отладки
```bash
cd /home/ark/projects/trading_bot
python3 service.py --mode debug --enable-trading --entry-mode parallel_lines
```

#### 3. 📊 Дашборд для отладки
```bash
cd /home/ark/projects/trading_bot
streamlit run trading_bot/trading_dashboard.py --server.port=8506 --server.address=0.0.0.0
```
**Доступ:** http://localhost:8506

#### 4. 💰 Торговый робот на реальном рынке
```bash
cd /home/ark/projects/trading_bot
python3 service.py --mode prod --enable-trading --entry-mode parallel_lines
```

#### 5. 📊 Дашборд для продакшена
```bash
cd /home/ark/projects/trading_bot
streamlit run trading_bot/trading_dashboard.py --server.port=8502 --server.address=0.0.0.0
```
**Доступ:** http://localhost:8502

## Проверка статуса

```bash
./status.sh
```

## Остановка всех компонентов

```bash
./stop_all.sh
```

## Просмотр логов

```bash
# Логи инструмента разметки
tail -f logs/labeling.log

# Логи торгового робота для отладки
tail -f logs/debug_bot.log

# Логи торгового робота продакшена
tail -f logs/prod_bot.log

# Логи дашбордов
tail -f logs/debug_dashboard.log
tail -f logs/prod_dashboard.log
```

## Проблемы и решения

### Ошибка: "ModuleNotFoundError: No module named 'streamlit'"
**Решение:** Установите зависимости:
```bash
pip3 install streamlit pandas plotly matplotlib python-dotenv
```

### Ошибка: "No such file or directory: streamlit"
**Решение:** Установите streamlit:
```bash
pip3 install streamlit
```

### Ошибка: "TINKOFF_INVEST_TOKEN не найден"
**Решение:** Создайте файл `.env` с токеном:
```bash
echo "TINKOFF_INVEST_TOKEN=your_token_here" > .env
```

## Порты компонентов

| Компонент | Порт | URL |
|-----------|------|-----|
| 🎨 Инструмент разметки | 8505 | http://localhost:8505 |
| 🤖 Дашборд отладки | 8506 | http://localhost:8506 |
| 💰 Дашборд продакшена | 8502 | http://localhost:8502 |

## Важные замечания

⚠️ **ВНИМАНИЕ:** Торговый робот продакшена работает с **реальными деньгами**!
- Убедитесь, что все параметры настроены правильно
- Начните с минимальных объемов
- Мониторьте работу через дашборд
- Проверьте логи перед запуском
