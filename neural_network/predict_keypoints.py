"""
Предсказание ключевых точек паттернов с помощью скользящего окна
"""

import pandas as pd
import numpy as np
import torch
import matplotlib
matplotlib.use('Agg')  # Неинтерактивный бэкенд
import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg
from PIL import Image


def candles_to_image(df, window=100, image_size=(224, 224)):
    """
    Преобразует свечи в изображение графика
    
    Args:
        df: DataFrame со свечами (columns: open, high, low, close, volume)
        window: Количество свечей для отображения
        image_size: Размер выходного изображения (height, width)
    
    Returns:
        tuple: (img_tensor, normalization_params)
            img_tensor: Тензор изображения (3, H, W)
            normalization_params: dict с параметрами нормализации
    """
    # Берем последние window свечей
    if len(df) > window:
        df_plot = df.tail(window).copy()
        window_start = len(df) - window
    else:
        df_plot = df.copy()
        window_start = 0
    
    # Нормализуем цены (приводим к диапазону 0-1)
    price_min = df_plot[['low']].min().min()
    price_max = df_plot[['high']].max().max()
    price_range = price_max - price_min
    
    if price_range == 0:
        price_range = 1
    
    # Нормализуем данные
    df_normalized = df_plot.copy()
    for col in ['open', 'high', 'low', 'close']:
        df_normalized[col] = (df_plot[col] - price_min) / price_range
    
    # Нормализуем объем
    volume_max = df_plot['volume'].max()
    if volume_max > 0:
        df_normalized['volume'] = df_plot['volume'] / volume_max
    
    # Сохраняем параметры нормализации
    normalization_params = {
        'price_min': price_min,
        'price_max': price_max,
        'window_start': window_start,
        'window_size': len(df_plot)
    }
    
    # Создаем фигуру matplotlib
    fig = plt.figure(figsize=(10, 6), dpi=22.4)  # 224x224 пикселя при dpi=22.4
    fig.patch.set_facecolor('black')
    ax = fig.add_subplot(111)
    ax.set_facecolor('black')
    ax.axis('off')
    
    # Рисуем свечи
    for i, row in df_normalized.iterrows():
        idx = df_normalized.index.get_loc(i)
        open_price = row['open']
        close_price = row['close']
        high_price = row['high']
        low_price = row['low']
        
        # Цвет свечи
        color = 'green' if close_price >= open_price else 'red'
        
        # Тело свечи
        body_height = abs(close_price - open_price)
        body_bottom = min(open_price, close_price)
        rect = plt.Rectangle((idx - 0.3, body_bottom), 0.6, body_height, 
                           facecolor=color, edgecolor=color, linewidth=0.5)
        ax.add_patch(rect)
        
        # Тени
        ax.plot([idx, idx], [low_price, high_price], color=color, linewidth=1)
    
    # Убираем отступы
    plt.subplots_adjust(left=0, right=1, top=1, bottom=0)
    
    # Конвертируем в PIL Image
    canvas = FigureCanvasAgg(fig)
    canvas.draw()
    buf = canvas.buffer_rgba()
    img_array = np.asarray(buf)
    img_pil = Image.fromarray(img_array).convert('RGB')
    
    # Закрываем фигуру
    plt.close(fig)
    
    # Изменяем размер
    img_pil = img_pil.resize(image_size, Image.LANCZOS)
    
    # Конвертируем в numpy array и нормализуем
    img_array = np.array(img_pil).astype(np.float32) / 255.0
    
    # Преобразуем в формат (C, H, W)
    img_tensor = torch.from_numpy(img_array).permute(2, 0, 1)
    
    return img_tensor, normalization_params


def predict_with_sliding_window(df, model, window=100, step=10, device='cpu', min_confidence=0.5):
    """
    Предсказывает паттерны используя скользящее окно
    
    Args:
        df: DataFrame со свечами (columns: open, high, low, close, volume)
        model: Обученная модель нейронной сети
        window: Размер окна для анализа
        step: Шаг скользящего окна
        device: Устройство для вычислений ('cpu' или 'cuda')
        min_confidence: Минимальная уверенность для принятия паттерна
    
    Returns:
        list: Список предсказаний в формате:
            [{
                'class': 1 или 2 (1=бычий, 2=медвежий),
                'probability': float (уверенность),
                'points': [
                    {'idx': int, 'price': float},  # T0
                    {'idx': int, 'price': float},  # T1
                    {'idx': int, 'price': float},  # T2
                    {'idx': int, 'price': float},  # T3
                    {'idx': int, 'price': float}   # T4
                ]
            }, ...]
    """
    if model is None:
        return []
    
    model.eval()
    predictions = []
    
    # Проверяем, что в DataFrame достаточно данных
    if len(df) < window:
        return []
    
    # Скользящее окно
    for start_idx in range(0, len(df) - window + 1, step):
        end_idx = start_idx + window
        df_window = df.iloc[start_idx:end_idx].copy()
        
        try:
            # Преобразуем свечи в изображение
            img_tensor, norm_params = candles_to_image(df_window, window=window)
            
            # Добавляем batch dimension
            img_tensor = img_tensor.unsqueeze(0).to(device)
            
            # Предсказание
            with torch.no_grad():
                class_logits, keypoints = model(img_tensor)
                
                # Применяем softmax для получения вероятностей
                probabilities = torch.nn.functional.softmax(class_logits, dim=1)
                predicted_class = torch.argmax(probabilities, dim=1).item()
                confidence = probabilities[0][predicted_class].item()
            
            # Фильтруем по минимальной уверенности и классу (1=бычий, 2=медвежий)
            if predicted_class in [1, 2] and confidence >= min_confidence:
                # Преобразуем ключевые точки из нормализованных координат обратно в индексы и цены
                keypoints_np = keypoints[0].cpu().numpy()  # [5, 2] - 5 точек, x и y
                
                # Денормализуем координаты
                price_min = norm_params['price_min']
                price_max = norm_params['price_max']
                price_range = price_max - price_min
                
                points = []
                for i, (x_norm, y_norm) in enumerate(keypoints_np):
                    # x_norm в диапазоне [0, 1] -> индекс в окне [0, window-1]
                    idx_in_window = int(x_norm * (window - 1))
                    # Ограничиваем индекс
                    idx_in_window = max(0, min(window - 1, idx_in_window))
                    
                    # Реальный индекс в DataFrame
                    real_idx = start_idx + idx_in_window
                    
                    # y_norm в диапазоне [0, 1] -> цена
                    price = price_min + y_norm * price_range
                    
                    # Получаем реальную цену из DataFrame для точности
                    if real_idx < len(df):
                        # Используем close цену для точки
                        price = df.iloc[real_idx]['close']
                    
                    points.append({
                        'idx': real_idx,
                        'price': float(price)
                    })
                
                # Определяем окно паттерна (от T0 до T4)
                window_start = points[0]['idx'] if points else start_idx
                window_end = points[4]['idx'] if len(points) > 4 else end_idx - 1
                
                predictions.append({
                    'class': int(predicted_class),
                    'probability': float(confidence),
                    'points': points,
                    'window_start': window_start,
                    'window_end': window_end
                })
        
        except Exception as e:
            # Пропускаем окна с ошибками
            continue
    
    return predictions
