# Инструкция по установке

## Быстрый старт

1. Убедитесь, что у вас установлен Python 3.10+

2. Установите зависимости:
```bash
pip install -r requirements.txt
```

3. Создайте файл `.env` в корне проекта:
```
TINKOFF_INVEST_TOKEN=your_token_here
```

4. Запустите дашборд:
```bash
streamlit run dashboard.py --server.port=8501
```

Или используйте Docker:
```bash
docker-compose up -d
```

## Зависимости

Проект требует библиотеку `t-tech-investments` для работы с API Tinkoff Invest.
Убедитесь, что она доступна в вашем окружении Python.
