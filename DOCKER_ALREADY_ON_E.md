# ✅ Docker уже настроен на диск E!

## Текущая ситуация

**Отлично!** Docker уже настроен для хранения данных на диске E:

- ✅ **Симлинк создан:** `/var/lib/docker` → `/mnt/e/docker`
- ✅ **Конфигурация:** `/etc/docker/daemon.json` настроен с `data-root: /mnt/e/docker`
- ✅ **Данные на диске E:** `/mnt/e/docker` (840M)
- ⚠️ **Проблема:** Docker daemon не запущен

## Как запустить Docker

### Вариант 1: Docker Desktop (если установлен в Windows)

1. Откройте Docker Desktop из меню Пуск Windows
2. Дождитесь полного запуска (иконка в трее станет зеленой)
3. Проверьте в WSL:
   ```bash
   docker info
   ```

### Вариант 2: Запуск через systemd (если доступен)

```bash
# Попробуйте запустить (может потребоваться права root)
sudo systemctl start docker
# или
sudo service docker start

# Проверка
docker info
```

### Вариант 3: Запуск вручную (если systemd недоступен)

```bash
# Запуск dockerd вручную
sudo dockerd --data-root=/mnt/e/docker &
```

## Проверка после запуска

```bash
# Проверка расположения
docker info | grep "Docker Root Dir"
# Должно показать: /mnt/e/docker

# Проверка размера
du -sh /mnt/e/docker

# Тестовый запуск
docker run hello-world
```

## Использование дисков

- **Диск E:** 269G / 932G (29% заполнено), свободно: 664G
- **Диск C:** 395G / 466G (85% заполнено), свободно: 71G
- **Docker данные:** 840M на диске E ✅

## Запуск проекта

После запуска Docker daemon можно запустить все компоненты:

```bash
cd /home/ark/projects/trading_bot
./docker-start.sh
```

## Полезные команды

```bash
# Проверка статуса Docker
./check-docker-location.sh

# Просмотр логов Docker
sudo journalctl -u docker -f
# или
sudo tail -f /var/log/docker.log
```

## Примечание

Если Docker Desktop установлен в Windows, он автоматически использует настройки из `/etc/docker/daemon.json` при запуске через WSL2.
