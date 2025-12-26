"""
Тренировщик модели для обучения и дообучения нейронной сети
"""

import os
import torch
import torch.nn as nn
import torch.optim as optim
from torch.optim.lr_scheduler import ReduceLROnPlateau
import numpy as np
from tqdm import tqdm
import json
from datetime import datetime

from .model import FlagPatternCNN


class ModelTrainer:
    """
    Класс для обучения и дообучения модели
    """
    
    def __init__(self, model, device=None):
        """
        Args:
            model: Экземпляр модели FlagPatternCNN
            device: Устройство для обучения (cuda/cpu)
        """
        self.model = model
        
        if device is None:
            self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        else:
            self.device = device
        
        self.model.to(self.device)
        
        # История обучения
        self.history = {
            'train_loss': [],
            'train_acc': [],
            'val_loss': [],
            'val_acc': [],
            'epochs': []
        }
    
    def train_epoch(self, train_loader, criterion, optimizer):
        """Одна эпоха обучения"""
        self.model.train()
        running_loss = 0.0
        correct = 0
        total = 0
        
        for images, labels in tqdm(train_loader, desc="Training"):
            images = images.to(self.device)
            labels = labels.to(self.device)
            
            # Обнуляем градиенты
            optimizer.zero_grad()
            
            # Прямой проход
            outputs = self.model(images)
            loss = criterion(outputs, labels)
            
            # Обратный проход
            loss.backward()
            optimizer.step()
            
            # Статистика
            running_loss += loss.item()
            _, predicted = torch.max(outputs.data, 1)
            total += labels.size(0)
            correct += (predicted == labels).sum().item()
        
        epoch_loss = running_loss / len(train_loader)
        epoch_acc = 100 * correct / total
        
        return epoch_loss, epoch_acc
    
    def validate(self, val_loader, criterion):
        """Валидация модели"""
        self.model.eval()
        running_loss = 0.0
        correct = 0
        total = 0
        
        with torch.no_grad():
            for images, labels in tqdm(val_loader, desc="Validation"):
                images = images.to(self.device)
                labels = labels.to(self.device)
                
                outputs = self.model(images)
                loss = criterion(outputs, labels)
                
                running_loss += loss.item()
                _, predicted = torch.max(outputs.data, 1)
                total += labels.size(0)
                correct += (predicted == labels).sum().item()
        
        epoch_loss = running_loss / len(val_loader)
        epoch_acc = 100 * correct / total
        
        return epoch_loss, epoch_acc
    
    def train(self, train_loader, val_loader=None, epochs=10, learning_rate=0.001,
              save_dir='models', save_best=True, save_last=True, resume_from=None):
        """
        Обучение модели
        
        Args:
            train_loader: DataLoader для обучения
            val_loader: DataLoader для валидации (опционально)
            epochs: Количество эпох
            learning_rate: Скорость обучения
            save_dir: Директория для сохранения моделей
            save_best: Сохранять ли лучшую модель
            save_last: Сохранять ли последнюю модель
            resume_from: Путь к чекпоинту для продолжения обучения
        """
        os.makedirs(save_dir, exist_ok=True)
        
        # Загружаем чекпоинт если указан
        start_epoch = 0
        best_val_acc = 0.0
        
        if resume_from and os.path.exists(resume_from):
            checkpoint = torch.load(resume_from, map_location=self.device)
            self.model.load_state_dict(checkpoint['model_state_dict'])
            start_epoch = checkpoint.get('epoch', 0) + 1
            best_val_acc = checkpoint.get('best_val_acc', 0.0)
            self.history = checkpoint.get('history', self.history)
            print(f"✅ Продолжение обучения с эпохи {start_epoch}")
        
        # Критерий и оптимизатор
        criterion = nn.CrossEntropyLoss()
        optimizer = optim.Adam(self.model.parameters(), lr=learning_rate, weight_decay=1e-5)
        scheduler = ReduceLROnPlateau(optimizer, mode='min', factor=0.5, patience=3, verbose=True)
        
        print(f"🚀 Начало обучения на устройстве: {self.device}")
        print(f"   Эпох: {epochs}")
        print(f"   Learning rate: {learning_rate}")
        print(f"   Размер датасета: {len(train_loader.dataset)}")
        
        for epoch in range(start_epoch, epochs):
            print(f"\n{'='*60}")
            print(f"Эпоха {epoch + 1}/{epochs}")
            print(f"{'='*60}")
            
            # Обучение
            train_loss, train_acc = self.train_epoch(train_loader, criterion, optimizer)
            self.history['train_loss'].append(train_loss)
            self.history['train_acc'].append(train_acc)
            
            print(f"Train Loss: {train_loss:.4f}, Train Acc: {train_acc:.2f}%")
            
            # Валидация
            if val_loader:
                val_loss, val_acc = self.validate(val_loader, criterion)
                self.history['val_loss'].append(val_loss)
                self.history['val_acc'].append(val_acc)
                self.history['epochs'].append(epoch + 1)
                
                print(f"Val Loss: {val_loss:.4f}, Val Acc: {val_acc:.2f}%")
                
                # Обновляем learning rate
                scheduler.step(val_loss)
                
                # Сохраняем лучшую модель
                if save_best and val_acc > best_val_acc:
                    best_val_acc = val_acc
                    best_model_path = os.path.join(save_dir, 'best_model.pth')
                    self.save_checkpoint(best_model_path, epoch, best_val_acc)
                    print(f"✅ Сохранена лучшая модель (Val Acc: {val_acc:.2f}%)")
            else:
                self.history['epochs'].append(epoch + 1)
            
            # Сохраняем последнюю модель
            if save_last:
                last_model_path = os.path.join(save_dir, 'last_model.pth')
                self.save_checkpoint(last_model_path, epoch, best_val_acc if val_loader else 0)
        
        print(f"\n{'='*60}")
        print("✅ Обучение завершено!")
        print(f"{'='*60}")
        
        # Сохраняем историю
        history_path = os.path.join(save_dir, 'training_history.json')
        with open(history_path, 'w') as f:
            json.dump(self.history, f, indent=2)
        print(f"📊 История сохранена: {history_path}")
    
    def save_checkpoint(self, path, epoch, best_val_acc):
        """Сохраняет чекпоинт модели"""
        checkpoint = {
            'epoch': epoch,
            'model_state_dict': self.model.state_dict(),
            'best_val_acc': best_val_acc,
            'history': self.history,
            'timestamp': datetime.now().isoformat()
        }
        torch.save(checkpoint, path)
    
    def fine_tune(self, new_data_loader, epochs=5, learning_rate=0.0001):
        """
        Дообучение модели на новых данных
        
        Args:
            new_data_loader: DataLoader с новыми размеченными данными
            epochs: Количество эпох дообучения
            learning_rate: Скорость обучения (обычно меньше чем при основном обучении)
        """
        print(f"🔄 Дообучение модели на {len(new_data_loader.dataset)} новых образцах...")
        
        criterion = nn.CrossEntropyLoss()
        optimizer = optim.Adam(self.model.parameters(), lr=learning_rate, weight_decay=1e-5)
        
        for epoch in range(epochs):
            print(f"\nЭпоха дообучения {epoch + 1}/{epochs}")
            train_loss, train_acc = self.train_epoch(new_data_loader, criterion, optimizer)
            print(f"Loss: {train_loss:.4f}, Acc: {train_acc:.2f}%")
    
    def predict_batch(self, data_loader):
        """
        Предсказание на батче данных
        
        Returns:
            predicted_labels, probabilities
        """
        self.model.eval()
        all_preds = []
        all_probs = []
        
        with torch.no_grad():
            for images, _ in data_loader:
                images = images.to(self.device)
                preds, probs = self.model.predict(images)
                all_preds.extend(preds.cpu().numpy())
                all_probs.extend(probs.cpu().numpy())
        
        return np.array(all_preds), np.array(all_probs)


if __name__ == "__main__":
    # Тестирование тренировщика
    print("Тестирование тренировщика...")
    
    # Создаем модель
    model = FlagPatternCNN(num_classes=3)
    trainer = ModelTrainer(model)
    
    print(f"✅ Тренировщик создан на устройстве: {trainer.device}")

