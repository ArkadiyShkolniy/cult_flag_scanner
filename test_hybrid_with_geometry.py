#!/usr/bin/env python3
"""
Тестирование гибридного подхода с валидацией геометрии
Математический сканер находит паттерны с правильной геометрией
NN фильтрует по уверенности
"""
import os
import sys
from pathlib import Path
from datetime import datetime, timezone
from dotenv import load_dotenv
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

sys.path.insert(0, str(Path(__file__).parent))

from scanners.combined_scanner import ComplexFlagScanner
from scanners.hybrid_scanner import HybridFlagScanner
from neural_network.predict_keypoints import predict_with_sliding_window
from config import TIMEFRAMES

load_dotenv()


def create_interactive_chart(df, patterns, ticker, timeframe, title_suffix=""):
    """Создает интерактивный график с паттернами"""
    fig = make_subplots(rows=1, cols=1, shared_xaxes=True, vertical_spacing=0.03)
    
    # Свечной график
    customdata = [[i, df.iloc[i]['time']] for i in range(len(df))]
    fig.add_trace(
        go.Candlestick(
            x=list(range(len(df))),
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
    
    # Отрисовка паттернов
    pattern_colors = ['lime', 'yellow', 'cyan', 'magenta', 'orange']
    point_colors = {'T0': 'lime', 'T1': 'red', 'T2': 'cyan', 'T3': 'orange', 'T4': 'magenta'}
    point_symbols = {'T0': 'circle', 'T1': 'diamond', 'T2': 'circle', 'T3': 'diamond', 'T4': 'circle'}
    
    for i, pattern in enumerate(patterns):
        pattern_type = "Бычий" if 'BEARISH' not in pattern.get('pattern', '') else "Медвежий"
        color = pattern_colors[i % len(pattern_colors)]
        
        # Точки
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
                            marker=dict(size=12, color=point_colors[point_name], symbol=point_symbols[point_name], line=dict(width=2, color='white')),
                            text=[f'{point_name}#{i+1}'],
                            textposition='top center',
                            name=f'{point_name} {pattern_type} #{i+1}',
                            showlegend=False,
                            hovertemplate=f'<b>{point_name}</b><br>Индекс: {idx}<br>Цена: {price:.2f}<extra></extra>'
                        ),
                        row=1, col=1
                    )
        
        # Линии
        if all(p in pattern for p in ['t0', 't1', 't2', 't3', 't4']):
            t0_idx = pattern['t0']['idx']
            t1_idx = pattern['t1']['idx']
            t2_idx = pattern['t2']['idx']
            t3_idx = pattern['t3']['idx']
            t4_idx = pattern['t4']['idx']
            
            # Флагшток
            fig.add_trace(
                go.Scatter(
                    x=[t0_idx, t1_idx],
                    y=[pattern['t0']['price'], pattern['t1']['price']],
                    mode='lines',
                    line=dict(color=color, width=3, dash='solid'),
                    showlegend=False
                ),
                row=1, col=1
            )
            # Линия 1-3
            fig.add_trace(
                go.Scatter(
                    x=[t1_idx, t3_idx],
                    y=[pattern['t1']['price'], pattern['t3']['price']],
                    mode='lines',
                    line=dict(color=color, width=2, dash='dash'),
                    showlegend=False
                ),
                row=1, col=1
            )
            # Линия 2-4
            fig.add_trace(
                go.Scatter(
                    x=[t2_idx, t4_idx],
                    y=[pattern['t2']['price'], pattern['t4']['price']],
                    mode='lines',
                    line=dict(color=color, width=2, dash='dash'),
                    showlegend=False
                ),
                row=1, col=1
            )
    
    fig.update_layout(
        height=800,
        xaxis_rangeslider_visible=False,
        title=f'{ticker} ({timeframe}) - {title_suffix}',
        template='plotly_dark',
        hovermode='x unified'
    )
    return fig


def main():
    token = os.environ.get("TINKOFF_INVEST_TOKEN")
    if not token:
        print("❌ Токен не найден!")
        return
    
    print("=" * 60)
    print("🧪 ГИБРИДНЫЙ ПОДХОД: МАТЕМАТИКА + NN")
    print("=" * 60)
    print()
    
    ticker = "MXH6"
    class_code = "SPBFUT"
    timeframe = "1h"
    from_date = datetime(2025, 10, 20, tzinfo=timezone.utc)
    to_date = datetime(2025, 12, 20, tzinfo=timezone.utc)
    
    print(f"📊 Инструмент: {ticker}")
    print(f"📅 Период: {from_date.date()} - {to_date.date()}")
    print()
    
    # Загрузка данных
    print("📥 Загрузка данных...")
    scanner = ComplexFlagScanner(token)
    tf_config = TIMEFRAMES.get(timeframe, TIMEFRAMES['1h'])
    df = scanner.get_candles_df_by_dates(ticker, class_code, from_date, to_date, interval=tf_config['interval'])
    
    if df.empty:
        print("❌ Данные не загружены!")
        return
    
    print(f"✅ Загружено {len(df)} свечей")
    print()
    
    # Шаг 1: Математический сканер находит паттерны с правильной геометрией
    print("🔍 Шаг 1: Математический сканер (правильная геометрия)...")
    math_patterns = scanner.analyze(df, debug=False, timeframe=timeframe)
    print(f"✅ Найдено математическим сканером: {len(math_patterns)} паттернов")
    print()
    
    if not math_patterns:
        print("⚠️  Математический сканер не нашел паттернов")
        print("   Попробуйте другой период или инструмент")
        return
    
    # Шаг 2: Фильтрация через NN (опционально)
    print("🔍 Шаг 2: Фильтрация через NN (опционально)...")
    hybrid_scanner = HybridFlagScanner(token, use_nn=True, nn_min_confidence=0.7, device='cpu')
    
    # Для каждого математического паттерна проверяем уверенность NN
    nn_filtered_patterns = []
    
    # Получаем предсказания NN
    nn_predictions = predict_with_sliding_window(
        df, hybrid_scanner.nn_model, window=100, step=10,
        device=hybrid_scanner.device, min_confidence=0.5  # Низкий порог для проверки
    )
    
    print(f"   Получено предсказаний от NN: {len(nn_predictions)}")
    
    # Для каждого математического паттерна ищем соответствующее предсказание NN
    for math_p in math_patterns:
        # Находим индексы паттерна
        math_start = min(math_p['t0']['idx'], math_p['t1']['idx'], math_p['t2']['idx'], math_p['t3']['idx'], math_p['t4']['idx'])
        math_end = max(math_p['t0']['idx'], math_p['t1']['idx'], math_p['t2']['idx'], math_p['t3']['idx'], math_p['t4']['idx'])
        
        # Ищем пересекающееся предсказание NN
        best_nn_match = None
        max_overlap = 0
        
        for nn_p in nn_predictions:
            nn_start = nn_p['window_start']
            nn_end = nn_p['window_end']
            
            overlap_start = max(math_start, nn_start)
            overlap_end = min(math_end, nn_end)
            overlap = max(0, overlap_end - overlap_start)
            
            if overlap > max_overlap:
                max_overlap = overlap
                best_nn_match = nn_p
        
        if best_nn_match and best_nn_match['probability'] >= 0.7:
            # Добавляем информацию от NN
            math_p['nn_confidence'] = best_nn_match['probability']
            math_p['nn_class'] = best_nn_match['class']
            nn_filtered_patterns.append(math_p)
        else:
            # Паттерн без высокой уверенности NN
            math_p['nn_confidence'] = best_nn_match['probability'] if best_nn_match else 0.0
            math_p['nn_class'] = best_nn_match['class'] if best_nn_match else 0
    
    print(f"✅ Осталось после фильтрации NN (≥70%): {len(nn_filtered_patterns)}")
    print()
    
    # Выводим результаты
    print("📊 РЕЗУЛЬТАТЫ:")
    print("-" * 60)
    print(f"   • Математический сканер: {len(math_patterns)} паттернов")
    print(f"   • С высокой уверенностью NN (≥70%): {len(nn_filtered_patterns)}")
    print(f"   • Без высокой уверенности NN: {len(math_patterns) - len(nn_filtered_patterns)}")
    print()
    
    if math_patterns:
        print("✅ РЕКОМЕНДАЦИЯ: Использовать все паттерны от математического сканера")
        print("   (они имеют правильную геометрию, NN может использоваться как дополнительный фильтр)")
        print()
    
    # Визуализация
    print("📊 Создание графика...")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f'neural_network/hybrid_mxh6_{timestamp}.html'
    
    # Показываем все паттерны от математического сканера
    fig = create_interactive_chart(df, math_patterns, ticker, timeframe, 
                                   f"Гибридный подход ({len(math_patterns)} паттернов)")
    fig.write_html(output_file)
    print(f"   ✅ Сохранено: {output_file}")
    
    try:
        fig.show()
    except:
        print("   💡 Откройте файл в браузере")
    
    print()
    print("=" * 60)
    print("✅ АНАЛИЗ ЗАВЕРШЕН")
    print("=" * 60)


if __name__ == "__main__":
    main()

