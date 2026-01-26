# Настройка GitHub репозитория

## Создание удаленного репозитория на GitHub

1. Перейдите на [GitHub](https://github.com) и войдите в свой аккаунт

2. Нажмите кнопку "New" (или "+" в правом верхнем углу) → "New repository"

3. Заполните информацию:
   - **Repository name**: `complex-flag-scanner` (или другое название)
   - **Description**: "Scanner for complex flag patterns (0-1-2-3-4) on financial markets"
   - **Visibility**: Public или Private (на ваше усмотрение)
   - **НЕ** инициализируйте репозиторий с README, .gitignore или лицензией (у нас уже есть файлы)

4. Нажмите "Create repository"

## Подключение локального репозитория к GitHub

После создания репозитория на GitHub, выполните следующие команды:

```bash
cd /Users/arkadiyshkolniy/Documents/cult_trade/invest-python-main/complex_flag_scanner

# Добавьте удаленный репозиторий (замените YOUR_USERNAME на ваш GitHub username)
git remote add origin https://github.com/YOUR_USERNAME/complex-flag-scanner.git

# Переименуйте ветку в main (если нужно)
git branch -M main

# Отправьте код на GitHub
git push -u origin main
```

## Альтернативный вариант: через SSH

Если у вас настроен SSH ключ для GitHub:

```bash
git remote add origin git@github.com:YOUR_USERNAME/complex-flag-scanner.git
git branch -M main
git push -u origin main
```

## Проверка

После выполнения команд, обновите страницу репозитория на GitHub - вы должны увидеть все ваши файлы.

## Дополнительные команды

### Если нужно изменить URL удаленного репозитория:
```bash
git remote set-url origin NEW_URL
```

### Просмотр текущих удаленных репозиториев:
```bash
git remote -v
```

### Следующие коммиты:
```bash
git add .
git commit -m "Your commit message"
git push
```
