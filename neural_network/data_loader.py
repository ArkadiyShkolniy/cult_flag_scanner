"""
Загрузчик данных для обучения нейронной сети
Преобразует данные свечей в изображения и подготавливает датасет
"""

import os
import pandas as pd
import numpy as np
import torch
from torch.utils.data import Dataset, DataLoader
import matplotlib
matplotlib.use('Agg')  # Неинтерактивный бэкенд
import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg
import io
from PIL import Image


class FlagPatternDataset(Dataset):
    """
    Датасет для обучения сети на паттернах "Флаг"
    """
    
    def __init__(self, data_dir, transform=None, image_size=(224, 224)):
        """
        Args:
            data_dir: Директория с данными (CSV файлы и метки)
            transform: Трансформации для аугментации
            image_size: Размер выходного изображения (height, width)
        """
        self.data_dir = data_dir
        self.transform = transform
        self.image_size = image_size
        
        # Загружаем список файлов с метками
        self.annotations_file = os.path.join(data_dir, 'annotations.csv')
        if os.path.exists(self.annotations_file):
            self.annotations = pd.read_csv(self.annotations_file)
        else:
            self.annotations = pd.DataFrame(columns=['file', 'label', 'ticker', 'timeframe'])
            print("⚠️ Файл аннотаций не найден, создан пустой датасет")
        
    def __len__(self):
        return len(self.annotations)
    
    def __getitem__(self, idx):
        """Получает один элемент датасета"""
        row = self.annotations.iloc[idx]
        file_path = os.path.join(self.data_dir, row['file'])
        
        # Загружаем данные свечей
        df = pd.read_csv(file_path)
        
        # Преобразуем в изображение
        image = self._candles_to_image(df)
        
        # Применяем трансформации
        if self.transform:
            image = self.transform(image)
        
        # Метка класса (0=нет, 1=бычий, 2=медвежий)
        label = int(row['label'])
        
        return image, label
    
    def _candles_to_image(self, df, window=100):
        """
        Преобразует свечи в изображение графика
        
        Args:
            df: DataFrame со свечами (columns: time, open, high, low, close, volume)
            window: Количество свечей для отображения (если данных больше)
        
        Returns:
            Тензор изображения (3, H, W) в формате torch.Tensor
        """
        # Берем последние window свечей
        if len(df) > window:
            df_plot = df.tail(window).copy()
        else:
            df_plot = df.copy()
        
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
        img_pil = img_pil.resize(self.image_size, Image.LANCZOS)
        
        # Конвертируем в numpy array и нормализуем
        img_array = np.array(img_pil).astype(np.float32) / 255.0
        
        # Преобразуем в формат (C, H, W)
        img_tensor = torch.from_numpy(img_array).permute(2, 0, 1)
        
        return img_tensor


def create_data_loader(data_dir, batch_size=32, shuffle=True, transform=None, 
                       image_size=(224, 224), train_split=0.8):
    """
    Создает DataLoader для обучения
    
    Args:
        data_dir: Директория с данными
        batch_size: Размер батча
        shuffle: Перемешивать ли данные
        transform: Трансформации
        image_size: Размер изображения
        train_split: Доля данных для обучения (остальное для валидации)
    
    Returns:
        train_loader, val_loader
    """
    dataset = FlagPatternDataset(data_dir, transform=transform, image_size=image_size)
    
    # Разделение на train/val
    train_size = int(train_split * len(dataset))
    val_size = len(dataset) - train_size
    
    if train_size > 0 and val_size > 0:
        train_dataset, val_dataset = torch.utils.data.random_split(
            dataset, [train_size, val_size]
        )
        
        train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=shuffle)
        val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False)
        
        return train_loader, val_loader
    else:
        # Если данных мало, используем весь датасет для обучения
        train_loader = DataLoader(dataset, batch_size=batch_size, shuffle=shuffle)
        return train_loader, None


if __name__ == "__main__":
    # Тестирование загрузчика
    print("Тестирование загрузчика данных...")
    
    # Создаем тестовые данные
    test_dir = "test_data"
    os.makedirs(test_dir, exist_ok=True)
    
    # Тестовый CSV
    test_df = pd.DataFrame({
        'time': pd.date_range('2024-01-01', periods=100, freq='1H'),
        'open': np.random.rand(100) * 100 + 50,
        'high': np.random.rand(100) * 100 + 52,
        'low': np.random.rand(100) * 100 + 48,
        'close': np.random.rand(100) * 100 + 50,
        'volume': np.random.randint(1000, 10000, 100)
    })
    
    test_file = os.path.join(test_dir, "test_candles.csv")
    test_df.to_csv(test_file, index=False)
    
    # Создаем аннотацию
    annotations = pd.DataFrame({
        'file': ['test_candles.csv'],
        'label': [1],  # Бычий паттерн
        'ticker': ['TEST'],
        'timeframe': ['1h']
    })
    annotations.to_csv(os.path.join(test_dir, 'annotations.csv'), index=False)
    
    # Тестируем загрузчик
    dataset = FlagPatternDataset(test_dir)
    print(f"Размер датасета: {len(dataset)}")
    
    if len(dataset) > 0:
        image, label = dataset[0]
        print(f"Размер изображения: {image.shape}")
        print(f"Метка: {label}")

