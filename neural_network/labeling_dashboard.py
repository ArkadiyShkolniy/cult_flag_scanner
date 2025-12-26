"""
Интерактивный дашборд для разметки паттернов "Флаг"
Позволяет загружать данные, визуализировать график и отмечать точки T0-T4 для обучения нейросети
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv
from pathlib import Path

# Добавляем путь к корню проекта
sys.path.insert(0, str(Path(__file__).parent.parent))

from scanners.combined_scanner import ComplexFlagScanner
from config import TIMEFRAMES
from neural_network.annotator import PatternAnnotator

load_dotenv()
st.set_page_config(page_title="Разметка паттернов", layout="wide")

st.title("🎨 Разметка паттернов 'Флаг' для обучения нейросети")

# Инициализация
token = os.environ.get("TINKOFF_INVEST_TOKEN")
if not token:
    st.error("❌ Токен не найден! Убедитесь что файл .env содержит TINKOFF_INVEST_TOKEN")
    st.stop()

scanner = ComplexFlagScanner(token)
annotator = PatternAnnotator()

# Инициализация сессии
if 'points' not in st.session_state:
    st.session_state.points = {}
if 'df_data' not in st.session_state:
    st.session_state.df_data = None
if 'pattern_type' not in st.session_state:
    st.session_state.pattern_type = 'bullish'  # bullish или bearish
if 'selected_candle_idx' not in st.session_state:
    st.session_state.selected_candle_idx = None  # Выбранный индекс свечи на графике


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
                                 f'Время: {point_data["time"]}<extra></extra>'
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
                fig.add_trace(
                    go.Scatter(
                        x=[valid_points['T1']['idx'], valid_points['T3']['idx']],
                        y=[valid_points['T1']['price'], valid_points['T3']['price']],
                        mode='lines',
                        line=dict(color='red', width=2, dash='dash'),
                        name='Линия T1-T3',
                        showlegend=True
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
        
        # Проверяем порядок точек
        sorted_points = sorted(valid_points.items(), key=lambda x: x[1]['idx'])
        point_names = [p[0] for p in sorted_points]
        
        if point_names != ['T0', 'T1', 'T2', 'T3', 'T4']:
            st.error("❌ Точки должны быть в хронологическом порядке T0 < T1 < T2 < T3 < T4!")
            return
        
        # Определяем метку
        label = 1 if st.session_state.pattern_type == 'bullish' else 2
        
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
        
        # Добавляем аннотацию
        annotator.annotate_pattern(
            candles_file=candles_file,
            label=label,
            ticker=ticker,
            timeframe=selected_timeframe,
            pattern_type=pattern_info['pattern'],
            notes=f"Размечено вручную. Тип: {st.session_state.pattern_type}"
        )
        
        st.success(f"✅ Паттерн сохранен для обучения! (label={label}, {'Бычий' if label==1 else 'Медвежий'})")
        
        # Очищаем точки для следующей разметки
        st.session_state.points = {}
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
    
    # Выбор инструмента
    ticker = st.text_input("Тикер", value="VKCO")
    class_code = st.selectbox("Class Code", ["TQBR", "SPBFUT", "FUT"], index=0)
    
    # Выбор таймфрейма
    selected_timeframe = st.selectbox(
        "Таймфрейм",
        options=list(TIMEFRAMES.keys()),
        format_func=lambda x: TIMEFRAMES[x]['title'],
        index=1
    )
    tf_config = TIMEFRAMES[selected_timeframe]
    
    # Количество дней истории
    days_back = st.slider("Дней истории", 1, max(30, tf_config['days_back']), 
                         min(10, tf_config['days_back']))
    
    # Кнопка загрузки данных
    if st.button("📥 Загрузить данные", type="primary"):
        with st.spinner("Загрузка данных..."):
            try:
                df = scanner.get_candles_df(
                    ticker, 
                    class_code, 
                    days_back=days_back,
                    interval=tf_config['interval']
                )
                
                if not df.empty:
                    st.session_state.df_data = df
                    st.session_state.points = {}  # Сбрасываем точки
                    st.session_state.current_ticker = ticker  # Сохраняем для сохранения
                    st.session_state.current_timeframe = selected_timeframe  # Сохраняем для сохранения
                    st.success(f"✅ Загружено {len(df)} свечей")
                else:
                    st.error("❌ Данные не загружены")
            except Exception as e:
                st.error(f"❌ Ошибка загрузки: {e}")
    
    st.divider()
    
    # Тип паттерна
    st.subheader("Тип паттерна")
    pattern_type = st.radio(
        "Выберите тип",
        ["Бычий (Bullish)", "Медвежий (Bearish)"],
        index=0 if st.session_state.pattern_type == 'bullish' else 1,
        key='pattern_type_radio'
    )
    st.session_state.pattern_type = 'bullish' if 'Бычий' in pattern_type else 'bearish'
    
    st.divider()
    
    # Инструкции
    with st.expander("📖 Инструкция"):
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
    
    # Кнопки управления
    if st.button("🗑️ Очистить точки"):
        st.session_state.points = {}
        st.rerun()
    
    # Подсчитываем только валидные точки
    valid_points_count = sum(1 for v in st.session_state.points.values() 
                            if v is not None and isinstance(v, dict) and 'idx' in v)
    
    if st.button("💾 Сохранить для обучения", type="primary", disabled=valid_points_count < 5):
        if valid_points_count == 5:
            save_annotation()
        else:
            st.warning("⚠️ Отметьте все 5 точек!")

# --- Основная область ---

if st.session_state.df_data is None:
    st.info("👈 Выберите инструмент и таймфрейм в боковой панели, затем нажмите 'Загрузить данные'")
else:
    df = st.session_state.df_data
    
    # Получаем сохраненные значения для использования в функциях
    current_ticker = st.session_state.get('current_ticker', ticker)
    current_timeframe = st.session_state.get('current_timeframe', selected_timeframe)
    
    # Создаем график
    fig = create_interactive_chart(df, st.session_state.points, st.session_state.pattern_type, current_ticker, current_timeframe)
    
    # Кнопки для отметки точек (альтернатива клику на графике)
    st.subheader("📍 Отметка точек")
    col1, col2, col3, col4, col5 = st.columns(5)
    
    # Удаляем кнопки T0-T4, так как они устанавливают None и вызывают ошибки
    # Используем только метод ввода через индекс
    
    # Информация о выборе на графике
    if st.session_state.selected_candle_idx is not None:
        st.info(f"📍 На графике выбран индекс: **{st.session_state.selected_candle_idx}** (время: {df.iloc[st.session_state.selected_candle_idx]['time']})")
    
    # Отображение графика с обработкой выбора
    selected_points = st.plotly_chart(fig, use_container_width=True, key="chart", on_select="rerun")
    
    # Обрабатываем выбор точки на графике
    if selected_points:
        if 'selection' in selected_points and 'points' in selected_points['selection']:
            points_list = selected_points['selection']['points']
            if points_list:
                selected_point = points_list[0]
                # Получаем индекс из customdata или из координаты x
                candle_idx = None
                if 'customdata' in selected_point and selected_point['customdata']:
                    # customdata это список [idx, time]
                    candle_idx = int(selected_point['customdata'][0])
                elif 'x' in selected_point:
                    candle_idx = int(selected_point['x'])
                elif 'pointIndex' in selected_point:
                    candle_idx = int(selected_point['pointIndex'])
                
                if candle_idx is not None and 0 <= candle_idx < len(df):
                    st.session_state.selected_candle_idx = candle_idx
                    st.rerun()
    
    # Ввод точек через индексы
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
                # Используем выбранный индекс или значение по умолчанию
                default_idx = st.session_state.selected_candle_idx if st.session_state.selected_candle_idx is not None else (len(df) // 2)
                default_idx = max(0, min(default_idx, len(df) - 1))  # Ограничиваем диапазон
                
                idx_input = st.number_input(
                    f"Индекс свечи для {next_point}",
                    min_value=0,
                    max_value=len(df) - 1,
                    value=default_idx,
                    key=f'idx_{next_point}',
                    help="💡 Кликните на графике по нужной свече, и индекс автоматически подтянется сюда"
                )
                
                # Показываем выбранный индекс если он есть
                if st.session_state.selected_candle_idx is not None:
                    st.info(f"📍 Выбранный индекс на графике: {st.session_state.selected_candle_idx}")
            
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
                    # Сбрасываем выбранный индекс после использования
                    st.session_state.selected_candle_idx = None
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
