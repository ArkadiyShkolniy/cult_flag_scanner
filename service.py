import time
import os
import sys
import io
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

load_dotenv()

SCAN_INTERVAL = 60 * 10

def run_complex_flag_scanner():
    token = os.environ.get("TINKOFF_INVEST_TOKEN")
    if not token:
        print("❌ [Complex Flag Scanner] Токен не найден.")
        return

    print(f"🚀 [Complex Flag Scanner] Запуск. Сканирование всех акций TQBR...")
    
    scanner = ComplexFlagScanner(token)
    sent_signals_cache = {}

    while True:
        try:
            print(f"\n🌍 [Complex Flag] {datetime.now().strftime('%H:%M:%S')} Начало сканирования...")
            
            shares = scanner.get_all_shares()
            print(f"   Найдено {len(shares)} инструментов. Анализ...")
            
            found_count = 0
            
            for i, share in enumerate(shares):
                time.sleep(0.2)
                
                try:
                    df = scanner.get_candles_by_uid(share.uid, days_back=5)
                    
                    if not df.empty:
                        patterns = scanner.analyze_flag_0_1_2_3_4(df)
                        
                        if patterns:
                            pattern_info = patterns[0]
                            
                            current_candle_time = df.iloc[-1].name
                            last_sent_time = sent_signals_cache.get(share.ticker)
                            
                            if last_sent_time and last_sent_time == current_candle_time:
                                continue
                            
                            sent_signals_cache[share.ticker] = current_candle_time
                            found_count += 1
                            
                            t0 = pattern_info['t0']['price']
                            t1 = pattern_info['t1']['price']
                            t2 = pattern_info['t2']['price']
                            t3 = pattern_info['t3']['price']
                            t4 = pattern_info['t4']['price']
                            pole_height = pattern_info['pole_height']
                            current_price = pattern_info['current_price']
                            
                            print(f"   🏳️ {share.ticker}: Пробой флага найден!")
                            print(f"      T0: {t0:.2f}, T1: {t1:.2f}, T2: {t2:.2f}, T3: {t3:.2f}, T4: {t4:.2f}")
                            print(f"      Высота: {pole_height:.2f}, Текущая цена: {current_price:.2f}")
                            
                except Exception as e:
                    pass
                    
                if (i + 1) % 50 == 0:
                    print(f"   Прогресс: {i + 1}/{len(shares)}...")

            print(f"🏁 [Complex Flag] Сканирование завершено. Найдено сигналов: {found_count}")

        except Exception as e:
            print(f"❌ Критическая ошибка: {e}")
            import traceback
            traceback.print_exc()

        print(f"💤 Сон {SCAN_INTERVAL/60} мин...")
        time.sleep(SCAN_INTERVAL)

if __name__ == "__main__":
    run_complex_flag_scanner()