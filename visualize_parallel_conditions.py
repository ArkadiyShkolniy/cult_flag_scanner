"""
Визуализация условий входа по параллельности для LONG и SHORT.
"""
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np

def create_parallel_entry_visualization():
    """
    Создает визуализацию условий входа по параллельности.
    """
    # Создаем пример данных для визуализации
    np.random.seed(42)
    
    # Генерируем данные для LONG паттерна
    n_candles = 100
    base_price = 100
    
    # Создаем тренд вверх (T0 -> T1)
    trend_up = np.linspace(base_price, base_price + 20, 30)
    
    # Создаем коррекцию вниз (T1 -> T2)
    correction_down = np.linspace(base_price + 20, base_price + 10, 15)
    
    # Создаем отскок вверх (T2 -> T3)
    bounce_up = np.linspace(base_price + 10, base_price + 18, 20)
    
    # Создаем финальную коррекцию (T3 -> T4)
    final_correction = np.linspace(base_price + 18, base_price + 12, 15)
    
    # Объединяем все части
    prices = np.concatenate([trend_up, correction_down, bounce_up, final_correction])
    
    # Добавляем шум
    noise = np.random.normal(0, 0.5, len(prices))
    prices = prices + noise
    
    # Создаем DataFrame
    df = pd.DataFrame({
        'open': prices,
        'high': prices + np.abs(np.random.normal(0, 1, len(prices))),
        'low': prices - np.abs(np.random.normal(0, 1, len(prices))),
        'close': prices + np.random.normal(0, 0.5, len(prices)),
        'volume': np.random.randint(1000, 10000, len(prices))
    })
    
    # Определяем точки паттерна
    t0_idx = 0
    t1_idx = 29
    t2_idx = 44
    t3_idx = 64
    t4_idx = 79
    
    t0_price = df.iloc[t0_idx]['close']
    t1_price = df.iloc[t1_idx]['close']
    t2_price = df.iloc[t2_idx]['close']
    t3_price = df.iloc[t3_idx]['close']
    t4_price = df.iloc[t4_idx]['close']
    
    # Создаем паттерн
    pattern_long = {
        'pattern': 'BULLISH_FLAG',
        't0': {'idx': t0_idx, 'price': t0_price},
        't1': {'idx': t1_idx, 'price': t1_price},
        't2': {'idx': t2_idx, 'price': t2_price},
        't3': {'idx': t3_idx, 'price': t3_price},
        't4': {'idx': t4_idx, 'price': t4_price}
    }
    
    # Вычисляем линии
    slope_1_3 = (t3_price - t1_price) / (t3_idx - t1_idx)
    slope_2_4 = (t4_price - t2_price) / (t4_idx - t2_idx)
    
    # Вычисляем цены линий для всех индексов
    line_1_3_prices = []
    line_2_4_prices = []
    for i in range(len(df)):
        # Линия 1-3
        if t1_idx <= i <= t3_idx:
            line_1_3_price = t1_price + slope_1_3 * (i - t1_idx)
            line_1_3_prices.append(line_1_3_price)
        else:
            line_1_3_prices.append(None)
        
        # Линия 2-4
        if t2_idx <= i <= t4_idx:
            line_2_4_price = t2_price + slope_2_4 * (i - t2_idx)
            line_2_4_prices.append(line_2_4_price)
        else:
            line_2_4_prices.append(None)
    
    # Текущая цена (выше open T4 для LONG)
    t4_open = df.iloc[t4_idx]['open']
    current_price_long = t4_open + 2  # Текущая цена выше open T4
    
    # Создаем subplot для LONG
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=('LONG: Условия входа по параллельности', 'SHORT: Условия входа по параллельности'),
        vertical_spacing=0.15,
        row_heights=[0.5, 0.5]
    )
    
    # === LONG ПАТТЕРН ===
    indices = list(range(len(df)))
    
    # Свечи
    fig.add_trace(
        go.Candlestick(
            x=indices,
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close'],
            name='Свечи (LONG)',
            increasing_line_color='green',
            decreasing_line_color='red'
        ),
        row=1, col=1
    )
    
    # Точки паттерна
    point_names = ['T0', 'T1', 'T2', 'T3', 'T4']
    point_indices = [t0_idx, t1_idx, t2_idx, t3_idx, t4_idx]
    point_prices = [t0_price, t1_price, t2_price, t3_price, t4_price]
    
    for name, idx, price in zip(point_names, point_indices, point_prices):
        fig.add_trace(
            go.Scatter(
                x=[idx],
                y=[price],
                mode='markers+text',
                marker=dict(size=15, color='yellow', symbol='star'),
                text=[name],
                textposition='top center',
                name=f'{name} (LONG)',
                showlegend=False
            ),
            row=1, col=1
        )
    
    # Линия 1-3
    line_1_3_x = [i for i in range(t1_idx, t3_idx + 1)]
    line_1_3_y = [t1_price + slope_1_3 * (i - t1_idx) for i in line_1_3_x]
    fig.add_trace(
        go.Scatter(
            x=line_1_3_x,
            y=line_1_3_y,
            mode='lines',
            name='Линия 1-3',
            line=dict(color='blue', width=2, dash='dash')
        ),
        row=1, col=1
    )
    
    # Линия 2-4
    line_2_4_x = [i for i in range(t2_idx, t4_idx + 1)]
    line_2_4_y = [t2_price + slope_2_4 * (i - t2_idx) for i in line_2_4_x]
    fig.add_trace(
        go.Scatter(
            x=line_2_4_x,
            y=line_2_4_y,
            mode='lines',
            name='Линия 2-4',
            line=dict(color='orange', width=2, dash='dash')
        ),
        row=1, col=1
    )
    
    # Open T4
    fig.add_trace(
        go.Scatter(
            x=[t4_idx],
            y=[t4_open],
            mode='markers',
            marker=dict(size=12, color='purple', symbol='circle'),
            name='Open T4 (LONG)',
            showlegend=True
        ),
        row=1, col=1
    )
    
    # Текущая цена (для LONG)
    fig.add_trace(
        go.Scatter(
            x=[t4_idx],
            y=[current_price_long],
            mode='markers+text',
            marker=dict(size=15, color='green', symbol='triangle-up'),
            text=['Текущая цена<br>(ВХОД LONG)'],
            textposition='top center',
            name='Текущая цена (LONG)',
            showlegend=True
        ),
        row=1, col=1
    )
    
    # Аннотации для LONG
    annotations_long = [
        dict(
            x=t4_idx,
            y=current_price_long + 3,
            xref='x',
            yref='y',
            text='✅ LONG: current_price > open T4',
            showarrow=True,
            arrowhead=2,
            arrowcolor='green',
            bgcolor='rgba(0, 255, 0, 0.3)',
            bordercolor='green',
            borderwidth=2
        ),
        dict(
            x=(t1_idx + t3_idx) / 2,
            y=(t1_price + t3_price) / 2 + 2,
            xref='x',
            yref='y',
            text=f'Линия 1-3<br>slope={slope_1_3:.3f}',
            showarrow=False,
            bgcolor='rgba(0, 0, 255, 0.2)',
            bordercolor='blue',
            borderwidth=1
        ),
        dict(
            x=(t2_idx + t4_idx) / 2,
            y=(t2_price + t4_price) / 2 - 2,
            xref='x',
            yref='y',
            text=f'Линия 2-4<br>slope={slope_2_4:.3f}',
            showarrow=False,
            bgcolor='rgba(255, 165, 0, 0.2)',
            bordercolor='orange',
            borderwidth=1
        ),
        dict(
            x=t2_idx,
            y=t2_price + 1,
            xref='x',
            yref='y',
            text='T4 < T2 ✅',
            showarrow=True,
            arrowhead=2,
            arrowcolor='green',
            bgcolor='rgba(0, 255, 0, 0.2)',
            bordercolor='green',
            borderwidth=1
        )
    ]
    
    # === SHORT ПАТТЕРН ===
    # Создаем данные для SHORT (зеркально)
    base_price_short = 120
    
    # Тренд вниз (T0 -> T1)
    trend_down = np.linspace(base_price_short, base_price_short - 20, 30)
    
    # Коррекция вверх (T1 -> T2)
    correction_up = np.linspace(base_price_short - 20, base_price_short - 10, 15)
    
    # Отскок вниз (T2 -> T3)
    bounce_down = np.linspace(base_price_short - 10, base_price_short - 18, 20)
    
    # Финальная коррекция вверх (T3 -> T4)
    final_correction_up = np.linspace(base_price_short - 18, base_price_short - 12, 15)
    
    prices_short = np.concatenate([trend_down, correction_up, bounce_down, final_correction_up])
    noise_short = np.random.normal(0, 0.5, len(prices_short))
    prices_short = prices_short + noise_short
    
    df_short = pd.DataFrame({
        'open': prices_short,
        'high': prices_short + np.abs(np.random.normal(0, 1, len(prices_short))),
        'low': prices_short - np.abs(np.random.normal(0, 1, len(prices_short))),
        'close': prices_short + np.random.normal(0, 0.5, len(prices_short)),
        'volume': np.random.randint(1000, 10000, len(prices_short))
    })
    
    t0_price_short = df_short.iloc[t0_idx]['close']
    t1_price_short = df_short.iloc[t1_idx]['close']
    t2_price_short = df_short.iloc[t2_idx]['close']
    t3_price_short = df_short.iloc[t3_idx]['close']
    t4_price_short = df_short.iloc[t4_idx]['close']
    
    # Вычисляем линии для SHORT
    slope_1_3_short = (t3_price_short - t1_price_short) / (t3_idx - t1_idx)
    slope_2_4_short = (t4_price_short - t2_price_short) / (t4_idx - t2_idx)
    
    # Свечи SHORT
    fig.add_trace(
        go.Candlestick(
            x=indices,
            open=df_short['open'],
            high=df_short['high'],
            low=df_short['low'],
            close=df_short['close'],
            name='Свечи (SHORT)',
            increasing_line_color='green',
            decreasing_line_color='red'
        ),
        row=2, col=1
    )
    
    # Точки паттерна SHORT
    point_prices_short = [t0_price_short, t1_price_short, t2_price_short, t3_price_short, t4_price_short]
    for name, idx, price in zip(point_names, point_indices, point_prices_short):
        fig.add_trace(
            go.Scatter(
                x=[idx],
                y=[price],
                mode='markers+text',
                marker=dict(size=15, color='yellow', symbol='star'),
                text=[name],
                textposition='top center',
                name=f'{name} (SHORT)',
                showlegend=False
            ),
            row=2, col=1
        )
    
    # Линия 1-3 SHORT
    line_1_3_y_short = [t1_price_short + slope_1_3_short * (i - t1_idx) for i in line_1_3_x]
    fig.add_trace(
        go.Scatter(
            x=line_1_3_x,
            y=line_1_3_y_short,
            mode='lines',
            name='Линия 1-3 (SHORT)',
            line=dict(color='blue', width=2, dash='dash'),
            showlegend=False
        ),
        row=2, col=1
    )
    
    # Линия 2-4 SHORT
    line_2_4_y_short = [t2_price_short + slope_2_4_short * (i - t2_idx) for i in line_2_4_x]
    fig.add_trace(
        go.Scatter(
            x=line_2_4_x,
            y=line_2_4_y_short,
            mode='lines',
            name='Линия 2-4 (SHORT)',
            line=dict(color='orange', width=2, dash='dash'),
            showlegend=False
        ),
        row=2, col=1
    )
    
    # Open T4 SHORT
    t4_open_short = df_short.iloc[t4_idx]['open']
    fig.add_trace(
        go.Scatter(
            x=[t4_idx],
            y=[t4_open_short],
            mode='markers',
            marker=dict(size=12, color='purple', symbol='circle'),
            name='Open T4 (SHORT)',
            showlegend=False
        ),
        row=2, col=1
    )
    
    # Текущая цена (для SHORT - ниже open T4)
    current_price_short = t4_open_short - 2
    fig.add_trace(
        go.Scatter(
            x=[t4_idx],
            y=[current_price_short],
            mode='markers+text',
            marker=dict(size=15, color='red', symbol='triangle-down'),
            text=['Текущая цена<br>(ВХОД SHORT)'],
            textposition='bottom center',
            name='Текущая цена (SHORT)',
            showlegend=False
        ),
        row=2, col=1
    )
    
    # Аннотации для SHORT
    annotations_short = [
        dict(
            x=t4_idx,
            y=current_price_short - 3,
            xref='x2',
            yref='y2',
            text='✅ SHORT: current_price < open T4',
            showarrow=True,
            arrowhead=2,
            arrowcolor='red',
            bgcolor='rgba(255, 0, 0, 0.3)',
            bordercolor='red',
            borderwidth=2
        ),
        dict(
            x=(t1_idx + t3_idx) / 2,
            y=(t1_price_short + t3_price_short) / 2 - 2,
            xref='x2',
            yref='y2',
            text=f'Линия 1-3<br>slope={slope_1_3_short:.3f}',
            showarrow=False,
            bgcolor='rgba(0, 0, 255, 0.2)',
            bordercolor='blue',
            borderwidth=1
        ),
        dict(
            x=(t2_idx + t4_idx) / 2,
            y=(t2_price_short + t4_price_short) / 2 + 2,
            xref='x2',
            yref='y2',
            text=f'Линия 2-4<br>slope={slope_2_4_short:.3f}',
            showarrow=False,
            bgcolor='rgba(255, 165, 0, 0.2)',
            bordercolor='orange',
            borderwidth=1
        ),
        dict(
            x=t2_idx,
            y=t2_price_short - 1,
            xref='x2',
            yref='y2',
            text='T4 > T2 ✅',
            showarrow=True,
            arrowhead=2,
            arrowcolor='red',
            bgcolor='rgba(255, 0, 0, 0.2)',
            bordercolor='red',
            borderwidth=1
        )
    ]
    
    # Обновляем layout
    fig.update_layout(
        height=1200,
        title_text='Условия входа по параллельности: LONG и SHORT',
        title_x=0.5,
        template='plotly_dark',
        showlegend=True,
        hovermode='x unified',
        annotations=annotations_long + annotations_short
    )
    
    # Обновляем оси
    fig.update_xaxes(title_text='Индекс свечи', row=1, col=1)
    fig.update_xaxes(title_text='Индекс свечи', row=2, col=1)
    fig.update_yaxes(title_text='Цена (LONG)', row=1, col=1)
    fig.update_yaxes(title_text='Цена (SHORT)', row=2, col=1)
    
    # Сохраняем
    output_file = 'parallel_entry_conditions_visualization.html'
    fig.write_html(output_file)
    print(f"✅ Визуализация сохранена: {output_file}")
    print()
    print("=" * 70)
    print("📊 УСЛОВИЯ ВХОДА ПО ПАРАЛЛЕЛЬНОСТИ")
    print("=" * 70)
    print()
    print("LONG:")
    print("  1. T4 формируется (current_idx >= t4_idx, ±1 свеча)")
    print("  2. Линии 1-3 и 2-4 параллельны (отклонение <= 10%)")
    print("  3. T4 < T2 (нижняя точка коррекции)")
    print("  4. Текущая цена > open T4 ✅")
    print()
    print("SHORT:")
    print("  1. T4 формируется (current_idx >= t4_idx, ±1 свеча)")
    print("  2. Линии 1-3 и 2-4 параллельны (отклонение <= 10%)")
    print("  3. T4 > T2 (верхняя точка коррекции)")
    print("  4. Текущая цена < open T4 ✅")
    print()
    print("=" * 70)
    
    return fig

if __name__ == "__main__":
    create_parallel_entry_visualization()
