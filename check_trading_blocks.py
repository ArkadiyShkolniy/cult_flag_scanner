#!/usr/bin/env python3
"""
Скрипт для проверки всех возможных блокировок открытия сделок
"""
import json
from pathlib import Path
import os

print("=" * 60)
print("ПРОВЕРКА БЛОКИРОВОК ОТКРЫТИЯ СДЕЛОК")
print("=" * 60)

# 1. Проверка переменных окружения
print("\n1. ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ:")
print(f"   BOT_ENV: {os.environ.get('BOT_ENV', 'НЕ УСТАНОВЛЕНА')}")
print(f"   DRY_RUN: {os.environ.get('DRY_RUN', 'НЕ УСТАНОВЛЕНА')}")
print(f"   DEBUG_MODE: {os.environ.get('DEBUG_MODE', 'НЕ УСТАНОВЛЕНА')}")
print(f"   USE_AI_FILTER: {os.environ.get('USE_AI_FILTER', 'НЕ УСТАНОВЛЕНА')}")
print(f"   DATA_DIR: {os.environ.get('DATA_DIR', 'НЕ УСТАНОВЛЕНА')}")

# 2. Проверка конфигурации торговли
print("\n2. КОНФИГУРАЦИЯ ТОРГОВЛИ:")
config_files = [
    "trading_bot/trading_config.json",
    "trading_bot/data_prod/trading_config.json"
]

for config_file in config_files:
    path = Path(config_file)
    if path.exists():
        with open(path, 'r') as f:
            config = json.load(f)
        print(f"   {config_file}:")
        print(f"      fixed_lot_size: {config.get('fixed_lot_size', 'НЕ УСТАНОВЛЕН')}")
    else:
        print(f"   {config_file}: НЕ НАЙДЕН")

# 3. Проверка AI модели
print("\n3. AI МОДЕЛЬ:")
model_path = Path("neural_network/models/trading_model_rf.pkl")
if model_path.exists():
    print(f"   ✅ Модель найдена: {model_path}")
    size = model_path.stat().st_size / 1024
    print(f"      Размер: {size:.1f} KB")
else:
    print(f"   ❌ Модель НЕ найдена: {model_path}")

# 4. Проверка активных позиций
print("\n4. АКТИВНЫЕ ПОЗИЦИИ:")
trades_files = [
    "trading_bot/trades_active.json",
    "trading_bot/data_prod/trades_active.json"
]

for trades_file in trades_files:
    path = Path(trades_file)
    if path.exists():
        with open(path, 'r') as f:
            trades = json.load(f)
        count = len(trades) if isinstance(trades, dict) else 0
        print(f"   {trades_file}: {count} активных позиций")
        if count > 0:
            for ticker, trade in (trades.items() if isinstance(trades, dict) else []):
                print(f"      - {ticker}: {trade.get('direction', '?')} @ {trade.get('entry_price', '?')}")
    else:
        print(f"   {trades_file}: НЕ НАЙДЕН (нет активных позиций)")

# 5. Проверка последних логов
print("\n5. ПОСЛЕДНИЕ СООБЩЕНИЯ В ЛОГАХ:")
log_files = [
    "logs/prod_bot.log",
    "logs/debug_bot.log"
]

for log_file in log_files:
    path = Path(log_file)
    if path.exists():
        print(f"\n   {log_file}:")
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
            # Ищем последние важные сообщения
            important_lines = [
                line for line in lines[-100:]
                if any(keyword in line for keyword in [
                    'СИГНАЛ', 'флаг найден', 'T4', 'Отмена', '0 лотов', 
                    'AI FILTER', 'TradeManager', 'Настройки', 'Условия входа'
                ])
            ]
            for line in important_lines[-10:]:
                print(f"      {line.strip()}")

print("\n" + "=" * 60)
print("ПРОВЕРКА ЗАВЕРШЕНА")
print("=" * 60)
