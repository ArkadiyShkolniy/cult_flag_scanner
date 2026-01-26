"""
Утилиты для отправки сообщений и графиков в Telegram
"""

import os
import io
import requests
from datetime import datetime
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from PIL import Image
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def create_flag_chart_image(df, pattern_info, ticker, timeframe):
    """
    Создает изображение графика с отмеченным паттерном для Telegram
    
    Args:
        df: DataFrame со свечами
        pattern_info: Информация о паттерне (с точками T0-T4)
        ticker: Тикер инструмента
        timeframe: Таймфрейм
        
    Returns:
        BytesIO объект с изображением
    """
    try:
        # Используем индексы для непрерывного графика
        indices_x = list(range(len(df)))
        
        # Создаем subplot
        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.03,
            row_heights=[0.7, 0.3],
            subplot_titles=(f'{ticker} ({timeframe}) - Паттерн "Флаг"', 'Объем')
        )
        
        # Свечи
        fig.add_trace(
            go.Candlestick(
                x=indices_x,
                open=df['open'],
                high=df['high'],
                low=df['low'],
                close=df['close'],
                name='Свечи'
            ),
            row=1, col=1
        )
        
        # Отмеченные точки
        point_colors = {
            'T0': 'lime',
            'T1': 'red',
            'T2': 'cyan',
            'T3': 'orange',
            'T4': 'magenta'
        }
        
        point_symbols = {
            'T0': 'circle',
            'T1': 'diamond',
            'T2': 'circle',
            'T3': 'diamond',
            'T4': 'circle'
        }
        
        for point_name in ['T0', 'T1', 'T2', 'T3', 'T4']:
            if point_name.lower() in pattern_info:
                point_data = pattern_info[point_name.lower()]
                fig.add_trace(
                    go.Scatter(
                        x=[point_data['idx']],
                        y=[point_data['price']],
                        mode='markers+text',
                        marker=dict(
                            size=15,
                            color=point_colors[point_name],
                            symbol=point_symbols[point_name],
                            line=dict(width=2, color='white')
                        ),
                        text=[point_name],
                        textposition='top center',
                        name=point_name,
                        showlegend=True
                    ),
                    row=1, col=1
                )
        
        # Линии между точками
        if 't0' in pattern_info and 't1' in pattern_info:
            fig.add_trace(
                go.Scatter(
                    x=[pattern_info['t0']['idx'], pattern_info['t1']['idx']],
                    y=[pattern_info['t0']['price'], pattern_info['t1']['price']],
                    mode='lines',
                    line=dict(color='lime', width=3, dash='solid'),
                    name='Флагшток (T0-T1)',
                    showlegend=True
                ),
                row=1, col=1
            )
        
        if 't1' in pattern_info and 't3' in pattern_info:
            fig.add_trace(
                go.Scatter(
                    x=[pattern_info['t1']['idx'], pattern_info['t3']['idx']],
                    y=[pattern_info['t1']['price'], pattern_info['t3']['price']],
                    mode='lines',
                    line=dict(color='red', width=2, dash='dash'),
                    name='Линия T1-T3',
                    showlegend=True
                ),
                row=1, col=1
            )
        
        if 't2' in pattern_info and 't4' in pattern_info:
            fig.add_trace(
                go.Scatter(
                    x=[pattern_info['t2']['idx'], pattern_info['t4']['idx']],
                    y=[pattern_info['t2']['price'], pattern_info['t4']['price']],
                    mode='lines',
                    line=dict(color='cyan', width=2, dash='dash'),
                    name='Линия T2-T4',
                    showlegend=True
                ),
                row=1, col=1
            )
        
        # Объем
        colors = ['red' if df.iloc[i]['close'] < df.iloc[i]['open'] else 'green' 
                  for i in range(len(df))]
        fig.add_trace(
            go.Bar(
                x=indices_x,
                y=df['volume'],
                marker_color=colors,
                name='Объем'
            ),
            row=2, col=1
        )
        
        # Настройка меток оси X
        tick_step = max(1, len(df) // 15)
        tick_indices = list(range(0, len(df), tick_step))
        tick_times = []
        for i in tick_indices:
            time_val = df.iloc[i]['time']
            if pd.isna(time_val):
                tick_times.append('')
            elif isinstance(time_val, pd.Timestamp):
                if timeframe == '1d':
                    tick_times.append(time_val.strftime('%Y-%m-%d'))
                else:
                    tick_times.append(time_val.strftime('%m-%d %H:%M'))
            else:
                tick_times.append(str(time_val))
        
        fig.update_layout(
            height=800,
            xaxis_rangeslider_visible=False,
            title=f"{ticker} ({timeframe}) - Паттерн 'Флаг'",
            template="plotly_dark",
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
        
        # Конвертируем Plotly в изображение через matplotlib
        # Сначала сохраняем как HTML временно, затем конвертируем
        # Альтернатива: используем kaleido если установлен, иначе matplotlib
        
        # Простой способ: используем matplotlib для создания графика
        return create_matplotlib_chart(df, pattern_info, ticker, timeframe)
        
    except Exception as e:
        print(f"❌ Ошибка создания графика: {e}")
        import traceback
        traceback.print_exc()
        return None


def create_matplotlib_chart(df, pattern_info, ticker, timeframe):
    """Создает график через matplotlib (более надежно для Docker)"""
    try:
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), height_ratios=[3, 1])
        fig.patch.set_facecolor('black')
        ax1.set_facecolor('black')
        ax2.set_facecolor('black')
        
        # Берем последние 100 свечей для отображения
        df_plot = df.tail(100).copy() if len(df) > 100 else df.copy()
        indices = list(range(len(df_plot)))
        
        # Свечи
        for i, (idx, row) in enumerate(df_plot.iterrows()):
            color = 'green' if row['close'] >= row['open'] else 'red'
            # Тело свечи
            body_height = abs(row['close'] - row['open'])
            body_bottom = min(row['open'], row['close'])
            ax1.bar(i, body_height, bottom=body_bottom, width=0.6, color=color, edgecolor=color)
            # Тени
            ax1.plot([i, i], [row['low'], row['high']], color=color, linewidth=1)
        
        # Точки паттерна
        point_colors = {'T0': 'lime', 'T1': 'red', 'T2': 'cyan', 'T3': 'orange', 'T4': 'magenta'}
        point_markers = {'T0': 'o', 'T1': 'D', 'T2': 'o', 'T3': 'D', 'T4': 'o'}
        
        # Определяем смещение индексов (если берем последние N свечей)
        offset = len(df) - len(df_plot) if len(df) > len(df_plot) else 0
        
        for point_name in ['T0', 'T1', 'T2', 'T3', 'T4']:
            if point_name.lower() in pattern_info:
                point_data = pattern_info[point_name.lower()]
                point_abs_idx = point_data['idx']  # Абсолютный индекс в исходном df
                
                # Вычисляем индекс в df_plot
                point_idx_in_plot = point_abs_idx - offset
                
                # Проверяем что точка попадает в диапазон df_plot
                if 0 <= point_idx_in_plot < len(df_plot):
                    ax1.scatter(point_idx_in_plot, point_data['price'], 
                              s=200, c=point_colors[point_name], 
                              marker=point_markers[point_name], 
                              edgecolors='white', linewidths=2, zorder=5)
                    ax1.annotate(point_name, 
                               (point_idx_in_plot, point_data['price']),
                               xytext=(0, 15), textcoords='offset points',
                               fontsize=12, fontweight='bold', color='white')
        
        # Линии
        if 't0' in pattern_info and 't1' in pattern_info:
            t0_abs_idx = pattern_info['t0']['idx']
            t1_abs_idx = pattern_info['t1']['idx']
            t0_idx = t0_abs_idx - offset
            t1_idx = t1_abs_idx - offset
            
            if 0 <= t0_idx < len(df_plot) and 0 <= t1_idx < len(df_plot):
                ax1.plot([t0_idx, t1_idx], 
                        [pattern_info['t0']['price'], pattern_info['t1']['price']],
                        color='lime', linewidth=3, linestyle='-', label='Флагшток')
        
        if 't1' in pattern_info and 't3' in pattern_info:
            t1_abs_idx = pattern_info['t1']['idx']
            t3_abs_idx = pattern_info['t3']['idx']
            t1_idx = t1_abs_idx - offset
            t3_idx = t3_abs_idx - offset
            
            if 0 <= t1_idx < len(df_plot) and 0 <= t3_idx < len(df_plot):
                ax1.plot([t1_idx, t3_idx], 
                        [pattern_info['t1']['price'], pattern_info['t3']['price']],
                        color='red', linewidth=2, linestyle='--', label='T1-T3')
        
        if 't2' in pattern_info and 't4' in pattern_info:
            t2_abs_idx = pattern_info['t2']['idx']
            t4_abs_idx = pattern_info['t4']['idx']
            t2_idx = t2_abs_idx - offset
            t4_idx = t4_abs_idx - offset
            
            if 0 <= t2_idx < len(df_plot) and 0 <= t4_idx < len(df_plot):
                ax1.plot([t2_idx, t4_idx], 
                        [pattern_info['t2']['price'], pattern_info['t4']['price']],
                        color='cyan', linewidth=2, linestyle='--', label='T2-T4')
        
        # Объем
        colors_vol = ['red' if df_plot.iloc[i]['close'] < df_plot.iloc[i]['open'] else 'green' 
                     for i in range(len(df_plot))]
        ax2.bar(indices, df_plot['volume'], color=colors_vol, alpha=0.6)
        
        ax1.set_title(f'{ticker} ({timeframe}) - Паттерн "Флаг"', color='white', fontsize=14, fontweight='bold')
        ax1.set_ylabel('Цена', color='white')
        ax1.tick_params(colors='white')
        ax1.grid(True, alpha=0.3)
        ax1.legend(loc='upper left', facecolor='black', edgecolor='white', labelcolor='white')
        
        ax2.set_ylabel('Объем', color='white')
        ax2.set_xlabel('Время', color='white')
        ax2.tick_params(colors='white')
        ax2.grid(True, alpha=0.3)
        
        # Сохраняем в BytesIO
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=100, facecolor='black', bbox_inches='tight')
        buf.seek(0)
        plt.close(fig)
        
        return buf
        
    except Exception as e:
        print(f"❌ Ошибка создания matplotlib графика: {e}")
        import traceback
        traceback.print_exc()
        return None


def send_telegram_signal(message: str, image_buf=None):
    """Отправка сообщения и картинки в Telegram"""
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    
    if not bot_token or not chat_id:
        print("⚠️ Telegram токены не настроены (TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)")
        return False

    try:
        if image_buf:
            # Отправка ФОТО
            url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
            files = {'photo': ('chart.png', image_buf, 'image/png')}
            data = {
                "chat_id": chat_id, 
                "caption": message, 
                "parse_mode": "HTML"
            }
            resp = requests.post(url, data=data, files=files, timeout=10)
        else:
            # Отправка ТЕКСТА
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            data = {
                "chat_id": chat_id, 
                "text": message, 
                "parse_mode": "HTML"
            }
            resp = requests.post(url, json=data, timeout=5)

        if resp.status_code == 200:
            return True
        else:
            print(f"❌ Telegram Error: {resp.status_code} - {resp.text}")
            return False
            
    except Exception as e:
        print(f"❌ Telegram Connection Error: {e}")
        return False

