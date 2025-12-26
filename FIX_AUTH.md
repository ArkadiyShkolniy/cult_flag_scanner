# Исправление проблемы аутентификации

## Проблема
Ошибка: "Invalid username or token. Password authentication is not supported"

## Решение: Используйте токен в URL

### Шаг 1: Создайте токен (если еще нет)

1. Перейдите: https://github.com/settings/tokens
2. "Generate new token" → "Generate new token (classic)"
3. Название: `cult_flag_scanner`
4. Права: отметьте `repo`
5. Generate token
6. **Скопируйте токен полностью** (начинается с `ghp_`)

### Шаг 2: Вставьте токен в URL

```bash
cd /Users/arkadiyshkolniy/Documents/cult_trade/invest-python-main/complex_flag_scanner

# ВАЖНО: Замените ghp_xxxxxxxxxxxxxxxxxxxx на ваш РЕАЛЬНЫЙ токен
git remote set-url origin https://ghp_xxxxxxxxxxxxxxxxxxxx@github.com/ArkadiyShkolniy/cult_flag_scanner.git

# Проверьте что URL правильный (токен должен быть виден)
git remote -v

# Отправьте код
git push -u origin main
```

### Шаг 3: После успешной отправки (безопасность)

Уберите токен из URL:
```bash
git remote set-url origin https://github.com/ArkadiyShkolniy/cult_flag_scanner.git
```

## Пример правильной команды

Если ваш токен: `ghp_abc123xyz789`, команда будет:

```bash
git remote set-url origin https://ghp_abc123xyz789@github.com/ArkadiyShkolniy/cult_flag_scanner.git
git push -u origin main
```

## Проверка

Токен должен:
- ✅ Начинаться с `ghp_`
- ✅ Быть скопирован полностью (40+ символов)
- ✅ Не содержать пробелов
- ✅ Иметь права `repo`

## Альтернатива: GitHub CLI

Если хотите избежать проблем с токенами:

```bash
# Установите GitHub CLI (если еще нет)
brew install gh

# Авторизуйтесь
gh auth login

# Отправьте код
git push -u origin main
```
