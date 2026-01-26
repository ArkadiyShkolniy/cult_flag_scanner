# 🚀 Быстрый старт - Удаленная разработка на Windows

## ⚡ Краткая шпаргалка

### Первоначальная настройка (один раз)
```bash
# 1. Подключиться к Windows/WSL2 через VS Code Remote SSH
# 2. В терминале WSL2:
cd ~/projects/invest-python-main/complex_flag_scanner

# 3. Проверить окружение
chmod +x scripts/*.sh
./scripts/check_remote_setup.sh

# 4. Создать .env файл (если еще нет)
nano .env
# Добавить: TINKOFF_INVEST_TOKEN=your_token

# 5. Запустить контейнеры
docker compose up -d
```

---

## 📋 Ежедневное использование

### Утренний запуск
```bash
# 1. Подключиться через VS Code Remote SSH
# 2. В терминале:
cd ~/projects/invest-python-main/complex_flag_scanner

# 3. Проверить статус
./scripts/manage_containers.sh status

# 4. Если нужно - запустить
./scripts/manage_containers.sh start
```

### Запуск обучения нейросети
```bash
# В фоновой сессии (не прервется при отключении SSH)
./scripts/start_training.sh 100 16 0.003

# Смотреть прогресс
tail -f neural_network/training_log.txt

# Или подключиться к screen сессии
screen -r nn_training
```

### Проверка логов
```bash
# Все логи
docker compose logs -f

# Логи торгового робота
docker compose logs -f trading-bot

# Логи обучения (если в screen)
screen -r nn_training
```

### Остановка/перезапуск
```bash
# Перезапустить торгового робота
./scripts/manage_containers.sh restart trading-bot

# Остановить все
./scripts/manage_containers.sh stop

# Запустить снова
./scripts/manage_containers.sh start
```

---

## 🌐 Доступ к дашбордам

После подключения через VS Code Remote SSH:

1. **Пробросить порты в VS Code:**
   - `F1` → `Remote-SSH: Forward Port from Active Host`
   - Порты: `8504`, `8505`, `8506`

2. **Открыть в браузере:**
   - Разметка: http://localhost:8505
   - Trading Dashboard: http://localhost:8506

---

## 🔍 Мониторинг

### Проверка статуса
```bash
# Статус контейнеров
docker compose ps

# Использование ресурсов
docker stats --no-stream

# Проверка обучения
tail -n 20 neural_network/training_log.txt
```

### Screen сессии
```bash
# Список сессий
screen -list

# Подключиться
screen -r nn_training

# Создать новую сессию
screen -S my_session

# Отключиться (не завершая): Ctrl+A, затем D
# Завершить: Ctrl+A, затем K, затем Y
```

---

## 🐛 Быстрое решение проблем

### Контейнеры не запускаются
```bash
docker compose down
docker compose up -d
```

### Обучение не запускается
```bash
# Проверить, запущены ли контейнеры
docker compose ps

# Перезапустить labeling контейнер
docker compose restart labeling
```

### Не могу подключиться по SSH
```bash
# На удаленной Windows машине (в WSL2):
sudo service ssh restart

# Проверить IP
hostname -I
```

### Порты не открываются
```bash
# Проверить, что контейнеры запущены
docker compose ps

# Проверить проброс портов в VS Code
# F1 → Remote-SSH: Kill VS Code Server → Переподключиться
```

---

## 📝 Полезные команды

```bash
# Быстрый доступ к логам
alias logs-bot='docker compose logs -f trading-bot'
alias logs-labeling='docker compose logs -f labeling'

# Добавить в ~/.bashrc для постоянного использования
echo "alias logs-bot='docker compose logs -f trading-bot'" >> ~/.bashrc
echo "alias logs-labeling='docker compose logs -f labeling'" >> ~/.bashrc
```

---

**Подробная инструкция:** См. `REMOTE_WINDOWS_SETUP.md`
