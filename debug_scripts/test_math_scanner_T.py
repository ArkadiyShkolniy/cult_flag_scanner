#!/usr/bin/env python3
"""
Тестирование математического сканера на акции T за период 17.11.25 - 09.01.26
Визуализация всех найденных паттернов
"""

import os
import sys
from pathlib import Path
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
from dotenv import load_dotenv

# Добавляем путь к корню проекта
sys.path.insert(0, str(Path(__file__).parent.parent))

from scanners.combined_scanner import ComplexFlagScanner
from config import TIMEFRAMES

load_dotenv()


def visualize_patterns(candles_df, patterns, ticker, timeframe):
    """Визуализирует все найденные паттерны"""
    
    if not patterns:
        print("⚠️  Паттерны не найдены для визуализации")
        return None
    
    fig = make_subplots(
        rows=1, cols=1,
        subplot_titles=(f'{ticker} ({timeframe}) - Найденные паттерны: {len(patterns)}',)
    )
    
    indices_x = list(range(len(candles_df)))
    customdata = [[i, candles_df.iloc[i]['time']] for i in range(len(candles_df))]
    
    # Свечной график
    fig.add_trace(
        go.Candlestick(
            x=indices_x,
            open=candles_df['open'],
            high=candles_df['high'],
            low=candles_df['low'],
            close=candles_df['close'],
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
    line_colors = ['lime', 'yellow', 'cyan', 'magenta', 'orange', 'red', 'blue', 'green', 'pink', 'lightblue']
    point_colors = {'T0': 'lime', 'T1': 'red', 'T2': 'cyan', 'T3': 'orange', 'T4': 'magenta'}
    point_symbols = {'T0': 'circle', 'T1': 'diamond', 'T2': 'circle', 'T3': 'diamond', 'T4': 'circle'}
    
    is_bearish_list = []
    for pattern_idx, pattern_info in enumerate(patterns):
        is_bearish = "BEARISH" in pattern_info.get('pattern', '')
        is_bearish_list.append(is_bearish)
        
        base_color = line_colors[pattern_idx % len(line_colors)]
        pattern_alpha = 0.8 if pattern_idx > 0 else 1.0
        
        # Точки паттерна
        points_data = [
            ('T0', pattern_info['t0']),
            ('T1', pattern_info['t1']),
            ('T2', pattern_info['t2']),
            ('T3', pattern_info['t3']),
            ('T4', pattern_info['t4']),
        ]
        
        for point_name, point in points_data:
            idx = point['idx']
            price = point['price']
            color = point_colors.get(point_name, 'yellow')
            symbol = point_symbols.get(point_name, 'circle')
            
            if 0 <= idx < len(candles_df):
                marker_size = 14 if pattern_idx == 0 else 12
                show_text = pattern_idx < 3
                
                fig.add_trace(
                    go.Scatter(
                        x=[idx],
                        y=[price],
                        mode='markers+text' if show_text else 'markers',
                        marker=dict(size=marker_size, color=color, symbol=symbol, 
                                   line=dict(width=2, color='white'), opacity=pattern_alpha),
                        text=[f'{point_name}'] if show_text and pattern_idx == 0 else ([''] if show_text else []),
                        textposition='top center',
                        name=f'{point_name} #{pattern_idx+1}' if pattern_idx > 0 else f'{point_name}',
                        showlegend=(pattern_idx < 3),
                        hovertemplate=f'<b>{point_name}</b> (паттерн #{pattern_idx+1})<br>' +
                                     f'Индекс: {idx}<br>' +
                                     f'Цена: {price:.2f}<br>' +
                                     f'Время: {point.get("time", "N/A")}<br>' +
                                     f'Тип: {"Медвежий" if is_bearish else "Бычий"}<extra></extra>'
                    ),
                    row=1, col=1
                )
        
        # Флагшток (T0 -> T1)
        fig.add_trace(
            go.Scatter(
                x=[pattern_info['t0']['idx'], pattern_info['t1']['idx']],
                y=[pattern_info['t0']['price'], pattern_info['t1']['price']],
                mode='lines',
                line=dict(color=base_color, width=3 if pattern_idx == 0 else 2.5, dash='solid'),
                opacity=pattern_alpha,
                name=f'Флагшток #{pattern_idx+1}' if pattern_idx > 0 else 'Флагшток (T0-T1)',
                showlegend=(pattern_idx < 3),
                hovertemplate=f'Флагшток #{pattern_idx+1}<extra></extra>'
            ),
            row=1, col=1
        )
        
        # Линии тренда
        if is_bearish:
            # Для медвежьего: T1-T3 - поддержка (нижняя), T2-T4 - сопротивление (верхняя)
            # Линия поддержки (T1 -> T3)
            fig.add_trace(
                go.Scatter(
                    x=[pattern_info['t1']['idx'], pattern_info['t3']['idx']],
                    y=[pattern_info['t1']['price'], pattern_info['t3']['price']],
                    mode='lines',
                    line=dict(color=base_color, width=2.5 if pattern_idx == 0 else 2, dash='dash'),
                    opacity=pattern_alpha,
                    name=f'Поддержка #{pattern_idx+1}' if pattern_idx > 0 else 'Поддержка (T1-T3)',
                    showlegend=(pattern_idx < 3),
                    hovertemplate=f'Поддержка T1-T3 #{pattern_idx+1}<extra></extra>'
                ),
                row=1, col=1
            )
            
            # Линия сопротивления (T2 -> T4)
            fig.add_trace(
                go.Scatter(
                    x=[pattern_info['t2']['idx'], pattern_info['t4']['idx']],
                    y=[pattern_info['t2']['price'], pattern_info['t4']['price']],
                    mode='lines',
                    line=dict(color=base_color, width=2 if pattern_idx == 0 else 1.5, dash='dash'),
                    opacity=pattern_alpha,
                    name=f'Сопротивление #{pattern_idx+1}' if pattern_idx > 0 else 'Сопротивление (T2-T4)',
                    showlegend=(pattern_idx < 3),
                    hovertemplate=f'Сопротивление T2-T4 #{pattern_idx+1}<extra></extra>'
                ),
                row=1, col=1
            )
        else:
            # Для бычьего: T1-T3 - сопротивление (верхняя), T2-T4 - поддержка (нижняя)
            # Линия сопротивления (T1 -> T3)
            fig.add_trace(
                go.Scatter(
                    x=[pattern_info['t1']['idx'], pattern_info['t3']['idx']],
                    y=[pattern_info['t1']['price'], pattern_info['t3']['price']],
                    mode='lines',
                    line=dict(color=base_color, width=2.5 if pattern_idx == 0 else 2, dash='dash'),
                    opacity=pattern_alpha,
                    name=f'Сопротивление #{pattern_idx+1}' if pattern_idx > 0 else 'Сопротивление (T1-T3)',
                    showlegend=(pattern_idx < 3),
                    hovertemplate=f'Сопротивление T1-T3 #{pattern_idx+1}<extra></extra>'
                ),
                row=1, col=1
            )
            
            # Линия поддержки (T2 -> T4)
            fig.add_trace(
                go.Scatter(
                    x=[pattern_info['t2']['idx'], pattern_info['t4']['idx']],
                    y=[pattern_info['t2']['price'], pattern_info['t4']['price']],
                    mode='lines',
                    line=dict(color=base_color, width=2 if pattern_idx == 0 else 1.5, dash='dash'),
                    opacity=pattern_alpha,
                    name=f'Поддержка #{pattern_idx+1}' if pattern_idx > 0 else 'Поддержка (T2-T4)',
                    showlegend=(pattern_idx < 3),
                    hovertemplate=f'Поддержка T2-T4 #{pattern_idx+1}<extra></extra>'
                ),
                row=1, col=1
            )
    
    # Настройка осей
    tick_step = max(1, len(candles_df) // 20)
    tick_indices = list(range(0, len(candles_df), tick_step))
    tick_times = []
    for i in tick_indices:
        time_val = candles_df.iloc[i]['time']
        if pd.notna(time_val):
            if isinstance(time_val, pd.Timestamp):
                tick_times.append(time_val.strftime('%m-%d %H:%M'))
            else:
                tick_times.append(str(time_val))
        else:
            tick_times.append('')
    
    # Заголовок
    bullish_count = sum(1 for is_bear in is_bearish_list if not is_bear)
    bearish_count = sum(1 for is_bear in is_bearish_list if is_bear)
    
    title = f'{ticker} ({timeframe}) - Найдено паттернов: {len(patterns)} (Бычьих: {bullish_count}, Медвежьих: {bearish_count})'
    
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
    print("=" * 80)
    print("ТЕСТИРОВАНИЕ МАТЕМАТИЧЕСКОГО СКАНЕРА НА АКЦИИ T")
    print("=" * 80)
    print()
    
    # Параметры
    ticker = "T"
    class_code = "TQBR"
    start_date = "2025-11-17"
    end_date = "2026-01-09"
    timeframe = "1h"
    
    print(f"📊 Параметры:")
    print(f"   • Тикер: {ticker}")
    print(f"   • Класс: {class_code}")
    print(f"   • Период: {start_date} - {end_date}")
    print(f"   • Таймфрейм: {timeframe}")
    print()
    
    # Инициализация сканера
    token = os.environ.get("TINKOFF_INVEST_TOKEN")
    if not token:
        print("❌ Токен не найден в переменных окружения!")
        return
    
    scanner = ComplexFlagScanner(token)
    
    # Загружаем данные
    print("📥 Загрузка данных...")
    try:
        df = scanner.get_candles_df(
            ticker=ticker,
            class_code=class_code,
            days_back=60,
            interval=TIMEFRAMES[timeframe]['interval']
        )
        
        if df.empty:
            print("❌ Данные не получены!")
            return
        
        # Фильтруем по датам
        df['time'] = pd.to_datetime(df['time'])
        df = df[(df['time'] >= start_date) & (df['time'] <= end_date)]
        
        if df.empty:
            print(f"❌ Нет данных за указанный период!")
            return
        
        print(f"   ✅ Загружено {len(df)} свечей")
        print(f"   📅 Период: {df['time'].min()} - {df['time'].max()}")
        print()
        
    except Exception as e:
        print(f"❌ Ошибка загрузки данных: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Поиск паттернов
    print("🔍 Поиск паттернов математическим сканером...")
    try:
        patterns = scanner.analyze(df, debug=False, timeframe=timeframe)
        
        print(f"   ✅ Найдено {len(patterns)} паттернов")
        print()
        
        # Группируем по типу
        bullish = [p for p in patterns if "BEARISH" not in p.get('pattern', '')]
        bearish = [p for p in patterns if "BEARISH" in p.get('pattern', '')]
        
        print(f"   📈 Бычьих (LONG): {len(bullish)}")
        print(f"   📉 Медвежьих (SHORT): {len(bearish)}")
        print()
        
    except Exception as e:
        print(f"❌ Ошибка поиска паттернов: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Визуализация
    print("📊 Создание визуализации...")
    try:
        if patterns:
            fig = visualize_patterns(df, patterns, ticker, timeframe)
            
            if fig:
                # Сохраняем HTML
                output_file = f"test_math_scanner_T_{start_date}_to_{end_date}.html"
                fig.write_html(output_file)
                print(f"   ✅ Визуализация сохранена: {output_file}")
                print()
                
                # Выводим информацию о паттернах
                print("=" * 80)
                print("НАЙДЕННЫЕ ПАТТЕРНЫ")
                print("=" * 80)
                print()
                
                for i, pattern_info in enumerate(patterns, 1):
                    is_bearish = "BEARISH" in pattern_info.get('pattern', '')
                    pattern_type = "Медвежий (SHORT)" if is_bearish else "Бычий (LONG)"
                    
                    print(f"{i}. {pattern_type}")
                    print(f"   T0: индекс={pattern_info['t0']['idx']}, цена={pattern_info['t0']['price']:.2f}, время={pattern_info['t0'].get('time', 'N/A')}")
                    print(f"   T1: индекс={pattern_info['t1']['idx']}, цена={pattern_info['t1']['price']:.2f}, время={pattern_info['t1'].get('time', 'N/A')}")
                    print(f"   T2: индекс={pattern_info['t2']['idx']}, цена={pattern_info['t2']['price']:.2f}, время={pattern_info['t2'].get('time', 'N/A')}")
                    print(f"   T3: индекс={pattern_info['t3']['idx']}, цена={pattern_info['t3']['price']:.2f}, время={pattern_info['t3'].get('time', 'N/A')}")
                    print(f"   T4: индекс={pattern_info['t4']['idx']}, цена={pattern_info['t4']['price']:.2f}, время={pattern_info['t4'].get('time', 'N/A')}")
                    print(f"   Высота флагштока: {pattern_info.get('pole_height', 0):.2f}")
                    print(f"   Текущая цена: {pattern_info.get('current_price', 0):.2f}")
                    print()
        else:
            # Создаем график без паттернов
            fig = make_subplots(rows=1, cols=1, subplot_titles=(f'{ticker} ({timeframe}) - Паттерны не найдены',))
            indices_x = list(range(len(df)))
            customdata = [[i, df.iloc[i]['time']] for i in range(len(df))]
            
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
            
            fig.update_layout(
                height=800,
                xaxis_rangeslider_visible=False,
                title=f'{ticker} ({timeframe}) - Паттерны не найдены (все кандидаты отклонены геометрическими правилами)',
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
            
            output_file = f"test_math_scanner_T_{start_date}_to_{end_date}.html"
            fig.write_html(output_file)
            print(f"   ✅ Визуализация сохранена: {output_file}")
            print()
            print("   ⚠️  Паттерны не найдены - все кандидаты отклонены из-за:")
            print("      • Нарушения геометрических правил (T2, T3, T4)")
            print("      • Пересечения линий T1-T3 или T2-T4 со свечами")
            print("      • Расхождения линий тренда")
            print()
    except Exception as e:
        print(f"❌ Ошибка визуализации: {e}")
        import traceback
        traceback.print_exc()
    
    print("=" * 80)
    print("✅ ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")
    print("=" * 80)


if __name__ == "__main__":
    main()
