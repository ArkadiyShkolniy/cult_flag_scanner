import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
# import seaborn as sns
from pathlib import Path

# Настройки
DATA_FILE = Path("neural_network/data/annotations.csv")
OUTPUT_IMG = Path("neural_network/average_pattern_analysis.png")

def normalize_pattern(row, direction):
    """
    Нормализует координаты паттерна.
    Центр (0,0) - это точка T1.
    Масштаб по Y - высота флагштока.
    """
    t0_price, t1_price = row['t0_price'], row['t1_price']
    t2_price, t3_price = row['t2_price'], row['t3_price']
    t4_price = row['t4_price']
    
    t0_idx, t1_idx = row['t0_idx'], row['t1_idx']
    t2_idx, t3_idx = row['t2_idx'], row['t3_idx']
    t4_idx = row['t4_idx']
    
    # Высота флагштока
    pole_height = abs(t1_price - t0_price)
    if pole_height == 0: return None
    
    # Функция нормализации Y
    # Для LONG: T1 - вершина (0), T0 - дно (-1). Цены ниже T1 отрицательные.
    # Для SHORT: T1 - дно (0), T0 - вершина (+1). Цены выше T1 положительные.
    
    if direction == 'LONG':
        # Нормализуем так, чтобы T1=0, T0=-1
        # y_norm = (price - t1) / pole_height
        def norm_y(p): return (p - t1_price) / pole_height
    else: # SHORT
        # Нормализуем так, чтобы T1=0, T0=+1
        # y_norm = (price - t1) / pole_height
        def norm_y(p): return (p - t1_price) / pole_height

    # Функция нормализации X (относительно T1)
    def norm_x(idx): return idx - t1_idx
    
    return {
        't0': (norm_x(t0_idx), norm_y(t0_price)),
        't1': (0, 0),
        't2': (norm_x(t2_idx), norm_y(t2_price)),
        't3': (norm_x(t3_idx), norm_y(t3_price)),
        't4': (norm_x(t4_idx), norm_y(t4_price)),
    }

def analyze_direction(df, direction_label, direction_name):
    """
    Анализирует паттерны конкретного направления (1=LONG, 2=SHORT).
    """
    subset = df[df['label'] == direction_label]
    if len(subset) == 0:
        return None, None
        
    normalized_points = {'t0': [], 't1': [], 't2': [], 't3': [], 't4': []}
    
    valid_count = 0
    for _, row in subset.iterrows():
        try:
            norm = normalize_pattern(row, direction_name)
            if norm:
                for key in normalized_points:
                    normalized_points[key].append(norm[key])
                valid_count += 1
        except Exception:
            continue
            
    # Считаем статистику
    stats = {}
    for key in normalized_points:
        coords = np.array(normalized_points[key])
        stats[key] = {
            'x_mean': np.mean(coords[:, 0]),
            'y_mean': np.mean(coords[:, 1]),
            'x_std': np.std(coords[:, 0]),
            'y_std': np.std(coords[:, 1]),
            'count': len(coords)
        }
        
    return stats, valid_count

def plot_average_patterns():
    print("📊 Анализ усредненного паттерна...")
    
    if not DATA_FILE.exists():
        print(f"❌ Файл не найден: {DATA_FILE}")
        return

    df = pd.read_csv(DATA_FILE)
    # Убираем записи без координат
    df = df.dropna(subset=['t0_price', 't4_price'])
    
    stats_long, count_long = analyze_direction(df, 1, 'LONG')
    stats_short, count_short = analyze_direction(df, 2, 'SHORT')
    
    # Настройка графиков
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 7))
    
    # --- LONG ---
    if stats_long:
        points = ['t0', 't1', 't2', 't3', 't4']
        x = [stats_long[p]['x_mean'] for p in points]
        y = [stats_long[p]['y_mean'] for p in points]
        y_err = [stats_long[p]['y_std'] for p in points]
        
        # Рисуем линию
        ax1.plot(x, y, 'g-o', linewidth=2, label='Средний LONG')
        
        # Рисуем облако разброса (Standard Deviation)
        ax1.fill_between(x, 
                         np.array(y) - np.array(y_err), 
                         np.array(y) + np.array(y_err), 
                         color='green', alpha=0.2, label='Разброс (1 std)')
        
        # Подписи
        for i, p in enumerate(points):
            ax1.annotate(f"{p}\n({y[i]:.2f})", (x[i], y[i]), xytext=(0, 10), textcoords='offset points', ha='center')
            
        ax1.set_title(f"Средний LONG паттерн (N={count_long})")
        ax1.set_xlabel("Бары (относительно T1)")
        ax1.set_ylabel("Цена (Нормирована к высоте флагштока)")
        ax1.grid(True, alpha=0.3)
        ax1.axhline(0, color='black', linestyle='--', alpha=0.5) # Уровень T1
        
        # Вывод статистики текстом
        print(f"\n📈 LONG Статистика (относительно высоты флагштока 1.0):")
        print(f"   T2 коррекция: {abs(stats_long['t2']['y_mean']):.1%} (std {stats_long['t2']['y_std']:.1%})")
        print(f"   T3 отскок: {abs(stats_long['t3']['y_mean']):.1%} (от T1)")
        print(f"   Длительность T1-T4: {stats_long['t4']['x_mean']:.1f} баров")

    # --- SHORT ---
    if stats_short:
        points = ['t0', 't1', 't2', 't3', 't4']
        x = [stats_short[p]['x_mean'] for p in points]
        y = [stats_short[p]['y_mean'] for p in points]
        y_err = [stats_short[p]['y_std'] for p in points]
        
        # Рисуем линию
        ax2.plot(x, y, 'r-o', linewidth=2, label='Средний SHORT')
        
        # Рисуем облако разброса
        ax2.fill_between(x, 
                         np.array(y) - np.array(y_err), 
                         np.array(y) + np.array(y_err), 
                         color='red', alpha=0.2, label='Разброс (1 std)')
        
        # Подписи
        for i, p in enumerate(points):
            ax2.annotate(f"{p}\n({y[i]:.2f})", (x[i], y[i]), xytext=(0, -15), textcoords='offset points', ha='center')
            
        ax2.set_title(f"Средний SHORT паттерн (N={count_short})")
        ax2.set_xlabel("Бары (относительно T1)")
        ax2.grid(True, alpha=0.3)
        ax2.axhline(0, color='black', linestyle='--', alpha=0.5) # Уровень T1

        print(f"\n📉 SHORT Статистика:")
        print(f"   T2 коррекция: {abs(stats_short['t2']['y_mean']):.1%} (std {stats_short['t2']['y_std']:.1%})")
        print(f"   T3 отскок: {abs(stats_short['t3']['y_mean']):.1%} (от T1)")
        print(f"   Длительность T1-T4: {stats_short['t4']['x_mean']:.1f} баров")

    plt.tight_layout()
    plt.savefig(OUTPUT_IMG)
    print(f"\n✅ График сохранен в {OUTPUT_IMG}")

if __name__ == "__main__":
    plot_average_patterns()
