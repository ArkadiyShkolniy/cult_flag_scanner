# Установка пакета t-tech-investments

Если автоматическая установка не работает, выполните следующие шаги:

## Вариант 1: Установка в запущенном контейнере

```bash
# Войти в контейнер дашборда
sudo docker exec -it dashboard_prod bash

# Установить пакет
pip install t-tech-investments

# Выйти из контейнера
exit

# Перезапустить контейнер
sudo docker restart dashboard_prod
```

## Вариант 2: Установка на хосте и копирование

```bash
# Установить пакет на хосте
pip3 install t-tech-investments

# Найти путь к пакету
python3 -c "import t_tech; import os; print(os.path.dirname(t_tech.__file__))"

# Скопировать пакет в контейнер (замените путь на реальный)
sudo docker cp /usr/local/lib/python3.*/site-packages/t_tech dashboard_prod:/usr/local/lib/python3.11/site-packages/
```

## Вариант 3: Использование volume для установки

Если пакет установлен на хосте, можно смонтировать его через volume в docker-compose.yml

## Проверка установки

```bash
# Проверить наличие пакета в контейнере
sudo docker exec dashboard_prod python3 -c "import t_tech; print('OK')"
```
