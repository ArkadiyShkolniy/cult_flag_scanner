"""
Объединенный интерактивный дашборд для разметки паттернов "Флаг"
Включает:
- Ручную разметку точек T0-T4
- Автоматический поиск паттернов с помощью нейросети
- Подтверждение/отклонение найденных паттернов
- Редактирование существующих аннотаций
- Исправление записей с нарушениями геометрии
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
import sys
import json
import sqlite3
import torch
import torch.nn.functional as F
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from pathlib import Path

# Добавляем путь к корню проекта
sys.path.insert(0, str(Path(__file__).parent.parent))

from scanners.combined_scanner import ComplexFlagScanner
from scanners.bullish_flag_scanner import BullishFlagScanner
from scanners.bearish_flag_scanner import BearishFlagScanner
from t_tech.invest import Client, InstrumentIdType

from config import TIMEFRAMES
from neural_network.annotator import PatternAnnotator
from neural_network.check_annotations_geometry import check_long_constraints, check_short_constraints
from neural_network.model_keypoints import create_keypoint_model
from neural_network.data_loader_keypoints import FlagPatternKeypointDataset
from neural_network.predict_keypoints import predict_with_sliding_window

load_dotenv()
st.set_page_config(page_title="Разметка паттернов", layout="wide")

st.title("🎨 Разметка паттернов 'Флаг' для обучения нейросети")

# Инициализация
token = os.environ.get("TINKOFF_INVEST_TOKEN")
if not token:
    st.error("❌ Токен не найден! Убедитесь что файл .env содержит TINKOFF_INVEST_TOKEN")
    st.stop()

# Настройка кэша (можно включить для ускорения загрузки, но по умолчанию отключен из-за проблем)
use_cache_default = st.sidebar.checkbox("💾 Использовать кэш", value=False, key="use_cache", 
                                         help="Если включено, данные будут кэшироваться для ускорения. По умолчанию отключено.")
# Кнопка очистки кэша
if st.sidebar.button("🗑️ Очистить кэш", help="Удаляет все кэшированные данные свечей"):
    try:
        from data_cache import CandleDataCache
        cache = CandleDataCache()
        # Удаляем все данные из кэша
        conn = sqlite3.connect(cache.db_path)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM candles_cache')
        deleted = cursor.rowcount
        conn.commit()
        conn.close()
        st.sidebar.success(f"✅ Кэш очищен ({deleted} записей удалено)")
        st.rerun()
    except Exception as e:
        st.sidebar.error(f"❌ Ошибка очистки кэша: {e}")

scanner = ComplexFlagScanner(token)
annotator = PatternAnnotator()

# Инициализация сессии (объединенная)
if 'points' not in st.session_state:
    st.session_state.points = {}
if 'df_data' not in st.session_state:
    st.session_state.df_data = None
if 'pattern_type' not in st.session_state:
    st.session_state.pattern_type = 'bullish'  # bullish или bearish
if 'nn_predictions' not in st.session_state:
    st.session_state.nn_predictions = []
if 'confirmed_patterns' not in st.session_state:
    st.session_state.confirmed_patterns = []
if 'rejected_patterns' not in st.session_state:
    st.session_state.rejected_patterns = []
if 'saved_math_patterns' not in st.session_state:
    st.session_state.saved_math_patterns = []  # ID сохраненных математических паттернов
if 'model' not in st.session_state:
    st.session_state.model = None
if 'device' not in st.session_state:
    st.session_state.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
if 'selected_pattern_idx' not in st.session_state:
    st.session_state.selected_pattern_idx = None  # Индекс выбранного паттерна для отображения
if 'show_all_patterns' not in st.session_state:
    st.session_state.show_all_patterns = True  # Показывать все паттерны или только выбранный


# ============================================================================
# ФУНКЦИИ (определяем до использования)
# ============================================================================

def create_interactive_chart(df, points, pattern_type, ticker='', timeframe='1h'):
    """Создает интерактивный график с возможностью отмечать точки"""
    
    # Используем индексы для непрерывного графика
    indices_x = list(range(len(df)))
    customdata_candles = [[i, df.iloc[i]['time']] for i in range(len(df))]
    
    # Создаем subplot
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.7, 0.3],
        subplot_titles=('График свечей (кликните для отметки точек)', 'Объем')
    )
    
    # Свечи
    colors = ['red' if df.iloc[i]['close'] < df.iloc[i]['open'] else 'green' 
              for i in range(len(df))]
    
    fig.add_trace(
        go.Candlestick(
            x=indices_x,
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close'],
            name='Свечи',
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
    
    # Добавляем EMA, если они есть
    if 'ema_7' in df.columns:
        fig.add_trace(
            go.Scatter(
                x=indices_x,
                y=df['ema_7'],
                mode='lines',
                line=dict(color='yellow', width=1),
                name='EMA 7',
                opacity=0.7
            ),
            row=1, col=1
        )
        
    if 'ema_14' in df.columns:
        fig.add_trace(
            go.Scatter(
                x=indices_x,
                y=df['ema_14'],
                mode='lines',
                line=dict(color='purple', width=1),
                name='EMA 14',
                opacity=0.7
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
        if point_name in points and points[point_name] is not None:
            point_data = points[point_name]
            # Проверяем что point_data является словарем с нужными ключами
            if isinstance(point_data, dict) and 'idx' in point_data and 'price' in point_data:
                fig.add_trace(
                go.Scatter(
                    x=[point_data['idx']],
                    y=[point_data['price']],
                    mode='markers+text',
                    marker=dict(
                        size=20,
                        color=point_colors[point_name],
                        symbol=point_symbols[point_name],
                        line=dict(width=2, color='white')
                    ),
                    text=[point_name],
                    textposition='top center',
                    name=point_name,
                    showlegend=True,
                    hovertemplate=f'<b>{point_name}</b><br>' +
                                 f'Индекс: {point_data["idx"]}<br>' +
                                 f'Цена: {point_data["price"]:.2f}<br>' +
                                 f'Время: {point_data.get("time", "")}<extra></extra>'
                ),
                row=1, col=1
            )
    
    # Линии между точками (если есть минимум 2 точки)
    # Фильтруем только валидные точки (не None)
    valid_points = {k: v for k, v in points.items() if v is not None and isinstance(v, dict) and 'idx' in v and 'price' in v}
    
    if len(valid_points) >= 2:
        sorted_points = sorted(valid_points.items(), key=lambda x: x[1]['idx'])
        if len(sorted_points) >= 2:
            # Флагшток T0-T1
            if 'T0' in valid_points and 'T1' in valid_points:
                fig.add_trace(
                    go.Scatter(
                        x=[valid_points['T0']['idx'], valid_points['T1']['idx']],
                        y=[valid_points['T0']['price'], valid_points['T1']['price']],
                        mode='lines',
                        line=dict(color='lime', width=3, dash='solid'),
                        name='Флагшток (T0-T1)',
                        showlegend=True
                    ),
                    row=1, col=1
                )
            
            # Линия T1-T3 (если обе точки есть)
            if 'T1' in valid_points and 'T3' in valid_points:
                # Основная линия T1-T3
                fig.add_trace(
                    go.Scatter(
                        x=[valid_points['T1']['idx'], valid_points['T3']['idx']],
                        y=[valid_points['T1']['price'], valid_points['T3']['price']],
                        mode='lines',
                        line=dict(color='red', width=2, dash='solid'),
                        name='Линия T1-T3',
                        showlegend=True
                    ),
                    row=1, col=1
                )
                
                # Продление линии T1-T3 до T4 (если T4 есть)
                if 'T4' in valid_points:
                    t1_idx = valid_points['T1']['idx']
                    t3_idx = valid_points['T3']['idx']
                    t4_idx = valid_points['T4']['idx']
                    t1_price = valid_points['T1']['price']
                    t3_price = valid_points['T3']['price']
                    
                    if t3_idx != t1_idx:
                        slope = (t3_price - t1_price) / (t3_idx - t1_idx)
                        projected_price = t1_price + slope * (t4_idx - t1_idx)
                        
                        fig.add_trace(
                            go.Scatter(
                                x=[valid_points['T3']['idx'], t4_idx],
                                y=[valid_points['T3']['price'], projected_price],
                                mode='lines',
                                line=dict(color='red', width=2, dash='dash'), # Такой же цвет, dash стиль
                                name='Продление T1-T3',
                                showlegend=False, # Скрываем из легенды чтобы не дублировать
                                hovertemplate='Продление T1-T3<br>Цена: %{y:.2f}'
                            ),
                            row=1, col=1
                        )

            # Линия T2-T4 (если обе точки есть)
            if 'T2' in valid_points and 'T4' in valid_points:
                fig.add_trace(
                    go.Scatter(
                        x=[valid_points['T2']['idx'], valid_points['T4']['idx']],
                        y=[valid_points['T2']['price'], valid_points['T4']['price']],
                        mode='lines',
                        line=dict(color='cyan', width=2, dash='dash'),
                        name='Линия T2-T4',
                        showlegend=True
                    ),
                    row=1, col=1
                )
    
    # Объем
    fig.add_trace(
        go.Bar(
            x=indices_x,
            y=df['volume'],
            marker_color=colors,
            name='Объем',
            customdata=customdata_candles,
            hovertemplate='<b>Индекс:</b> %{customdata[0]}<br>' +
                         '<b>Время:</b> %{customdata[1]}<br>' +
                         '<b>Объем:</b> %{y}<extra></extra>'
        ),
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
            if timeframe == '1d':
                tick_times.append(time_val.strftime('%Y-%m-%d'))
            else:
                tick_times.append(time_val.strftime('%Y-%m-%d %H:%M'))
        else:
            tick_times.append(str(time_val))
    
    # Определяем формат времени для подписи тиков
    time_format = '%Y-%m-%d' if timeframe == '1d' else '%Y-%m-%d %H:%M'
    
    fig.update_layout(
        height=800,
        xaxis_rangeslider_visible=False,
        title=f"График {ticker} ({timeframe}) - Разметка паттерна",
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
        ),
        clickmode='event+select'  # Включаем выбор точек
    )
    
    return fig


def process_point_selection(selected_points, df):
    """Обрабатывает выбор точки на графике"""
    if not selected_points:
        return
    
    # Определяем какая точка должна быть отмечена следующей
    point_order = ['T0', 'T1', 'T2', 'T3', 'T4']
    next_point = None
    
    for point_name in point_order:
        if point_name not in st.session_state.points:
            next_point = point_name
            break
    
    if next_point is None:
        st.warning("⚠️ Все точки уже отмечены! Очистите точки чтобы начать заново.")
        return
    
    # Получаем данные из выбранной точки
    point_data = selected_points[0]
    
    # Получаем индекс свечи (из customdata или вычисляем из x)
    if 'customdata' in point_data and point_data['customdata']:
        candle_idx = int(point_data['customdata'][0])
    else:
        # Если нет customdata, вычисляем индекс из координаты x
        x_coord = point_data.get('x', point_data.get('pointIndex', 0))
        candle_idx = int(x_coord)
    
    # Ограничиваем индекс
    candle_idx = max(0, min(candle_idx, len(df) - 1))
    
    # Получаем цену
    y_coord = point_data.get('y', 0)
    
    # Для бычьего паттерна определяем цену в зависимости от точки
    if st.session_state.pattern_type == 'bullish':
        if next_point in ['T0', 'T2', 'T4']:
            # Для этих точек используем low
            price = df.iloc[candle_idx]['low']
        else:  # T1, T3
            # Для этих точек используем high
            price = df.iloc[candle_idx]['high']
    else:  # bearish
        if next_point in ['T0', 'T2', 'T4']:
            # Для медвежьего - наоборот
            price = df.iloc[candle_idx]['high']
        else:  # T1, T3
            price = df.iloc[candle_idx]['low']
    
    # Сохраняем точку
    st.session_state.points[next_point] = {
        'idx': candle_idx,
        'price': price,
        'time': df.iloc[candle_idx]['time']
    }
    
    st.success(f"✅ Отмечена точка {next_point} (индекс {candle_idx}, цена {price:.2f})")
    st.rerun()


def check_geometry_before_save(valid_points, label, timeframe='1h'):
    """Проверяет геометрию паттерна перед сохранением"""
    if len(valid_points) != 5:
        return []
    
    T0 = valid_points['T0']['price']
    T1 = valid_points['T1']['price']
    T2 = valid_points['T2']['price']
    T3 = valid_points['T3']['price']
    T4 = valid_points['T4']['price']
    
    # Получаем индексы для проверки сходимости линий
    t0_idx = valid_points['T0'].get('idx')
    t1_idx = valid_points['T1'].get('idx')
    t2_idx = valid_points['T2'].get('idx')
    t3_idx = valid_points['T3'].get('idx')
    t4_idx = valid_points['T4'].get('idx')
    
    violations = []
    if label == 1:  # LONG
        violations = check_long_constraints(T0, T1, T2, T3, T4, timeframe, t0_idx, t1_idx, t2_idx, t3_idx, t4_idx)
    elif label == 2:  # SHORT
        violations = check_short_constraints(T0, T1, T2, T3, T4, timeframe, t0_idx, t1_idx, t2_idx, t3_idx, t4_idx)
    
    return violations


def delete_annotation():
    """Удаляет текущую аннотацию"""
    if 'editing_file' not in st.session_state or not st.session_state.editing_file:
        st.error("❌ Нет активной записи для удаления!")
        return
    
    try:
        editing_file = st.session_state.editing_file
        annotations_df = annotator.annotations.copy()
        
        # Находим и удаляем запись
        mask = annotations_df['file'] == editing_file
        if mask.any():
            # Удаляем запись
            annotations_df = annotations_df[~mask].copy()
            annotator.annotations = annotations_df
            annotator.save_annotations()
            
            # Очищаем session_state
            st.session_state.points = {}
            st.session_state.df_data = None
            if 'editing_annotation_idx' in st.session_state:
                st.session_state.editing_annotation_idx = None
            if 'editing_file' in st.session_state:
                st.session_state.editing_file = None
            
            st.success(f"✅ Запись удалена: {editing_file}")
            
            # Автоматически обновляем список нарушений после удаления
            try:
                import subprocess
                result = subprocess.run(
                    ["python3", "neural_network/list_violations.py"],
                    cwd=Path.cwd(),
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                if result.returncode == 0:
                    st.info("🔄 Список нарушений обновлен автоматически")
                else:
                    st.warning(f"⚠️ Не удалось обновить список нарушений автоматически")
            except Exception as e:
                st.warning(f"⚠️ Не удалось обновить список нарушений: {e}")
            
            st.rerun()
        else:
            st.error("❌ Запись не найдена!")
    except Exception as e:
        st.error(f"❌ Ошибка удаления: {e}")
        import traceback
        st.code(traceback.format_exc())


def load_model(model_path='neural_network/models/keypoint_model_best.pth'):
    """Загружает модель нейросети"""
    if st.session_state.model is not None:
        return st.session_state.model
    
    try:
        model = create_keypoint_model(
            num_classes=3,
            num_keypoints=5,
            image_height=224,
            image_width=224,
            pretrained_path=model_path
        )
        model.to(st.session_state.device)
        model.eval()
        st.session_state.model = model
        return model
    except Exception as e:
        st.error(f"❌ Ошибка загрузки модели: {e}")
        return None


def find_patterns_with_nn(df, timeframe, window=100, step=10, min_confidence=0.6):
    """Находит паттерны с помощью нейросети"""
    model = load_model()
    if model is None:
        return []
    
    try:
        predictions = predict_with_sliding_window(
            df, model, window=window, step=step, 
            device=st.session_state.device, min_confidence=min_confidence
        )
        return predictions
    except Exception as e:
        st.error(f"❌ Ошибка поиска паттернов: {e}")
        import traceback
        st.code(traceback.format_exc())
        return []


def create_chart_with_predictions(df, predictions, confirmed_patterns, rejected_patterns, ticker, timeframe, selected_pattern_idx=None, show_all=True):
    """Создает график с предсказаниями нейросети и статусами подтверждения
    
    Args:
        selected_pattern_idx: Индекс паттерна для отображения (если None и show_all=False, показываем все)
        show_all: Если True, показываем все паттерны, иначе только выбранный
    """
    indices_x = list(range(len(df)))
    customdata = [[i, df.iloc[i]['time']] for i in range(len(df))]
    
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.7, 0.3],
        subplot_titles=('График с предсказаниями нейросети', 'Объем')
    )
    
    # Свечи
    colors = ['red' if df.iloc[i]['close'] < df.iloc[i]['open'] else 'green' 
              for i in range(len(df))]
    
    fig.add_trace(
        go.Candlestick(
            x=indices_x,
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close'],
            name='Свечи',
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
    
    # Добавляем EMA, если они есть
    if 'ema_7' in df.columns:
        fig.add_trace(
            go.Scatter(
                x=indices_x,
                y=df['ema_7'],
                mode='lines',
                line=dict(color='yellow', width=1),
                name='EMA 7',
                opacity=0.7
            ),
            row=1, col=1
        )
        
    if 'ema_14' in df.columns:
        fig.add_trace(
            go.Scatter(
                x=indices_x,
                y=df['ema_14'],
                mode='lines',
                line=dict(color='purple', width=1),
                name='EMA 14',
                opacity=0.7
            ),
            row=1, col=1
        )
    
    # Цвета для точек
    point_colors = {'T0': 'lime', 'T1': 'red', 'T2': 'cyan', 'T3': 'orange', 'T4': 'magenta'}
    point_symbols = {'T0': 'circle', 'T1': 'diamond', 'T2': 'circle', 'T3': 'diamond', 'T4': 'circle'}
    line_colors = ['lime', 'yellow', 'cyan', 'magenta', 'orange', 'pink', 'lightblue']
    
    class_names = {0: 'нет паттерна', 1: 'бычий', 2: 'медвежий'}
    
    # Сортируем предсказания по вероятности
    sorted_predictions = sorted(predictions, key=lambda x: x['probability'], reverse=True)
    
    # Фильтруем паттерны для отображения
    if not show_all and selected_pattern_idx is not None and 0 <= selected_pattern_idx < len(sorted_predictions):
        # Показываем только выбранный паттерн
        patterns_to_show = [sorted_predictions[selected_pattern_idx]]
    else:
        # Показываем все паттерны
        patterns_to_show = sorted_predictions
    
    # Отображаем предсказания
    for display_idx, prediction in enumerate(patterns_to_show):
        # Находим реальный индекс паттерна в отсортированном списке
        if show_all:
            # Для всех паттернов используем индекс из отсортированного списка
            try:
                pattern_idx = sorted_predictions.index(prediction)
            except ValueError:
                # Если не найден, используем display_idx
                pattern_idx = display_idx
        else:
            # Для одного паттерна используем выбранный индекс
            pattern_idx = selected_pattern_idx if selected_pattern_idx is not None else 0
        pred_points = prediction['points']
        predicted_class = prediction['class']
        pred_prob = prediction['probability']
        predicted_name = class_names.get(predicted_class, 'неизвестно')
        
        # Проверяем статус паттерна
        points = prediction.get('points', [])
        window_start = prediction.get('window_start', points[0]['idx'] if points and len(points) > 0 else 0)
        window_end = prediction.get('window_end', points[4]['idx'] if points and len(points) > 4 else 0)
        pattern_id = f"{pattern_idx}_{window_start}_{window_end}"
        is_confirmed = any(cp['id'] == pattern_id for cp in confirmed_patterns)
        is_rejected = any(rp['id'] == pattern_id for rp in rejected_patterns)
        
        # Определяем стиль отображения
        if is_confirmed:
            line_style = 'solid'
            line_width = 3
            opacity = 1.0
            status_text = "✅ Подтвержден"
        elif is_rejected:
            line_style = 'dot'
            line_width = 1
            opacity = 0.3
            status_text = "❌ Отклонен"
        else:
            line_style = 'dash'
            line_width = 2
            opacity = 0.7
            status_text = "⏳ Ожидает решения"
        
        base_color = line_colors[pattern_idx % len(line_colors)]
        
        # Точки
        for point in pred_points:
            point_name = point['name']
            idx = point['idx']
            price = point['price']
            color = point_colors.get(point_name, 'yellow')
            symbol = point_symbols.get(point_name, 'circle')
            
            if 0 <= idx < len(df):
                fig.add_trace(
                    go.Scatter(
                        x=[idx],
                        y=[price],
                        mode='markers+text',
                        marker=dict(size=12, color=color, symbol=symbol, 
                                   line=dict(width=2, color='white'), opacity=opacity),
                        text=[f'{point_name}'] if (show_all and pattern_idx < 3) or not show_all else [''],
                        textposition='top center',
                        name=f'{point_name} #{pattern_idx+1}' if (show_all and pattern_idx > 0) else f'{point_name}',
                        showlegend=((show_all and pattern_idx < 3) or not show_all),
                        hovertemplate=f'<b>{point_name}</b> (паттерн #{pattern_idx+1})<br>' +
                                     f'Индекс: {idx}<br>' +
                                     f'Цена: {price:.2f}<br>' +
                                     f'Класс: {predicted_name}<br>' +
                                     f'Вероятность: {pred_prob:.1%}<br>' +
                                     f'Статус: {status_text}<extra></extra>'
                    ),
                    row=1, col=1
                )
        
        # Линии паттерна
        if len(pred_points) == 5:
            # Флагшток (T0 -> T1)
            fig.add_trace(
                go.Scatter(
                    x=[pred_points[0]['idx'], pred_points[1]['idx']],
                    y=[pred_points[0]['price'], pred_points[1]['price']],
                    mode='lines',
                    line=dict(color=base_color, width=line_width, dash=line_style),
                    opacity=opacity,
                    name=f'Паттерн #{pattern_idx+1} ({predicted_name}, {pred_prob:.0%}) {status_text}' if show_all else f'Паттерн ({predicted_name}, {pred_prob:.0%}) {status_text}',
                    showlegend=True,
                    hovertemplate=f'Паттерн #{pattern_idx+1}<br>' +
                                 f'Класс: {predicted_name}<br>' +
                                 f'Вероятность: {pred_prob:.1%}<br>' +
                                 f'Статус: {status_text}<extra></extra>'
                ),
                row=1, col=1
            )
            
            # Линия T1-T3
            fig.add_trace(
                go.Scatter(
                    x=[pred_points[1]['idx'], pred_points[3]['idx']],
                    y=[pred_points[1]['price'], pred_points[3]['price']],
                    mode='lines',
                    line=dict(color=base_color, width=line_width-0.5, dash='solid'),
                    opacity=opacity * 0.8,
                    showlegend=False
                ),
                row=1, col=1
            )
            
            # Продление T1-T3 до T4
            t1_idx = pred_points[1]['idx']
            t3_idx = pred_points[3]['idx']
            t4_idx = pred_points[4]['idx']
            t1_price = pred_points[1]['price']
            t3_price = pred_points[3]['price']
            
            if t3_idx != t1_idx:
                slope = (t3_price - t1_price) / (t3_idx - t1_idx)
                projected_price = t1_price + slope * (t4_idx - t1_idx)
                
                fig.add_trace(
                    go.Scatter(
                        x=[t3_idx, t4_idx],
                        y=[t3_price, projected_price],
                        mode='lines',
                        line=dict(color=base_color, width=line_width-0.5, dash='dash'),
                        opacity=opacity * 0.8,
                        showlegend=False,
                        hoverinfo='skip'
                    ),
                    row=1, col=1
                )
            
            # Линия T2-T4
            fig.add_trace(
                go.Scatter(
                    x=[pred_points[2]['idx'], pred_points[4]['idx']],
                    y=[pred_points[2]['price'], pred_points[4]['price']],
                    mode='lines',
                    line=dict(color=base_color, width=line_width-0.5, dash='dash'),
                    opacity=opacity * 0.8,
                    showlegend=False
                ),
                row=1, col=1
            )
    
    # Объем
    fig.add_trace(
        go.Bar(
            x=indices_x,
            y=df['volume'],
            marker_color=colors,
            name='Объем',
            customdata=customdata,
            hovertemplate='<b>Индекс:</b> %{customdata[0]}<br>' +
                         '<b>Время:</b> %{customdata[1]}<br>' +
                         '<b>Объем:</b> %{y}<extra></extra>'
        ),
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
            if timeframe == '1d':
                tick_times.append(time_val.strftime('%Y-%m-%d'))
            else:
                tick_times.append(time_val.strftime('%Y-%m-%d %H:%M'))
        else:
            tick_times.append(str(time_val))
    
    confirmed_count = len(confirmed_patterns)
    rejected_count = len(rejected_patterns)
    pending_count = len(predictions) - confirmed_count - rejected_count
    
    # Формируем заголовок
    if show_all:
        title = f"{ticker} ({timeframe}) - Найдено: {len(predictions)} | ✅ {confirmed_count} | ❌ {rejected_count} | ⏳ {pending_count}"
    else:
        if selected_pattern_idx is not None and 0 <= selected_pattern_idx < len(sorted_predictions):
            selected_pred = sorted_predictions[selected_pattern_idx]
            selected_name = class_names.get(selected_pred['class'], 'неизвестно')
            title = f"{ticker} ({timeframe}) - Паттерн #{selected_pattern_idx+1}: {selected_name} ({selected_pred['probability']:.1%})"
        else:
            title = f"{ticker} ({timeframe}) - Выберите паттерн для отображения"
    
    fig.update_layout(
        height=800,
        xaxis_rangeslider_visible=False,
        title=title,
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
    
    return fig


def check_duplicate_pattern(ticker, timeframe, t1_price, t4_price, annotations_df):
    """
    Проверяет, существует ли уже такой паттерн в разметке.
    Сравнивает тикер, таймфрейм и цены точек T1 и T4.
    """
    if annotations_df.empty:
        return False
        
    # Фильтруем по тикеру и таймфрейму
    mask = (annotations_df['ticker'] == ticker) & (annotations_df['timeframe'] == timeframe)
    df_filtered = annotations_df[mask]
    
    if df_filtered.empty:
        return False
        
    # Проверяем цены с небольшим допуском (для float)
    for _, row in df_filtered.iterrows():
        # Если найден паттерн с почти идентичными ценами T1 и T4
        if abs(row['t1_price'] - t1_price) < 1e-4 and abs(row['t4_price'] - t4_price) < 1e-4:
            return True
            
    return False

def save_confirmed_pattern(pattern_data, df, ticker, timeframe):
    """Сохраняет подтвержденный паттерн как положительный пример"""
    try:
        # Проверка на дубликаты ПЕРЕД сохранением
        # Извлекаем цены T1 и T4 из pattern_data
        t1_price = next((p['price'] for p in pattern_data['points'] if p['name'] == 'T1'), None)
        t4_price = next((p['price'] for p in pattern_data['points'] if p['name'] == 'T4'), None)
        
        if t1_price is not None and t4_price is not None:
            if check_duplicate_pattern(ticker, timeframe, t1_price, t4_price, annotator.annotations):
                st.warning(f"⚠️ Паттерн {ticker} ({timeframe}) уже существует в базе! Сохранение пропущено.")
                return True # Возвращаем True, чтобы скрыть кнопку, как будто сохранили
        
        # Извлекаем окно данных для паттерна
        window_start = pattern_data.get('window_start', 0)
        window_end = pattern_data.get('window_end', len(df))
        
        # Берем окно данных вокруг паттерна
        # Слева (до T0) берем побольше контекста для индикаторов (EMA и т.д.)
        # Справа (после T4) берем минимум (имитация момента обнаружения)
        margin_left = 50 
        margin_right = 3
        
        start_idx = max(0, window_start - margin_left)
        end_idx = min(len(df), window_end + margin_right)
        df_window = df.iloc[start_idx:end_idx].copy().reset_index(drop=True)
        
        # Корректируем индексы точек относительно нового окна
        points_adjusted = []
        for point in pattern_data['points']:
            original_idx = point['idx']
            adjusted_idx = original_idx - start_idx
            if 0 <= adjusted_idx < len(df_window):
                points_adjusted.append({
                    'name': point['name'],
                    'idx': adjusted_idx,
                    'price': point['price']
                })
        
        if len(points_adjusted) != 5:
            st.warning(f"⚠️ Не все точки попадают в окно данных. Пропущено точек: {5 - len(points_adjusted)}")
            return False
        
        # Сохраняем свечи
        candles_file = annotator.save_candles(
            df=df_window,
            ticker=ticker,
            timeframe=timeframe
        )
        
        # Определяем метку (1 для бычьего, 2 для медвежьего)
        label = pattern_data['class']
        
        # Преобразуем точки в нужный формат (с учетом скорректированных индексов)
        points = {}
        for point in points_adjusted:
            point_name = point['name']
            idx = point['idx']
            price = point['price']
            
            # Получаем время из DataFrame окна
            if 0 <= idx < len(df_window):
                time_val = df_window.iloc[idx]['time']
            else:
                time_val = ''
            
            points[point_name] = {
                'idx': idx,
                'price': price,
                'time': time_val
            }
        
        # Сохраняем аннотацию
        pattern_type = 'FLAG_0_1_2_3_4' if label == 1 else 'BEARISH_FLAG_0_1_2_3_4'
        
        annotator.annotate_pattern(
            candles_file=candles_file,
            label=label,
            ticker=ticker,
            timeframe=timeframe,
            pattern_type=pattern_type,
            notes=f"Подтвержден пользователем из предсказаний нейросети. Вероятность: {pattern_data['probability']:.1%}",
            points=points
        )
        
        return True
    except Exception as e:
        st.error(f"❌ Ошибка сохранения подтвержденного паттерна: {e}")
        import traceback
        st.code(traceback.format_exc())
        return False


def save_rejected_pattern(pattern_data, df, ticker, timeframe):
    """Сохраняет отклоненный паттерн как отрицательный пример (label=0)"""
    try:
        # Извлекаем окно данных для паттерна
        window_start = pattern_data.get('window_start', 0)
        window_end = pattern_data.get('window_end', len(df))
        
        # Берем окно данных вокруг паттерна
        # Слева (до T0) берем побольше контекста для индикаторов (EMA и т.д.)
        # Справа (после T4) берем минимум (имитация момента обнаружения)
        margin_left = 50 
        margin_right = 3
        
        start_idx = max(0, window_start - margin_left)
        end_idx = min(len(df), window_end + margin_right)
        df_window = df.iloc[start_idx:end_idx].copy().reset_index(drop=True)
        
        # Корректируем индексы точек относительно нового окна
        points_adjusted = []
        for point in pattern_data['points']:
            original_idx = point['idx']
            adjusted_idx = original_idx - start_idx
            if 0 <= adjusted_idx < len(df_window):
                points_adjusted.append({
                    'name': point['name'],
                    'idx': adjusted_idx,
                    'price': point['price']
                })
        
        if len(points_adjusted) != 5:
            st.warning(f"⚠️ Не все точки попадают в окно данных. Пропущено точек: {5 - len(points_adjusted)}")
            return False
        
        # Сохраняем свечи
        candles_file = annotator.save_candles(
            df=df_window,
            ticker=ticker,
            timeframe=timeframe
        )
        
        # Преобразуем точки в нужный формат (с учетом скорректированных индексов)
        points = {}
        for point in points_adjusted:
            point_name = point['name']
            idx = point['idx']
            price = point['price']
            
            # Получаем время из DataFrame окна
            if 0 <= idx < len(df_window):
                time_val = df_window.iloc[idx]['time']
            else:
                time_val = ''
            
            points[point_name] = {
                'idx': idx,
                'price': price,
                'time': time_val
            }
        
        # Сохраняем как отрицательный пример (label=0)
        annotator.annotate_pattern(
            candles_file=candles_file,
            label=0,  # Нет паттерна
            ticker=ticker,
            timeframe=timeframe,
            pattern_type='NO_PATTERN',
            notes=f"Отклонен пользователем. Нейросеть предсказала {pattern_data['class']} с вероятностью {pattern_data['probability']:.1%}",
            points=points
        )
        
        return True
    except Exception as e:
        st.error(f"❌ Ошибка сохранения отклоненного паттерна: {e}")
        import traceback
        st.code(traceback.format_exc())
        return False


def save_annotation():
    """Сохраняет размеченный паттерн для обучения"""
    # Фильтруем только валидные точки
    valid_points = {k: v for k, v in st.session_state.points.items() 
                   if v is not None and isinstance(v, dict) and 'idx' in v and 'price' in v}
    
    if len(valid_points) != 5:
        st.error("❌ Отметьте все 5 точек!")
        return
    
    try:
        df = st.session_state.df_data
        
        # Получаем значения из session_state (они должны быть сохранены при загрузке)
        ticker = st.session_state.get('current_ticker', 'UNKNOWN')
        selected_timeframe = st.session_state.get('current_timeframe', '1h')

        # Проверка на дубликаты ПЕРЕД сохранением (только для новых записей)
        editing_mode = ('editing_annotation_idx' in st.session_state and st.session_state.editing_annotation_idx is not None) or \
                       ('editing_file' in st.session_state and st.session_state.editing_file)

        if not editing_mode:
            t1_price = valid_points['T1']['price']
            t4_price = valid_points['T4']['price']
            
            if check_duplicate_pattern(ticker, selected_timeframe, t1_price, t4_price, annotator.annotations):
                 st.error(f"⚠️ Паттерн {ticker} ({selected_timeframe}) уже существует в базе! Сохранение отменено.")
                 return

        # Проверяем порядок точек
        sorted_points = sorted(valid_points.items(), key=lambda x: x[1]['idx'])
        point_names = [p[0] for p in sorted_points]
        
        if point_names != ['T0', 'T1', 'T2', 'T3', 'T4']:
            st.error("❌ Точки должны быть в хронологическом порядке T0 < T1 < T2 < T3 < T4!")
            return

        # --- ОБРЕЗКА ДАННЫХ (Slicing) ---
        # Чтобы избежать утечки данных (Data Leakage), обрезаем данные вокруг паттерна.
        # Слева оставляем контекст (50 свечей), справа - минимум (3 свечи).
        
        # Находим границы паттерна
        t0_idx = valid_points['T0']['idx']
        t4_idx = valid_points['T4']['idx']
        
        margin_left = 50
        margin_right = 3
        
        start_idx = max(0, t0_idx - margin_left)
        end_idx = min(len(df), t4_idx + margin_right)
        
        df_window = df.iloc[start_idx:end_idx].copy().reset_index(drop=True)
        
        # Корректируем координаты точек под новое окно
        adjusted_points = {}
        for pname, pdata in valid_points.items():
            new_idx = pdata['idx'] - start_idx
            # Проверка на всякий случай
            if not (0 <= new_idx < len(df_window)):
                 st.warning(f"⚠️ Точка {pname} оказалась за пределами окна после обрезки.")
            
            adjusted_points[pname] = {
                'idx': new_idx,
                'price': pdata['price'],
                'time': df_window.iloc[new_idx]['time'] if 0 <= new_idx < len(df_window) else ''
            }
            
        # Используем обрезанный DF и скорректированные точки далее
        df = df_window
        valid_points = adjusted_points # Заменяем для сохранения
        
        # Определяем метку
        label = 1 if st.session_state.pattern_type == 'bullish' else 2
        
        # АВТОМАТИЧЕСКАЯ ПРОВЕРКА ГЕОМЕТРИИ
        # Передаем adjusted_points, так как цены те же, а индексы важны только для последовательности (которая сохраняется)
        # Но функции проверки могут использовать индексы для расчета наклона. Разница индексов сохраняется, так что ок.
        violations = check_geometry_before_save(valid_points, label, selected_timeframe)
        if violations:
            st.warning("⚠️ **Обнаружены нарушения геометрических ограничений:**")
            for violation in violations:
                st.warning(f"   • {violation}")
            
            st.info("💡 Исправьте точки для соответствия геометрическим ограничениям или установите флаг ниже для сохранения")
            
            # Используем checkbox для подтверждения сохранения
            save_anyway = st.checkbox("✅ Сохранить несмотря на нарушения", value=False, key="save_anyway_checkbox")
            if not save_anyway:
                return
        
        # Сохраняем свечи
        candles_file = annotator.save_candles(
            df=df,
            ticker=ticker,
            timeframe=selected_timeframe
        )
        
        # Создаем информацию о паттерне
        pattern_info = {
            'pattern': 'FLAG_0_1_2_3_4' if label == 1 else 'BEARISH_FLAG_0_1_2_3_4',
            'timeframe': selected_timeframe,
            't0': valid_points['T0'],
            't1': valid_points['T1'],
            't2': valid_points['T2'],
            't3': valid_points['T3'],
            't4': valid_points['T4'],
            'labeled_manually': True
        }
        
        # Проверяем, редактируем ли существующую аннотацию
        # Также проверяем, есть ли editing_file, даже если idx = None (для случаев, когда запись не найдена, но файл загружен)
        editing_mode = ('editing_annotation_idx' in st.session_state and st.session_state.editing_annotation_idx is not None) or \
                       ('editing_file' in st.session_state and st.session_state.editing_file)
        
        if editing_mode:
            # Обновляем существующую аннотацию
            editing_file = st.session_state.get('editing_file')
            editing_idx = st.session_state.get('editing_annotation_idx')
            
            # Находим строку в annotations
            annotations_df = annotator.annotations.copy()
            row_idx = None
            
            # Если есть индекс, используем его
            if editing_idx is not None and editing_idx in annotations_df.index:
                row_idx = editing_idx
            elif editing_file:
                # Ищем по файлу
                mask = annotations_df['file'] == editing_file
                if not mask.any():
                    # Пробуем найти по имени файла
                    import os
                    file_basename = os.path.basename(editing_file)
                    mask = annotations_df['file'].str.endswith(file_basename)
                
                if mask.any():
                    matching_indices = annotations_df[mask].index.tolist()
                    row_idx = matching_indices[0]
            
            if row_idx is not None:
                # Обновляем существующую аннотацию
                # Обновляем координаты
                for point_name in ['T0', 'T1', 'T2', 'T3', 'T4']:
                    point_lower = point_name.lower()
                    point_data = valid_points.get(point_name)
                    if point_data:
                        annotations_df.at[row_idx, f'{point_lower}_idx'] = point_data['idx']
                        annotations_df.at[row_idx, f'{point_lower}_price'] = point_data['price']
                
                # Сохраняем
                annotator.annotations = annotations_df
                annotator.save_annotations()
                
                st.success(f"✅ Координаты обновлены в существующей аннотации!")
            else:
                # Если не найдено, создаем новую запись
                st.warning("⚠️ Запись не найдена в базе. Будет создана новая запись.")
                editing_mode = False
        else:
            # Добавляем новую аннотацию с координатами точек
            annotator.annotate_pattern(
                candles_file=candles_file,
                label=label,
                ticker=ticker,
                timeframe=selected_timeframe,
                pattern_type=pattern_info['pattern'],
                notes=f"Размечено вручную. Тип: {st.session_state.pattern_type}",
                points=valid_points
            )
            
            st.success(f"✅ Паттерн сохранен для обучения! (label={label}, {'Бычий' if label==1 else 'Медвежий'})")
        
        # Очищаем точки для следующей разметки
        st.session_state.points = {}
        if 'editing_annotation_idx' in st.session_state:
            st.session_state.editing_annotation_idx = None
        st.rerun()
        
    except Exception as e:
        st.error(f"❌ Ошибка сохранения: {e}")
        import traceback
        st.code(traceback.format_exc())


# ============================================================================
# ОСНОВНОЙ КОД
# ============================================================================

# --- Боковая панель ---
with st.sidebar:
    st.header("⚙️ Настройки")
    
    # Режим работы
    annotation_mode = st.radio(
        "Режим работы",
        ["Ручная разметка", "Нейросеть сканер", "Математический сканер", "Математический сканер (PROD)", "Добавить координаты к существующим", "Исправить записи с нарушениями"],
        help="Ручная разметка - создание новых аннотаций вручную\nНейросеть сканер - автоматический поиск паттернов с подтверждением/отклонением\nМатематический сканер - поиск всех паттернов на истории\nМатематический сканер (PROD) - поиск только СВЕЖИХ паттернов (как в боевом режиме)\nДобавить координаты - дополнение существующих аннотаций координатами точек\nИсправить записи с нарушениями - переразметка записей, не соответствующих геометрическим ограничениям",
        key='annotation_mode_radio'
    )
    # Сохраняем режим в session_state для использования в основной области
    st.session_state.annotation_mode = annotation_mode
    
    st.divider()
    
    # Режим: Добавление координат к существующим
    if annotation_mode == "Добавить координаты к существующим":
        st.subheader("📋 Выбор файла для редактирования")
        
        # Загружаем список аннотаций
        try:
            annotations_list = annotator.annotations.copy()
            
            # Фильтруем те, у которых нет координат (уже размеченные автоматически скрыты)
            if 't0_idx' in annotations_list.columns:
                missing_coords = annotations_list['t0_idx'].isna()
                annotations_list = annotations_list[missing_coords].copy()
            
            # Показываем статистику
            total_count = len(annotator.annotations)
            if 't0_idx' in annotator.annotations.columns:
                completed_count = annotator.annotations['t0_idx'].notna().sum()
                st.caption(f"Всего: {total_count} | Размечено: {completed_count} | Осталось: {len(annotations_list)}")
            
            if len(annotations_list) > 0:
                # Создаем список для выбора
                file_options = []
                for idx, row in annotations_list.iterrows():
                    label_name = {0: 'нет', 1: 'бычий', 2: 'медвежий'}.get(row.get('label', 0), 'неизвестно')
                    option_text = f"{row.get('ticker', '?')} ({row.get('timeframe', '?')}) - {label_name} - {row.get('file', '?')}"
                    file_options.append((idx, option_text))
                
                selected_idx = st.selectbox(
                    "Выберите файл для добавления координат",
                    options=[opt[0] for opt in file_options],
                    format_func=lambda x: [opt[1] for opt in file_options if opt[0] == x][0] if file_options else ""
                )
                
                if st.button("📥 Загрузить выбранный файл", type="primary"):
                    # Находим выбранную строку по индексу
                    selected_row = annotations_list.loc[selected_idx]
                    file_path = annotator.data_dir / selected_row['file']
                    
                    if file_path.exists():
                        df = pd.read_csv(file_path)
                        st.session_state.df_data = df
                        st.session_state.points = {}
                        st.session_state.current_ticker = selected_row.get('ticker', 'UNKNOWN')
                        st.session_state.current_timeframe = selected_row.get('timeframe', '1h')
                        st.session_state.editing_annotation_idx = selected_idx
                        st.session_state.editing_file = selected_row['file']
                        st.session_state.pattern_type = 'bullish' if selected_row.get('label') == 1 else 'bearish'
                        st.success(f"✅ Файл загружен: {selected_row['file']}")
                        st.rerun()
                    else:
                        st.error(f"❌ Файл не найден: {file_path}")
            else:
                st.info("✅ Все аннотации уже имеют координаты!")
                st.info("Или выберите режим 'Новая разметка' для создания новых")
        except Exception as e:
            st.error(f"Ошибка загрузки аннотаций: {e}")
        
        st.divider()
    
    # Режим: Исправить записи с нарушениями
    if annotation_mode == "Исправить записи с нарушениями":
        st.subheader("⚠️ Исправление нарушений геометрии")
        
        violations_file = Path("neural_network/data/violations_list.json")
        
        if violations_file.exists():
            try:
                with open(violations_file, 'r', encoding='utf-8') as f:
                    violations_list = json.load(f)
                
                # Фильтруем только те записи, которые существуют в annotations.csv
                annotations_df = annotator.annotations.copy()
                existing_files = set(annotations_df['file'].values)
                
                # Фильтруем нарушения, оставляя только существующие записи
                filtered_violations = []
                for viol in violations_list:
                    viol_file = viol.get('file', '')
                    # Проверяем по полному пути или по имени файла
                    if viol_file in existing_files:
                        filtered_violations.append(viol)
                    else:
                        # Пробуем найти по имени файла
                        import os
                        file_basename = os.path.basename(viol_file)
                        if any(file_basename in f for f in existing_files):
                            filtered_violations.append(viol)
                
                violations_list = filtered_violations
                
                st.caption(f"Найдено записей с нарушениями: {len(violations_list)}")
                
                # Кнопка для обновления списка нарушений
                if st.button("🔄 Обновить список нарушений", help="Пересоздать список на основе текущих данных"):
                    import subprocess
                    try:
                        result = subprocess.run(
                            ["python3", "neural_network/list_violations.py"],
                            cwd=Path.cwd(),
                            capture_output=True,
                            text=True,
                            timeout=30
                        )
                        if result.returncode == 0:
                            st.success("✅ Список нарушений обновлен!")
                            st.rerun()
                        else:
                            st.error(f"❌ Ошибка обновления: {result.stderr}")
                    except Exception as e:
                        st.error(f"❌ Ошибка обновления: {e}")
                
                if len(violations_list) > 0:
                    # Создаем список для выбора
                    violation_options = []
                    for i, viol in enumerate(violations_list):
                        pattern_type = "LONG (бычий)" if viol['label'] == 1 else "SHORT (медвежий)"
                        option_text = f"{i+1}. {pattern_type} - {viol['ticker']} ({viol['timeframe']})"
                        violation_options.append((i, option_text, viol))
                    
                    selected_viol_idx = st.selectbox(
                        "Выберите запись для исправления",
                        options=[opt[0] for opt in violation_options],
                        format_func=lambda x: [opt[1] for opt in violation_options if opt[0] == x][0] if violation_options else ""
                    )
                    
                    # Показываем информацию о нарушениях
                    selected_viol = violation_options[selected_viol_idx][2]
                    st.info(f"**Нарушения:**\n" + "\n".join([f"• {v}" for v in selected_viol['violations']]))
                    
                    # Показываем текущие координаты
                    with st.expander("📊 Текущие координаты"):
                        points = selected_viol['current_points']
                        for point_name in ['T0', 'T1', 'T2', 'T3', 'T4']:
                            point_data = points.get(point_name, {})
                            st.text(f"{point_name}: индекс {point_data.get('idx', 'N/A'):.0f}, цена {point_data.get('price', 0):.2f}")
                    
                    if st.button("📥 Загрузить для исправления", type="primary"):
                        # Загружаем файл со свечами
                        file_path = annotator.data_dir / selected_viol['file']
                        
                        if file_path.exists():
                            df = pd.read_csv(file_path)
                            st.session_state.df_data = df
                            
                            # Загружаем текущие точки из аннотации
                            current_points = selected_viol['current_points']
                            # Добавляем время из DataFrame для каждой точки
                            loaded_points = {}
                            for point_name in ['T0', 'T1', 'T2', 'T3', 'T4']:
                                point_data = current_points[point_name]
                                idx = int(point_data['idx'])
                                # Убеждаемся, что индекс в пределах DataFrame
                                if 0 <= idx < len(df):
                                    loaded_points[point_name] = {
                                        'idx': idx,
                                        'price': point_data['price'],
                                        'time': df.iloc[idx]['time'] if 'time' in df.columns else ''
                                    }
                                else:
                                    # Если индекс вне пределов, используем пустое время
                                    loaded_points[point_name] = {
                                        'idx': idx,
                                        'price': point_data['price'],
                                        'time': ''
                                    }
                            st.session_state.points = loaded_points
                            
                            st.session_state.current_ticker = selected_viol['ticker']
                            st.session_state.current_timeframe = selected_viol['timeframe']
                            st.session_state.pattern_type = 'bullish' if selected_viol['label'] == 1 else 'bearish'
                            
                            # Находим индекс аннотации в annotations.csv
                            annotations_df = annotator.annotations.copy()
                            
                            # Пробуем найти по полному пути к файлу
                            search_file = selected_viol['file']
                            mask = annotations_df['file'] == search_file
                            
                            # Если не найдено, пробуем найти по имени файла (без пути)
                            if not mask.any():
                                import os
                                file_basename = os.path.basename(search_file)
                                mask = annotations_df['file'].str.endswith(file_basename)
                            
                            # Если все еще не найдено, пробуем найти по тикеру и таймфрейму
                            if not mask.any():
                                ticker = selected_viol['ticker']
                                timeframe = selected_viol['timeframe']
                                mask = (annotations_df['ticker'] == ticker) & (annotations_df['timeframe'] == timeframe)
                                # Берем последнюю запись с таким тикером и таймфреймом
                                if mask.any():
                                    matching_rows = annotations_df[mask]
                                    # Берем последнюю запись
                                    last_idx = matching_rows.index[-1]
                                    st.session_state.editing_annotation_idx = last_idx
                                    st.session_state.editing_file = annotations_df.loc[last_idx, 'file']
                                    st.warning(f"⚠️ Найдена запись по тикеру и таймфрейму. Используется файл: {st.session_state.editing_file}")
                                else:
                                    st.error(f"❌ Аннотация не найдена в базе!")
                                    st.error(f"   Искали файл: {search_file}")
                                    st.error(f"   Тикер: {ticker}, Таймфрейм: {timeframe}")
                                    st.info("💡 Запись будет создана как новая при сохранении")
                                    # Не устанавливаем editing_file, чтобы создать новую запись
                                    st.session_state.editing_annotation_idx = None
                                    st.session_state.editing_file = None
                            else:
                                matching_indices = annotations_df[mask].index.tolist()
                                if matching_indices:
                                    st.session_state.editing_annotation_idx = matching_indices[0]
                                    st.session_state.editing_file = annotations_df.loc[matching_indices[0], 'file']
                                    
                                    st.success(f"✅ Запись загружена для исправления!")
                                    st.info("⚠️ Текущие точки отображены на графике. Исправьте их и сохраните изменения.")
                            
                            # Всегда разрешаем загрузку, даже если аннотация не найдена
                            # Пользователь сможет сохранить как новую запись
                            st.rerun()
                        else:
                            st.error(f"❌ Файл не найден: {file_path}")
                else:
                    st.success("✅ Нет записей с нарушениями!")
            except Exception as e:
                st.error(f"Ошибка загрузки списка нарушений: {e}")
                import traceback
                st.code(traceback.format_exc())
        else:
            st.warning("⚠️ Файл со списком нарушений не найден!")
            st.info("Запустите скрипт: python neural_network/list_violations.py")
        
        st.divider()
    
    # Режим: Ручная разметка, Нейросеть сканер или Математический сканер (обычный и PROD)
    if annotation_mode in ["Ручная разметка", "Нейросеть сканер", "Математический сканер", "Математический сканер (PROD)"]:
        # Список популярных инструментов
        COMMON_TICKERS = [
            "MXH6", "RIH6", "SiH6", "GDH6", "EuH6", "BRG6", "NGG6", # Фьючерсы
            "SBER", "GAZP", "LKOH", "ROSN", "NVTK", "GMKN", "YNDX", "VTBR", "SNGS", "PLZL", # Топ акций
            "MGNT", "TATN", "MTSS", "ALRS", "CHMF", "NLMK", "SBERP", "SNGSP", "MOEX", "AFKS"
        ]
        
        # Выбор инструмента
        st.write("### Инструмент")
        selection_method = st.radio("Способ выбора", ["Из списка", "Ввести вручную"], horizontal=True, label_visibility="collapsed")
        
        if selection_method == "Из списка":
            ticker = st.selectbox("Выберите тикер", COMMON_TICKERS)
        else:
            ticker = st.text_input("Введите тикер", value="VKCO")
            
        # Автоматическое определение Class Code
        default_class_code = "SPBFUT" if len(ticker) == 4 and ticker[-2].isdigit() else "TQBR"
        class_code = st.selectbox("Class Code", ["TQBR", "SPBFUT", "FUT"], index=["TQBR", "SPBFUT", "FUT"].index(default_class_code))
    
        # Выбор таймфрейма
        selected_timeframe = st.selectbox(
            "Таймфрейм",
            options=list(TIMEFRAMES.keys()),
            format_func=lambda x: TIMEFRAMES[x]['title'],
            index=1
        )
        tf_config = TIMEFRAMES[selected_timeframe]
    else:
        # В режиме редактирования используем значения из session_state
        selected_timeframe = st.session_state.get('current_timeframe', '1h')
        tf_config = TIMEFRAMES.get(selected_timeframe, TIMEFRAMES['1h'])
        ticker = st.session_state.get('current_ticker', 'UNKNOWN')
        class_code = "TQBR"  # По умолчанию для режима редактирования
    
    # Выбор режима загрузки данных
    date_mode = st.radio(
        "Режим загрузки данных",
        ["По количеству дней", "По датам"],
        horizontal=True
    )
    
    if date_mode == "По количеству дней":
        days_back = st.slider("Дней истории", 1, max(30, tf_config['days_back']), 
                             min(10, tf_config['days_back']))
        from_date = None
        to_date = None
    else:
        # Выбор дат
        col_date1, col_date2 = st.columns(2)
        with col_date1:
            from_date = st.date_input(
                "Начальная дата",
                value=datetime.now().date() - timedelta(days=30),
                max_value=datetime.now().date()
            )
        with col_date2:
            to_date = st.date_input(
                "Конечная дата",
                value=datetime.now().date(),
                max_value=datetime.now().date(),
                min_value=from_date
            )
        
        # Преобразуем даты в datetime для API (с UTC timezone)
        from_date = datetime.combine(from_date, datetime.min.time())
        from_date = from_date.replace(tzinfo=timezone.utc)
        to_date = datetime.combine(to_date, datetime.max.time())
        to_date = to_date.replace(tzinfo=timezone.utc)
        
        days_back = None
    
    # Кнопка загрузки данных
    if st.button("📥 Загрузить данные", type="primary"):
        with st.spinner("Загрузка данных..."):
            try:
                # Пересоздаем scanner (кэш не поддерживается в ComplexFlagScanner)
                use_cache_current = st.session_state.get('use_cache', False)
                current_scanner = ComplexFlagScanner(token)
                
                if use_cache_current:
                    st.info(f"💾 Используется кэш для ускорения загрузки")
                else:
                    st.info(f"🔄 Кэш отключен, загрузка напрямую через API")
                
                if date_mode == "По количеству дней":
                    st.info(f"🔄 Загрузка данных для {ticker} ({class_code}), таймфрейм: {selected_timeframe}, дней назад: {days_back}")
                    df = current_scanner.get_candles_df(
                        ticker, 
                        class_code, 
                        days_back=days_back,
                        interval=tf_config['interval']
                    )
                else:
                    # Загрузка по датам
                    st.info(f"🔄 Загрузка данных для {ticker} ({class_code}), таймфрейм: {selected_timeframe}, период: {from_date.strftime('%Y-%m-%d')} - {to_date.strftime('%Y-%m-%d')}")
                    df = current_scanner.get_candles_df_by_dates(
                        ticker,
                        class_code,
                        from_date=from_date,
                        to_date=to_date,
                        interval=tf_config['interval']
                    )
                
                if df is None:
                    st.error("❌ Данные не загружены: метод вернул None. Проверьте подключение к API и корректность параметров.")
                elif df.empty:
                    # Проверяем, существует ли инструмент
                    try:
                        with Client(token) as client:
                            try:
                                item = client.instruments.get_instrument_by(
                                    id_type=InstrumentIdType.INSTRUMENT_ID_TYPE_TICKER,
                                    class_code=class_code,
                                    id=ticker
                                ).instrument
                                
                                if item:
                                    st.warning(f"⚠️ Инструмент {ticker} ({class_code}) найден (UID: {item.uid}), но нет данных для указанного периода.")
                                    
                                    # Дополнительная информация в зависимости от типа инструмента и таймфрейма
                                    suggestions = []
                                    if class_code == 'SPBFUT':
                                        suggestions.append("⚠️ Для фьючерсов доступны данные только за период их обращения (обычно 1-3 месяца)")
                                        suggestions.append(f"💡 Для таймфрейма {selected_timeframe} попробуйте уменьшить количество дней назад до 30-60 дней")
                                    else:
                                        suggestions.append("💡 Увеличьте количество дней назад (для режима 'По количеству дней')")
                                        suggestions.append("💡 Выберите более ранний период (для режима 'По датам')")
                                    
                                    suggestions.append("💡 Проверьте, торгуется ли инструмент на указанном таймфрейме")
                                    if selected_timeframe == '1d':
                                        suggestions.append("💡 Для таймфрейма 1d может потребоваться больше дней истории (но для фьючерсов это ограничено периодом обращения)")
                                    
                                    if use_cache_current:
                                        suggestions.append("🔄 Попробуйте отключить кэш и загрузить данные напрямую через API")
                                    
                                    st.info("\n".join(suggestions))
                                else:
                                    st.error(f"❌ Инструмент {ticker} ({class_code}) не найден в системе.")
                                    st.info(f"💡 Проверьте:\n"
                                           f"- Правильность написания ticker\n"
                                           f"- Правильность class_code (TQBR для акций, SPBFUT для фьючерсов)")
                            except Exception as inst_check:
                                st.error(f"❌ Ошибка проверки инструмента: {inst_check}")
                    except Exception as e:
                        st.error(f"❌ Ошибка подключения к API: {e}")
                    
                    st.error(f"❌ Данные не загружены: получен пустой DataFrame для {ticker} ({class_code}), таймфрейм: {selected_timeframe}")
                else:
                    st.session_state.df_data = df
                    st.session_state.points = {}  # Сбрасываем точки
                    st.session_state.current_ticker = ticker  # Сохраняем для сохранения
                    st.session_state.current_timeframe = selected_timeframe  # Сохраняем для сохранения
                    # Сбрасываем предсказания нейросети при загрузке новых данных
                    if annotation_mode == "Нейросеть сканер":
                        st.session_state.nn_predictions = []
                        st.session_state.confirmed_patterns = []
                        st.session_state.rejected_patterns = []
                    st.success(f"✅ Загружено {len(df)} свечей для {ticker} ({selected_timeframe})")
            except AttributeError as e:
                st.error(f"❌ Ошибка: метод не найден. Проверьте, что scanner поддерживает нужный метод.\nОшибка: {e}")
                st.exception(e)
            except Exception as e:
                st.error(f"❌ Ошибка загрузки данных: {e}")
                st.exception(e)
    
    st.divider()
    
    # Настройки для режима "Разметка с нейросетью"
    if annotation_mode == "Нейросеть сканер":
        st.subheader("🤖 Настройки нейросети")
        
        model_path = st.text_input(
            "Путь к модели",
            value="neural_network/models/keypoint_model_best.pth",
            help="Путь к файлу обученной модели"
        )
        
        col1, col2 = st.columns(2)
        with col1:
            window_size = st.number_input("Размер окна", min_value=50, max_value=200, value=100, step=10)
        with col2:
            step_size = st.number_input("Шаг окна", min_value=5, max_value=50, value=10, step=5)
        
        min_confidence = st.slider(
            "Минимальная уверенность",
            min_value=0.0,
            max_value=1.0,
            value=0.6,
            step=0.05,
            help="Минимальная вероятность для отображения паттерна"
        )
        
        scan_all_stocks = st.checkbox("🔄 Сканировать ВСЕ доступные акции (может занять время)", value=False, key="nn_scan_all")
        
        st.divider()
        
        # Кнопка поиска паттернов
        if st.session_state.df_data is not None or scan_all_stocks:
            if st.button("🔍 Найти паттерны (нейросеть)", type="primary"):
                if scan_all_stocks:
                    # Режим сканирования ВСЕХ акций
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    found_predictions = []
                    
                    try:
                        # Инициализируем сканер для получения списка акций
                        temp_scanner = BullishFlagScanner(token=os.environ.get("TINKOFF_INVEST_TOKEN"))
                        status_text.text("Получение списка акций...")
                        all_shares = temp_scanner.get_all_shares()
                        total_shares = len(all_shares)
                        
                        tf_config = TIMEFRAMES[selected_timeframe]
                        
                        for i, share in enumerate(all_shares):
                            # Обновляем прогресс
                            progress = (i + 1) / total_shares
                            progress_bar.progress(progress)
                            status_text.text(f"Нейросеть: {share.ticker} ({i+1}/{total_shares})...")
                            
                            try:
                                # Загружаем свечи
                                df_share = temp_scanner.get_candles_by_uid(
                                    share.uid, 
                                    days_back=tf_config['days_back'],
                                    interval=tf_config['interval']
                                )
                                
                                if not df_share.empty and len(df_share) > window_size:
                                    # Ищем паттерны нейросетью
                                    preds = find_patterns_with_nn(
                                        df_share, selected_timeframe, 
                                        window=window_size, step=step_size, 
                                        min_confidence=min_confidence
                                    )
                                    
                                    # Добавляем тикер к предсказаниям
                                    for p in preds:
                                        p['ticker'] = share.ticker
                                        # Сохраняем DF в паттерне (для визуализации потом, хотя это ест память)
                                        # Для нейросети DF может быть большим, сохранять весь DF для каждого паттерна - накладно.
                                        # Но create_chart_with_predictions требует DF.
                                        # Оптимизация: сохраним DF один раз для группы паттернов одного тикера?
                                        # Пока сохраним ссылку, Python оптимизирует память (df один и тот же объект).
                                        p['df'] = df_share 
                                        found_predictions.append(p)
                                        
                            except Exception as e:
                                print(f"Error scanning {share.ticker}: {e}")
                                continue
                        
                        st.session_state.nn_predictions = found_predictions
                        status_text.text(f"Сканирование завершено! Найдено {len(found_predictions)} паттернов.")
                        progress_bar.empty()
                        
                    except Exception as e:
                        st.error(f"Ошибка при сканировании всех акций: {e}")
                
                else:
                    # Обычный режим (один тикер)
                    with st.spinner("Поиск паттернов нейросетью..."):
                        df = st.session_state.df_data
                        predictions = find_patterns_with_nn(
                            df, selected_timeframe, 
                            window=window_size, step=step_size, 
                            min_confidence=min_confidence
                        )
                        # Добавляем текущий тикер
                        for p in predictions:
                            p['ticker'] = ticker
                            p['df'] = df
                            
                        st.session_state.nn_predictions = predictions
                        st.success(f"✅ Найдено паттернов: {len(predictions)}")
        
        # Статистика
        if st.session_state.nn_predictions:
            st.subheader("📊 Статистика")
            confirmed = len(st.session_state.confirmed_patterns)
            rejected = len(st.session_state.rejected_patterns)
            pending = len(st.session_state.nn_predictions) - confirmed - rejected
            
            st.metric("Всего найдено", len(st.session_state.nn_predictions))
            st.metric("✅ Подтверждено", confirmed)
            st.metric("❌ Отклонено", rejected)
            st.metric("⏳ Ожидает", pending)
        
        st.divider()

    # Настройки для режима "Математический сканер" (Обычный и PROD)
    if annotation_mode in ["Математический сканер", "Математический сканер (PROD)"]:
        is_prod_mode = annotation_mode == "Математический сканер (PROD)"
        
        st.subheader(f"🔬 Настройки сканера {'(PROD - только свежие)' if is_prod_mode else '(History - поиск на истории)'}")
        
        scan_all_stocks = st.checkbox("🔄 Сканировать ВСЕ доступные акции (может занять время)", value=False)
        
        # Определяем дефолтное окно в зависимости от таймфрейма
        default_window = 3
        if '5m' in str(selected_timeframe).lower():
            default_window = 10
        elif '1h' in str(selected_timeframe).lower() or 'h' in str(selected_timeframe).lower():
            default_window = 3
        elif '1d' in str(selected_timeframe).lower() or 'd' in str(selected_timeframe).lower():
            default_window = 1
            
        # Используем session_state для отслеживания изменения таймфрейма и обновления слайдера
        if 'last_math_timeframe' not in st.session_state:
            st.session_state.last_math_timeframe = selected_timeframe
        
        window_scan = st.slider(
            "Окно поиска экстремумов (Window)",
            min_value=1,
            max_value=30,
            value=default_window,
            help="Сколько свечей слева и справа должно быть ниже/выше, чтобы точка считалась экстремумом."
        )
        st.session_state.window_scan = window_scan
        
        # Настройка минимальной высоты флагштока
        default_pole_pct = 3.0
        if '5m' in selected_timeframe: 
            default_pole_pct = 1.0
        elif '1d' in selected_timeframe: 
            default_pole_pct = 5.0
            
        min_pole_pct = st.number_input(
            "Минимальная высота флагштока (%)",
            min_value=0.1,
            max_value=100.0,
            value=default_pole_pct,
            step=0.5,
            help="Минимальное изменение цены на флагштоке (T0-T1) в процентах."
        )
        
        # Кнопка поиска доступна если загружены данные ИЛИ включен режим сканирования всех акций
        if st.session_state.df_data is not None or scan_all_stocks:
            btn_label = "🔍 Найти СВЕЖИЕ паттерны (PROD)" if is_prod_mode else "🔍 Найти ВСЕ паттерны (History)"
            if st.button(btn_label, type="primary"):
                scan_type = 'latest' if is_prod_mode else 'all'
                
                # Инициализируем сканеры с настоящим токеном
                bull_scanner = BullishFlagScanner(token=token)
                bear_scanner = BearishFlagScanner(token=token)
                
                found_patterns = []
                
                if scan_all_stocks:
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    try:
                        # Получаем список всех акций
                        status_text.text("Получение списка акций...")
                        all_shares = bull_scanner.get_all_shares()
                        total_shares = len(all_shares)
                        
                        # Ограничим для теста или безопасности, если слишком много? Нет, пользователь просил "всех".
                        # Но API имеет лимиты. Добавим небольшую паузу.
                        
                        tf_config = TIMEFRAMES[selected_timeframe]
                        
                        for i, share in enumerate(all_shares):
                            # Обновляем прогресс
                            progress = (i + 1) / total_shares
                            progress_bar.progress(progress)
                            status_text.text(f"Сканирование {share.ticker} ({i+1}/{total_shares})...")
                            
                            try:
                                # Загружаем свечи
                                df_share = bull_scanner.get_candles_by_uid(
                                    share.uid, 
                                    days_back=tf_config['days_back'],
                                    interval=tf_config['interval']
                                )
                                
                                if not df_share.empty:
                                    # Добавляем EMA (они добавляются внутри get_candles, но на всякий случай)
                                    # Ищем LONG
                                    bull_patterns = bull_scanner.analyze(
                                        df_share, 
                                        timeframe=selected_timeframe, 
                                        window=window_scan, 
                                        scan_type=scan_type,
                                        min_pole_pct=min_pole_pct
                                    )
                                    for p in bull_patterns:
                                        p['type'] = 'bullish'
                                        p['ticker'] = share.ticker # Добавляем тикер
                                        p['df'] = df_share # ВАЖНО: сохраняем DF для отображения!
                                        found_patterns.append(p)
                                        
                                    # Ищем SHORT
                                    bear_patterns = bear_scanner.analyze(
                                        df_share, 
                                        timeframe=selected_timeframe, 
                                        window=window_scan, 
                                        scan_type=scan_type,
                                        min_pole_pct=min_pole_pct
                                    )
                                    for p in bear_patterns:
                                        p['type'] = 'bearish'
                                        p['ticker'] = share.ticker
                                        p['df'] = df_share
                                        found_patterns.append(p)
                                        
                            except Exception as e:
                                print(f"Error scanning {share.ticker}: {e}")
                                continue
                                
                        status_text.text(f"Сканирование завершено! Найдено {len(found_patterns)} паттернов.")
                        progress_bar.empty()
                        
                    except Exception as e:
                        st.error(f"Ошибка при сканировании всех акций: {e}")
                
                else:
                    # Обычный режим (один тикер)
                    with st.spinner(f"Поиск паттернов с window={window_scan}, pole>={min_pole_pct}%, type={scan_type}..."):
                        df = st.session_state.df_data
                        # Ищем LONG
                        bull_patterns = bull_scanner.analyze(
                            df, 
                            timeframe=selected_timeframe, 
                            window=window_scan, 
                            scan_type=scan_type,
                            min_pole_pct=min_pole_pct
                        )
                        for p in bull_patterns:
                            p['type'] = 'bullish'
                            p['ticker'] = ticker # Добавляем текущий тикер
                            p['df'] = df
                            found_patterns.append(p)
                            
                        # Ищем SHORT
                        bear_patterns = bear_scanner.analyze(
                            df, 
                            timeframe=selected_timeframe, 
                            window=window_scan, 
                            scan_type=scan_type,
                            min_pole_pct=min_pole_pct
                        )
                        for p in bear_patterns:
                            p['type'] = 'bearish'
                            p['ticker'] = ticker
                            p['df'] = df
                            found_patterns.append(p)
                        
                st.session_state.math_patterns = found_patterns
                if is_prod_mode:
                    if found_patterns:
                        st.success(f"✅ Найдено свежих паттернов: {len(found_patterns)}")
                    else:
                        st.warning("⚠️ Свежих паттернов не найдено (T4 сформировалась недавно).")
                else:
                    st.success(f"✅ Найдено паттернов: {len(found_patterns)}")
        
        st.divider()
    
    # Тип паттерна (только для ручной разметки)
    if annotation_mode == "Ручная разметка":
        st.subheader("Тип паттерна")
        pattern_type = st.radio(
            "Выберите тип",
            ["Бычий (Bullish)", "Медвежий (Bearish)"],
            index=0 if st.session_state.pattern_type == 'bullish' else 1,
            key='pattern_type_radio'
        )
        st.session_state.pattern_type = 'bullish' if 'Бычий' in pattern_type else 'bearish'
        
        st.divider()
        
        # Инструкции для ручной разметки
        with st.expander("📖 Инструкция (ручная разметка)"):
            st.markdown("""
            **Как размечать паттерн:**
            
            1. Загрузите данные (выберите тикер и нажмите "Загрузить данные")
            2. На графике кликните по свечам чтобы отметить точки:
               - **T0**: Начало паттерна (низ для бычьего, верх для медвежьего)
               - **T1**: Вершина/дно флагштока
               - **T2**: Первый откат
               - **T3**: Второй пик/дно
               - **T4**: Второй откат (финальная точка)
            3. Точки отмечаются последовательно: T0 → T1 → T2 → T3 → T4
            4. После отметки всех точек нажмите "Сохранить для обучения"
            
            **Важно:** Отмечайте точки в хронологическом порядке!
            """)
        
        st.divider()
        
        # Кнопки управления для ручной разметки
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🗑️ Очистить точки"):
                st.session_state.points = {}
                st.rerun()
        
        with col2:
            # Подсчитываем только валидные точки
            valid_points_count = sum(1 for v in st.session_state.points.values() 
                                    if v is not None and isinstance(v, dict) and 'idx' in v)
            
            if st.button("💾 Сохранить для обучения", type="primary", disabled=valid_points_count < 5):
                if valid_points_count == 5:
                    save_annotation()
                else:
                    st.warning("⚠️ Отметьте все 5 точек!")
        
        with col3:
            # Кнопка удаления записи (показываем только если редактируем существующую)
            show_delete = ('editing_file' in st.session_state and st.session_state.editing_file) or \
                          (st.session_state.df_data is not None and 'current_ticker' in st.session_state)
            
            if show_delete:
                if st.button("🗑️ Удалить запись", type="secondary", help="Удалить текущую аннотацию из базы данных"):
                    delete_annotation()
    
    # Инструкции для режима с нейросетью
    if annotation_mode == "Нейросеть сканер":
        with st.expander("📖 Инструкция (разметка с нейросетью)"):
            st.markdown("""
            **Как работать с дашбордом:**
            
            1. **Загрузите данные**: Выберите инструмент, таймфрейм и период, нажмите "Загрузить данные"
            2. **Найдите паттерны**: Нажмите "Найти паттерны (нейросеть)" - нейросеть автоматически найдет возможные паттерны
            3. **Проверьте паттерны**: На графике будут показаны все найденные паттерны
            4. **Подтвердите или отклоните**: Для каждого паттерна нажмите:
               - ✅ **Подтвердить** - если паттерн правильный (сохранится как положительный пример)
               - ❌ **Отклонить** - если паттерн неправильный (сохранится как отрицательный пример)
            
            **Улучшение обучения:**
            - Подтвержденные паттерны используются для обучения модели
            - Отклоненные паттерны помогают модели лучше различать ложные срабатывания
            - Чем больше данных вы разметите, тем лучше будет работать модель
            """)

# --- Основная область ---

if st.session_state.df_data is None:
    st.info("👈 Выберите инструмент и таймфрейм в боковой панели, затем нажмите 'Загрузить данные'")
else:
    df = st.session_state.df_data
    
    # Получаем сохраненные значения для использования в функциях
    current_ticker = st.session_state.get('current_ticker', ticker)
    current_timeframe = st.session_state.get('current_timeframe', selected_timeframe)
    
    # Получаем режим работы из session_state (сохраняется в боковой панели)
    annotation_mode = st.session_state.get('annotation_mode', 'Ручная разметка')
    
    # Режим: Разметка с нейросетью
    if annotation_mode == "Нейросеть сканер":
        # Отображаем график с предсказаниями
        if st.session_state.nn_predictions:
            # Проверяем, есть ли паттерны от разных тикеров
            unique_tickers = set()
            for pred in st.session_state.nn_predictions:
                if 'ticker' in pred:
                    unique_tickers.add(pred['ticker'])
            multiple_tickers = len(unique_tickers) > 1
            
            # Управление отображением паттернов
            st.subheader("🔍 Управление отображением паттернов")
            
            col_view1, col_view2, col_view3 = st.columns([2, 1, 1])
            
            with col_view1:
                show_all = st.checkbox(
                    "Показать все паттерны",
                    value=st.session_state.show_all_patterns,
                    key='show_all_checkbox',
                    help="Если выключено, будет показан только выбранный паттерн"
                )
                st.session_state.show_all_patterns = show_all
            
            with col_view2:
                if not show_all and len(st.session_state.nn_predictions) > 0:
                    # Сортируем паттерны по вероятности для выбора
                    sorted_preds = sorted(st.session_state.nn_predictions, key=lambda x: x['probability'], reverse=True)
                    pattern_options = []
                    class_names = {0: 'нет паттерна', 1: 'бычий', 2: 'медвежий'}
                    
                    for idx, pred in enumerate(sorted_preds):
                        pred_name = class_names.get(pred['class'], 'неизвестно')
                        # Проверяем статус паттерна
                        points = pred.get('points', [])
                        window_start = pred.get('window_start', points[0]['idx'] if points and len(points) > 0 else 0)
                        window_end = pred.get('window_end', points[4]['idx'] if points and len(points) > 4 else 0)
                        pattern_id = f"{idx}_{window_start}_{window_end}"
                        is_confirmed = any(cp['id'] == pattern_id for cp in st.session_state.confirmed_patterns)
                        is_rejected = any(rp['id'] == pattern_id for rp in st.session_state.rejected_patterns)
                        status = "✅" if is_confirmed else "❌" if is_rejected else "⏳"
                        pattern_options.append(f"#{idx+1}: {pred_name} ({pred['probability']:.1%}) {status}")
                    
                    selected_option = st.selectbox(
                        "Выберите паттерн",
                        options=list(range(len(pattern_options))),
                        format_func=lambda x: pattern_options[x] if x < len(pattern_options) else "",
                        index=st.session_state.selected_pattern_idx if st.session_state.selected_pattern_idx is not None and st.session_state.selected_pattern_idx < len(pattern_options) else 0,
                        key='pattern_selector'
                    )
                    st.session_state.selected_pattern_idx = selected_option
                else:
                    st.session_state.selected_pattern_idx = None
            
            with col_view3:
                if not show_all:
                    st.info(f"Показан паттерн #{st.session_state.selected_pattern_idx + 1 if st.session_state.selected_pattern_idx is not None else 0}")
                else:
                    st.info(f"Показано паттернов: {len(st.session_state.nn_predictions)}")
            
            st.divider()
            
            # Сортируем предсказания по вероятности (нужно для работы с multiple_tickers)
            sorted_preds = sorted(st.session_state.nn_predictions, key=lambda x: x['probability'], reverse=True)
            
            # Определяем данные для графика
            display_df = df
            display_ticker = current_ticker
            
            # Если выбран конкретный паттерн (и особенно если тикеров много), берем его данные
            if not show_all and st.session_state.selected_pattern_idx is not None:
                if st.session_state.selected_pattern_idx < len(sorted_preds):
                    sel_pred = sorted_preds[st.session_state.selected_pattern_idx]
                    if 'df' in sel_pred: display_df = sel_pred['df']
                    if 'ticker' in sel_pred: display_ticker = sel_pred['ticker']

            # Создаем график с учетом настроек отображения
            fig = create_chart_with_predictions(
                display_df, 
                st.session_state.nn_predictions if not multiple_tickers else ([sorted_preds[st.session_state.selected_pattern_idx]] if st.session_state.selected_pattern_idx is not None and st.session_state.selected_pattern_idx < len(sorted_preds) else []),
                st.session_state.confirmed_patterns,
                st.session_state.rejected_patterns,
                display_ticker,
                current_timeframe,
                selected_pattern_idx=st.session_state.selected_pattern_idx if not show_all and not multiple_tickers else (0 if multiple_tickers else None),
                show_all=show_all
            )
            st.plotly_chart(fig, use_container_width=True, key="nn_chart")
            
            # Список паттернов для подтверждения/отклонения
            st.subheader("📋 Найденные паттерны")
            
            class_names = {0: 'нет паттерна', 1: 'бычий', 2: 'медвежий'}
            
            for pattern_idx, prediction in enumerate(st.session_state.nn_predictions):
                points = prediction.get('points', [])
                window_start = prediction.get('window_start', points[0]['idx'] if points and len(points) > 0 else 0)
                window_end = prediction.get('window_end', points[4]['idx'] if points and len(points) > 4 else 0)
                pattern_id = f"{pattern_idx}_{window_start}_{window_end}"
                is_confirmed = any(cp['id'] == pattern_id for cp in st.session_state.confirmed_patterns)
                is_rejected = any(rp['id'] == pattern_id for rp in st.session_state.rejected_patterns)
                
                if is_confirmed or is_rejected:
                    continue  # Пропускаем уже обработанные
                
                with st.container():
                    col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
                    
                    with col1:
                        predicted_class = prediction['class']
                        pred_prob = prediction['probability']
                        predicted_name = class_names.get(predicted_class, 'неизвестно')
                        
                        # Показываем точки
                        point_names = ['T0', 'T1', 'T2', 'T3', 'T4']
                        points_text = ", ".join([
                            f"{point_names[i] if i < len(point_names) else f'T{i}'}(idx={p['idx']}, цена={p['price']:.2f})" 
                            for i, p in enumerate(prediction.get('points', []))
                        ])
                        
                        st.write(f"**Паттерн #{pattern_idx + 1}**: {predicted_name} | Вероятность: {pred_prob:.1%}")
                        st.caption(f"Точки: {points_text}")
                        points = prediction.get('points', [])
                        window_start = prediction.get('window_start', points[0]['idx'] if points and len(points) > 0 else 0)
                        window_end = prediction.get('window_end', points[4]['idx'] if points and len(points) > 4 else 0)
                        st.caption(f"Окно: {window_start} - {window_end}")
                    
                    with col2:
                        if st.button(f"✅ Подтвердить", key=f"confirm_{pattern_idx}", type="primary"):
                            # Сохраняем подтвержденный паттерн
                            if save_confirmed_pattern(prediction, df, current_ticker, current_timeframe):
                                st.session_state.confirmed_patterns.append({
                                    'id': pattern_id,
                                    'pattern': prediction
                                })
                                st.success("✅ Паттерн подтвержден и сохранен!")
                                st.rerun()
                    
                    with col3:
                        if st.button(f"❌ Отклонить", key=f"reject_{pattern_idx}", type="secondary"):
                            # Сохраняем отклоненный паттерн
                            if save_rejected_pattern(prediction, df, current_ticker, current_timeframe):
                                st.session_state.rejected_patterns.append({
                                    'id': pattern_id,
                                    'pattern': prediction
                                })
                                st.success("❌ Паттерн отклонен и сохранен как отрицательный пример!")
                                st.rerun()
                    
                    with col4:
                        # Показываем геометрические проверки
                        if len(prediction['points']) == 5:
                            points_dict = {p['name']: {'idx': p['idx'], 'price': p['price']} for p in prediction['points']}
                            t0 = points_dict['T0']['price']
                            t1 = points_dict['T1']['price']
                            t2 = points_dict['T2']['price']
                            t3 = points_dict['T3']['price']
                            t4 = points_dict['T4']['price']
                            t0_idx = points_dict['T0']['idx']
                            t1_idx = points_dict['T1']['idx']
                            t2_idx = points_dict['T2']['idx']
                            t3_idx = points_dict['T3']['idx']
                            t4_idx = points_dict['T4']['idx']
                            
                            if predicted_class == 1:  # LONG
                                violations = check_long_constraints(
                                    t0, t1, t2, t3, t4, current_timeframe, 
                                    t0_idx, t1_idx, t2_idx, t3_idx, t4_idx
                                )
                            elif predicted_class == 2:  # SHORT
                                violations = check_short_constraints(
                                    t0, t1, t2, t3, t4, current_timeframe,
                                    t0_idx, t1_idx, t2_idx, t3_idx, t4_idx
                                )
                            else:
                                violations = []
                            
                            if violations:
                                st.warning(f"⚠️ {len(violations)} нарушений")
                                with st.expander("Детали нарушений"):
                                    for v in violations:
                                        st.text(f"• {v}")
                            else:
                                st.success("✅ Геометрия OK")
                    
                    st.divider()
        else:
            st.info("👆 Нажмите 'Найти паттерны (нейросеть)' в боковой панели для поиска паттернов")
            
            # Показываем график без паттернов
            fig = create_chart_with_predictions(
                df, [], [], [], current_ticker, current_timeframe
            )
            st.plotly_chart(fig, use_container_width=True, key="chart")
    
    # Режим: Математический сканер (Обычный и PROD)
    elif annotation_mode in ["Математический сканер", "Математический сканер (PROD)"]:
        if 'math_patterns' in st.session_state and st.session_state.math_patterns:
            is_prod_mode = annotation_mode == "Математический сканер (PROD)"
            st.subheader(f"📋 Результаты математического сканера {'(PROD)' if is_prod_mode else ''}")
            
            patterns = st.session_state.math_patterns
            
            # Конвертируем паттерны в формат для create_chart_with_predictions
            formatted_patterns = []
            for p in patterns:
                is_bullish = p['type'] == 'bullish'
                points = []
                for pname in ['t0', 't1', 't2', 't3', 't4']:
                    if pname in p:
                        points.append({
                            'name': pname.upper(),
                            'idx': p[pname]['idx'],
                            'price': p[pname]['price']
                        })
                
                formatted_patterns.append({
                    'class': 1 if is_bullish else 2,
                    'probability': p.get('quality_score', 0) / 100.0, # Нормализуем для отображения
                    'points': points,
                    'window_start': p['t0']['idx'],
                    'window_end': p['t4']['idx'],
                    'ticker': p.get('ticker', current_ticker) # Добавляем тикер
                })
            
            # Проверяем, есть ли паттерны от разных тикеров
            unique_tickers = set(fp['ticker'] for fp in formatted_patterns)
            multiple_tickers = len(unique_tickers) > 1
            
            # Управление отображением
            col_view1, col_view2 = st.columns([1, 2])
            
            with col_view1:
                # Если разные тикеры, принудительно отключаем "Показать все" и блокируем чекбокс
                if multiple_tickers:
                    show_all_math = False
                    st.checkbox("Показать все паттерны", value=False, disabled=True, key='show_all_math_checkbox_disabled', help="Недоступно при просмотре результатов по разным инструментам")
                    st.info(f"Найдено по: {', '.join(list(unique_tickers)[:3])}...")
                else:
                    show_all_math = st.checkbox(
                        "Показать все паттерны",
                        value=True,
                        key='show_all_math_checkbox'
                    )
            
            # Всегда создаем селектор, чтобы пользователь мог выбрать паттерн
            with col_view2:
                pattern_options = []
                for idx, p in enumerate(patterns):
                    p_type = "LONG" if p['type'] == 'bullish' else "SHORT"
                    p_ticker = p.get('ticker', current_ticker)
                    quality = p.get('quality_score', 0)
                    # Добавляем тикер в описание
                    pattern_options.append(f"#{idx+1}: {p_ticker} - {p_type} [{p.get('type')}] (Q: {quality})")
                
                # Добавляем поиск для удобства
                search_term = st.text_input(
                    "🔍 Поиск по тикеру или типу",
                    value="",
                    key='pattern_search_math',
                    placeholder="Например: VSMO или LONG"
                )
                
                # Фильтруем опции по поисковому запросу
                filtered_indices = [] # Храним оригинальные индексы
                filtered_options = []
                
                if search_term:
                    search_lower = search_term.lower()
                    for idx, option in enumerate(pattern_options):
                        if search_lower in option.lower():
                            filtered_options.append(option)
                            filtered_indices.append(idx)
                else:
                    filtered_options = pattern_options
                    filtered_indices = list(range(len(pattern_options)))

                if not filtered_options:
                     st.info("🔍 Ничего не найдено")
                     selected_math_idx = 0
                else:
                    # Используем session_state для сохранения выбора
                    if 'last_selected_math_idx' not in st.session_state:
                         st.session_state.last_selected_math_idx = 0
                    
                    # Пытаемся найти индекс в отфильтрованном списке, который соответствует последнему выбранному
                    current_index_in_filtered = 0
                    if st.session_state.last_selected_math_idx in filtered_indices:
                         current_index_in_filtered = filtered_indices.index(st.session_state.last_selected_math_idx)
                    
                    # Создаем контейнеры для правильного визуального порядка
                    selector_container = st.empty()
                    buttons_container = st.container()
                    
                    # --- ЛОГИКА КНОПОК ---
                    # Рисуем кнопки в buttons_container (который будет ниже селектора)
                    
                    new_idx_in_filtered = current_index_in_filtered
                    changed_by_buttons = False
                    
                    with buttons_container:
                        col_nav1, col_nav2, col_nav3 = st.columns([1, 6, 1])
                        with col_nav1:
                            if st.button("⬅️", key='prev_pattern_btn', help="Предыдущий паттерн"):
                                new_idx_in_filtered = max(0, current_index_in_filtered - 1)
                                changed_by_buttons = True
                        with col_nav3:
                            if st.button("➡️", key='next_pattern_btn', help="Следующий паттерн"):
                                new_idx_in_filtered = min(len(filtered_options) - 1, current_index_in_filtered + 1)
                                changed_by_buttons = True
                    
                    if changed_by_buttons:
                        real_idx = filtered_indices[new_idx_in_filtered]
                        st.session_state.last_selected_math_idx = real_idx
                        # Обновляем state для селектора (безопасно, т.к. селектор еще не создан в этом прогоне)
                        st.session_state['math_pattern_selector'] = new_idx_in_filtered
                        # Обновляем локальную переменную
                        current_index_in_filtered = new_idx_in_filtered
                        st.rerun()

                    # --- СЕЛЕКТОР ---
                    # Рисуем в selector_container, который был создан выше (визуально он над кнопками)
                    with selector_container:
                        selected_sorted_idx = st.selectbox(
                            "Выберите паттерн из списка", 
                            range(len(filtered_options)), 
                            format_func=lambda x: filtered_options[x] if x < len(filtered_options) else "",
                            index=current_index_in_filtered,
                            key='math_pattern_selector'
                        )
                    
                    # Если пользователь изменил выбор через селектор (и это не вызвано кнопками)
                    if selected_sorted_idx != current_index_in_filtered and not changed_by_buttons:
                         real_idx = filtered_indices[selected_sorted_idx]
                         st.session_state.last_selected_math_idx = real_idx
                         st.rerun()
                    
                    # Используем значение из state для дальнейшей работы
                    selected_math_idx = st.session_state.last_selected_math_idx

            
            # Если выбран конкретный паттерн, используем его данные (df и ticker)
            display_df = df
            display_ticker = current_ticker
            
            # Определяем, что показывать на графике
            if show_all_math:
                # Показываем все паттерны, игнорируя селектор
                patterns_for_chart = formatted_patterns
                selected_idx_for_chart = None
                # Берем DF из первого паттерна (или текущий)
                if formatted_patterns:
                    first_ticker = formatted_patterns[0]['ticker']
                    # Ищем паттерн с этим тикером
                    for p in patterns:
                        if p.get('ticker') == first_ticker and 'df' in p:
                            display_df = p['df']
                            display_ticker = first_ticker
                            break
            else:
                # Показываем только выбранный паттерн
                if selected_math_idx is not None and selected_math_idx < len(patterns):
                    selected_pattern = patterns[selected_math_idx]
                    if 'df' in selected_pattern:
                        display_df = selected_pattern['df']
                    if 'ticker' in selected_pattern:
                        display_ticker = selected_pattern['ticker']
                    
                    # Для графика передаем только выбранный паттерн
                    patterns_for_chart = [formatted_patterns[selected_math_idx]]
                    selected_idx_for_chart = 0  # Он теперь первый в списке
                else:
                    patterns_for_chart = formatted_patterns
                    selected_idx_for_chart = None
            
            # Рисуем график используя универсальную функцию
            fig = create_chart_with_predictions(
                display_df, 
                patterns_for_chart, 
                [], # confirmed
                [], # rejected
                display_ticker, 
                current_timeframe,
                selected_pattern_idx=selected_idx_for_chart if not show_all_math else None,
                show_all=show_all_math
            )
            
            # Исправляем заголовок, если показываем один паттерн
            if not show_all_math and selected_math_idx is not None and selected_math_idx < len(patterns):
                 p = patterns[selected_math_idx]
                 p_ticker = p.get('ticker', current_ticker)
                 p_type = "LONG" if p['type'] == 'bullish' else "SHORT"
                 quality = p.get('quality_score', 0)
                 # Формируем правильный заголовок с оригинальным номером
                 custom_title = f"{p_ticker} ({current_timeframe}) - Паттерн #{selected_math_idx+1}: {p_type} (Q: {quality})"
                 fig.update_layout(title=custom_title)
            
            st.plotly_chart(fig, use_container_width=True, key="math_chart")
            
            # --- БЛОК РЕДАКТИРОВАНИЯ ---
            if not show_all_math and selected_math_idx is not None and selected_math_idx < len(patterns):
                 with st.expander("✏️ Редактировать точки паттерна", expanded=False):
                      p = patterns[selected_math_idx]
                      
                      # Собираем текущие индексы точек из всех возможных мест
                      current_indices_map = {}
                      
                      # 1. Пробуем взять из корневых ключей t0..t4 (как в сканере)
                      for key in ['t0', 't1', 't2', 't3', 't4']:
                          if key in p and isinstance(p[key], dict):
                               idx = p[key].get('idx') or p[key].get('index')
                               if idx is not None:
                                   current_indices_map[key.upper()] = int(idx)
                      
                      # 2. Также проверяем ключи в верхнем регистре T0..T4
                      for key in ['T0', 'T1', 'T2', 'T3', 'T4']:
                          if key in p and isinstance(p[key], dict):
                               idx = p[key].get('idx') or p[key].get('index')
                               if idx is not None:
                                   current_indices_map[key.upper()] = int(idx)

                      # 3. Если что-то не нашли, пробуем добрать из списка points
                      for pt in p.get('points', []):
                           name = pt.get('name', '').upper()
                           idx = pt.get('idx') or pt.get('index')
                           if name and idx is not None:
                                current_indices_map[name] = int(idx)

                      # Форма редактирования
                      with st.form(key=f"edit_pattern_{selected_math_idx}"):
                           st.write("Измените индексы точек:")
                           cols = st.columns(5)
                           new_indices = {}
                           
                           # Максимальный индекс
                           max_idx = len(display_df) - 1
                           
                           for i, pt_name in enumerate(['T0', 'T1', 'T2', 'T3', 'T4']):
                                # Берем текущее значение или 0
                                current_idx = current_indices_map.get(pt_name, 0)
                                
                                # Защита от выхода за границы
                                current_idx = min(max(0, current_idx), max_idx)
                                
                                with cols[i]:
                                     new_indices[pt_name] = st.number_input(
                                          f"{pt_name}", 
                                          min_value=0, 
                                          max_value=max_idx, 
                                          value=current_idx,
                                          key=f"edit_{pt_name}_{selected_math_idx}"
                                     )
                           
                           if st.form_submit_button("💾 Применить изменения"):
                                # Обновляем точки
                                new_points_list = []
                                p_type = p.get('type', 'bullish')
                                
                                # Копия паттерна для обновления
                                updated_pattern = st.session_state.math_patterns[selected_math_idx].copy()
                                
                                for pt_name in ['T0', 'T1', 'T2', 'T3', 'T4']:
                                     idx = int(new_indices[pt_name])
                                     # Определяем цену
                                     if p_type == 'bullish':
                                          if pt_name in ['T0', 'T2', 'T4']:
                                               price = display_df.iloc[idx]['low']
                                          else:
                                               price = display_df.iloc[idx]['high']
                                     else: # bearish
                                          if pt_name in ['T0', 'T2', 'T4']:
                                               price = display_df.iloc[idx]['high']
                                          else:
                                               price = display_df.iloc[idx]['low']
                                     
                                     # Получаем время
                                     time_val = str(display_df.index[idx])
                                     if 'time' in display_df.columns:
                                          time_val = display_df.iloc[idx]['time']
                                     elif 'Date' in display_df.columns:
                                          time_val = display_df.iloc[idx]['Date']

                                     point_data = {
                                          'name': pt_name,
                                          'idx': idx,
                                          'price': float(price),
                                          'time': time_val
                                     }
                                     
                                     new_points_list.append(point_data)
                                     
                                     # ВАЖНО: Обновляем ключи t0, t1... в корне словаря, так как formatted_patterns читает оттуда
                                     updated_pattern[pt_name.lower()] = {
                                         'idx': idx,
                                         'price': float(price),
                                         'time': time_val
                                     }
                                
                                updated_pattern['points'] = new_points_list
                                
                                # Обновляем паттерн в session_state
                                st.session_state.math_patterns[selected_math_idx] = updated_pattern
                                
                                st.success("✅ Паттерн обновлен!")
                                st.rerun()
            
            # Детали и сохранение паттернов
            st.subheader("💾 Сохранение результатов")
            
            # Определяем какие паттерны показывать в списке
            if show_all_math:
                patterns_to_list = enumerate(formatted_patterns)
            else:
                patterns_to_list = [(selected_math_idx, formatted_patterns[selected_math_idx])]
            
            for idx, pattern_data in patterns_to_list:
                # Получаем оригинальный паттерн для доступа к df и ticker
                original_pattern = patterns[idx]
                p_ticker = original_pattern.get('ticker', current_ticker)
                
                # Генерируем уникальный ID для паттерна (добавляем тикер для уникальности)
                pattern_id = f"math_{p_ticker}_{pattern_data['window_start']}_{pattern_data['window_end']}_{idx}"
                is_saved = pattern_id in st.session_state.saved_math_patterns
                
                with st.container():
                    col1, col2, col3 = st.columns([3, 2, 1])
                    
                    with col1:
                        p_type = "LONG (бычий)" if pattern_data['class'] == 1 else "SHORT (медвежий)"
                        # quality = patterns[idx].get('quality_score', 0)
                        
                        points_text = ", ".join([
                            f"{p['name']}({p['price']:.2f})" 
                            for p in pattern_data['points']
                        ])
                        
                        st.write(f"**Паттерн #{idx + 1}**: {p_ticker} - {p_type}")
                        st.caption(f"Точки: {points_text}")
                    
                    with col2:
                        # Создаем две колонки для кнопок: Сохранить и Отклонить
                        btn_col1, btn_col2 = st.columns(2)
                        
                        with btn_col1:
                            if is_saved:
                                st.success("✅ Сохранено")
                            else:
                                if st.button(f"✅ В разметку", key=f"save_math_{idx}", help="Сохранить как валидный паттерн (класс 1 или 2)"):
                                    # Используем DF и тикер конкретного паттерна
                                    p_df = original_pattern.get('df', df)
                                    if save_confirmed_pattern(pattern_data, p_df, p_ticker, current_timeframe):
                                        st.session_state.saved_math_patterns.append(pattern_id)
                                        st.success("✅ Паттерн сохранен!")
                                        st.rerun()
                        
                        with btn_col2:
                            # Кнопка для сохранения как отрицательный пример (Hard Negative)
                            is_rejected = pattern_id + "_rejected" in st.session_state.saved_math_patterns
                            if is_rejected:
                                st.error("❌ Отклонено")
                            else:
                                if not is_saved: # Не показываем, если уже подтвердили
                                    if st.button(f"❌ Ложный", key=f"reject_math_{idx}", help="Сохранить как 'Нет паттерна' (Hard Negative) для обучения"):
                                        # Используем функцию сохранения отклоненных
                                        # Добавляем пометку, что это от мат. сканера
                                        pattern_data_copy = pattern_data.copy()
                                        pattern_data_copy['probability'] = pattern_data.get('probability', 0)
                                        
                                        p_df = original_pattern.get('df', df)
                                        if save_rejected_pattern(pattern_data_copy, p_df, p_ticker, current_timeframe):
                                            st.session_state.saved_math_patterns.append(pattern_id + "_rejected")
                                            st.success("❌ Сохранено как негативный пример!")
                                            st.rerun()
                    
                    with col3:
                         # Показываем геометрические проверки (повторно, для наглядности)
                        if len(pattern_data['points']) == 5:
                            points_dict = {p['name']: {'idx': p['idx'], 'price': p['price']} for p in pattern_data['points']}
                            
                            # Извлекаем данные для проверки
                            t0, t1, t2, t3, t4 = [points_dict[k]['price'] for k in ['T0', 'T1', 'T2', 'T3', 'T4']]
                            t0_idx, t1_idx, t2_idx, t3_idx, t4_idx = [points_dict[k]['idx'] for k in ['T0', 'T1', 'T2', 'T3', 'T4']]
                            
                            violations = []
                            if pattern_data['class'] == 1:
                                violations = check_long_constraints(t0, t1, t2, t3, t4, current_timeframe, t0_idx, t1_idx, t2_idx, t3_idx, t4_idx)
                            else:
                                violations = check_short_constraints(t0, t1, t2, t3, t4, current_timeframe, t0_idx, t1_idx, t2_idx, t3_idx, t4_idx)
                                
                            if violations:
                                st.warning(f"⚠️ {len(violations)} нарушений")
                                with st.expander("Детали"):
                                    for v in violations:
                                        st.caption(f"• {v}")
                            else:
                                st.success("✅ Геометрия OK")

                    st.divider()

            # Детали выбранного паттерна (json)
            if not show_all_math:
                with st.expander("ℹ️ Технические данные (JSON)"):
                    st.json(patterns[selected_math_idx])
            
        else:
            st.info("👆 Настройте параметры и нажмите 'Найти паттерны (математика)'")
            # Пустой график
            fig = create_interactive_chart(df, {}, 'bullish', current_ticker, current_timeframe)
            st.plotly_chart(fig, use_container_width=True)

    # Режим: Ручная разметка (и другие режимы редактирования)
    else:
        # Создаем график для ручной разметки
        fig = create_interactive_chart(df, st.session_state.points, st.session_state.pattern_type, current_ticker, current_timeframe)
        
        # Кнопки для отметки точек (альтернатива клику на графике)
        st.subheader("📍 Отметка точек")
        col1, col2, col3, col4, col5 = st.columns(5)
        
        # Удаляем кнопки T0-T4, так как они устанавливают None и вызывают ошибки
        # Используем только метод ввода через индекс
        
        # Отображение графика
        st.plotly_chart(fig, use_container_width=True, key="chart")
        
        # Ввод точек через индексы (альтернативный способ)
        with st.expander("🔢 Отметить точки по индексу (альтернативный способ)"):
            point_order = ['T0', 'T1', 'T2', 'T3', 'T4']
            next_point = None
            for point_name in point_order:
                # Проверяем что точка либо отсутствует, либо None, либо невалидная
                if point_name not in st.session_state.points or \
                   st.session_state.points[point_name] is None or \
                   not isinstance(st.session_state.points[point_name], dict) or \
                   'idx' not in st.session_state.points[point_name]:
                    next_point = point_name
                    break
            
            if next_point:
                st.write(f"Следующая точка для отметки: **{next_point}**")
                
                col_a, col_b = st.columns(2)
                with col_a:
                    idx_input = st.number_input(
                        f"Индекс свечи для {next_point}",
                        min_value=0,
                        max_value=len(df) - 1,
                        value=len(df) // 2,
                        key=f'idx_{next_point}'
                    )
                
                with col_b:
                    if st.button(f"Отметить {next_point}", key=f'btn_{next_point}'):
                        # Определяем цену в зависимости от типа паттерна и точки
                        if st.session_state.pattern_type == 'bullish':
                            if next_point in ['T0', 'T2', 'T4']:
                                price = df.iloc[idx_input]['low']
                            else:
                                price = df.iloc[idx_input]['high']
                        else:  # bearish
                            if next_point in ['T0', 'T2', 'T4']:
                                price = df.iloc[idx_input]['high']
                            else:
                                price = df.iloc[idx_input]['low']
                        
                        st.session_state.points[next_point] = {
                            'idx': idx_input,
                            'price': price,
                            'time': df.iloc[idx_input]['time']
                        }
                        st.success(f"✅ Точка {next_point} отмечена!")
                        st.rerun()
            else:
                st.info("Все точки отмечены!")
        
        # Показываем статус разметки
        def is_point_valid(point_name):
            return (point_name in st.session_state.points and 
                    st.session_state.points[point_name] is not None and
                    isinstance(st.session_state.points[point_name], dict) and
                    'idx' in st.session_state.points[point_name])
        
        col1, col2, col3 = st.columns(3)
        with col1:
            status_t0 = "✅" if is_point_valid('T0') else "⏳"
            st.metric("T0", status_t0)
        with col2:
            status_t1 = "✅" if is_point_valid('T1') else "⏳"
            st.metric("T1", status_t1)
        with col3:
            status_t2 = "✅" if is_point_valid('T2') else "⏳"
            st.metric("T2", status_t2)
        
        col4, col5 = st.columns(2)
        with col4:
            status_t3 = "✅" if is_point_valid('T3') else "⏳"
            st.metric("T3", status_t3)
        with col5:
            status_t4 = "✅" if is_point_valid('T4') else "⏳"
            st.metric("T4", status_t4)
        
        # Показываем информацию о точках
        valid_points = {k: v for k, v in st.session_state.points.items() if v is not None and isinstance(v, dict) and 'idx' in v}
        if valid_points:
            st.subheader("📍 Отмеченные точки")
            points_df = pd.DataFrame([
                {
                    'Точка': point_name,
                    'Индекс': point_data['idx'],
                    'Цена': f"{point_data['price']:.2f}",
                    'Время': str(point_data.get('time', 'N/A'))
                }
                for point_name, point_data in sorted(valid_points.items(), key=lambda x: x[1]['idx'])
            ])
            st.dataframe(points_df, use_container_width=True, hide_index=True)
    
    # Статистика аннотаций
    with st.expander("📊 Статистика размеченных данных"):
        try:
            stats = annotator.get_statistics()
            if stats['total'] > 0:
                st.write(f"**Всего размечено:** {stats['total']}")
                st.write("**По меткам:**")
                for label, count in stats['by_label'].items():
                    label_name = {0: 'Нет паттерна', 1: 'Бычий', 2: 'Медвежий'}.get(label, f'Unknown({label})')
                    st.write(f"  - {label_name}: {count}")
                st.write("**По таймфреймам:**")
                for tf, count in stats['by_timeframe'].items():
                    st.write(f"  - {tf}: {count}")
            else:
                st.info("Пока нет размеченных данных")
        except Exception as e:
            st.info(f"Статистика пока недоступна: {e}")
