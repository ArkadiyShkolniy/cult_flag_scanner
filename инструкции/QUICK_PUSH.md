# Быстрая отправка кода на GitHub

## Проблема с SSH

SSH ключ не настроен. Используем HTTPS с Personal Access Token.

## Шаги:

1. **Создайте Personal Access Token на GitHub:**
   - Перейдите: https://github.com/settings/tokens
   - Нажмите "Generate new token" → "Generate new token (classic)"
   - Название: `cult_flag_scanner`
   - Срок действия: выбирайте по желанию
   - Права: отметьте `repo` (полный доступ к репозиториям)
   - Нажмите "Generate token"
   - **Скопируйте токен** (он показывается только один раз!)

2. **Отправьте код:**
```bash
cd /Users/arkadiyshkolniy/Documents/cult_trade/invest-python-main/complex_flag_scanner
git push -u origin main
```

3. **При запросе credentials:**
   - Username: `ArkadiyShkolniy`
   - Password: **вставьте ваш Personal Access Token** (не обычный пароль!)

4. macOS Keychain сохранит credentials, следующие push будут без запроса.

## Альтернатива: GitHub CLI

Если у вас установлен GitHub CLI (`gh`):

```bash
cd /Users/arkadiyshkolniy/Documents/cult_trade/invest-python-main/complex_flag_scanner
gh auth login
git push -u origin main
```

## Проверка

После успешной отправки откройте:
https://github.com/ArkadiyShkolniy/cult_flag_scanner

Все ваши файлы должны быть там!
