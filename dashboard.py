import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
import sys
import time
from dotenv import load_dotenv
from t_tech.invest import Client, InstrumentIdType

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from scanners.combined_scanner import ComplexFlagScanner
from config import TIMEFRAMES

load_dotenv()
st.set_page_config(page_title="Complex Flag Scanner Dashboard", layout="wide")

st.title("🏳️ Сканер Сложного Флага (0-1-2-3-4) - Акции и Фьючерсы")

# Инициализация
token = os.environ.get("TINKOFF_INVEST_TOKEN")
if not token:
    st.error("Токен не найден!")
    st.stop()

scanner = ComplexFlagScanner(token)

# Список фьючерсов (аналогично service.py)
FUTURES_TO_SCAN = [
    {'ticker': 'MXH6', 'class_code': 'SPBFUT', 'name': 'Индекс Мосбиржи H6'},
    {'ticker': 'RIH6', 'class_code': 'SPBFUT', 'name': 'Индекс РТС H6'},
    {'ticker': 'GDH6', 'class_code': 'SPBFUT', 'name': 'Золото H6'},
    {'ticker': 'SiH6', 'class_code': 'SPBFUT', 'name': 'Серебро H6'},
    {'ticker': 'SVH6', 'class_code': 'SPBFUT', 'name': 'Серебро/Валюта H6'},
]

def get_future_instrument(ticker, class_code):
    """Получает инструмент фьючерса по тикеру и class_code"""
    try:
        with Client(token) as client:
            instrument = client.instruments.get_instrument_by(
                id_type=InstrumentIdType.INSTRUMENT_ID_TYPE_TICKER,
                class_code=class_code,
                id=ticker
            ).instrument
            
            return {
                'ticker': instrument.ticker,
                'uid': instrument.uid,
                'name': instrument.name,
                'class_code': class_code,
                'type': 'Фьючерс'
            }
    except Exception as e:
        return None

def get_all_futures():
    """Получает список всех доступных фьючерсов"""
    futures = []
    for future_config in FUTURES_TO_SCAN:
        future = get_future_instrument(future_config['ticker'], future_config['class_code'])
        if future:
            future['display_name'] = future_config['name']
            futures.append(future)
    return futures

# --- Боковая панель ---
with st.sidebar:
    st.header("Управление")
    
    # Выбор таймфрейма
    selected_timeframe = st.selectbox(
        "Таймфрейм",
        options=list(TIMEFRAMES.keys()),
        format_func=lambda x: TIMEFRAMES[x]['title'],
        index=1 # По умолчанию 1h
    )
    tf_config = TIMEFRAMES[selected_timeframe]
    
    mode = st.radio("Режим", ["Сканирование рынка", "Одиночный анализ"])
    
    if mode == "Сканирование рынка":
        instrument_type = st.selectbox(
            "Тип инструментов",
            ["Все", "Только акции", "Только фьючерсы"],
            index=0
        )
        if st.button("🚀 ЗАПУСТИТЬ СКАНИРОВАНИЕ"):
            st.session_state['scan_in_progress'] = True
            st.session_state['scan_results'] = []
            st.session_state['instrument_type'] = instrument_type
    
    if mode == "Одиночный анализ":
        ticker_input = st.text_input("Тикер", value="RMH6")
        class_code_input = st.text_input("Class Code", value="SPBFUT")
    
    # days_back теперь берется из конфига таймфрейма, но можно оставить возможность переопределить для одиночного анализа
    if mode == "Одиночный анализ":
        days_back = st.slider("Дней истории", 1, tf_config['days_back'] * 2, tf_config['days_back'])
    else:
        days_back = tf_config['days_back'] # Для сканирования используем из конфига

# --- Логика сканирования всех инструментов ---
if mode == "Сканирование рынка":
    instrument_type = st.session_state.get('instrument_type', 'Все')
    st.info(f"💡 Выбран таймфрейм: {tf_config['title']}. Тип инструментов: {instrument_type}. Нажмите кнопку 'ЗАПУСТИТЬ СКАНИРОВАНИЕ' для поиска.")
    
    # Запуск сканирования
    if st.session_state.get('scan_in_progress', False):
        # Собираем список инструментов для сканирования
        all_instruments = []
        
        if instrument_type in ["Все", "Только акции"]:
            shares = scanner.get_all_shares()
            for share in shares:
                all_instruments.append({
                    'ticker': share.ticker,
                    'uid': share.uid,
                    'name': share.name,
                    'class_code': share.class_code,
                    'type': 'Акция'
                })
        
        if instrument_type in ["Все", "Только фьючерсы"]:
            futures = get_all_futures()
            for future in futures:
                all_instruments.append({
                    'ticker': future['ticker'],
                    'uid': future['uid'],
                    'name': future['name'],
                    'class_code': future['class_code'],
                    'type': 'Фьючерс'
                })
        
        instrument_type_text = {
            "Все": f"{len([i for i in all_instruments if i['type'] == 'Акция'])} акций + {len([i for i in all_instruments if i['type'] == 'Фьючерс'])} фьючерсов",
            "Только акции": f"{len(all_instruments)} акций",
            "Только фьючерсы": f"{len(all_instruments)} фьючерсов"
        }
        
        st.write(f"📊 Найдено: {instrument_type_text[instrument_type]}. Начинаю анализ на ТФ {selected_timeframe}...")
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        results = []
        
        for i, instrument in enumerate(all_instruments):
            status_text.text(f"Анализ {i+1}/{len(all_instruments)}: {instrument['ticker']} ({instrument['type']})")
            progress_bar.progress((i + 1) / len(all_instruments))
            
            time.sleep(0.15)  # Задержка для лимитов API
            
            try:
                # Используем настройки выбранного таймфрейма
                df = scanner.get_candles_by_uid(
                    instrument['uid'], 
                    days_back=days_back,
                    interval=tf_config['interval']
                )
                
                if not df.empty:
                    # Используем метод analyze, который проверяет оба типа паттернов
                    patterns = scanner.analyze(df, timeframe=selected_timeframe)
                    
                    if patterns:
                        pattern_info = patterns[0]
                        pattern_type = "Бычий" if "BEARISH" not in pattern_info['pattern'] else "Медвежий"
                        results.append({
                            "Тикер": instrument['ticker'],
                            "Тип": instrument['type'],
                            "Таймфрейм": selected_timeframe,
                            "Паттерн": pattern_type,
                            "T0": pattern_info['t0']['price'],
                            "T1": pattern_info['t1']['price'],
                            "T2": pattern_info['t2']['price'],
                            "T3": pattern_info['t3']['price'],
                            "T4": pattern_info['t4']['price'],
                            "Высота флагштока": pattern_info['pole_height'],
                            "Текущая цена": pattern_info['current_price'],
                            "Время": df.iloc[-1]['time'],
                            "pattern_info": pattern_info,  # Сохраняем полную информацию для графика
                            "df": df  # Сохраняем данные для графика
                        })
            except Exception as e:
                continue
        
        progress_bar.empty()
        status_text.text("✅ Сканирование завершено!")
        
        st.session_state['scan_in_progress'] = False
        st.session_state['scan_results'] = results
        
        if results:
            st.success(f"🎉 Найдено {len(results)} сигналов!")
        else:
            st.warning("Паттернов не найдено.")
    
    # Отображение результатов
    if 'scan_results' in st.session_state and st.session_state['scan_results']:
        st.write("---")
        st.subheader("📋 Результаты сканирования")
        
        # Создаем таблицу без технических полей
        display_results = []
        for r in st.session_state['scan_results']:
            display_results.append({
                "Тикер": r["Тикер"],
                "Тип": r.get("Тип", "Акция"),
                "Паттерн": r.get("Паттерн", "-"),
                "ТФ": r.get("Таймфрейм", selected_timeframe),
                "T0": f"{r['T0']:.2f}",
                "T1": f"{r['T1']:.2f}",
                "T3": f"{r['T3']:.2f}",
                "T4": f"{r['T4']:.2f}",
                "Высота": f"{r['Высота флагштока']:.2f}",
                "Цена": f"{r['Текущая цена']:.2f}",
                "Время": r['Время']
            })
        
        results_df = pd.DataFrame(display_results)
        st.dataframe(results_df, use_container_width=True)
        
        # Выбор тикера для просмотра графика
        selected_ticker = st.selectbox(
            "Выберите тикер для просмотра графика:",
            [r["Тикер"] for r in st.session_state['scan_results']]
        )
        
        if selected_ticker:
            # Находим данные выбранного тикера
            selected_result = next(r for r in st.session_state['scan_results'] if r["Тикер"] == selected_ticker)
            pattern_info = selected_result['pattern_info']
            df_chart = selected_result['df']
            
            # Переключаемся на отображение графика
            show_detail_chart = True
        else:
            show_detail_chart = False
    else:
        show_detail_chart = False
        selected_ticker = None

else:
    # Режим одиночного анализа
    show_detail_chart = True
    
    # Используем настройки выбранного таймфрейма
    df_chart = scanner.get_candles_df(
        ticker_input, 
        class_code_input, 
        days_back=days_back,
        interval=tf_config['interval']
    )
    
    # Используем метод analyze, который проверяет оба типа паттернов
    patterns = scanner.analyze(df_chart, timeframe=selected_timeframe) if not df_chart.empty else []
    pattern_info = patterns[0] if patterns else None
    
    selected_ticker = ticker_input

# --- Отображение детального графика ---
if show_detail_chart and (mode == "Одиночный анализ" or ('scan_results' in st.session_state and selected_ticker)):
    st.write("---")
    st.subheader(f"📈 График: {selected_ticker} ({selected_timeframe})")
    
    if df_chart.empty:
        st.warning("Нет данных для отображения.")
    elif pattern_info is None:
        st.info("Паттерн 0-1-2-3-4 не найден на текущих данных.")
    else:
        # Показываем информацию о паттерне
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("T0 (Начало)", f"{pattern_info['t0']['price']:.2f}")
            st.caption(f"Время: {pattern_info['t0']['time']}")
        with col2:
            st.metric("T1 (Вершина флагштока)", f"{pattern_info['t1']['price']:.2f}")
            st.caption(f"Время: {pattern_info['t1']['time']}")
        with col3:
            st.metric("Высота флагштока", f"{pattern_info['pole_height']:.2f}")
        
        col4, col5 = st.columns(2)
        with col4:
            st.metric("T3 (Второй пик)", f"{pattern_info['t3']['price']:.2f}")
            # Проверка зависит от типа паттерна
            if "BEARISH" in pattern_info['pattern']:
                 st.caption(f"✅ T3 >= T1: {pattern_info['t3']['price']:.2f} >= {pattern_info['t1']['price']:.2f}")
            else:
                 st.caption(f"✅ T3 <= T1: {pattern_info['t3']['price']:.2f} <= {pattern_info['t1']['price']:.2f}")
                 
        with col5:
            st.metric("T4 (Второй откат)", f"{pattern_info['t4']['price']:.2f}")
            # Проверка зависит от типа паттерна
            if "BEARISH" in pattern_info['pattern']:
                max_t4_allowed = pattern_info['t0']['price'] - 0.5 * pattern_info['pole_height'] # Грубая оценка для текста
                st.caption(f"✅ T4 коррекция OK") 
            else:
                min_t4_allowed = pattern_info['t0']['price'] + 0.5 * pattern_info['pole_height']
                st.caption(f"✅ T4 >= T0+50%: {pattern_info['t4']['price']:.2f} >= {min_t4_allowed:.2f}")
        
        col6, col7 = st.columns(2)
        with col6:
            st.metric("Текущая цена", f"{pattern_info['current_price']:.2f}")
        with col7:
            st.caption(f"Линия пробоя: {pattern_info['resistance_line']:.2f}")

        # Создаем график (используем индексы вместо времени для непрерывного графика)
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                            vertical_spacing=0.03, row_heights=[0.7, 0.3])
        
        # Используем индексы вместо времени для оси X
        indices_x = list(range(len(df_chart)))
        customdata_candles = [[i, df_chart.iloc[i]['time']] for i in range(len(df_chart))]
        
        # Свечи
        fig.add_trace(go.Candlestick(
            x=indices_x,  # Используем индексы вместо времени
            open=df_chart['open'], high=df_chart['high'], low=df_chart['low'], close=df_chart['close'],
            name='Цена',
            customdata=customdata_candles,
            hovertemplate='<b>Индекс:</b> %{customdata[0]}<br>' +
                         '<b>Время:</b> %{customdata[1]}<br>' +
                         '<b>Open:</b> %{open:.2f}<br>' +
                         '<b>High:</b> %{high:.2f}<br>' +
                         '<b>Low:</b> %{low:.2f}<br>' +
                         '<b>Close:</b> %{close:.2f}<extra></extra>'
        ), row=1, col=1)
        
        # Точки паттерна (используем индексы вместо времени)
        points_data = [
            ('T0', pattern_info['t0'], 'lime', 'circle'),
            ('T1', pattern_info['t1'], 'red', 'diamond'),
            ('T2', pattern_info['t2'], 'cyan', 'circle'),
            ('T3', pattern_info['t3'], 'orange', 'diamond'),
            ('T4', pattern_info['t4'], 'magenta', 'circle'),
        ]
        
        for label, point, color, symbol in points_data:
            idx = point['idx']
            point_price = point['price']
            fig.add_trace(go.Scatter(
                x=[idx],  # Используем индекс вместо времени
                y=[point_price],
                mode='markers+text',
                marker=dict(size=15, color=color, symbol=symbol, line=dict(width=2, color='white')),
                text=[label],
                textposition='top center',
                name=label,
                showlegend=True,
                customdata=[[idx, point['time']]],
                hovertemplate=f'<b>{label}</b><br>' +
                             f'<b>Индекс:</b> {idx}<br>' +
                             '<b>Время:</b> %{customdata[0][1]}<br>' +
                             f'<b>Цена:</b> {point_price:.2f}<extra></extra>'
            ), row=1, col=1)
        
        # Линия флагштока (T0 -> T1) - используем индексы
        fig.add_trace(go.Scatter(
            x=[pattern_info['t0']['idx'], pattern_info['t1']['idx']],
            y=[pattern_info['t0']['price'], pattern_info['t1']['price']],
            mode='lines',
            line=dict(color='lime', width=3, dash='solid'),
            name='Флагшток (T0-T1)',
            showlegend=True
        ), row=1, col=1)
        
        # Линия сопротивления (T1 -> T3) - используем индексы
        fig.add_trace(go.Scatter(
            x=[pattern_info['t1']['idx'], pattern_info['t3']['idx']],
            y=[pattern_info['t1']['price'], pattern_info['t3']['price']],
            mode='lines',
            line=dict(color='red', width=2.5, dash='dash'),
            name='Сопротивление (T1-T3)',
            showlegend=True
        ), row=1, col=1)
        
        # Продолжение линии сопротивления - используем индексы
        last_idx = len(df_chart) - 1
        fig.add_trace(go.Scatter(
            x=[pattern_info['t3']['idx'], last_idx],
            y=[pattern_info['t3']['price'], pattern_info['resistance_line']],
            mode='lines',
            line=dict(color='red', width=1.5, dash='dot'),
            name='Продолжение линии',
            showlegend=False
        ), row=1, col=1)
        
        # Линия поддержки (T2 -> T4) - используем индексы
        fig.add_trace(go.Scatter(
            x=[pattern_info['t2']['idx'], pattern_info['t4']['idx']],
            y=[pattern_info['t2']['price'], pattern_info['t4']['price']],
            mode='lines',
            line=dict(color='cyan', width=2, dash='dash'),
            name='Поддержка (T2-T4)',
            showlegend=True
        ), row=1, col=1)
        
        # Объем - используем индексы вместо времени
        colors = ['red' if row['open'] - row['close'] >= 0 else 'green' 
                  for index, row in df_chart.iterrows()]
        fig.add_trace(go.Bar(
            x=indices_x, y=df_chart['volume'],  # Используем индексы вместо времени
            marker_color=colors,
            name='Объем',
            customdata=customdata_candles,
            hovertemplate='<b>Индекс:</b> %{customdata[0]}<br>' +
                         '<b>Время:</b> %{customdata[1]}<br>' +
                         '<b>Объем:</b> %{y}<extra></extra>'
        ), row=2, col=1)
        
        # Настройка меток оси X: показываем время вместо индексов
        # Используем только каждую N-ю метку для читаемости
        tick_step = max(1, len(df_chart) // 20)  # Примерно 20 меток
        tick_indices = list(range(0, len(df_chart), tick_step))
        # Форматируем время с учетом возможных типов
        tick_times = []
        for i in tick_indices:
            time_val = df_chart.iloc[i]['time']
            if pd.isna(time_val):
                tick_times.append('')
            elif isinstance(time_val, pd.Timestamp):
                if selected_timeframe == '1d':
                    tick_times.append(time_val.strftime('%Y-%m-%d'))
                else:
                    tick_times.append(time_val.strftime('%Y-%m-%d %H:%M'))
            else:
                tick_times.append(str(time_val))
        
        fig.update_layout(
            height=800,
            xaxis_rangeslider_visible=False,
            title=f"График {selected_ticker} ({selected_timeframe}) - Паттерн Флаг 0-1-2-3-4",
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
        
        st.plotly_chart(fig, use_container_width=True)
