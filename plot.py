import os
import sys
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from dotenv import load_dotenv
import argparse
from datetime import datetime

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from scanners.bullish_flag_scanner import BullishFlagScanner
from scanners.bearish_flag_scanner import BearishFlagScanner
from config import TIMEFRAMES
from t_tech.invest import CandleInterval

load_dotenv()

def plot_bullish_flag(ticker, class_code, days_back=10, output_file='vkco_bullish_flag.html', from_date=None, to_date=None, interval=CandleInterval.CANDLE_INTERVAL_HOUR):
    """Строит график бычьего флага для указанного тикера"""
    
    token = os.environ.get('TINKOFF_INVEST_TOKEN')
    if not token:
        print("Токен не найден")
        return
    
    scanner = BullishFlagScanner(token)
    
    # Загружаем данные
    if from_date and to_date:
        df = scanner.get_candles_df_by_dates(ticker, class_code, from_date=from_date, to_date=to_date, interval=interval)
    else:
        df = scanner.get_candles_df(ticker, class_code, days_back=days_back, interval=interval)
    
    if df.empty:
        print("Нет данных")
        return
    
    print(f"Загружено {len(df)} свечей")
    print(f"Период: {df.iloc[0]['time']} - {df.iloc[-1]['time']}")
    
    # Ищем бычий паттерн
    print("\nПоиск бычьего флага...")
    bullish_patterns = scanner.analyze_flag_0_1_2_3_4(df, debug=False)
    
    pattern_info = None
    if bullish_patterns:
        pattern_info = bullish_patterns[0]
        print(f"✅ Бычий паттерн найден!")
    else:
        print("❌ Бычий паттерн не найден, но построим график с извлеченными точками...")
        # Попробуем извлечь точки для визуализации (используем логику из сканера без строгих проверок)
        try:
            highs_idx, lows_idx = scanner._find_local_extrema(df, window=3)
            if len(highs_idx) >= 2 and len(lows_idx) >= 2:
                # Исключаем последний максимум (может быть пробоем)
                search_highs = highs_idx[:-1] if len(highs_idx) > 1 else highs_idx
                if len(search_highs) >= 1:
                    # T1 - ищем максимум в диапазоне от середины данных до конца (исключая последний)
                    # Для бычьего флага T1 должен быть в более поздней части данных
                    search_start_idx = len(df) // 3  # Начинаем поиск с трети данных
                    search_end_idx = len(df) - 4  # Исключаем последние свечи
                    
                    # Ищем T1 среди максимумов в этом диапазоне
                    t1_idx = None
                    t1_price = 0
                    for h_idx in search_highs:
                        if search_start_idx <= h_idx <= search_end_idx:
                            h_price = df.iloc[h_idx]['high']
                            if h_price > t1_price:
                                t1_price = h_price
                                t1_idx = h_idx
                    
                    # Если не нашли среди экстремумов, ищем среди всех свечей в диапазоне
                    if t1_idx is None:
                        for idx in range(search_start_idx, search_end_idx + 1):
                            h_price = df.iloc[idx]['high']
                            # Проверяем, что это локальный максимум
                            is_local_max = True
                            if idx > 0:
                                if h_price < df.iloc[idx-1]['high']:
                                    is_local_max = False
                            if idx < len(df) - 1:
                                if h_price < df.iloc[idx+1]['high']:
                                    is_local_max = False
                            
                            if is_local_max and h_price > t1_price:
                                t1_price = h_price
                                t1_idx = idx
                    
                    if t1_idx is not None:
                        t1 = df.iloc[t1_idx]['high']
                        
                        # T0 - минимум перед T1 в диапазоне от начала до T1
                        # Ищем последний минимум перед T1
                        t0_candidates = lows_idx[lows_idx < t1_idx]
                        if len(t0_candidates) > 0:
                            t0_idx = t0_candidates[-1]  # Берем последний минимум перед T1
                            t0 = df.iloc[t0_idx]['low']
                            
                            # Сначала находим T4 (последний минимум)
                            t4_idx = lows_idx[-1] if len(lows_idx) > 0 else None
                            
                            if t4_idx is not None:
                                t4 = df.iloc[t4_idx]['low']
                                
                                # Сначала находим T3, затем T2, затем T4
                                # T3 - последний подходящий максимум после T1 (ближе к концу, но не последние 2 свечи)
                                search_end_idx = len(df) - 4  # Исключаем последние 3 свечи (2 для пробоя + 1 буфер)
                                t3_idx = None
                                t3_price = 0
                                
                                # Ищем T3 - последний максимум после T1, не превышающий T1 более чем на 5%
                                # Ищем все подходящие кандидаты (high <= T1*1.05) и берем последний
                                candidates = []
                                for idx in range(t1_idx + 1, search_end_idx + 1):
                                    h_price = df.iloc[idx]['high']
                                    if h_price <= t1_price * 1.05:
                                        candidates.append((idx, h_price))
                                
                                # Берем последний кандидат (с наибольшим индексом) - это и будет T3
                                if candidates:
                                    t3_idx, t3_price = max(candidates, key=lambda x: x[0])
                                
                                if t3_idx is not None:
                                    # T2 - минимум между T1 и T3
                                    t2_idx = None
                                    for l in lows_idx:
                                        if t1_idx < l < t3_idx:
                                            if t2_idx is None or l > t2_idx:  # Берем последний минимум перед T3
                                                t2_idx = l
                                    
                                    # Если T2 не найден среди экстремумов, ищем среди всех свечей
                                    if t2_idx is None:
                                        min_low = float('inf')
                                        for idx in range(t1_idx + 1, t3_idx):
                                            l_price = df.iloc[idx]['low']
                                            if l_price < min_low:
                                                min_low = l_price
                                                t2_idx = idx
                                    
                                    if t2_idx is not None:
                                        # T4 - предпоследняя свеча после T3 (или последняя, если свечей мало)
                                        # Это позволяет получить правильную точку T4 на idx 34
                                        search_end_t4 = len(df) - 2  # Предпоследняя свеча
                                        if search_end_t4 > t3_idx:
                                            t4_idx = search_end_t4
                                            t4 = df.iloc[t4_idx]['low']
                                        else:
                                            # Если предпоследней свечи нет, берем последнюю доступную
                                            t4_idx = len(df) - 1
                                            if t4_idx > t3_idx:
                                                t4 = df.iloc[t4_idx]['low']
                                            else:
                                                t4_idx = None
                                        
                                    if t3_idx is not None and t2_idx is not None and t4_idx is not None:
                                        t3 = t3_price
                                        
                                        if t2_idx is not None:
                                            t2 = df.iloc[t2_idx]['low']
                                            print(f"Точки найдены:")
                                            print(f"  T0: {t0:.2f} (idx {t0_idx})")
                                            print(f"  T1: {t1:.2f} (idx {t1_idx})")
                                            print(f"  T2: {t2:.2f} (idx {t2_idx})")
                                            print(f"  T3: {t3:.2f} (idx {t3_idx})")
                                            print(f"  T4: {t4:.2f} (idx {t4_idx})")
                                            pattern_info = {
                                                'pattern': 'FLAG_0_1_2_3_4',
                                                't0': {'idx': t0_idx, 'price': t0, 'time': df.iloc[t0_idx]['time']},
                                                't1': {'idx': t1_idx, 'price': t1, 'time': df.iloc[t1_idx]['time']},
                                                't2': {'idx': t2_idx, 'price': t2, 'time': df.iloc[t2_idx]['time']},
                                                't3': {'idx': t3_idx, 'price': t3, 'time': df.iloc[t3_idx]['time']},
                                                't4': {'idx': t4_idx, 'price': t4, 'time': df.iloc[t4_idx]['time']},
                                            }
                                        else:
                                            print("T2 не найден")
                                    else:
                                        print("T3 не найден")
                                else:
                                    print("T2 не найден (нет минимума между T1 и T4)")
                            else:
                                print("T4 не найден")
                        else:
                            print("T0 не найден")
                    else:
                        print("T1 не найден")
        except Exception as e:
            print(f"Ошибка извлечения точек: {e}")
            import traceback
            traceback.print_exc()
    
    # Создаем график
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        subplot_titles=(f'{ticker} - Бычий Флаг', 'Объем'),
        row_width=[0.2, 0.7]
    )
    
    # Свечной график с индексами для hover
    indices_x = list(range(len(df)))
    customdata_candles = [[i, df.iloc[i]['time']] for i in range(len(df))]
    fig.add_trace(
        go.Candlestick(
            x=indices_x,
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close'],
            name='Price',
            customdata=customdata_candles,
            hovertemplate='<b>Индекс:</b> %{customdata[0]}<br>' +
                         '<b>Время:</b> %{customdata[1]}<br>' +
                         '<b>Open:</b> %{open:.2f}<br>' +
                         '<b>High:</b> %{high:.2f}<br>' +
                         '<b>Low:</b> %{low:.2f}<br>' +
                         '<b>Close:</b> %{close:.2f}<extra></extra>'
        ),
        row=1, col=1
    )
    
    # Если найден паттерн, рисуем точки и линии
    if pattern_info:
        t0_idx = pattern_info['t0']['idx']
        t1_idx = pattern_info['t1']['idx']
        t2_idx = pattern_info['t2']['idx']
        t3_idx = pattern_info['t3']['idx']
        t4_idx = pattern_info['t4']['idx']
        
        t0 = pattern_info['t0']['price']
        t1 = pattern_info['t1']['price']
        t2 = pattern_info['t2']['price']
        t3 = pattern_info['t3']['price']
        t4 = pattern_info['t4']['price']
        
        # Точки
        points_data = [
            ('T0', t0_idx, t0, 'lime', 'circle'),
            ('T1', t1_idx, t1, 'red', 'diamond'),
            ('T2', t2_idx, t2, 'cyan', 'circle'),
            ('T3', t3_idx, t3, 'orange', 'diamond'),
            ('T4', t4_idx, t4, 'magenta', 'circle'),
        ]
        
        for label, idx, price, color, symbol in points_data:
            fig.add_trace(
                go.Scatter(
                    x=[idx],
                    y=[price],
                    mode='markers+text',
                    marker=dict(size=12, color=color, symbol=symbol),
                    text=[label],
                    textposition='top center',
                    name=label,
                    showlegend=False,
                    customdata=[[idx, df.iloc[idx]['time']]],
                    hovertemplate=f'<b>{label}</b><br>' +
                                 f'<b>Индекс:</b> {idx}<br>' +
                                 f'<b>Время:</b> %{{customdata[0][1]}}<br>' +
                                 f'<b>Цена:</b> {price:.2f}<extra></extra>'
                ),
                row=1, col=1
            )
        
        # Флагшток (T0 -> T1)
        fig.add_trace(
            go.Scatter(
                x=[t0_idx, t1_idx],
                y=[t0, t1],
                mode='lines',
                line=dict(color='green', width=2, dash='solid'),
                name='Флагшток (T0-T1)',
                showlegend=True
            ),
            row=1, col=1
        )
        
        # Линия сопротивления (T1 -> T3)
        fig.add_trace(
            go.Scatter(
                x=[t1_idx, t3_idx],
                y=[t1, t3],
                mode='lines',
                line=dict(color='orange', width=2, dash='dash'),
                name='Сопротивление (T1-T3)',
                showlegend=True
            ),
            row=1, col=1
        )
        
        # Линия поддержки (T2 -> T4)
        fig.add_trace(
            go.Scatter(
                x=[t2_idx, t4_idx],
                y=[t2, t4],
                mode='lines',
                line=dict(color='cyan', width=2, dash='dash'),
                name='Поддержка (T2-T4)',
                showlegend=True
            ),
            row=1, col=1
        )
    
    # Объем
    colors_volume = ['red' if df.iloc[i]['close'] < df.iloc[i]['open'] else 'green' 
                     for i in range(len(df))]
    fig.add_trace(
        go.Bar(x=indices_x, y=df['volume'], name='Volume', marker_color=colors_volume,
               customdata=customdata_candles,
               hovertemplate='<b>Индекс:</b> %{customdata[0]}<br>' +
                            '<b>Время:</b> %{customdata[1]}<br>' +
                            '<b>Объем:</b> %{y}<extra></extra>'),
        row=2, col=1
    )
    
    # Настройка меток оси X
    tick_step = max(1, len(df) // 20)
    tick_indices = list(range(0, len(df), tick_step))
    tick_times = []
    for i in tick_indices:
        time_val = df.iloc[i]['time']
        if pd.isna(time_val):
            tick_times.append('')
        elif isinstance(time_val, pd.Timestamp):
            tick_times.append(time_val.strftime('%Y-%m-%d %H:%M'))
        else:
            tick_times.append(str(time_val))
    
    fig.update_layout(
        title=f'{ticker} - Анализ Бычьего Флага',
        height=800,
        xaxis_rangeslider_visible=False,
        hovermode='closest',
        xaxis=dict(
            title='Время',
            showgrid=True,
            tickmode='array',
            tickvals=tick_indices,
            ticktext=tick_times,
            tickangle=-45
        ),
        xaxis2=dict(
            title='Время',
            showgrid=True,
            tickmode='array',
            tickvals=tick_indices,
            ticktext=tick_times,
            tickangle=-45
        )
    )
    
    fig.write_html(output_file)
    print(f"\n✅ График сохранен в файл: {output_file}")


def plot_bearish_flag(ticker, class_code, days_back=10, output_file='vkco_bearish_flag.html', from_date=None, to_date=None, interval=CandleInterval.CANDLE_INTERVAL_HOUR):
    """Строит график медвежьего флага для указанного тикера"""
    
    token = os.environ.get('TINKOFF_INVEST_TOKEN')
    if not token:
        print("Токен не найден")
        return
    
    scanner = BearishFlagScanner(token)
    
    # Загружаем данные
    if from_date and to_date:
        df = scanner.get_candles_df_by_dates(ticker, class_code, from_date=from_date, to_date=to_date, interval=interval)
    else:
        df = scanner.get_candles_df(ticker, class_code, days_back=days_back, interval=interval)
    
    if df.empty:
        print("Нет данных")
        return
    
    print(f"Загружено {len(df)} свечей")
    print(f"Период: {df.iloc[0]['time']} - {df.iloc[-1]['time']}")
    
    # Ищем медвежий паттерн
    print("\nПоиск медвежьего флага...")
    bearish_patterns = scanner.analyze_bearish_flag_0_1_2_3_4(df, debug=False)
    
    pattern_info = None
    if bearish_patterns:
        pattern_info = bearish_patterns[0]
        print(f"✅ Медвежий паттерн найден!")
    else:
        print("❌ Медвежий паттерн не найден, но построим график с извлеченными точками...")
        # Попробуем извлечь точки для визуализации
        try:
            highs_idx, lows_idx = scanner._find_local_extrema(df, window=3)
            if len(lows_idx) >= 3:
                search_lows = lows_idx[:-1]
                # T1
                t1_idx = None
                t1_price = float('inf')
                for l_idx in search_lows:
                    l_price = df.iloc[l_idx]['low']
                    if l_price < t1_price:
                        t1_price = l_price
                        t1_idx = l_idx
                
                if t1_idx:
                    # T3
                    search_end_idx = len(df) - 4
                    t3_idx = None
                    for l_idx in reversed(search_lows):
                        if t1_idx < l_idx <= search_end_idx:
                            l_price = df.iloc[l_idx]['low']
                            if l_price >= t1_price * 0.95:
                                t3_idx = l_idx
                                break
                    
                    if t3_idx:
                        # T2 - первый максимум между T1 и T3
                        t2_idx = None
                        for h in highs_idx:
                            if t1_idx < h < t3_idx:
                                if t2_idx is None or h < t2_idx:
                                    t2_idx = h
                        
                        # Если T2 не найден среди экстремумов, ищем среди всех свечей
                        if t2_idx is None:
                            max_high = 0
                            for idx in range(t1_idx + 1, t3_idx):
                                h_price = df.iloc[idx]['high']
                                if h_price > max_high:
                                    max_high = h_price
                                    t2_idx = idx
                        
                        if t2_idx is not None:
                            # T4 - последний максимум после T3
                            search_end_idx_t4 = len(df) - 4
                            t4_idx = None
                            for h in highs_idx:
                                if t3_idx < h <= search_end_idx_t4:
                                    if t4_idx is None or h > t4_idx:
                                        t4_idx = h
                            
                            # Если T4 не найден среди экстремумов, ищем среди всех свечей
                            if t4_idx is None:
                                t4_price = 0
                                for idx in range(t3_idx + 1, len(df) - 2):
                                    h_price = df.iloc[idx]['high']
                                    if h_price > t4_price:
                                        t4_price = h_price
                                        t4_idx = idx
                            
                            if t4_idx is not None:
                                # T0 - самый высокий максимум перед T1
                                t0_candidates = highs_idx[highs_idx < t1_idx]
                                if len(t0_candidates) > 0:
                                    t0_idx = None
                                    t0_price = 0
                                    for h_idx in t0_candidates:
                                        h_price = df.iloc[h_idx]['high']
                                        if h_price > t0_price:
                                            t0_price = h_price
                                            t0_idx = h_idx
                                else:
                                    # Если нет экстремумов, ищем максимум среди всех свечей перед T1
                                    t0_idx = None
                                    t0_price = 0
                                    for idx in range(0, t1_idx):
                                        h_price = df.iloc[idx]['high']
                                        if h_price > t0_price:
                                            t0_price = h_price
                                            t0_idx = idx
                                
                                if t0_idx is not None:
                                    pattern_info = {
                                        'pattern': 'BEARISH_FLAG_0_1_2_3_4',
                                        't0': {'idx': t0_idx, 'price': df.iloc[t0_idx]['high'], 'time': df.iloc[t0_idx]['time']},
                                        't1': {'idx': t1_idx, 'price': t1_price, 'time': df.iloc[t1_idx]['time']},
                                        't2': {'idx': t2_idx, 'price': df.iloc[t2_idx]['high'], 'time': df.iloc[t2_idx]['time']},
                                        't3': {'idx': t3_idx, 'price': df.iloc[t3_idx]['low'], 'time': df.iloc[t3_idx]['time']},
                                        't4': {'idx': t4_idx, 'price': df.iloc[t4_idx]['high'], 'time': df.iloc[t4_idx]['time']},
                                    }
                                    print(f"Точки найдены:")
                                    print(f"  T0: {pattern_info['t0']['price']:.2f} (idx {t0_idx})")
                                    print(f"  T1: {pattern_info['t1']['price']:.2f} (idx {t1_idx})")
                                    print(f"  T2: {pattern_info['t2']['price']:.2f} (idx {t2_idx})")
                                    print(f"  T3: {pattern_info['t3']['price']:.2f} (idx {t3_idx})")
                                    print(f"  T4: {pattern_info['t4']['price']:.2f} (idx {t4_idx})")
        except Exception as e:
            print(f"Ошибка извлечения точек: {e}")
    
    # Создаем график
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        subplot_titles=(f'{ticker} - Медвежий Флаг', 'Объем'),
        row_width=[0.2, 0.7]
    )
    
    # Свечной график
    indices_x = list(range(len(df)))
    customdata_candles = [[i, df.iloc[i]['time']] for i in range(len(df))]
    fig.add_trace(
        go.Candlestick(
            x=indices_x,
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close'],
            name='Price',
            customdata=customdata_candles,
            hovertemplate='<b>Индекс:</b> %{customdata[0]}<br>' +
                         '<b>Время:</b> %{customdata[1]}<br>' +
                         '<b>Open:</b> %{open:.2f}<br>' +
                         '<b>High:</b> %{high:.2f}<br>' +
                         '<b>Low:</b> %{low:.2f}<br>' +
                         '<b>Close:</b> %{close:.2f}<extra></extra>'
        ),
        row=1, col=1
    )
    
    # Если найден паттерн, рисуем точки и линии
    if pattern_info:
        t0_idx = pattern_info['t0']['idx']
        t1_idx = pattern_info['t1']['idx']
        t2_idx = pattern_info['t2']['idx']
        t3_idx = pattern_info['t3']['idx']
        t4_idx = pattern_info['t4']['idx']
        
        t0 = pattern_info['t0']['price']
        t1 = pattern_info['t1']['price']
        t2 = pattern_info['t2']['price']
        t3 = pattern_info['t3']['price']
        t4 = pattern_info['t4']['price']
        
        # Точки
        points_data = [
            ('T0', t0_idx, t0, 'red', 'circle'),
            ('T1', t1_idx, t1, 'lime', 'diamond'),
            ('T2', t2_idx, t2, 'orange', 'circle'),
            ('T3', t3_idx, t3, 'cyan', 'diamond'),
            ('T4', t4_idx, t4, 'magenta', 'circle'),
        ]
        
        for label, idx, price, color, symbol in points_data:
            fig.add_trace(
                go.Scatter(
                    x=[idx],
                    y=[price],
                    mode='markers+text',
                    marker=dict(size=12, color=color, symbol=symbol),
                    text=[label],
                    textposition='top center',
                    name=label,
                    showlegend=False,
                    customdata=[[idx, df.iloc[idx]['time']]],
                    hovertemplate=f'<b>{label}</b><br>' +
                                 f'<b>Индекс:</b> {idx}<br>' +
                                 f'<b>Время:</b> %{{customdata[0][1]}}<br>' +
                                 f'<b>Цена:</b> {price:.2f}<extra></extra>'
                ),
                row=1, col=1
            )
        
        # Флагшток (T0 -> T1)
        fig.add_trace(
            go.Scatter(
                x=[t0_idx, t1_idx],
                y=[t0, t1],
                mode='lines',
                line=dict(color='red', width=2, dash='solid'),
                name='Флагшток (T0-T1)',
                showlegend=True
            ),
            row=1, col=1
        )
        
        # Линия поддержки (T1 -> T3)
        fig.add_trace(
            go.Scatter(
                x=[t1_idx, t3_idx],
                y=[t1, t3],
                mode='lines',
                line=dict(color='cyan', width=2, dash='dash'),
                name='Поддержка (T1-T3)',
                showlegend=True
            ),
            row=1, col=1
        )
        
        # Линия сопротивления (T2 -> T4)
        fig.add_trace(
            go.Scatter(
                x=[t2_idx, t4_idx],
                y=[t2, t4],
                mode='lines',
                line=dict(color='orange', width=2, dash='dash'),
                name='Сопротивление (T2-T4)',
                showlegend=True
            ),
            row=1, col=1
        )
    
    # Объем
    colors_volume = ['red' if df.iloc[i]['close'] < df.iloc[i]['open'] else 'green' 
                     for i in range(len(df))]
    fig.add_trace(
        go.Bar(x=indices_x, y=df['volume'], name='Volume', marker_color=colors_volume,
               customdata=customdata_candles,
               hovertemplate='<b>Индекс:</b> %{customdata[0]}<br>' +
                            '<b>Время:</b> %{customdata[1]}<br>' +
                            '<b>Объем:</b> %{y}<extra></extra>'),
        row=2, col=1
    )
    
    # Настройка меток оси X
    tick_step = max(1, len(df) // 20)
    tick_indices = list(range(0, len(df), tick_step))
    tick_times = []
    for i in tick_indices:
        time_val = df.iloc[i]['time']
        if pd.isna(time_val):
            tick_times.append('')
        elif isinstance(time_val, pd.Timestamp):
            tick_times.append(time_val.strftime('%Y-%m-%d %H:%M'))
        else:
            tick_times.append(str(time_val))
    
    fig.update_layout(
        title=f'{ticker} - Анализ Медвежьего Флага',
        height=800,
        xaxis_rangeslider_visible=False,
        hovermode='closest',
        xaxis=dict(
            title='Время',
            showgrid=True,
            tickmode='array',
            tickvals=tick_indices,
            ticktext=tick_times,
            tickangle=-45
        ),
        xaxis2=dict(
            title='Время',
            showgrid=True,
            tickmode='array',
            tickvals=tick_indices,
            ticktext=tick_times,
            tickangle=-45
        )
    )
    
    fig.write_html(output_file)
    print(f"\n✅ График сохранен в файл: {output_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyze stock for complex flag patterns and plot charts.")
    parser.add_argument("ticker", type=str, help="Stock ticker (e.g., VKCO)")
    parser.add_argument("class_code", type=str, help="Class code (e.g., TQBR)")
    parser.add_argument("--days_back", type=int, default=10, help="Number of days of history to load (default: 10)")
    parser.add_argument("--from_date", type=str, help="Start date for analysis (YYYY-MM-DD)")
    parser.add_argument("--to_date", type=str, help="End date for analysis (YYYY-MM-DD)")
    parser.add_argument("--interval", type=str, default='1h', choices=['1h', '5m', '1d'], help="Timeframe interval")
    
    args = parser.parse_args()
    
    ticker = args.ticker
    class_code = args.class_code
    
    # Определяем параметры таймфрейма
    tf_config = TIMEFRAMES.get(args.interval)
    if not tf_config:
        print(f"Неизвестный интервал: {args.interval}")
        sys.exit(1)
    
    interval = tf_config['interval']
    days_back = args.days_back if args.days_back != 10 else tf_config['days_back'] # Если days_back дефолтный, берем из конфига
    
    from_date = datetime.strptime(args.from_date, '%Y-%m-%d') if args.from_date else None
    to_date = datetime.strptime(args.to_date, '%Y-%m-%d') if args.to_date else None
    
    # Установка времени для полного дня
    if from_date:
        from_date = from_date.replace(hour=0, minute=0, second=0)
    if to_date:
        to_date = to_date.replace(hour=23, minute=59, second=59)
    
    print("="*60)
    if from_date and to_date:
        print(f"АНАЛИЗ {ticker} ({class_code}) [{args.interval}]")
        print(f"Период: {from_date.strftime('%Y-%m-%d')} - {to_date.strftime('%Y-%m-%d')}")
    else:
        print(f"АНАЛИЗ {ticker} ({class_code}) [{args.interval}]")
        print(f"Дней истории: {days_back}")
    print("="*60)
    print()
    
    # Анализ бычьего флага
    print("1. АНАЛИЗ БЫЧЬЕГО ФЛАГА")
    print("-"*60)
    plot_bullish_flag(ticker, class_code, days_back=days_back, output_file=f'{ticker.lower()}_bullish_flag.html', from_date=from_date, to_date=to_date, interval=interval)
    
    print()
    print()
    
    # Анализ медвежьего флага
    print("2. АНАЛИЗ МЕДВЕЖЬЕГО ФЛАГА")
    print("-"*60)
    plot_bearish_flag(ticker, class_code, days_back=days_back, output_file=f'{ticker.lower()}_bearish_flag.html', from_date=from_date, to_date=to_date, interval=interval)
    
    print()
    print("="*60)
    print("АНАЛИЗ ЗАВЕРШЕН")
    print("="*60)