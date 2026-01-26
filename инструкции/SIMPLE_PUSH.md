# Простая инструкция по отправке кода

## Шаг 1: Создайте или проверьте токен

1. Перейдите: https://github.com/settings/tokens
2. Если токена нет → "Generate new token (classic)"
   - Название: `cult_flag_scanner`
   - Права: отметьте **только** `repo` (Full control of private repositories)
   - Generate token
   - **Скопируйте токен** (начинается с `ghp_`)

## Шаг 2: Используйте токен

Выберите ОДИН из способов:

### Способ A: Вставить токен в URL (проще всего)

```bash
cd /Users/arkadiyshkolniy/Documents/cult_trade/invest-python-main/complex_flag_scanner

# Замените YOUR_TOKEN на ваш реальный токен (который начинается с ghp_)
git remote set-url origin https://YOUR_TOKEN@github.com/ArkadiyShkolniy/cult_flag_scanner.git

git push -u origin main
```

**После успешной отправки удалите токен из URL:**
```bash
git remote set-url origin https://github.com/ArkadiyShkolniy/cult_flag_scanner.git
```

### Способ B: Ввести при запросе (безопаснее)

```bash
cd /Users/arkadiyshkolniy/Documents/cult_trade/invest-python-main/complex_flag_scanner

git push -u origin main
```

При запросе:
- **Username**: `ArkadiyShkolniy`
- **Password**: вставьте ваш токен (не пароль GitHub!)

## Важно!

- Токен должен начинаться с `ghp_`
- Не используйте пароль от GitHub - только токен!
- Убедитесь, что скопировали токен полностью, без пробелов

## Проверка

После успешной отправки:
https://github.com/ArkadiyShkolniy/cult_flag_scanner
