# Решение проблемы аутентификации

## Проблема
"Invalid username or token. Password authentication is not supported for Git operations."

## Решение

### Вариант 1: GitHub CLI (самый простой способ)

Если у вас установлен GitHub CLI:

```bash
cd /Users/arkadiyshkolniy/Documents/cult_trade/invest-python-main/complex_flag_scanner

# Авторизоваться через браузер
gh auth login

# Выберите:
# - GitHub.com
# - HTTPS
# - Authenticate Git with your GitHub credentials? Yes
# - Login with a web browser

# После авторизации:
git push -u origin main
```

### Вариант 2: Правильный Personal Access Token

1. **Убедитесь, что токен правильный:**
   - Токен должен начинаться с `ghp_` (fine-grained) или быть классическим токеном
   - Токен должен иметь права `repo`

2. **Используйте токен в URL (временно):**

```bash
cd /Users/arkadiyshkolniy/Documents/cult_trade/invest-python-main/complex_flag_scanner

# Замените YOUR_TOKEN на ваш реальный токен
git remote set-url origin https://YOUR_TOKEN@github.com/ArkadiyShkolniy/cult_flag_scanner.git

git push -u origin main
```

⚠️ **Внимание:** Токен будет виден в git config, лучше потом удалить его:
```bash
git remote set-url origin https://github.com/ArkadiyShkolniy/cult_flag_scanner.git
```

3. **Или используйте токен при push (более безопасно):**

```bash
cd /Users/arkadiyshkolniy/Documents/cult_trade/invest-python-main/complex_flag_scanner

# При запросе credentials:
git push -u origin main
# Username: ArkadiyShkolniy
# Password: ghp_ваш_токен_здесь
```

### Вариант 3: Fine-grained Personal Access Token

Если классический токен не работает, создайте Fine-grained token:

1. Перейдите: https://github.com/settings/tokens?type=beta
2. Generate new token → Generate new token (fine-grained)
3. Repository access: Only select repositories → выберите `cult_flag_scanner`
4. Permissions → Repository permissions → Contents: Read and write
5. Generate token
6. Используйте его как в Варианте 2

## Проверка токена

Убедитесь, что токен:
- ✅ Начинается с `ghp_` (fine-grained) или это классический токен
- ✅ Имеет права `repo` (классический) или `Contents: Read and write` (fine-grained)
- ✅ Не истек
- ✅ Правильно скопирован (без лишних пробелов)

## После успешного push

Проверьте репозиторий:
https://github.com/ArkadiyShkolniy/cult_flag_scanner
