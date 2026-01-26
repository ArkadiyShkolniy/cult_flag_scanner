import time
import os
import sys
import io
import requests
import pandas as pd
import logging
import matplotlib
matplotlib.use('Agg')  # Неинтерактивный бэкенд для Docker
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from t_tech.invest import Client, InstrumentIdType

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from scanners.combined_scanner import ComplexFlagScanner
from trading_bot.trade_manager import TradeManager
from trading_bot.trade_strategy import TradeStrategy
# from trading_bot.pattern_watcher import PatternWatcher  # Отключено - не используется
from config import TIMEFRAMES
from telegram_utils import send_telegram_signal, create_flag_chart_image

load_dotenv()

# Настройка логирования
def setup_logging(mode='debug'):
    """Настраивает логирование в файл и консоль"""
    log_dir = Path(__file__).parent / "logs"
    log_dir.mkdir(exist_ok=True)
    
    log_file = log_dir / f"{mode}_bot.log"
    
    # Формат логов: время, уровень, сообщение
    log_format = '%(asctime)s [%(levelname)s] %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'
    
    # Настройка root logger
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        datefmt=date_format,
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)  # Также выводим в консоль для Docker
        ]
    )
    
    return logging.getLogger(__name__)

SCAN_INTERVAL = 60 * 10

# Список фьючерсов для сканирования
# Формат: {ticker, class_code, name}
# Примечание: Тикеры фьючерсов меняются каждый месяц
# Формат тикера: БАЗОВЫЙ_АКТИВ + МЕСЯЦ + ГОД
# Месяцы: H(Mar), M(Jun), U(Sep), Z(Dec) и другие
# Если фьючерс не найден (истек или не существует), он будет пропущен
# Обновлено: январь 2026 - используем ближайшие актуальные фьючерсы
FUTURES_TO_SCAN = [
    # Индекс Мосбиржи (MX - базовый актив)
    {'ticker': 'MXH6', 'class_code': 'SPBFUT', 'name': 'Индекс Мосбиржи H6'},  # Март 2026
    {'ticker': 'MXM6', 'class_code': 'SPBFUT', 'name': 'Индекс Мосбиржи M6'},  # Июнь 2026
    # Индекс РТС (RI - базовый актив)
    {'ticker': 'RIH6', 'class_code': 'SPBFUT', 'name': 'Индекс РТС H6'},  # Март 2026
    {'ticker': 'RIM6', 'class_code': 'SPBFUT', 'name': 'Индекс РТС M6'},  # Июнь 2026
    # Золото (GD - базовый актив)
    {'ticker': 'GDH6', 'class_code': 'SPBFUT', 'name': 'Золото H6'},  # Март 2026
    {'ticker': 'GDM6', 'class_code': 'SPBFUT', 'name': 'Золото M6'},  # Июнь 2026
    # Серебро (Si - базовый актив)
    {'ticker': 'SIH6', 'class_code': 'SPBFUT', 'name': 'Серебро H6'},  # Март 2026
    {'ticker': 'SIM6', 'class_code': 'SPBFUT', 'name': 'Серебро M6'},  # Июнь 2026
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
        print(f"      ⚠️ Не удалось загрузить {ticker}: {str(e)[:100]}")
        return None


def run_complex_flag_scanner():
    import argparse
    parser = argparse.ArgumentParser(description='Complex Flag Scanner Service')
    parser.add_argument('--mode', type=str, choices=['debug', 'prod'], default='debug', 
                        help='Режим работы: debug (поиск на истории, без уведомлений) или prod (поиск свежих паттернов + Telegram)')
    parser.add_argument('--entry-mode', type=str, choices=['ema_squeeze'], default='ema_squeeze',
                        help='Режим входа: ema_squeeze')
    parser.add_argument('--enable-trading', action='store_true',
                        help='Включить автоматическое открытие позиций')
    args = parser.parse_args()
    
    mode = args.mode
    is_prod = mode == 'prod'
    scan_type = 'latest' if is_prod else 'all'
    entry_mode = args.entry_mode
    enable_trading = args.enable_trading
    
    # Настройка логирования
    logger = setup_logging(mode)
    
    token = os.environ.get("TINKOFF_INVEST_TOKEN")
    if not token:
        logger.error("❌ [Complex Flag Scanner] Токен не найден.")
        return

    logger.info(f"🚀 [Complex Flag Scanner] Запуск в режиме: {mode.upper()}")
    logger.info(f"   Тип сканирования: {scan_type}")
    logger.info(f"   Режим входа: {entry_mode}")
    logger.info(f"   Торговля: {'ВКЛЮЧЕНА' if enable_trading else 'ОТКЛЮЧЕНА'}")
    logger.info(f"   Сканирование акций TQBR и фьючерсов на таймфреймах: {', '.join(TIMEFRAMES.keys())}...")
    
    # Инициализация PatternWatcher для отслеживания паттернов без T4 - ОТКЛЮЧЕНО
    # pattern_watcher = PatternWatcher()
    
    # Инициализация компонентов для торговли (если включена)
    trade_manager = None
    strategy = None
    if enable_trading:
        # Определяем папку данных в зависимости от режима
        data_dir = "trading_bot/data_prod" if is_prod else "trading_bot"
        
        # В PROD режиме dry_run=False (реальная торговля), в DEBUG - True
        # Но пользователь может переопределить через аргумент (хотя лучше полагаться на mode)
        dry_run = not is_prod 
        
        # В PROD режиме debug_mode=False (реальный расчет объема), в DEBUG - True (фиксированный лот)
        debug_mode = not is_prod
        
        # Проверяем переменные окружения
        use_ai_filter = os.environ.get("USE_AI_FILTER", "True").lower() == "true"
        
        logger.info(f"   ⚙️ Настройки TradeManager:")
        logger.info(f"      dry_run={dry_run}, debug_mode={debug_mode}, use_ai_filter={use_ai_filter}")
        
        trade_manager = TradeManager(
            token, 
            dry_run=dry_run, 
            debug_mode=debug_mode,
            use_ai_filter=use_ai_filter,
            data_dir=data_dir, 
            logger=logger
        )
        strategy = TradeStrategy()
        logger.info(f"   ✅ TradeManager инициализирован (Data Dir: {data_dir}, Dry Run: {dry_run})")
        logger.info("   ✅ TradeStrategy инициализирован")
    
    # Настройка Telegram
    telegram_enabled = False
    if is_prod:
        telegram_token = os.environ.get("TELEGRAM_BOT_TOKEN")
        telegram_chat = os.environ.get("TELEGRAM_CHAT_ID")
        if telegram_token and telegram_chat:
            telegram_enabled = True
            try:
                send_telegram_signal("🚀 <b>Complex Flag Scanner запущен (PROD)</b>\nМониторинг свежих паттернов T4.")
                logger.info("   ✅ Telegram уведомления включены")
            except Exception as e:
                logger.warning(f"   ⚠️ Ошибка отправки приветственного сообщения в Telegram: {e}")
        else:
            logger.warning("   ⚠️ Telegram уведомления отключены (не настроены токены в .env)")
    else:
        logger.warning("   ⚠️ Telegram уведомления отключены (режим DEBUG)")
    
    scanner = ComplexFlagScanner(token)
    # Кэш отправленных сигналов: ключ (ticker, timeframe, pattern_type) -> значение candle_time
    sent_signals_cache = {}

    while True:
        try:
            # Московское время (UTC+3)
            moscow_tz = timezone(timedelta(hours=3))
            moscow_time = datetime.now(timezone.utc).astimezone(moscow_tz)
            logger.info(f"\n🌍 [Complex Flag] {moscow_time.strftime('%H:%M:%S')} Начало сканирования ({mode})...")
            
            # Получаем акции
            shares = scanner.get_all_shares()
            logger.info(f"   Найдено {len(shares)} акций.")
            
            # Фьючерсы временно отключены
            futures = []
            # logger.info(f"   Загрузка фьючерсов...")
            # for future_config in FUTURES_TO_SCAN:
            #     future = get_future_instrument(scanner, future_config['ticker'], future_config['class_code'])
            #     if future:
            #         future['display_name'] = future_config['name']
            #         futures.append(future)
            #         time.sleep(0.1)  # Небольшая пауза
            
            # logger.info(f"   Загружено {len(futures)} фьючерсов.")
            logger.info(f"   Всего инструментов для сканирования: {len(shares)} (фьючерсы отключены)")
            
            total_found_count = 0
            
            # Внешний цикл по таймфреймам
            for tf_name, tf_config in TIMEFRAMES.items():
                logger.info(f"\n   ⏳ Сканирование таймфрейма: {tf_config['title']} ({tf_name})...")
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
                            # Добавляем индикаторы (нужны для проверки условий входа и расчета SL/TP)
                            df = scanner.bullish_scanner._add_indicators(df)
                            
                            # ПРОВЕРКА ОТСЛЕЖИВАЕМЫХ ПАТТЕРНОВ (без T4) - ОТКЛЮЧЕНО ДЛЯ ДИАГНОСТИКИ
                            # ОТКЛЮЧЕНО: Проверяем, сформировалась ли T4 для паттернов, которые мы отслеживаем
                            # if enable_trading and trade_manager and strategy:
                            #     current_idx = len(df) - 1
                            #     watched_t4_pattern = pattern_watcher.check_t4_formation(
                            #         share.ticker, tf_name, df, current_idx, tolerance_percent=0.01
                            #     )
                            #     
                            #     if watched_t4_pattern:
                            #         # T4 сформировалась для отслеживаемого паттерна!
                            #         logger.info(f"   🎯 {share.ticker} [{tf_name}]: T4 сформировалась для отслеживаемого паттерна!")
                            #         logger.info(f"      T0: {watched_t4_pattern['t0']['price']:.2f}, T1: {watched_t4_pattern['t1']['price']:.2f}, T2: {watched_t4_pattern['t2']['price']:.2f}, T3: {watched_t4_pattern['t3']['price']:.2f}, T4: {watched_t4_pattern['t4']['price']:.2f}")
                            #         
                            #         # Проверяем условия входа
                            #         try:
                            #             pattern = {
                            #                 'pattern': watched_t4_pattern.get('pattern', 'FLAG'),
                            #                 't0': {'idx': watched_t4_pattern['t0']['idx'], 'price': watched_t4_pattern['t0']['price']},
                            #                 't1': {'idx': watched_t4_pattern['t1']['idx'], 'price': watched_t4_pattern['t1']['price']},
                            #                 't2': {'idx': watched_t4_pattern['t2']['idx'], 'price': watched_t4_pattern['t2']['price']},
                            #                 't3': {'idx': watched_t4_pattern['t3']['idx'], 'price': watched_t4_pattern['t3']['price']},
                            #                 't4': {'idx': watched_t4_pattern['t4']['idx'], 'price': watched_t4_pattern['t4']['price']},
                            #             }
                            #             
                            #             current_price = df.iloc[-1]['close']
                            #             
                            #             result = strategy.check_entry_signal(
                            #                 df=df,
                            #                 pattern=pattern,
                            #                 entry_mode='ema_squeeze',  # Parallel Lines отключено, используем только EMA Squeeze
                            #                 current_price=current_price
                            #             )
                            #             
                            #             if len(result) == 3:
                            #                 signal, desc, active_mode = result
                            #             else:
                            #                 signal, desc = result
                            #                 active_mode = 'ema_squeeze'  # Parallel Lines отключено
                            #             
                            #             if signal:
                            #                 logger.info(f"      ✅ СИГНАЛ НА ВХОД (отслеживаемый паттерн)!")
                            #                 logger.info(f"      📝 {desc}")
                            #                 
                            #                 # Если active_mode не определен, используем ema_squeeze (так как Parallel Lines отключено)
                            #                 final_entry_mode = active_mode if active_mode else 'ema_squeeze'
                            #                 exit_levels = strategy.calculate_exit_levels(
                            #                     df, pattern, current_price, entry_mode=final_entry_mode
                            #                 )
                            #                 
                            #                 stop_loss = exit_levels['stop_loss']
                            #                 take_profit = exit_levels['take_profit']
                            #                 
                            #                 pattern_type = "Бычий" if "BEARISH" not in pattern.get('pattern', 'FLAG') else "Медвежий"
                            #                 direction = 'LONG' if pattern_type == "Бычий" else 'SHORT'
                            #                 strategy_desc = f"{final_entry_mode} Entry ({tf_name})"
                            #                 
                            #                 trade_manager.open_position(
                            #                     ticker=share.ticker,
                            #                     uid=share.uid,
                            #                     direction=direction,
                            #                     price=current_price,
                            #                     stop_loss=stop_loss,
                            #                     take_profit=take_profit,
                            #                     strategy_desc=strategy_desc,
                            #                     df_context=df,
                            #                     pattern_info=watched_t4_pattern,
                            #                     entry_mode=active_mode if active_mode else 'ema_squeeze'
                            #             )
                            #         else:
                            #             logger.info(f"      ❌ Условия входа не выполнены: {desc}")
                            #     except Exception as e:
                            #         logger.error(f"      ❌ Ошибка проверки условий входа для отслеживаемого паттерна: {e}")
                            #         import traceback
                            #         logger.error(traceback.format_exc())
                            
                            # Анализируем на оба типа паттернов
                            patterns = scanner.analyze(df, timeframe=tf_name, scan_type=scan_type)
                            
                            if patterns:
                                for pattern_info in patterns:
                                    current_candle_time = df.iloc[-1].name
                                    pattern_type = "Бычий" if "FLAG" in pattern_info['pattern'] and "BEARISH" not in pattern_info['pattern'] else "Медвежий"
                                    
                                    # Кэш по тикеру, таймфрейму и типу паттерна + времени T4 (чтобы не слать дубли одного паттерна)
                                    # Для 'all' (debug) можно показывать все, но чтобы не спамить в консоль одно и то же при повторном скане, тоже кэшируем
                                    # Используем время T4 как уникальный идентификатор конкретного паттерна
                                    t4_time = pattern_info['t4']['time']
                                    cache_key = (share.ticker, tf_name, pattern_type, t4_time)
                                    
                                    if cache_key in sent_signals_cache:
                                        continue
                                    
                                    sent_signals_cache[cache_key] = True
                                    found_count_tf += 1
                                    total_found_count += 1
                                    
                                    t0 = pattern_info['t0']['price']
                                    t1 = pattern_info['t1']['price']
                                    t2 = pattern_info['t2']['price']
                                    t3 = pattern_info['t3']['price']
                                    t4 = pattern_info['t4']['price']
                                    
                                    logger.info(f"   🚩 {share.ticker} [{tf_name}]: {pattern_type} флаг найден!")
                                    logger.info(f"      T0: {t0:.2f}, T1: {t1:.2f}, T2: {t2:.2f}, T3: {t3:.2f}, T4: {t4:.2f}")
                                    
                                    # Проверяем возраст T4
                                    current_idx = len(df) - 1
                                    t4_idx = pattern_info['t4']['idx']
                                    t4_age = current_idx - t4_idx
                                    
                                    # Проверяем время T4 (если есть)
                                    t4_time = None
                                    if 'time' in pattern_info.get('t4', {}):
                                        try:
                                            # datetime already imported globally
                                            t4_time = pd.to_datetime(pattern_info['t4']['time'])
                                            if t4_time.tzinfo is not None:
                                                t4_time = t4_time.replace(tzinfo=None)
                                        except:
                                            pass
                                    
                                    logger.info(f"      📍 Проверка T4: current_idx={current_idx}, t4_idx={t4_idx}, возраст={t4_age} свечей")
                                    if t4_time:
                                        logger.info(f"      📅 Время T4: {t4_time}")
                                    
                                    # ВАЖНО: В prod режиме входим только в свежие паттерны
                                    # Используем динамическую логику, аналогичную TradeStrategy
                                    if is_prod:
                                        # Вычисляем длину паттерна
                                        pattern_len = 20  # Default
                                        try:
                                            t0_idx = int(pattern_info['t0']['idx'])
                                            pattern_len = max(5, t4_idx - t0_idx)
                                        except:
                                            pass
                                        
                                        # Допустимая задержка: 20% от длины, но от 2 до 12 свечей
                                        # Мы даем небольшой запас (+2 свечи) относительно стратегии, 
                                        # чтобы не отфильтровать пограничные случаи здесь
                                        max_t4_age = min(14, max(4, int(pattern_len * 0.2) + 2))
                                        
                                        if t4_age > max_t4_age:
                                            logger.warning(f"      ⏭️ Паттерн пропущен: T4 слишком старый (возраст {t4_age} свечей > {max_t4_age}, длина {pattern_len})")
                                            continue
                                    
                                    # Дополнительная проверка по времени: T4 должен быть не старше 3 дней
                                    if is_prod and t4_time:
                                        # moscow_tz defined above at loop start
                                        current_time = datetime.now(timezone.utc).astimezone(moscow_tz).replace(tzinfo=None)
                                        time_diff = current_time - t4_time
                                        if time_diff > timedelta(days=3):
                                            logger.warning(f"      ⏭️ Паттерн пропущен: T4 слишком старый по времени (T4: {t4_time}, разница {time_diff.days} дней > 3 дней)")
                                            continue
                                    elif is_prod:
                                        # Если нет времени T4, но мы в prod режиме - пропускаем паттерн (безопаснее)
                                        logger.warning(f"      ⏭️ Паттерн пропущен: нет времени T4 для проверки свежести (prod режим)")
                                        continue
                                    
                                    # Проверка условий входа и открытие позиции (если торговля включена)
                                    logger.info(f"      ✅ Проверяем условия входа (T4 свежий: возраст {t4_age} свечей)...")
                                    
                                    if not enable_trading:
                                        logger.warning(f"      ⚠️ Торговля отключена (enable_trading=False)")
                                        continue
                                    
                                    if not trade_manager:
                                        logger.warning(f"      ⚠️ TradeManager не инициализирован")
                                        continue
                                    
                                    if not strategy:
                                        logger.warning(f"      ⚠️ Strategy не инициализирована")
                                        continue
                                    
                                    if enable_trading and trade_manager and strategy:
                                        try:
                                            # Подготавливаем паттерн для проверки
                                            pattern = {
                                                'pattern': pattern_info['pattern'],
                                                't0': {'idx': pattern_info['t0']['idx'], 'price': pattern_info['t0']['price']},
                                                't1': {'idx': pattern_info['t1']['idx'], 'price': pattern_info['t1']['price']},
                                                't2': {'idx': pattern_info['t2']['idx'], 'price': pattern_info['t2']['price']},
                                                't3': {'idx': pattern_info['t3']['idx'], 'price': pattern_info['t3']['price']},
                                                't4': {'idx': pattern_info['t4']['idx'], 'price': pattern_info['t4']['price']},
                                            }
                                            
                                            # Получаем текущую цену
                                            current_price = df.iloc[-1]['close']
                                            
                                            # Проверяем условия входа (EMA Squeeze)
                                            result = strategy.check_entry_signal(
                                                    df=df,
                                                    pattern=pattern,
                                                    entry_mode='ema_squeeze',  # Parallel Lines отключено, используем только EMA Squeeze
                                                    current_price=current_price
                                                )
                                            
                                            # Результат может быть (bool, str) или (bool, str, str)
                                            if len(result) == 3:
                                                signal, desc, active_mode = result
                                            else:
                                                signal, desc = result
                                                active_mode = 'ema_squeeze'  # Parallel Lines отключено, используем только EMA Squeeze
                                            
                                            if signal:
                                                logger.info(f"      ✅ СИГНАЛ НА ВХОД!")
                                                logger.info(f"      📝 {desc}")
                                                
                                                # Рассчитываем уровни выхода (используем режим сработавшего условия)
                                                # Если active_mode не определен, используем ema_squeeze (так как Parallel Lines отключено)
                                                final_entry_mode = active_mode if active_mode else 'ema_squeeze'
                                                exit_levels = strategy.calculate_exit_levels(
                                                    df, pattern, current_price, entry_mode=final_entry_mode
                                                )
                                                
                                                stop_loss = exit_levels['stop_loss']
                                                take_profit = exit_levels['take_profit']
                                                
                                                # Определяем направление
                                                direction = 'LONG' if pattern_type == "Бычий" else 'SHORT'
                                                
                                                # Формируем описание стратегии (используем режим сработавшего условия)
                                                strategy_desc = f"{final_entry_mode} Entry ({tf_name})"
                                                
                                                logger.info(f"      📊 Параметры сделки: Цена={current_price:.2f}, SL={stop_loss:.2f}, TP={take_profit:.2f}, Направление={direction}")
                                                
                                                # Открываем позицию
                                                trade_manager.open_position(
                                                    ticker=share.ticker,
                                                    uid=share.uid,
                                                    direction=direction,
                                                    price=current_price,
                                                    stop_loss=stop_loss,
                                                    take_profit=take_profit,
                                                    strategy_desc=strategy_desc,
                                                    df_context=df,
                                                    pattern_info=pattern_info,
                                                    entry_mode=final_entry_mode
                                                )
                                            else:
                                                logger.info(f"      ❌ Условия входа не выполнены: {desc}")
                                        except Exception as e:
                                            logger.error(f"      ⚠️ Ошибка проверки условий входа: {e}")
                                            import traceback
                                            logger.error(traceback.format_exc())
                                    
                                    if telegram_enabled:
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
                                        
                                        try:
                                            chart_image = create_flag_chart_image(df, pattern_info, share.ticker, tf_name)
                                            if send_telegram_signal(tg_message, chart_image):
                                                logger.info(f"      ✅ Отправлено в Telegram")
                                            else:
                                                logger.warning(f"      ⚠️ Не удалось отправить в Telegram")
                                        except Exception as img_err:
                                            logger.warning(f"      ⚠️ Ошибка генерации графика: {img_err}")
                                            send_telegram_signal(tg_message) # Пробуем без картинки
                                
                    except Exception as e:
                        # print(f"Error analyzing {share.ticker}: {e}")
                        pass
                        
                    if (i + 1) % 50 == 0:
                        logger.info(f"      Прогресс акций {tf_name}: {i + 1}/{len(shares)}...")
                
                # Сканируем фьючерсы (временно отключено - сканируем только акции)
                # logger.info(f"   📊 Сканирование фьючерсов ({tf_name})...")
                # for i, future in enumerate(futures):
                if False:  # Блок отключен - сканируем только акции
                    time.sleep(0.2) # Пауза чтобы не забить API
                    
                    try:
                        # Загружаем свечи с учетом настроек таймфрейма
                        df = scanner.get_candles_by_uid(
                            future['uid'], 
                            days_back=tf_config['days_back'],
                            interval=tf_config['interval']
                        )
                        
                        if not df.empty:
                            # Добавляем индикаторы (нужны для проверки условий входа и расчета SL/TP)
                            df = scanner.bullish_scanner._add_indicators(df)
                            
                            # Анализируем на оба типа паттернов
                            patterns = scanner.analyze(df, timeframe=tf_name, scan_type=scan_type)
                            
                            if patterns:
                                for pattern_info in patterns:
                                    current_candle_time = df.iloc[-1].name
                                    pattern_type = "Бычий" if "FLAG" in pattern_info['pattern'] and "BEARISH" not in pattern_info['pattern'] else "Медвежий"
                                    
                                    # Кэш по тикеру, таймфрейму, типу и времени T4
                                    t4_time = pattern_info['t4']['time']
                                    cache_key = (future['ticker'], tf_name, pattern_type, t4_time)
                                    
                                    if cache_key in sent_signals_cache:
                                        continue
                                    
                                    sent_signals_cache[cache_key] = True
                                    found_count_tf += 1
                                    total_found_count += 1
                                    
                                    t0 = pattern_info['t0']['price']
                                    t1 = pattern_info['t1']['price']
                                    t2 = pattern_info['t2']['price']
                                    t3 = pattern_info['t3']['price']
                                    t4 = pattern_info['t4']['price']
                                    
                                    logger.info(f"   🚩 {future['ticker']} ({future['display_name']}) [{tf_name}]: {pattern_type} флаг найден!")
                                    logger.info(f"      T0: {t0:.2f}, T1: {t1:.2f}, T2: {t2:.2f}, T3: {t3:.2f}, T4: {t4:.2f}")
                                    
                                    # Проверка условий входа и открытие позиции (если торговля включена)
                                    if enable_trading and trade_manager and strategy:
                                        try:
                                            # Подготавливаем паттерн для проверки
                                            pattern = {
                                                'pattern': pattern_info['pattern'],
                                                't0': {'idx': pattern_info['t0']['idx'], 'price': pattern_info['t0']['price']},
                                                't1': {'idx': pattern_info['t1']['idx'], 'price': pattern_info['t1']['price']},
                                                't2': {'idx': pattern_info['t2']['idx'], 'price': pattern_info['t2']['price']},
                                                't3': {'idx': pattern_info['t3']['idx'], 'price': pattern_info['t3']['price']},
                                                't4': {'idx': pattern_info['t4']['idx'], 'price': pattern_info['t4']['price']},
                                            }
                                            
                                            # Получаем текущую цену
                                            current_price = df.iloc[-1]['close']
                                            
                                            # Проверяем условия входа (EMA Squeeze)
                                            result = strategy.check_entry_signal(
                                                    df=df,
                                                    pattern=pattern,
                                                    entry_mode='ema_squeeze',  # Parallel Lines отключено, используем только EMA Squeeze
                                                    current_price=current_price
                                                )
                                            
                                            # Результат может быть (bool, str) или (bool, str, str)
                                            if len(result) == 3:
                                                signal, desc, active_mode = result
                                            else:
                                                signal, desc = result
                                                active_mode = 'ema_squeeze'  # Parallel Lines отключено, используем только EMA Squeeze
                                            
                                            if signal:
                                                logger.info(f"      ✅ СИГНАЛ НА ВХОД!")
                                                logger.info(f"      📝 {desc}")
                                                
                                                # Рассчитываем уровни выхода (используем режим сработавшего условия)
                                                # Если active_mode не определен, используем ema_squeeze (так как Parallel Lines отключено)
                                                final_entry_mode = active_mode if active_mode else 'ema_squeeze'
                                                exit_levels = strategy.calculate_exit_levels(
                                                    df, pattern, current_price, entry_mode=final_entry_mode
                                                )
                                                
                                                stop_loss = exit_levels['stop_loss']
                                                take_profit = exit_levels['take_profit']
                                                
                                                # Определяем направление
                                                direction = 'LONG' if pattern_type == "Бычий" else 'SHORT'
                                                
                                                # Формируем описание стратегии (используем режим сработавшего условия)
                                                strategy_desc = f"{final_entry_mode} Entry ({tf_name})"
                                                
                                                logger.info(f"      📊 Параметры сделки: Цена={current_price:.2f}, SL={stop_loss:.2f}, TP={take_profit:.2f}, Направление={direction}")
                                                
                                                # Открываем позицию
                                                trade_manager.open_position(
                                                    ticker=future['ticker'],
                                                    uid=future['uid'],
                                                    direction=direction,
                                                    price=current_price,
                                                    stop_loss=stop_loss,
                                                    take_profit=take_profit,
                                                    strategy_desc=strategy_desc,
                                                    df_context=df,
                                                    pattern_info=pattern_info,
                                                    entry_mode='ema_squeeze'  # Parallel Lines отключено
                                                )
                                            else:
                                                logger.info(f"      ❌ Условия входа не выполнены: {desc}")
                                        except Exception as e:
                                            logger.error(f"      ⚠️ Ошибка проверки условий входа: {e}")
                                            import traceback
                                            logger.error(traceback.format_exc())
                                    
                                    if telegram_enabled:
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
                                        
                                        try:
                                            chart_image = create_flag_chart_image(df, pattern_info, future['ticker'], tf_name)
                                            if send_telegram_signal(tg_message, chart_image):
                                                logger.info(f"      ✅ Отправлено в Telegram")
                                            else:
                                                logger.warning(f"      ⚠️ Не удалось отправить в Telegram")
                                        except Exception as img_err:
                                            logger.warning(f"      ⚠️ Ошибка генерации графика: {img_err}")
                                            send_telegram_signal(tg_message)
                                
                    except Exception as e:
                        pass
                
                logger.info(f"   ✅ Таймфрейм {tf_name} завершен. Найдено: {found_count_tf}")
                time.sleep(1) # Пауза между таймфреймами

            logger.info(f"🏁 [Complex Flag] Полный цикл завершен. Всего найдено: {total_found_count}")

        except Exception as e:
            logger.error(f"❌ Критическая ошибка: {e}")
            import traceback
            logger.error(traceback.format_exc())

        logger.info(f"💤 Сон {SCAN_INTERVAL/60} мин...")
        time.sleep(SCAN_INTERVAL)

if __name__ == "__main__":
    run_complex_flag_scanner()