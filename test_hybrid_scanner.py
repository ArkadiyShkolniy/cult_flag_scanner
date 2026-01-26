#!/usr/bin/env python3
"""
Тестирование и визуализация гибридного сканера на MXH6
"""
import os
import sys
from pathlib import Path
from datetime import datetime, timezone
from dotenv import load_dotenv
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))

from scanners.hybrid_scanner import HybridFlagScanner
from config import TIMEFRAMES

load_dotenv()


def visualize_patterns(df, patterns, ticker, timeframe, title_suffix=""):
    """
    Визуализирует свечи с найденными паттернами
    """
    fig = make_subplots(
        rows=1, cols=1,
        subplot_titles=(f'{ticker} ({timeframe}) - {title_suffix}',),
        vertical_spacing=0.1
    )
    
    indices_x = list(range(len(df)))
    customdata = [[i, df.iloc[i]['time']] for i in range(len(df))]
    
    # Свечной график
    fig.add_trace(
        go.Candlestick(
            x=indices_x,
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close'],
            name='Цена',
            customdata=customdata,
            hovertemplate='<b>Индекс:</b> %{customdata[0]}<br>' +
                         '<b>Время:</b> %{customdata[1]}<br>' +
                         '<b>Open:</b> %{open:.2f}<br>' +
                         '<b>High:</b> %{high:.2f}<br>' +
                         '<b>Low:</b> %{low:.2f}<br>' +
                         '<b>Close:</b> %{close:.2f}<extra></extra>'
        ),
        row=1, col=1
    )
    
    # Цвета для разных паттернов
    pattern_colors = ['lime', 'yellow', 'cyan', 'magenta', 'orange', 'pink', 'lightblue']
    point_colors = {'T0': 'lime', 'T1': 'red', 'T2': 'cyan', 'T3': 'orange', 'T4': 'magenta'}
    point_symbols = {'T0': 'circle', 'T1': 'diamond', 'T2': 'circle', 'T3': 'diamond', 'T4': 'circle'}
    
    # Отрисовываем паттерны
    for pattern_idx, pattern in enumerate(patterns):
        color = pattern_colors[pattern_idx % len(pattern_colors)]
        pattern_type = "Бычий" if 'BEARISH' not in pattern.get('pattern', '') else "Медвежий"
        nn_conf = pattern.get('nn_confidence', 0)
        source = pattern.get('source', 'math')
        
        # Отрисовываем точки T0-T4
        for point_name in ['T0', 'T1', 'T2', 'T3', 'T4']:
            point_lower = point_name.lower()
            if point_lower in pattern:
                point_data = pattern[point_lower]
                idx = point_data['idx']
                price = point_data['price']
                
                if 0 <= idx < len(df):
                    fig.add_trace(
                        go.Scatter(
                            x=[idx],
                            y=[price],
                            mode='markers+text',
                            marker=dict(
                                size=10 if pattern_idx == 0 else 8,
                                color=point_colors[point_name],
                                symbol=point_symbols[point_name],
                                line=dict(width=1.5, color='white')
                            ),
                            text=[f'{point_name}#{pattern_idx+1}' if pattern_idx > 0 else point_name],
                            textposition='top center',
                            name=f'{point_name} #{pattern_idx+1}' if pattern_idx > 0 else point_name,
                            showlegend=(pattern_idx < 5),  # Показываем легенду только для первых 5
                            hovertemplate=f'<b>{point_name} (Паттерн #{pattern_idx+1})</b><br>' +
                                         f'Индекс: {idx}<br>' +
                                         f'Цена: {price:.2f}<br>' +
                                         f'Тип: {pattern_type}<br>' +
                                         f'Источник: {source}<br>' +
                                         f'NN уверенность: {nn_conf:.1%}' +
                                         f'<extra></extra>'
                        ),
                        row=1, col=1
                    )
        
        # Отрисовываем линии паттерна
        if all(p in pattern for p in ['t0', 't1', 't2', 't3', 't4']):
            t0_idx = pattern['t0']['idx']
            t1_idx = pattern['t1']['idx']
            t2_idx = pattern['t2']['idx']
            t3_idx = pattern['t3']['idx']
            t4_idx = pattern['t4']['idx']
            
            # Флагшток (T0 -> T1)
            if 0 <= t0_idx < len(df) and 0 <= t1_idx < len(df):
                fig.add_trace(
                    go.Scatter(
                        x=[t0_idx, t1_idx],
                        y=[pattern['t0']['price'], pattern['t1']['price']],
                        mode='lines',
                        line=dict(color=color, width=2.5, dash='solid'),
                        name=f'Флагшток #{pattern_idx+1}' if pattern_idx > 0 else 'Флагшток',
                        showlegend=(pattern_idx < 5),
                        hovertemplate=f'Флагшток #{pattern_idx+1} ({pattern_type}, {nn_conf:.0%})<extra></extra>'
                    ),
                    row=1, col=1
                )
            
            # Линия 1-3 (T1 -> T3)
            if 0 <= t1_idx < len(df) and 0 <= t3_idx < len(df):
                fig.add_trace(
                    go.Scatter(
                        x=[t1_idx, t3_idx],
                        y=[pattern['t1']['price'], pattern['t3']['price']],
                        mode='lines',
                        line=dict(color=color, width=2, dash='dash'),
                        name=f'Линия 1-3 #{pattern_idx+1}' if pattern_idx > 0 else 'Линия 1-3',
                        showlegend=(pattern_idx < 5),
                        hovertemplate=f'Линия T1-T3 #{pattern_idx+1}<extra></extra>'
                    ),
                    row=1, col=1
                )
            
            # Линия 2-4 (T2 -> T4)
            if 0 <= t2_idx < len(df) and 0 <= t4_idx < len(df):
                fig.add_trace(
                    go.Scatter(
                        x=[t2_idx, t4_idx],
                        y=[pattern['t2']['price'], pattern['t4']['price']],
                        mode='lines',
                        line=dict(color=color, width=1.5, dash='dash'),
                        name=f'Линия 2-4 #{pattern_idx+1}' if pattern_idx > 0 else 'Линия 2-4',
                        showlegend=(pattern_idx < 5),
                        hovertemplate=f'Линия T2-T4 #{pattern_idx+1}<extra></extra>'
                    ),
                    row=1, col=1
                )
    
    # Настройка осей
    tick_step = max(1, len(df) // 20)
    tick_indices = list(range(0, len(df), tick_step))
    tick_times = []
    for i in tick_indices:
        time_val = df.iloc[i]['time']
        if pd.notna(time_val):
            if isinstance(time_val, pd.Timestamp):
                tick_times.append(time_val.strftime('%m-%d %H:%M'))
            else:
                tick_times.append(str(time_val))
        else:
            tick_times.append('')
    
    title = f'{ticker} ({timeframe}) - {title_suffix} | Найдено паттернов: {len(patterns)}'
    
    fig.update_layout(
        height=800,
        xaxis_rangeslider_visible=False,
        title=title,
        template='plotly_dark',
        hovermode='closest',
        xaxis=dict(
            title='Время',
            showgrid=True,
            tickmode='array',
            tickvals=tick_indices,
            ticktext=tick_times,
            tickangle=-45
        )
    )
    
    return fig


def main():
    token = os.environ.get("TINKOFF_INVEST_TOKEN")
    if not token:
        print("❌ Токен не найден!")
        return
    
    print("=" * 60)
    print("🔬 ТЕСТИРОВАНИЕ ГИБРИДНОГО СКАНЕРА")
    print("=" * 60)
    print()
    
    # Параметры
    ticker = "MXH6"
    class_code = "SPBFUT"
    timeframe = "1h"
    from_date = datetime(2025, 10, 20, tzinfo=timezone.utc)
    to_date = datetime(2025, 12, 25, tzinfo=timezone.utc)
    
    print(f"📊 Инструмент: {ticker}")
    print(f"📅 Период: {from_date.date()} - {to_date.date()}")
    print(f"⏱️  Таймфрейм: {timeframe}")
    print()
    
    # Создаем гибридный сканер
    print("🏗️  Инициализация гибридного сканера...")
    scanner = HybridFlagScanner(
        token=token,
        use_nn=True,
        nn_min_confidence=0.6,
        device='cpu'
    )
    print()
    
    # Загружаем данные
    print(f"📥 Загрузка данных...")
    tf_config = TIMEFRAMES.get(timeframe, TIMEFRAMES['1h'])
    df = scanner.get_candles_df_by_dates(ticker, class_code, from_date, to_date, interval=tf_config['interval'])
    
    if df.empty:
        print("❌ Данные не загружены!")
        return
    
    print(f"✅ Загружено {len(df)} свечей")
    print(f"   Период: {df.iloc[0]['time']} - {df.iloc[-1]['time']}")
    print()
    
    # Режим 1: Математика + фильтрация NN
    print("📈 Режим 1: Математика + фильтрация NN (≥60%)")
    print("-" * 60)
    patterns_hybrid = scanner.analyze(df, timeframe=timeframe, filter_by_nn=True, min_nn_confidence=0.6)
    
    print(f"✅ Найдено {len(patterns_hybrid)} паттернов:")
    for i, p in enumerate(patterns_hybrid, 1):
        pattern_type = "Бычий" if p.get('nn_class', 0) == 1 else "Медвежий"
        nn_conf = p.get('nn_confidence', 0)
        nn_match = p.get('nn_match', False)
        print(f"  {i}. {pattern_type} флаг: NN={nn_conf:.1%}, совпадение={'✅' if nn_match else '❌'}")
    print()
    
    # Режим 2: Только математика
    print("📈 Режим 2: Только математика")
    print("-" * 60)
    patterns_math = scanner.analyze(df, timeframe=timeframe, filter_by_nn=False)
    
    print(f"✅ Найдено {len(patterns_math)} паттернов:")
    for i, p in enumerate(patterns_math, 1):
        pattern_type = "Бычий" if 'BEARISH' not in p.get('pattern', '') else "Медвежий"
        nn_conf = p.get('nn_confidence', 0)
        print(f"  {i}. {pattern_type} флаг: NN={nn_conf:.1%}")
    print()
    
    # Режим 3: Только NN
    print("📈 Режим 3: Только нейронная сеть (≥70%)")
    print("-" * 60)
    patterns_nn = scanner.analyze_with_nn_only(df, min_confidence=0.7)
    
    print(f"✅ Найдено {len(patterns_nn)} паттернов:")
    for i, p in enumerate(patterns_nn, 1):
        pattern_type = "Бычий" if p.get('nn_class', 0) == 1 else "Медвежий"
        nn_conf = p.get('nn_confidence', 0)
        print(f"  {i}. {pattern_type} флаг: NN={nn_conf:.1%}")
    print()
    
    # Визуализация
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # График 1: Гибридный режим
    if patterns_hybrid:
        print("📊 Создание графика: Гибридный режим (математика + NN)...")
        fig1 = visualize_patterns(df, patterns_hybrid, ticker, timeframe, 
                                  "Гибридный режим (Математика + NN ≥60%)")
        output_file1 = f'neural_network/hybrid_{ticker}_{timeframe}_{timestamp}.html'
        fig1.write_html(output_file1)
        print(f"   ✅ Сохранено: {output_file1}")
        fig1.show()
        print()
    
    # График 2: Только математика
    if patterns_math:
        print("📊 Создание графика: Только математика...")
        fig2 = visualize_patterns(df, patterns_math, ticker, timeframe, 
                                  "Только математический анализ")
        output_file2 = f'neural_network/math_only_{ticker}_{timeframe}_{timestamp}.html'
        fig2.write_html(output_file2)
        print(f"   ✅ Сохранено: {output_file2}")
        print()
    
    # График 3: Только NN
    if patterns_nn:
        print("📊 Создание графика: Только нейронная сеть...")
        fig3 = visualize_patterns(df, patterns_nn, ticker, timeframe, 
                                  "Только нейронная сеть (≥70%)")
        output_file3 = f'neural_network/nn_only_{ticker}_{timeframe}_{timestamp}.html'
        fig3.write_html(output_file3)
        print(f"   ✅ Сохранено: {output_file3}")
        print()
    
    # Сводная статистика
    print("=" * 60)
    print("📊 СВОДНАЯ СТАТИСТИКА")
    print("=" * 60)
    print(f"  • Математика: {len(patterns_math)} паттернов")
    print(f"  • Гибридный (≥60%): {len(patterns_hybrid)} паттернов")
    print(f"  • Только NN (≥70%): {len(patterns_nn)} паттернов")
    print()
    
    print("=" * 60)
    print("✅ ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")
    print("=" * 60)


if __name__ == "__main__":
    main()

