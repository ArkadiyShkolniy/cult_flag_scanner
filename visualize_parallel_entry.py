"""
Визуализация логики входа в позицию на основе параллельности линий 1-3 и 2-4
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta

def create_parallel_entry_visualization():
    """
    Создает визуализацию логики входа по параллельности линий
    """
    
    # Создаем пример данных для бычьего паттерна
    # T0: 280, T1: 310, T2: 295, T3: 305, T4: 290
    
    # Генерируем индексы для точек
    t0_idx = 0
    t1_idx = 20
    t2_idx = 35
    t3_idx = 50
    t4_idx = 65
    
    # Цены точек
    t0_price = 280
    t1_price = 310
    t2_price = 295
    t3_price = 305
    t4_price = 290
    
    # Создаем DataFrame со свечами
    indices = list(range(80))
    dates = [datetime.now() + timedelta(hours=i) for i in indices]
    
    # Генерируем цены свечей, которые формируют паттерн
    candles = []
    for i in indices:
        if i <= t0_idx:
            price = t0_price + np.random.uniform(-2, 2)
        elif i <= t1_idx:
            # Восходящий тренд T0-T1
            progress = (i - t0_idx) / (t1_idx - t0_idx)
            base_price = t0_price + (t1_price - t0_price) * progress
            price = base_price + np.random.uniform(-3, 3)
        elif i <= t2_idx:
            # Коррекция T1-T2
            progress = (i - t1_idx) / (t2_idx - t1_idx)
            base_price = t1_price + (t2_price - t1_price) * progress
            price = base_price + np.random.uniform(-2, 2)
        elif i <= t3_idx:
            # Отскок T2-T3
            progress = (i - t2_idx) / (t3_idx - t2_idx)
            base_price = t2_price + (t3_price - t2_price) * progress
            price = base_price + np.random.uniform(-2, 2)
        elif i <= t4_idx:
            # Коррекция T3-T4
            progress = (i - t3_idx) / (t4_idx - t3_idx)
            base_price = t3_price + (t4_price - t3_price) * progress
            price = base_price + np.random.uniform(-2, 2)
        else:
            # После T4 - отскок вверх (зеленая свеча на входе)
            if i == t4_idx + 1:
                price = t4_price + 5  # Зеленая свеча - отскок
            else:
                price = t4_price + 5 + (i - t4_idx - 1) * 0.5 + np.random.uniform(-1, 1)
        
        # Создаем свечу
        open_price = price
        close_price = price + np.random.uniform(-2, 2)
        high_price = max(open_price, close_price) + abs(np.random.uniform(0, 2))
        low_price = min(open_price, close_price) - abs(np.random.uniform(0, 2))
        
        # На T4 делаем зеленую свечу (вход)
        if i == t4_idx:
            close_price = open_price + 3  # Зеленая свеча
        
        candles.append({
            'time': dates[i],
            'open': open_price,
            'high': high_price,
            'low': low_price,
            'close': close_price,
            'volume': np.random.uniform(1000, 5000)
        })
    
    df = pd.DataFrame(candles)
    
    # Создаем график
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.7, 0.3],
        subplot_titles=('Логика входа по параллельности линий 1-3 и 2-4', 'Объем')
    )
    
    # Свечи
    colors = ['red' if df.iloc[i]['close'] < df.iloc[i]['open'] else 'green' 
              for i in range(len(df))]
    
    fig.add_trace(
        go.Candlestick(
            x=indices,
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close'],
            name='Свечи',
            increasing_line_color='green',
            decreasing_line_color='red'
        ),
        row=1, col=1
    )
    
    # Точки паттерна
    point_colors = {'T0': 'lime', 'T1': 'red', 'T2': 'cyan', 'T3': 'orange', 'T4': 'magenta'}
    point_symbols = {'T0': 'circle', 'T1': 'diamond', 'T2': 'circle', 'T3': 'diamond', 'T4': 'circle'}
    
    points = {
        'T0': {'idx': t0_idx, 'price': t0_price},
        'T1': {'idx': t1_idx, 'price': t1_price},
        'T2': {'idx': t2_idx, 'price': t2_price},
        'T3': {'idx': t3_idx, 'price': t3_price},
        'T4': {'idx': t4_idx, 'price': t4_price}
    }
    
    for point_name, point_data in points.items():
        fig.add_trace(
            go.Scatter(
                x=[point_data['idx']],
                y=[point_data['price']],
                mode='markers',
                marker=dict(
                    symbol=point_symbols[point_name],
                    size=15,
                    color=point_colors[point_name],
                    line=dict(width=2, color='white')
                ),
                name=point_name,
                text=[point_name],
                textposition="top center",
                hovertemplate=f'<b>{point_name}</b><br>Индекс: {point_data["idx"]}<br>Цена: {point_data["price"]:.2f}<extra></extra>'
            ),
            row=1, col=1
        )
    
    # Линия 1-3 (T1-T3)
    line_1_3_x = [t1_idx, t3_idx]
    line_1_3_y = [t1_price, t3_price]
    fig.add_trace(
        go.Scatter(
            x=line_1_3_x,
            y=line_1_3_y,
            mode='lines',
            line=dict(color='yellow', width=2, dash='dash'),
            name='Линия 1-3 (T1-T3)',
            hovertemplate='Линия 1-3<extra></extra>'
        ),
        row=1, col=1
    )
    
    # Линия 2-4 (T2-T4)
    line_2_4_x = [t2_idx, t4_idx]
    line_2_4_y = [t2_price, t4_price]
    fig.add_trace(
        go.Scatter(
            x=line_2_4_x,
            y=line_2_4_y,
            mode='lines',
            line=dict(color='purple', width=2, dash='dash'),
            name='Линия 2-4 (T2-T4)',
            hovertemplate='Линия 2-4<extra></extra>'
        ),
        row=1, col=1
    )
    
    # Вычисляем slope для проверки параллельности
    slope_1_3 = (t3_price - t1_price) / (t3_idx - t1_idx) if (t3_idx - t1_idx) != 0 else 0
    slope_2_4 = (t4_price - t2_price) / (t4_idx - t2_idx) if (t4_idx - t2_idx) != 0 else 0
    
    # Продлеваем линии для визуализации параллельности
    extend_range = 10
    line_1_3_extended_x = [t1_idx - extend_range, t3_idx + extend_range]
    line_1_3_extended_y = [
        t1_price - slope_1_3 * extend_range,
        t3_price + slope_1_3 * extend_range
    ]
    fig.add_trace(
        go.Scatter(
            x=line_1_3_extended_x,
            y=line_1_3_extended_y,
            mode='lines',
            line=dict(color='yellow', width=1, dash='dot'),
            name='Линия 1-3 (продолжение)',
            showlegend=False,
            hoverinfo='skip'
        ),
        row=1, col=1
    )
    
    line_2_4_extended_x = [t2_idx - extend_range, t4_idx + extend_range]
    line_2_4_extended_y = [
        t2_price - slope_2_4 * extend_range,
        t4_price + slope_2_4 * extend_range
    ]
    fig.add_trace(
        go.Scatter(
            x=line_2_4_extended_x,
            y=line_2_4_extended_y,
            mode='lines',
            line=dict(color='purple', width=1, dash='dot'),
            name='Линия 2-4 (продолжение)',
            showlegend=False,
            hoverinfo='skip'
        ),
        row=1, col=1
    )
    
    # Маркер входа (на T4)
    entry_idx = t4_idx
    entry_price = t4_price
    fig.add_trace(
        go.Scatter(
            x=[entry_idx],
            y=[entry_price],
            mode='markers',
            marker=dict(
                symbol='star',
                size=20,
                color='white',
                line=dict(width=2, color='green')
            ),
            name='ВХОД (T4)',
            text=['ВХОД'],
            textposition="top center",
            hovertemplate='<b>ВХОД В ПОЗИЦИЮ</b><br>Индекс: {}<br>Цена: {:.2f}<extra></extra>'.format(entry_idx, entry_price)
        ),
        row=1, col=1
    )
    
    # Объем
    fig.add_trace(
        go.Bar(
            x=indices,
            y=df['volume'],
            name='Объем',
            marker_color=colors
        ),
        row=2, col=1
    )
    
    # Вычисляем информацию о параллельности
    avg_slope = (abs(slope_1_3) + abs(slope_2_4)) / 2
    diff = abs(slope_1_3 - slope_2_4)
    relative_diff = diff / avg_slope if avg_slope != 0 else 0
    is_parallel = relative_diff <= 0.1
    
    # Условия для LONG
    t4_below_t2 = t4_price < t2_price
    is_green_candle = df.iloc[t4_idx]['close'] > df.iloc[t4_idx]['open']
    
    # Обновляем layout
    fig.update_layout(
        height=900,
        showlegend=True,
        hovermode='x unified',
        xaxis_rangeslider_visible=False,
        template="plotly_dark",
        title=dict(
            text="<b>Логика входа по параллельности линий 1-3 и 2-4 (LONG)</b><br>" +
                 f"<span style='font-size:12px'>Slope 1-3: {slope_1_3:.4f} | Slope 2-4: {slope_2_4:.4f} | " +
                 f"Отклонение: {relative_diff*100:.2f}% | Параллельны: {'✅' if is_parallel else '❌'}</span>",
            x=0.5,
            xanchor='center'
        ),
        xaxis=dict(
            title='Индекс свечи',
            showgrid=True,
            gridcolor='rgba(128, 128, 128, 0.2)'
        ),
        xaxis2=dict(
            title='Индекс свечи',
            showgrid=True,
            gridcolor='rgba(128, 128, 128, 0.2)'
        ),
        yaxis=dict(
            title_text="Цена",
            showgrid=True,
            gridcolor='rgba(128, 128, 128, 0.2)'
        ),
        yaxis2=dict(
            title_text="Объем",
            showgrid=True,
            gridcolor='rgba(128, 128, 128, 0.2)'
        )
    )
    
    # Добавляем аннотации с условиями
    conditions_text = (
        f"<b>УСЛОВИЯ ВХОДА (LONG):</b><br>"
        f"1. Линии 1-3 и 2-4 параллельны: {'✅' if is_parallel else '❌'}<br>"
        f"2. T4 ниже T2: {'✅' if t4_below_t2 else '❌'} ({t4_price:.2f} < {t2_price:.2f})<br>"
        f"3. Зеленая свеча на T4: {'✅' if is_green_candle else '❌'}<br>"
        f"<br><b>РЕЗУЛЬТАТ:</b> {'✅ ВХОД РАЗРЕШЕН' if (is_parallel and t4_below_t2 and is_green_candle) else '❌ ВХОД ЗАПРЕЩЕН'}"
    )
    
    fig.add_annotation(
        text=conditions_text,
        xref="paper", yref="paper",
        x=0.02, y=0.98,
        xanchor="left", yanchor="top",
        bgcolor="rgba(0,0,0,0.7)",
        bordercolor="green",
        borderwidth=2,
        font=dict(size=11, color="white"),
        showarrow=False
    )
    
    # Сохраняем график
    output_file = "parallel_entry_visualization.html"
    fig.write_html(output_file)
    print(f"✅ График сохранен: {output_file}")
    print(f"\n📊 Информация:")
    print(f"   Slope 1-3: {slope_1_3:.4f}")
    print(f"   Slope 2-4: {slope_2_4:.4f}")
    print(f"   Отклонение: {relative_diff*100:.2f}%")
    print(f"   Параллельны: {'✅ Да' if is_parallel else '❌ Нет'}")
    print(f"   T4 < T2: {'✅ Да' if t4_below_t2 else '❌ Нет'} ({t4_price:.2f} < {t2_price:.2f})")
    print(f"   Зеленая свеча: {'✅ Да' if is_green_candle else '❌ Нет'}")
    print(f"   ВХОД: {'✅ РАЗРЕШЕН' if (is_parallel and t4_below_t2 and is_green_candle) else '❌ ЗАПРЕЩЕН'}")
    
    return fig

if __name__ == "__main__":
    fig = create_parallel_entry_visualization()
    print("\n✅ Визуализация создана!")
