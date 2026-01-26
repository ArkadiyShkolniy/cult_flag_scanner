FROM python:3.11-slim

WORKDIR /app

# Устанавливаем git и wget для установки пакетов
RUN apt-get update && apt-get install -y --no-install-recommends git wget curl && \
    rm -rf /var/lib/apt/lists/*

# Копируем requirements и устанавливаем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    # Устанавливаем t-tech-investments из официального источника (см. https://developer.tbank.ru/invest/sdk/python_sdk/faq_python)
    # Из-за ограничений нельзя установить через pip install, нужно скачать wheel файл
    (wget -q https://files.pythonhosted.org/packages/89/41/ca4f7b8985c74035744313af8af999d82e5793f8f3fc676b7580dadc9653/t_tech_investments-0.3.3-py3-none-any.whl -O /tmp/t_tech_investments-0.3.3-py3-none-any.whl && \
     pip install --no-cache-dir /tmp/t_tech_investments-0.3.3-py3-none-any.whl && rm /tmp/t_tech_investments-0.3.3-py3-none-any.whl && \
     echo "✅ t-tech-investments installed from official wheel file") || \
    (echo "⚠️ Warning: t-tech-investments installation failed, will try at runtime..." && true) && \
    # Устанавливаем остальные зависимости
    pip install --no-cache-dir -r requirements.txt

# Копируем код приложения
COPY . .

# Делаем скрипт установки зависимостей исполняемым
RUN chmod +x /app/install_deps.sh 2>/dev/null || true

# По умолчанию запускаем дашборд
CMD ["streamlit", "run", "dashboard.py", "--server.port=8501", "--server.address=0.0.0.0"]
