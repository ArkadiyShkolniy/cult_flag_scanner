#!/usr/bin/env python3
"""
Визуализация геометрических ограничений для SHORT (медвежий флаг)
Демонстрирует все возможные варианты фигур с соблюдением правил
"""

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import math

def create_flag_pattern(T0, T1, T2, T3, T4, title=""):
    """Создает данные для отрисовки паттерна флаг (для SHORT)"""
    # Временные точки (индексы свечей)
    times = np.array([0, 25, 50, 75, 100])
    prices = np.array([T0, T1, T2, T3, T4])
    
    # Линия флагштока T0-T1
    pole_times = np.array([0, 25])
    pole_prices = np.array([T0, T1])
    
    # Линия тренда T1-T3
    trend_lower_times = np.array([25, 75])
    trend_lower_prices = np.array([T1, T3])
    
    # Линия тренда T2-T4
    trend_upper_times = np.array([50, 100])
    trend_upper_prices = np.array([T2, T4])
    
    return {
        'times': times,
        'prices': prices,
        'pole_times': pole_times,
        'pole_prices': pole_prices,
        'trend_lower_times': trend_lower_times,
        'trend_lower_prices': trend_lower_prices,
        'trend_upper_times': trend_upper_times,
        'trend_upper_prices': trend_upper_prices,
        'title': title
    }


def calculate_fibonacci_levels(T0, T1):
    """Вычисляет уровни фибоначчи для хода T0-T1 (для SHORT)"""
    move = T0 - T1
    # Коррекция фибоначчи 0.62 от низа T1 вверх (аналогично LONG)
    fib_62 = T1 + 0.62 * move
    return {
        'fib_0': T0,
        'fib_62': fib_62,
        'fib_100': T1
    }


def check_constraints(T0, T1, T2, T3, T4):
    """Проверяет соблюдение всех геометрических ограничений для SHORT"""
    violations = []
    
    # Правило 1: T2 <= T1 + 0.62 * (T0 - T1) (коррекция фибоначчи 0.62 от T1 вверх)
    max_t2 = T1 + 0.62 * (T0 - T1)
    if T2 > max_t2:
        violations.append(f"T2 ({T2:.2f}) > фиба 0.62 ({max_t2:.2f})")
    
    # Правило 2: T3 <= T2 - 0.5 * (T2 - T1) И T3 >= T1
    move_12 = T2 - T1
    max_t3 = T2 - 0.5 * move_12
    if T3 > max_t3:
        violations.append(f"T3 ({T3:.2f}) > max падения ({max_t3:.2f})")
    if T3 < T1:
        violations.append(f"T3 ({T3:.2f}) < T1 ({T1:.2f})")
    
    # Правило 3: T4 >= T3 + 0.5 * (T2 - T3) И T4 <= T1 + 0.62 * (T0 - T1) (коррекция фибоначчи 0.62 от T1 вверх)
    move_23 = T2 - T3
    min_t4_from_t3 = T3 + 0.5 * move_23
    max_t4_from_pole = T1 + 0.62 * (T0 - T1)  # Коррекция фибоначчи 0.62 от T1 вверх
    
    if T4 < min_t4_from_t3:
        violations.append(f"T4 ({T4:.2f}) < min отката ({min_t4_from_t3:.2f})")
    if T4 > max_t4_from_pole:
        violations.append(f"T4 ({T4:.2f}) > фиба 0.62 ({max_t4_from_pole:.2f})")
    
    # Правило 4: Линии не должны расходиться
    slope_13 = (T3 - T1) / (75 - 25) if (75 - 25) != 0 else 0
    slope_24 = (T4 - T2) / (100 - 50) if (100 - 50) != 0 else 0
    
    # Для медвежьего флага обе линии направлены вверх (slope > 0)
    # Линии расходятся, если slope_24 > slope_13 * 1.02
    if slope_13 > 0 and slope_24 > slope_13 * 1.02:
        violations.append(f"Линии расходятся (slope_13={slope_13:.4f}, slope_24={slope_24:.4f})")
    
    return violations


def create_plot(patterns, fig_title):
    """Создает график с несколькими паттернами"""
    n_patterns = len(patterns)
    cols = 3
    rows = math.ceil(n_patterns / cols)
    
    # Создаем подзаголовки с информацией
    subplot_titles = []
    for p in patterns:
        T0, T1, T2, T3, T4 = p['prices'][0], p['prices'][1], \
                             p['prices'][2], p['prices'][3], p['prices'][4]
        violations = check_constraints(T0, T1, T2, T3, T4)
        is_valid = len(violations) == 0
        
        title = p['title']
        if is_valid:
            title += "<br><span style='color:green;font-size:10px'>✓ Валидно</span>"
        else:
            title += f"<br><span style='color:red;font-size:10px'>✗ {len(violations)} наруш.</span>"
        subplot_titles.append(title)
    
    fig = make_subplots(
        rows=rows, cols=cols,
        subplot_titles=subplot_titles,
        vertical_spacing=0.15,
        horizontal_spacing=0.1
    )
    
    for idx, pattern in enumerate(patterns):
        row = idx // cols + 1
        col = idx % cols + 1
        
        T0, T1, T2, T3, T4 = pattern['prices'][0], pattern['prices'][1], \
                             pattern['prices'][2], pattern['prices'][3], pattern['prices'][4]
        
        # Вычисляем уровни фибоначчи
        fibs = calculate_fibonacci_levels(T0, T1)
        
        # Проверяем ограничения
        violations = check_constraints(T0, T1, T2, T3, T4)
        is_valid = len(violations) == 0
        
        # Флагшток T0-T1
        fig.add_trace(
            go.Scatter(
                x=pattern['pole_times'],
                y=pattern['pole_prices'],
                mode='lines+markers',
                name='Флагшток',
                line=dict(color='red', width=3),
                marker=dict(size=10),
                showlegend=(idx == 0)
            ),
            row=row, col=col
        )
        
        # Линия тренда T1-T3 (нижняя)
        fig.add_trace(
            go.Scatter(
                x=pattern['trend_lower_times'],
                y=pattern['trend_lower_prices'],
                mode='lines',
                name='Тренд T1-T3',
                line=dict(color='orange', width=2, dash='solid'),
                showlegend=(idx == 0)
            ),
            row=row, col=col
        )
        
        # Линия тренда T2-T4 (верхняя)
        fig.add_trace(
            go.Scatter(
                x=pattern['trend_upper_times'],
                y=pattern['trend_upper_prices'],
                mode='lines',
                name='Тренд T2-T4',
                line=dict(color='orange', width=2, dash='solid'),
                showlegend=(idx == 0)
            ),
            row=row, col=col
        )
        
        # Точки паттерна
        point_labels = ['T0', 'T1', 'T2', 'T3', 'T4']
        point_colors = ['red', 'red', 'green', 'green', 'green']
        for i, (t, p, label, color) in enumerate(zip(pattern['times'], pattern['prices'], point_labels, point_colors)):
            fig.add_trace(
                go.Scatter(
                    x=[t],
                    y=[p],
                    mode='markers+text',
                    text=[label],
                    textposition='top center' if i < 2 else 'bottom center',
                    marker=dict(size=12, color=color),
                    showlegend=False,
                    textfont=dict(size=10, color='black')
                ),
                row=row, col=col
            )
        
        # Уровень фиба 0.62
        fig.add_hline(
            y=fibs['fib_62'],
            line_dash="dash",
            line_color="purple",
            opacity=0.5,
            annotation_text=f"Фиба 0.62",
            annotation_position="right",
            row=row, col=col
        )
        
        # Добавляем текст с координатами
        info_text = f"T0={T0:.1f}  T1={T1:.1f}<br>T2={T2:.1f}  T3={T3:.1f}  T4={T4:.1f}"
        fig.add_annotation(
            x=50,
            y=T1 - (T0 - T1) * 0.1,
            text=info_text,
            showarrow=False,
            font=dict(size=9),
            bgcolor="rgba(255,255,255,0.8)",
            bordercolor="black",
            borderwidth=1,
            row=row, col=col
        )
    
    fig.update_layout(
        height=350 * rows,
        title_text=fig_title,
        title_x=0.5,
        template='plotly_white',
        showlegend=True
    )
    
    # Обновляем оси для всех subplots
    for i in range(1, rows + 1):
        for j in range(1, cols + 1):
            fig.update_xaxes(title_text="Индекс свечи", row=i, col=j)
            fig.update_yaxes(title_text="Цена", row=i, col=j)
    
    return fig


def main():
    print("=" * 60)
    print("ВИЗУАЛИЗАЦИЯ ГЕОМЕТРИЧЕСКИХ ОГРАНИЧЕНИЙ SHORT")
    print("=" * 60)
    print()
    
    # Базовые параметры (для SHORT T0 выше T1)
    T0_base = 200  # Вершина
    T1_base = 100  # Низ (флагшток = 100)
    
    # ============================================================
    # ВАЛИДНЫЕ ПАТТЕРНЫ
    # ============================================================
    print("Создание валидных паттернов...")
    
    valid_patterns = []
    
    # 1. Минимальные значения (на границе ограничений)
    fib_62_level = T1_base + 0.62 * (T0_base - T1_base)  # 138
    T2_min = fib_62_level  # 138 (на границе)
    move_12 = T2_min - T1_base  # 38
    max_t3 = T2_min - 0.5 * move_12  # 119
    T3_min = T1_base  # 100 (на границе)
    move_23 = T2_min - T3_min  # 38
    min_t4 = T3_min + 0.5 * move_23  # 119
    T4_min = min_t4  # 119
    
    pattern1 = create_flag_pattern(T0_base, T1_base, T2_min, T3_min, T4_min, 
                                   "1. Минимальные значения")
    valid_patterns.append(pattern1)
    
    # 2. Средние значения
    fib_62_level = T1_base + 0.62 * (T0_base - T1_base)  # 138
    T2_mid = fib_62_level - 5  # 133 (ниже максимума)
    move_12_mid = T2_mid - T1_base  # 33
    max_t3_mid = T2_mid - 0.5 * move_12_mid  # 116.5
    T3_mid = T1_base + (max_t3_mid - T1_base) * 0.5  # 108.25
    move_23_mid = T2_mid - T3_mid  # 24.75
    T4_mid = T3_mid + 0.55 * move_23_mid  # 121.86
    
    pattern2 = create_flag_pattern(T0_base, T1_base, T2_mid, T3_mid, T4_mid,
                                   "2. Средние значения")
    valid_patterns.append(pattern2)
    
    # 3. Максимальные значения (T3 близко к T1)
    fib_62_level = T1_base + 0.62 * (T0_base - T1_base)  # 138
    T2_max = fib_62_level - 3  # 135
    move_12_max = T2_max - T1_base  # 35
    max_t3_max = T2_max - 0.5 * move_12_max  # 117.5
    T3_max = T1_base  # Минимум T3 = T1
    move_23_max = T2_max - T3_max  # 35
    T4_max = T3_max + 0.5 * move_23_max  # 117.5
    
    pattern3 = create_flag_pattern(T0_base, T1_base, T2_max, T3_max, T4_max,
                                   "3. T3 = T1 (минимум)")
    valid_patterns.append(pattern3)
    
    # 4. Схождение линий (усиливающийся флаг)
    fib_62_level = T1_base + 0.62 * (T0_base - T1_base)  # 138
    T2_conv = fib_62_level - 8  # 130
    move_12_conv = T2_conv - T1_base  # 30
    max_t3_conv = T2_conv - 0.5 * move_12_conv  # 115
    T3_conv = T1_base + (max_t3_conv - T1_base) * 0.3  # 104.5
    move_23_conv = T2_conv - T3_conv  # 25.5
    T4_conv = T3_conv + 0.6 * move_23_conv  # 119.8
    
    pattern4 = create_flag_pattern(T0_base, T1_base, T2_conv, T3_conv, T4_conv,
                                   "4. Схождение линий")
    valid_patterns.append(pattern4)
    
    # 5. Параллельные линии
    # Для параллельности: slope_13 = slope_24
    # slope_13 = (T3 - T1) / 50
    # slope_24 = (T4 - T2) / 50
    # Для параллельности: (T3 - T1) / 50 = (T4 - T2) / 50 => T3 - T1 = T4 - T2
    # Отсюда: T4 = T2 + (T3 - T1)
    
    fib_62_level = T1_base + 0.62 * (T0_base - T1_base)  # 138
    T2_par = fib_62_level - 10  # 128
    move_12_par = T2_par - T1_base  # 28
    max_t3_par = T2_par - 0.5 * move_12_par  # 114
    
    # Устанавливаем T4 на уровне фиба 0.62 (верхняя граница)
    T4_par = fib_62_level  # 138
    
    # Вычисляем T3 для параллельности: T4 = T2 + (T3 - T1) => T3 = T1 + (T4 - T2)
    T3_par = T1_base + (T4_par - T2_par)  # 100 + (138 - 128) = 110
    
    # Проверяем ограничения для T3
    if T3_par > max_t3_par:
        # Если T3 слишком высокий, используем максимальный T3
        T3_par = max_t3_par  # 114
        # Пересчитываем T4 для параллельности
        T4_par = T2_par + (T3_par - T1_base)  # 128 + (114 - 100) = 142
        # Но T4 должна быть <= fib_62_level, поэтому корректируем
        if T4_par > fib_62_level:
            # Если T4 выше максимума, устанавливаем T4 на максимум и пересчитываем T3
            T4_par = fib_62_level  # 138
            T3_par = T1_base + (T4_par - T2_par)  # 110
    
    # Проверяем минимальный откат от T3
    move_23_par = T2_par - T3_par  # 18
    min_t4_from_t3 = T3_par + 0.5 * move_23_par  # 119
    
    if T4_par < min_t4_from_t3:
        # Если T4 слишком низкий, ограничиваем
        T4_par = min_t4_from_t3  # 119
        # Пересчитываем T3 для параллельности
        T3_par = T1_base + (T4_par - T2_par)  # 91
        # Но T3 не может быть ниже T1
        if T3_par < T1_base:
            T3_par = T1_base  # 100
            # Пересчитываем T4 для параллельности
            T4_par = T2_par + (T3_par - T1_base)  # 128
    
    pattern5 = create_flag_pattern(T0_base, T1_base, T2_par, T3_par, T4_par,
                                   "5. Параллельные линии")
    valid_patterns.append(pattern5)
    
    # 6. Горизонтальная линия T2-T4
    # Для горизонтальности: T2 = T4
    fib_62_level = T1_base + 0.62 * (T0_base - T1_base)  # 138
    T2_horiz = fib_62_level - 15  # 123
    T4_horiz = T2_horiz  # 123 (горизонтальная линия: T2 = T4)
    move_12_horiz = T2_horiz - T1_base  # 23
    max_t3_horiz = T2_horiz - 0.5 * move_12_horiz  # 111.5
    
    # Выбираем T3 в допустимом диапазоне
    T3_horiz = T1_base + (max_t3_horiz - T1_base) * 0.5  # 105.75
    
    # Проверяем ограничения для T4
    move_23_horiz = T2_horiz - T3_horiz  # 17.25
    min_t4_from_t3 = T3_horiz + 0.5 * move_23_horiz  # 114.375
    
    if T4_horiz < min_t4_from_t3:
        # Если T4 слишком низкий, корректируем T2 = T4
        T4_horiz = min_t4_from_t3  # 114.375
        T2_horiz = T4_horiz  # 114.375
        # Пересчитываем T3 с учетом нового T2
        move_12_horiz = T2_horiz - T1_base  # 14.375
        max_t3_horiz = T2_horiz - 0.5 * move_12_horiz  # 107.19
        T3_horiz = T1_base + (max_t3_horiz - T1_base) * 0.5  # 103.59
    
    pattern6 = create_flag_pattern(T0_base, T1_base, T2_horiz, T3_horiz, T4_horiz,
                                   "6. Горизонтальная линия T2-T4")
    valid_patterns.append(pattern6)
    
    # 7. Глубокий флаг (T2 близко к фиба 0.62)
    fib_62_level = T1_base + 0.62 * (T0_base - T1_base)  # 138
    T2_deep = fib_62_level - 0.01  # 137.99 (почти на границе)
    move_12_deep = T2_deep - T1_base  # 37.99
    max_t3_deep = T2_deep - 0.5 * move_12_deep  # 118.995
    T3_deep = T1_base + (max_t3_deep - T1_base) * 0.55  # 110.45
    move_23_deep = T2_deep - T3_deep  # 27.54
    T4_deep = T3_deep + 0.5 * move_23_deep  # 124.22
    
    pattern7 = create_flag_pattern(T0_base, T1_base, T2_deep, T3_deep, T4_deep,
                                   "7. Глубокий флаг (T2 у фиба 0.62)")
    valid_patterns.append(pattern7)
    
    # ============================================================
    # ПАТТЕРНЫ С НАРУШЕНИЯМИ (для сравнения)
    # ============================================================
    print("Создание паттернов с нарушениями...")
    
    invalid_patterns = []
    
    # Нарушение 1: T2 выше фиба 0.62
    fib_62_level = T1_base + 0.62 * (T0_base - T1_base)  # 138
    T2_viol1 = fib_62_level + 10  # 148 (выше 138)
    T3_viol1 = T1_base + 10  # 110
    T4_viol1 = T3_viol1 + 0.5 * (T2_viol1 - T3_viol1)  # 129
    
    pattern_viol1 = create_flag_pattern(T0_base, T1_base, T2_viol1, T3_viol1, T4_viol1,
                                       "Нарушение: T2 > фиба 0.62")
    invalid_patterns.append(pattern_viol1)
    
    # Нарушение 2: T3 выше максимального падения
    fib_62_level = T1_base + 0.62 * (T0_base - T1_base)  # 138
    T2_viol2 = fib_62_level - 5  # 133
    move_12_viol2 = T2_viol2 - T1_base  # 33
    max_t3_required = T2_viol2 - 0.5 * move_12_viol2  # 116.5
    T3_viol2 = max_t3_required + 5  # 121.5 (выше максимума)
    T4_viol2 = T3_viol2 + 0.5 * (T2_viol2 - T3_viol2)  # 127.25
    
    pattern_viol2 = create_flag_pattern(T0_base, T1_base, T2_viol2, T3_viol2, T4_viol2,
                                       "Нарушение: T3 > max падения")
    invalid_patterns.append(pattern_viol2)
    
    # Нарушение 3: T4 выше фиба 0.62
    fib_62_level = T1_base + 0.62 * (T0_base - T1_base)  # 138
    T2_viol3 = fib_62_level - 8  # 130
    T3_viol3 = T1_base + 5  # 105
    T4_viol3 = fib_62_level + 10  # 148 (выше фиба 0.62 = 138)
    
    pattern_viol3 = create_flag_pattern(T0_base, T1_base, T2_viol3, T3_viol3, T4_viol3,
                                       "Нарушение: T4 > фиба 0.62")
    invalid_patterns.append(pattern_viol3)
    
    # Создаем графики
    print("Создание графиков...")
    
    fig_valid = create_plot(valid_patterns, "ВАЛИДНЫЕ ПАТТЕРНЫ SHORT (с соблюдением всех правил)")
    fig_invalid = create_plot(invalid_patterns, "ПАТТЕРНЫ SHORT С НАРУШЕНИЯМИ (для сравнения)")
    
    # Сохраняем
    output_valid = 'neural_network/geometry_rules_short_valid.html'
    output_invalid = 'neural_network/geometry_rules_short_invalid.html'
    
    fig_valid.write_html(output_valid)
    fig_invalid.write_html(output_invalid)
    
    print(f"✅ Валидные паттерны сохранены: {output_valid}")
    print(f"✅ Паттерны с нарушениями сохранены: {output_invalid}")
    print()
    
    # Выводим информацию о правилах
    print("=" * 60)
    print("ПРАВИЛА ГЕОМЕТРИЧЕСКИХ ОГРАНИЧЕНИЙ SHORT:")
    print("=" * 60)
    print("1. T0 - нет ограничений")
    print("2. T1 - нет ограничений")
    print("3. T2 <= T1 + 0.62 * (T0 - T1)  (не выше коррекции фиба 0.62 от T1)")
    print("4. T3 <= T2 - 0.5 * (T2 - T1)  (минимум 50% падения от T2)")
    print("   T3 >= T1  (не ниже дна флагштока)")
    print("5. T4 >= T3 + 0.5 * (T2 - T3)  (макс откат 50% от T2-T3)")
    print("   T4 <= T1 + 0.62 * (T0 - T1)  (не выше коррекции фиба 0.62 от T1)")
    print("6. Линии T1-T3 и T2-T4: параллельны или сходятся (не расходятся)")
    print()
    
    # Показываем графики
    try:
        fig_valid.show()
        fig_invalid.show()
    except:
        print("💡 Откройте HTML файлы в браузере для просмотра")
    
    print("=" * 60)
    print("✅ ВИЗУАЛИЗАЦИЯ ЗАВЕРШЕНА")
    print("=" * 60)


if __name__ == "__main__":
    main()

