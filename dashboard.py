import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
import sys
import time
from dotenv import load_dotenv

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from scanners.combined_scanner import ComplexFlagScanner

load_dotenv()
st.set_page_config(page_title="Complex Flag Scanner Dashboard", layout="wide")

st.title("🏳️ Сканер Сложного Флага (0-1-2-3-4) - Все Акции")

# Инициализация
token = os.environ.get("TINKOFF_INVEST_TOKEN")
if not token:
    st.error("Токен не найден!")
    st.stop()

scanner = ComplexFlagScanner(token)

# --- Боковая панель ---
with st.sidebar:
    st.header("Управление")
    
    if st.button("🚀 ЗАПУСТИТЬ СКАНИРОВАНИЕ ВСЕХ АКЦИЙ"):
        st.session_state['scan_in_progress'] = True
        st.session_state['scan_results'] = []
    
    mode = st.radio("Режим", ["Сканирование рынка", "Одиночный анализ"])
    
    if mode == "Одиночный анализ":
        ticker_input = st.text_input("Тикер", value="RMH6")
        class_code_input = st.text_input("Class Code", value="SPBFUT")
    
    days_back = st.slider("Дней истории", 1, 10, 5)

# --- Логика сканирования всех акций ---
if mode == "Сканирование рынка":
    st.info("💡 Нажмите кнопку 'ЗАПУСТИТЬ СКАНИРОВАНИЕ' в боковой панели для поиска паттернов на всех акциях")
    
    # Запуск сканирования
    if st.session_state.get('scan_in_progress', False):
        shares = scanner.get_all_shares()
        st.write(f"📊 Найдено {len(shares)} акций. Начинаю анализ...")
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        results = []
        
        for i, share in enumerate(shares):
            status_text.text(f"Анализ {i+1}/{len(shares)}: {share.ticker}")
            progress_bar.progress((i + 1) / len(shares))
            
            time.sleep(0.15)  # Задержка для лимитов API
            
            try:
                df = scanner.get_candles_by_uid(share.uid, days_back=days_back)
                if not df.empty:
                    patterns = scanner.analyze_flag_0_1_2_3_4(df)
                    if patterns:
                        pattern_info = patterns[0]
                        results.append({
                            "Тикер": share.ticker,
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
    df_chart = scanner.get_candles_df(ticker_input, class_code_input, days_back=days_back)
    patterns = scanner.analyze_flag_0_1_2_3_4(df_chart) if not df_chart.empty else []
    pattern_info = patterns[0] if patterns else None
    selected_ticker = ticker_input

# --- Отображение детального графика ---
if show_detail_chart and (mode == "Одиночный анализ" or ('scan_results' in st.session_state and selected_ticker)):
    st.write("---")
    st.subheader(f"📈 График: {selected_ticker}")
    
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
            st.caption(f"✅ T3 <= T1: {pattern_info['t3']['price']:.2f} <= {pattern_info['t1']['price']:.2f}")
        with col5:
            st.metric("T4 (Второй откат)", f"{pattern_info['t4']['price']:.2f}")
            min_t4_allowed = pattern_info['t0']['price'] + 0.5 * pattern_info['pole_height']
            st.caption(f"✅ T4 >= T0+50%: {pattern_info['t4']['price']:.2f} >= {min_t4_allowed:.2f}")
        
        col6, col7 = st.columns(2)
        with col6:
            st.metric("Текущая цена", f"{pattern_info['current_price']:.2f}")
        with col7:
            st.caption(f"Линия сопротивления: {pattern_info['resistance_line']:.2f}")

        # Создаем график
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                            vertical_spacing=0.03, row_heights=[0.7, 0.3])
        
        # Свечи
        fig.add_trace(go.Candlestick(
            x=df_chart['time'],
            open=df_chart['open'], high=df_chart['high'], low=df_chart['low'], close=df_chart['close'],
            name='Цена'
        ), row=1, col=1)
        
        # Точки паттерна
        points_data = [
            ('T0', pattern_info['t0'], 'lime', 'circle'),
            ('T1', pattern_info['t1'], 'red', 'diamond'),
            ('T2', pattern_info['t2'], 'cyan', 'circle'),
            ('T3', pattern_info['t3'], 'orange', 'diamond'),
            ('T4', pattern_info['t4'], 'magenta', 'circle'),
        ]
        
        for label, point, color, symbol in points_data:
            fig.add_trace(go.Scatter(
                x=[point['time']],
                y=[point['price']],
                mode='markers+text',
                marker=dict(size=15, color=color, symbol=symbol, line=dict(width=2, color='white')),
                text=[label],
                textposition='top center',
                name=label,
                showlegend=True
            ), row=1, col=1)
        
        # Линия флагштока (T0 -> T1)
        fig.add_trace(go.Scatter(
            x=[pattern_info['t0']['time'], pattern_info['t1']['time']],
            y=[pattern_info['t0']['price'], pattern_info['t1']['price']],
            mode='lines',
            line=dict(color='lime', width=3, dash='solid'),
            name='Флагшток (T0-T1)',
            showlegend=True
        ), row=1, col=1)
        
        # Линия сопротивления (T1 -> T3)
        fig.add_trace(go.Scatter(
            x=[pattern_info['t1']['time'], pattern_info['t3']['time']],
            y=[pattern_info['t1']['price'], pattern_info['t3']['price']],
            mode='lines',
            line=dict(color='red', width=2.5, dash='dash'),
            name='Сопротивление (T1-T3)',
            showlegend=True
        ), row=1, col=1)
        
        # Продолжение линии сопротивления
        last_time = df_chart.iloc[-1]['time']
        fig.add_trace(go.Scatter(
            x=[pattern_info['t3']['time'], last_time],
            y=[pattern_info['t3']['price'], pattern_info['resistance_line']],
            mode='lines',
            line=dict(color='red', width=1.5, dash='dot'),
            name='Продолжение линии',
            showlegend=False
        ), row=1, col=1)
        
        # Линия поддержки (T2 -> T4)
        fig.add_trace(go.Scatter(
            x=[pattern_info['t2']['time'], pattern_info['t4']['time']],
            y=[pattern_info['t2']['price'], pattern_info['t4']['price']],
            mode='lines',
            line=dict(color='cyan', width=2, dash='dash'),
            name='Поддержка (T2-T4)',
            showlegend=True
        ), row=1, col=1)
        
        # Объем
        colors = ['red' if row['open'] - row['close'] >= 0 else 'green' 
                  for index, row in df_chart.iterrows()]
        fig.add_trace(go.Bar(
            x=df_chart['time'], y=df_chart['volume'],
            marker_color=colors,
            name='Объем'
        ), row=2, col=1)
        
        fig.update_layout(
            height=800,
            xaxis_rangeslider_visible=False,
            title=f"График {selected_ticker} - Паттерн Флаг 0-1-2-3-4",
            template="plotly_dark"
        )
        
        st.plotly_chart(fig, use_container_width=True)