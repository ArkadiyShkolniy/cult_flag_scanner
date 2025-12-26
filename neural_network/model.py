"""
Архитектура нейронной сети для распознавания паттернов "Флаг"
Использует CNN для анализа изображений графиков свечей
"""

import torch
import torch.nn as nn
import torch.nn.functional as F


class FlagPatternCNN(nn.Module):
    """
    Сверточная нейронная сеть для классификации паттернов "Флаг"
    
    Вход: изображение графика свечей (3 канала: OHLC нормализованный)
    Выход: вероятность наличия паттерна (бычий/медвежий/нет)
    """
    
    def __init__(self, num_classes=3, image_height=224, image_width=224):
        """
        Args:
            num_classes: Количество классов (0=нет паттерна, 1=бычий, 2=медвежий)
            image_height: Высота входного изображения
            image_width: Ширина входного изображения
        """
        super(FlagPatternCNN, self).__init__()
        
        self.num_classes = num_classes
        self.image_height = image_height
        self.image_width = image_width
        
        # Первый блок сверток
        self.conv1 = nn.Conv2d(3, 32, kernel_size=3, padding=1)
        self.bn1 = nn.BatchNorm2d(32)
        self.conv2 = nn.Conv2d(32, 32, kernel_size=3, padding=1)
        self.bn2 = nn.BatchNorm2d(32)
        self.pool1 = nn.MaxPool2d(2, 2)
        
        # Второй блок сверток
        self.conv3 = nn.Conv2d(32, 64, kernel_size=3, padding=1)
        self.bn3 = nn.BatchNorm2d(64)
        self.conv4 = nn.Conv2d(64, 64, kernel_size=3, padding=1)
        self.bn4 = nn.BatchNorm2d(64)
        self.pool2 = nn.MaxPool2d(2, 2)
        
        # Третий блок сверток
        self.conv5 = nn.Conv2d(64, 128, kernel_size=3, padding=1)
        self.bn5 = nn.BatchNorm2d(128)
        self.conv6 = nn.Conv2d(128, 128, kernel_size=3, padding=1)
        self.bn6 = nn.BatchNorm2d(128)
        self.pool3 = nn.MaxPool2d(2, 2)
        
        # Четвертый блок сверток
        self.conv7 = nn.Conv2d(128, 256, kernel_size=3, padding=1)
        self.bn7 = nn.BatchNorm2d(256)
        self.conv8 = nn.Conv2d(256, 256, kernel_size=3, padding=1)
        self.bn8 = nn.BatchNorm2d(256)
        self.pool4 = nn.MaxPool2d(2, 2)
        
        # Вычисляем размер после сверток
        # После 4 пулов: 224 -> 112 -> 56 -> 28 -> 14
        self.fc_input_size = 256 * (image_height // 16) * (image_width // 16)
        
        # Полносвязные слои
        self.fc1 = nn.Linear(self.fc_input_size, 512)
        self.dropout1 = nn.Dropout(0.5)
        self.fc2 = nn.Linear(512, 256)
        self.dropout2 = nn.Dropout(0.5)
        self.fc3 = nn.Linear(256, num_classes)
        
    def forward(self, x):
        """Прямой проход"""
        # Блок 1
        x = F.relu(self.bn1(self.conv1(x)))
        x = F.relu(self.bn2(self.conv2(x)))
        x = self.pool1(x)
        
        # Блок 2
        x = F.relu(self.bn3(self.conv3(x)))
        x = F.relu(self.bn4(self.conv4(x)))
        x = self.pool2(x)
        
        # Блок 3
        x = F.relu(self.bn5(self.conv5(x)))
        x = F.relu(self.bn6(self.conv6(x)))
        x = self.pool3(x)
        
        # Блок 4
        x = F.relu(self.bn7(self.conv7(x)))
        x = F.relu(self.bn8(self.conv8(x)))
        x = self.pool4(x)
        
        # Выпрямление
        x = x.view(x.size(0), -1)
        
        # Полносвязные слои
        x = F.relu(self.fc1(x))
        x = self.dropout1(x)
        x = F.relu(self.fc2(x))
        x = self.dropout2(x)
        x = self.fc3(x)
        
        return x
    
    def predict(self, x):
        """Предсказание с применением softmax"""
        with torch.no_grad():
            outputs = self.forward(x)
            probabilities = F.softmax(outputs, dim=1)
            predicted_class = torch.argmax(probabilities, dim=1)
        return predicted_class, probabilities


def create_model(num_classes=3, image_height=224, image_width=224, pretrained_path=None):
    """
    Создает модель, опционально загружая предобученные веса
    
    Args:
        num_classes: Количество классов
        image_height: Высота изображения
        image_width: Ширина изображения
        pretrained_path: Путь к файлу с весами для загрузки
    
    Returns:
        Объект модели
    """
    model = FlagPatternCNN(num_classes, image_height, image_width)
    
    if pretrained_path:
        try:
            checkpoint = torch.load(pretrained_path, map_location='cpu')
            if 'model_state_dict' in checkpoint:
                model.load_state_dict(checkpoint['model_state_dict'])
            else:
                model.load_state_dict(checkpoint)
            print(f"✅ Загружены веса из {pretrained_path}")
        except Exception as e:
            print(f"⚠️ Не удалось загрузить веса: {e}")
    
    return model


if __name__ == "__main__":
    # Тестирование архитектуры
    model = FlagPatternCNN(num_classes=3)
    
    # Тестовый вход (batch_size=1, channels=3, height=224, width=224)
    test_input = torch.randn(1, 3, 224, 224)
    
    # Прямой проход
    output = model(test_input)
    print(f"Размер выхода: {output.shape}")
    print(f"Выходные значения: {output}")
    
    # Предсказание
    pred_class, probabilities = model.predict(test_input)
    print(f"Предсказанный класс: {pred_class.item()}")
    print(f"Вероятности: {probabilities}")

