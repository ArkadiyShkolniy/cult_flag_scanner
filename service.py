import time
import os
import sys
import io
import requests
import matplotlib
matplotlib.use('Agg')  # Неинтерактивный бэкенд для Docker
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
from dotenv import load_dotenv

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from scanners.combined_scanner import ComplexFlagScanner
from config import TIMEFRAMES
from telegram_utils import send_telegram_signal, create_flag_chart_image

load_dotenv()

SCAN_INTERVAL = 60 * 10

# Список фьючерсов для сканирования
# Формат: {ticker, class_code, name}
# Примечание: Тикеры фьючерсов меняются каждый месяц
# Формат тикера: БАЗОВЫЙ_АКТИВ + МЕСЯЦ + ГОД
# Месяцы: H(Mar), M(Jun), U(Sep), Z(Dec) и другие
# Для актуальных тикеров проверьте на бирже или используйте API для получения активных контрактов
# Если фьючерс не найден (истек или не существует), он будет пропущен
FUTURES_TO_SCAN = [
    # Индекс Мосбиржи (MX - базовый актив)
    {'ticker': 'MXH6', 'class_code': 'SPBFUT', 'name': 'Индекс Мосбиржи H6'},
    {'ticker': 'MXM6', 'class_code': 'SPBFUT', 'name': 'Индекс Мосбиржи M6'},
    {'ticker': 'MXU6', 'class_code': 'SPBFUT', 'name': 'Индекс Мосбиржи U6'},
    {'ticker': 'MXZ6', 'class_code': 'SPBFUT', 'name': 'Индекс Мосбиржи Z6'},
    # Индекс РТС (RI - базовый актив, не RTS!)
    {'ticker': 'RIH6', 'class_code': 'SPBFUT', 'name': 'Индекс РТС H6'},
    {'ticker': 'RIM6', 'class_code': 'SPBFUT', 'name': 'Индекс РТС M6'},
    {'ticker': 'RIU6', 'class_code': 'SPBFUT', 'name': 'Индекс РТС U6'},
    {'ticker': 'RIZ6', 'class_code': 'SPBFUT', 'name': 'Индекс РТС Z6'},
    # Золото (GLD - базовый актив)
    {'ticker': 'GLDH6', 'class_code': 'SPBFUT', 'name': 'Золото H6'},
    {'ticker': 'GLDM6', 'class_code': 'SPBFUT', 'name': 'Золото M6'},
    {'ticker': 'GLDU6', 'class_code': 'SPBFUT', 'name': 'Золото U6'},
    {'ticker': 'GLDZ6', 'class_code': 'SPBFUT', 'name': 'Золото Z6'},
    # Нефть Brent (BR - базовый актив)
    {'ticker': 'BRH6', 'class_code': 'SPBFUT', 'name': 'Нефть BR H6'},
    {'ticker': 'BRM6', 'class_code': 'SPBFUT', 'name': 'Нефть BR M6'},
    {'ticker': 'BRU6', 'class_code': 'SPBFUT', 'name': 'Нефть BR U6'},
    {'ticker': 'BRZ6', 'class_code': 'SPBFUT', 'name': 'Нефть BR Z6'},
    # Серебро (SIL - базовый актив)
    {'ticker': 'SILH6', 'class_code': 'SPBFUT', 'name': 'Серебро H6'},
    {'ticker': 'SILM6', 'class_code': 'SPBFUT', 'name': 'Серебро M6'},
    {'ticker': 'SILU6', 'class_code': 'SPBFUT', 'name': 'Серебро U6'},
    {'ticker': 'SILZ6', 'class_code': 'SPBFUT', 'name': 'Серебро Z6'},
]


def get_future_instrument(scanner, ticker, class_code):
    """Получает инструмент фьючерса по тикеру и class_code"""
    try:
        with Client(scanner.token) as client:
            instrument = client.instruments.get_instrument_by(
                id_type=InstrumentIdType.INSTRUMENT_ID_TYPE_TICKER,
                class_code=class_code,
                id=ticker
            ).instrument
            
            return {
                'ticker': instrument.ticker,
                'uid': instrument.uid,
                'name': instrument.name,
                'class_code': class_code
            }
    except Exception as e:
        return None


def run_complex_flag_scanner():
    token = os.environ.get("TINKOFF_INVEST_TOKEN")
    if not token:
        print("❌ [Complex Flag Scanner] Токен не найден.")
        return

    print(f"🚀 [Complex Flag Scanner] Запуск. Сканирование акций TQBR и фьючерсов на таймфреймах: {', '.join(TIMEFRAMES.keys())}...")
    
    # Проверяем настройки Telegram
    telegram_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    telegram_chat = os.environ.get("TELEGRAM_CHAT_ID")
    if telegram_token and telegram_chat:
        send_telegram_signal("🚀 <b>Complex Flag Scanner запущен</b>\nМониторинг паттернов 'Флаг' на всех таймфреймах (акции + фьючерсы).")
        print("   ✅ Telegram уведомления включены")
    else:
        print("   ⚠️ Telegram уведомления отключены (не настроены токены)")
    
    scanner = ComplexFlagScanner(token)
    # Кэш отправленных сигналов: ключ (ticker, timeframe) -> значение candle_time
    sent_signals_cache = {}

    while True:
        try:
            print(f"\n🌍 [Complex Flag] {datetime.now().strftime('%H:%M:%S')} Начало сканирования...")
            
            # Получаем акции
            shares = scanner.get_all_shares()
            print(f"   Найдено {len(shares)} акций.")
            
            # Получаем фьючерсы
            futures = []
            print(f"   Загрузка фьючерсов...")
            for future_config in FUTURES_TO_SCAN:
                future = get_future_instrument(scanner, future_config['ticker'], future_config['class_code'])
                if future:
                    future['display_name'] = future_config['name']
                    futures.append(future)
                    time.sleep(0.1)  # Небольшая пауза
            
            print(f"   Загружено {len(futures)} фьючерсов.")
            print(f"   Всего инструментов для сканирования: {len(shares) + len(futures)}")
            
            total_found_count = 0
            
            # Внешний цикл по таймфреймам
            for tf_name, tf_config in TIMEFRAMES.items():
                print(f"\n   ⏳ Сканирование таймфрейма: {tf_config['title']} ({tf_name})...")
                found_count_tf = 0
                
                # Сканируем акции
                for i, share in enumerate(shares):
                    time.sleep(0.2) # Пауза чтобы не забить API
                    
                    try:
                        # Загружаем свечи с учетом настроек таймфрейма
                        df = scanner.get_candles_by_uid(
                            share.uid, 
                            days_back=tf_config['days_back'],
                            interval=tf_config['interval']
                        )
                        
                        if not df.empty:
                            # Анализируем на оба типа паттернов
                            patterns = scanner.analyze(df, timeframe=tf_name)
                            
                            if patterns:
                                for pattern_info in patterns:
                                    current_candle_time = df.iloc[-1].name
                                    cache_key = (share.ticker, tf_name, pattern_info['pattern'])
                                    last_sent_time = sent_signals_cache.get(cache_key)
                                    
                                    if last_sent_time and last_sent_time == current_candle_time:
                                        continue
                                    
                                    sent_signals_cache[cache_key] = current_candle_time
                                    found_count_tf += 1
                                    total_found_count += 1
                                    
                                    t0 = pattern_info['t0']['price']
                                    t1 = pattern_info['t1']['price']
                                    t2 = pattern_info['t2']['price']
                                    t3 = pattern_info['t3']['price']
                                    t4 = pattern_info['t4']['price']
                                    pattern_type = "Бычий" if "FLAG" in pattern_info['pattern'] and "BEARISH" not in pattern_info['pattern'] else "Медвежий"
                                    
                                    print(f"   🚩 {share.ticker} [{tf_name}]: {pattern_type} флаг найден!")
                                    print(f"      T0: {t0:.2f}, T1: {t1:.2f}, T2: {t2:.2f}, T3: {t3:.2f}, T4: {t4:.2f}")
                                    
                                    # Формируем сообщение для Telegram
                                    direction_emoji = "🟢" if pattern_type == "Бычий" else "🔴"
                                    direction_text = "LONG" if pattern_type == "Бычий" else "SHORT"
                                    current_price = df.iloc[-1]['close']
                                    current_time = df.iloc[-1]['time']
                                    
                                    tg_message = (
                                        f"{direction_emoji} <b>ПАТТЕРН ФЛАГ: {share.ticker}</b>\n"
                                        f"<b>Тип:</b> Акция\n"
                                        f"<b>Направление:</b> {pattern_type} ({direction_text})\n"
                                        f"<b>Таймфрейм:</b> {tf_config['title']}\n"
                                        f"<b>Цена:</b> {current_price:.2f}\n"
                                        f"<b>Время:</b> {current_time}\n\n"
                                        f"<b>Точки паттерна:</b>\n"
                                        f"T0: {t0:.2f}\n"
                                        f"T1: {t1:.2f}\n"
                                        f"T2: {t2:.2f}\n"
                                        f"T3: {t3:.2f}\n"
                                        f"T4: {t4:.2f}\n\n"
                                        f"#{share.ticker} #{tf_name} #{direction_text}"
                                    )
                                    
                                    # Создаем график
                                    chart_image = create_flag_chart_image(df, pattern_info, share.ticker, tf_name)
                                    
                                    # Отправляем в Telegram
                                    if send_telegram_signal(tg_message, chart_image):
                                        print(f"      ✅ Отправлено в Telegram")
                                    else:
                                        print(f"      ⚠️ Не удалось отправить в Telegram")
                                
                    except Exception as e:
                        pass
                        
                    if (i + 1) % 50 == 0:
                        print(f"      Прогресс акций {tf_name}: {i + 1}/{len(shares)}...")
                
                # Сканируем фьючерсы
                print(f"   📊 Сканирование фьючерсов ({tf_name})...")
                for i, future in enumerate(futures):
                    time.sleep(0.2) # Пауза чтобы не забить API
                    
                    try:
                        # Загружаем свечи с учетом настроек таймфрейма
                        df = scanner.get_candles_by_uid(
                            future['uid'], 
                            days_back=tf_config['days_back'],
                            interval=tf_config['interval']
                        )
                        
                        if not df.empty:
                            # Анализируем на оба типа паттернов
                            patterns = scanner.analyze(df, timeframe=tf_name)
                            
                            if patterns:
                                for pattern_info in patterns:
                                    current_candle_time = df.iloc[-1].name
                                    cache_key = (future['ticker'], tf_name, pattern_info['pattern'])
                                    last_sent_time = sent_signals_cache.get(cache_key)
                                    
                                    if last_sent_time and last_sent_time == current_candle_time:
                                        continue
                                    
                                    sent_signals_cache[cache_key] = current_candle_time
                                    found_count_tf += 1
                                    total_found_count += 1
                                    
                                    t0 = pattern_info['t0']['price']
                                    t1 = pattern_info['t1']['price']
                                    t2 = pattern_info['t2']['price']
                                    t3 = pattern_info['t3']['price']
                                    t4 = pattern_info['t4']['price']
                                    pattern_type = "Бычий" if "FLAG" in pattern_info['pattern'] and "BEARISH" not in pattern_info['pattern'] else "Медвежий"
                                    
                                    print(f"   🚩 {future['ticker']} ({future['display_name']}) [{tf_name}]: {pattern_type} флаг найден!")
                                    print(f"      T0: {t0:.2f}, T1: {t1:.2f}, T2: {t2:.2f}, T3: {t3:.2f}, T4: {t4:.2f}")
                                    
                                    # Формируем сообщение для Telegram
                                    direction_emoji = "🟢" if pattern_type == "Бычий" else "🔴"
                                    direction_text = "LONG" if pattern_type == "Бычий" else "SHORT"
                                    current_price = df.iloc[-1]['close']
                                    current_time = df.iloc[-1]['time']
                                    
                                    tg_message = (
                                        f"{direction_emoji} <b>ПАТТЕРН ФЛАГ: {future['ticker']}</b>\n"
                                        f"<b>Тип:</b> Фьючерс ({future['display_name']})\n"
                                        f"<b>Направление:</b> {pattern_type} ({direction_text})\n"
                                        f"<b>Таймфрейм:</b> {tf_config['title']}\n"
                                        f"<b>Цена:</b> {current_price:.2f}\n"
                                        f"<b>Время:</b> {current_time}\n\n"
                                        f"<b>Точки паттерна:</b>\n"
                                        f"T0: {t0:.2f}\n"
                                        f"T1: {t1:.2f}\n"
                                        f"T2: {t2:.2f}\n"
                                        f"T3: {t3:.2f}\n"
                                        f"T4: {t4:.2f}\n\n"
                                        f"#{future['ticker']} #{tf_name} #{direction_text} #FUTURES"
                                    )
                                    
                                    # Создаем график
                                    chart_image = create_flag_chart_image(df, pattern_info, future['ticker'], tf_name)
                                    
                                    # Отправляем в Telegram
                                    if send_telegram_signal(tg_message, chart_image):
                                        print(f"      ✅ Отправлено в Telegram")
                                    else:
                                        print(f"      ⚠️ Не удалось отправить в Telegram")
                                
                    except Exception as e:
                        pass
                
                print(f"   ✅ Таймфрейм {tf_name} завершен. Найдено: {found_count_tf}")
                time.sleep(1) # Пауза между таймфреймами

            print(f"🏁 [Complex Flag] Полный цикл завершен. Всего найдено: {total_found_count}")

        except Exception as e:
            print(f"❌ Критическая ошибка: {e}")
            import traceback
            traceback.print_exc()

        print(f"💤 Сон {SCAN_INTERVAL/60} мин...")
        time.sleep(SCAN_INTERVAL)

if __name__ == "__main__":
    run_complex_flag_scanner()