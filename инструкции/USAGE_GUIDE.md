# Подробная инструкция по использованию модуля нейронной сети

## 📋 Содержание

1. [Установка зависимостей](#установка-зависимостей)
2. [Подготовка данных для обучения](#подготовка-данных-для-обучения)
3. [Разметка паттернов](#разметка-паттернов)
4. [Обучение модели](#обучение-модели)
5. [Дообучение на новых данных](#дообучение-на-новых-данных)
6. [Использование для предсказаний](#использование-для-предсказаний)
7. [Интеграция со сканером](#интеграция-со-сканером)
8. [Часто задаваемые вопросы](#часто-задаваемые-вопросы)

---

## 1. Установка зависимостей

### Требования

Модуль требует следующие библиотеки:
- PyTorch (для нейронных сетей)
- torchvision (для работы с изображениями)
- Pillow (для обработки изображений)
- tqdm (для прогресс-баров)

### Установка

```bash
# Перейдите в директорию проекта
cd complex_flag_scanner

# Установите зависимости
pip install torch torchvision pillow tqdm

# Или установите все зависимости проекта
pip install -r requirements.txt
```

### Проверка установки

```python
import torch
print(f"PyTorch версия: {torch.__version__}")
print(f"CUDA доступна: {torch.cuda.is_available()}")

# Если CUDA доступна, это ускорит обучение
if torch.cuda.is_available():
    print(f"CUDA устройство: {torch.cuda.get_device_name(0)}")
```

---

## 2. Подготовка данных для обучения

### Структура директорий

Модуль создает следующую структуру:

```
complex_flag_scanner/
└── neural_network/
    ├── data/                    # Данные для обучения
    │   ├── candles/            # CSV файлы со свечами
    │   │   ├── vkco_1h_20240101_120000.csv
    │   │   ├── sber_1h_20240101_130000.csv
    │   │   └── ...
    │   └── annotations.csv      # Файл с метками (создается автоматически)
    └── models/                  # Сохраненные модели
        ├── best_model.pth      # Лучшая модель
        └── last_model.pth      # Последняя модель
```

### Первичная инициализация

Директории создаются автоматически при первом использовании аннотатора:

```python
from neural_network.annotator import PatternAnnotator

# Создаст все необходимые директории
annotator = PatternAnnotator()
```

---

## 3. Разметка паттернов

### 3.1. Автоматическая разметка из результатов сканера

Самый простой способ - использовать результаты сканера:

```python
import os
from dotenv import load_dotenv
from scanners.combined_scanner import ComplexFlagScanner
from neural_network.annotator import PatternAnnotator

load_dotenv()

# Инициализация
token = os.environ.get('TINKOFF_INVEST_TOKEN')
scanner = ComplexFlagScanner(token)
annotator = PatternAnnotator()

# Сканируем акцию
ticker = 'VKCO'
class_code = 'TQBR'
timeframe = '1h'

df = scanner.get_candles_df(ticker, class_code, days_back=60, interval=scanner.bullish_scanner.get_candles_df(ticker, class_code).interval)
patterns = scanner.analyze(df, timeframe=timeframe)

# Если найден паттерн, сохраняем для обучения
if patterns:
    pattern_info = patterns[0]
    
    # Автоматическая разметка
    # Метка определяется автоматически: 1=бычий, 2=медвежий
    annotator.annotate_from_scanner(
        df=df,
        ticker=ticker,
        timeframe=timeframe,
        pattern_info=pattern_info
    )
    
    print(f"✅ Паттерн размечен: {pattern_info['pattern']}")
```

### 3.2. Ручная разметка

Если вы хотите вручную указать метку:

```python
from neural_network.annotator import PatternAnnotator
import pandas as pd

annotator = PatternAnnotator()

# Загружаем свечи
df = pd.read_csv('path/to/candles.csv')

# Сохраняем свечи и получаем имя файла
candles_file = annotator.save_candles(
    df=df,
    ticker='VKCO',
    timeframe='1h'
)

# Размечаем вручную
# label: 0 = нет паттерна, 1 = бычий, 2 = медвежий
annotator.annotate_pattern(
    candles_file=candles_file,
    label=1,  # Бычий паттерн
    ticker='VKCO',
    timeframe='1h',
    pattern_type='FLAG_0_1_2_3_4',
    notes='Хорошо сформированный паттерн'
)
```

### 3.3. Разметка ложных срабатываний

Важно помечать ложные срабатывания сканера:

```python
# Если сканер нашел паттерн, но вы видите что его нет
patterns = scanner.analyze(df, timeframe='1h')

if patterns:
    pattern_info = patterns[0]
    
    # Помечаем как ложное срабатывание
    annotator.annotate_false_positive(
        df=df,
        ticker=ticker,
        timeframe=timeframe,
        scanner_result=pattern_info
    )
    
    print("⚠️ Помечено как ложное срабатывание")
```

### 3.4. Пакетная разметка

Для разметки множества паттернов:

```python
import os
from scanners.combined_scanner import ComplexFlagScanner
from neural_network.annotator import PatternAnnotator

token = os.environ.get('TINKOFF_INVEST_TOKEN')
scanner = ComplexFlagScanner(token)
annotator = PatternAnnotator()

# Список инструментов для сканирования
tickers = ['VKCO', 'SBER', 'GAZP', 'LKOH', 'YNDX']

for ticker in tickers:
    print(f"\nСканирую {ticker}...")
    
    try:
        df = scanner.get_candles_df(ticker, 'TQBR', days_back=60)
        
        if not df.empty:
            patterns = scanner.analyze(df, timeframe='1h')
            
            if patterns:
                for pattern_info in patterns:
                    annotator.annotate_from_scanner(
                        df=df,
                        ticker=ticker,
                        timeframe='1h',
                        pattern_info=pattern_info
                    )
                    print(f"  ✅ Размечен паттерн: {pattern_info['pattern']}")
    except Exception as e:
        print(f"  ❌ Ошибка для {ticker}: {e}")

# Показываем статистику
annotator.print_statistics()
```

### 3.5. Просмотр статистики

```python
from neural_network.annotator import PatternAnnotator

annotator = PatternAnnotator()

# Вывести статистику
annotator.print_statistics()

# Или получить словарь со статистикой
stats = annotator.get_statistics()
print(f"Всего аннотаций: {stats['total']}")
print(f"По меткам: {stats['by_label']}")
print(f"По таймфреймам: {stats['by_timeframe']}")
```

---

## 4. Обучение модели

### 4.1. Первое обучение

```python
import torch
from neural_network.model import create_model
from neural_network.trainer import ModelTrainer
from neural_network.data_loader import create_data_loader

# Устройство для обучения (GPU если доступно)
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print(f"Используемое устройство: {device}")

# Создаем модель
model = create_model(num_classes=3)  # 0=нет, 1=бычий, 2=медвежий

# Загружаем данные
train_loader, val_loader = create_data_loader(
    data_dir='neural_network/data',
    batch_size=16,  # Размер батча (уменьшите если не хватает памяти)
    image_size=(224, 224),
    train_split=0.8  # 80% для обучения, 20% для валидации
)

print(f"Размер обучающей выборки: {len(train_loader.dataset)}")
if val_loader:
    print(f"Размер валидационной выборки: {len(val_loader.dataset)}")

# Создаем тренировщик
trainer = ModelTrainer(model, device=device)

# Обучаем модель
trainer.train(
    train_loader=train_loader,
    val_loader=val_loader,
    epochs=50,  # Количество эпох
    learning_rate=0.001,  # Скорость обучения
    save_dir='neural_network/models',
    save_best=True,  # Сохранять лучшую модель
    save_last=True   # Сохранять последнюю модель
)
```

### 4.2. Продолжение обучения (Resume)

Если обучение прервалось, можно продолжить:

```python
from neural_network.model import create_model
from neural_network.trainer import ModelTrainer
from neural_network.data_loader import create_data_loader

# Загружаем последнюю модель
model = create_model(
    num_classes=3,
    pretrained_path='neural_network/models/last_model.pth'
)

# Загружаем данные
train_loader, val_loader = create_data_loader('neural_network/data')

# Создаем тренировщик
trainer = ModelTrainer(model)

# Продолжаем обучение
trainer.train(
    train_loader=train_loader,
    val_loader=val_loader,
    epochs=50,
    learning_rate=0.0001,  # Можно уменьшить для продолжения
    save_dir='neural_network/models',
    resume_from='neural_network/models/last_model.pth'  # Продолжить с этого чекпоинта
)
```

### 4.3. Мониторинг обучения

После обучения проверьте историю:

```python
import json

# Загружаем историю обучения
with open('neural_network/models/training_history.json', 'r') as f:
    history = json.load(f)

# График точности
import matplotlib.pyplot as plt

plt.figure(figsize=(12, 4))

plt.subplot(1, 2, 1)
plt.plot(history['epochs'], history['train_acc'], label='Train')
if history['val_acc']:
    plt.plot(history['epochs'], history['val_acc'], label='Val')
plt.xlabel('Epoch')
plt.ylabel('Accuracy (%)')
plt.legend()
plt.title('Точность')

plt.subplot(1, 2, 2)
plt.plot(history['epochs'], history['train_loss'], label='Train')
if history['val_loss']:
    plt.plot(history['epochs'], history['val_loss'], label='Val')
plt.xlabel('Epoch')
plt.ylabel('Loss')
plt.legend()
plt.title('Потери')

plt.tight_layout()
plt.savefig('training_history.png')
plt.show()
```

---

## 5. Дообучение на новых данных

После того, как вы разметили новые паттерны, можно дообучить модель:

```python
from neural_network.model import create_model
from neural_network.trainer import ModelTrainer
from neural_network.data_loader import create_data_loader

# Загружаем предобученную модель
model = create_model(
    num_classes=3,
    pretrained_path='neural_network/models/best_model.pth'
)

# Загружаем новые данные (или все данные заново)
new_data_loader, _ = create_data_loader(
    data_dir='neural_network/data',
    batch_size=16,
    train_split=1.0  # Используем все данные для дообучения
)

# Создаем тренировщик
trainer = ModelTrainer(model)

# Дообучаем (используем меньший learning rate)
trainer.fine_tune(
    new_data_loader=new_data_loader,
    epochs=5,  # Меньше эпох для дообучения
    learning_rate=0.0001  # Меньший learning rate
)

# Сохраняем дообученную модель
trainer.save_checkpoint(
    'neural_network/models/finetuned_model.pth',
    epoch=0,
    best_val_acc=0
)
```

---

## 6. Использование для предсказаний

### 6.1. Предсказание на одном образце

```python
import torch
from neural_network.model import create_model
from neural_network.data_loader import FlagPatternDataset

# Загружаем модель
model = create_model(
    num_classes=3,
    pretrained_path='neural_network/models/best_model.pth'
)
model.eval()  # Режим оценки

# Загружаем данные
dataset = FlagPatternDataset('neural_network/data')
image, true_label = dataset[0]  # Берем первый образец

# Предсказание (добавляем batch dimension)
image_batch = image.unsqueeze(0)  # (1, 3, 224, 224)

pred_class, probabilities = model.predict(image_batch)

print(f"Истинная метка: {true_label}")
print(f"Предсказанный класс: {pred_class.item()}")
print(f"Вероятности: {probabilities[0]}")
print(f"  - Нет паттерна: {probabilities[0][0]:.2%}")
print(f"  - Бычий: {probabilities[0][1]:.2%}")
print(f"  - Медвежий: {probabilities[0][2]:.2%}")
```

### 6.2. Предсказание на батче

```python
from neural_network.model import create_model
from neural_network.trainer import ModelTrainer
from neural_network.data_loader import create_data_loader

# Загружаем модель
model = create_model(pretrained_path='neural_network/models/best_model.pth')

# Загружаем данные
test_loader, _ = create_data_loader(
    data_dir='neural_network/data',
    batch_size=32,
    shuffle=False
)

# Предсказания
trainer = ModelTrainer(model)
predictions, probabilities = trainer.predict_batch(test_loader)

print(f"Предсказано образцов: {len(predictions)}")
print(f"Распределение классов: {np.bincount(predictions)}")
```

### 6.3. Предсказание на новых свечах

```python
import pandas as pd
import torch
from neural_network.model import create_model
from neural_network.data_loader import FlagPatternDataset

# Загружаем модель
model = create_model(pretrained_path='neural_network/models/best_model.pth')
model.eval()

# Загружаем свечи (например, из сканера)
df = scanner.get_candles_df('VKCO', 'TQBR', days_back=60)

# Сохраняем временно
temp_file = 'neural_network/data/temp_candles.csv'
df.to_csv(temp_file, index=False)

# Создаем временный датасет
temp_dataset = FlagPatternDataset('neural_network/data', image_size=(224, 224))
# Примечание: нужно будет добавить запись в annotations.csv или использовать другой способ

# Преобразуем в изображение вручную
from neural_network.data_loader import FlagPatternDataset
image = temp_dataset._candles_to_image(df)

# Предсказание
image_batch = image.unsqueeze(0)
pred_class, probabilities = model.predict(image_batch)

class_names = ['Нет паттерна', 'Бычий', 'Медвежий']
print(f"Предсказание: {class_names[pred_class.item()]}")
print(f"Уверенность: {probabilities[0][pred_class.item()]:.2%}")
```

---

## 7. Интеграция со сканером

### 7.1. Валидация результатов сканера

Можно использовать нейросеть для проверки результатов сканера:

```python
import os
from dotenv import load_dotenv
from scanners.combined_scanner import ComplexFlagScanner
from neural_network.model import create_model
from neural_network.data_loader import FlagPatternDataset
import torch

load_dotenv()

token = os.environ.get('TINKOFF_INVEST_TOKEN')
scanner = ComplexFlagScanner(token)

# Загружаем модель
model = create_model(pretrained_path='neural_network/models/best_model.pth')
model.eval()

# Сканируем акцию
ticker = 'VKCO'
class_code = 'TQBR'
df = scanner.get_candles_df(ticker, class_code, days_back=60)

# Сканер находит паттерн
patterns = scanner.analyze(df, timeframe='1h')

if patterns:
    pattern_info = patterns[0]
    scanner_label = 1 if 'BEARISH' not in pattern_info['pattern'] else 2
    
    # Проверяем нейросетью
    dataset = FlagPatternDataset('neural_network/data')
    image = dataset._candles_to_image(df)
    image_batch = image.unsqueeze(0)
    
    pred_class, probabilities = model.predict(image_batch)
    nn_label = pred_class.item()
    
    print(f"Сканер: {'Бычий' if scanner_label == 1 else 'Медвежий'}")
    print(f"Нейросеть: {['Нет', 'Бычий', 'Медвежий'][nn_label]}")
    print(f"Уверенность нейросети: {probabilities[0][nn_label]:.2%}")
    
    # Если согласны
    if scanner_label == nn_label:
        print("✅ Оба метода согласны - паттерн подтвержден")
    else:
        print("⚠️ Методы не согласны - требуется проверка")
```

### 7.2. Комбинированный подход

Можно комбинировать правила и ML:

```python
def analyze_with_ml_validation(df, scanner, model, threshold=0.7):
    """
    Анализ с валидацией через ML
    threshold - минимальная уверенность нейросети
    """
    # Сканер находит паттерн
    patterns = scanner.analyze(df, timeframe='1h')
    
    if not patterns:
        return []
    
    # Проверяем нейросетью
    dataset = FlagPatternDataset('neural_network/data')
    image = dataset._candles_to_image(df)
    image_batch = image.unsqueeze(0)
    
    model.eval()
    pred_class, probabilities = model.predict(image_batch)
    
    max_prob = probabilities[0].max().item()
    predicted_label = pred_class.item()
    
    # Если уверенность низкая, отбрасываем
    if max_prob < threshold:
        return []
    
    # Если нейросеть говорит "нет паттерна", отбрасываем
    if predicted_label == 0:
        return []
    
    # Проверяем согласованность
    pattern_info = patterns[0]
    scanner_label = 1 if 'BEARISH' not in pattern_info['pattern'] else 2
    
    if scanner_label == predicted_label:
        # Добавляем уверенность ML в результат
        pattern_info['ml_confidence'] = max_prob
        pattern_info['ml_validated'] = True
        return [pattern_info]
    
    return []

# Использование
result = analyze_with_ml_validation(df, scanner, model, threshold=0.7)
if result:
    print(f"✅ Паттерн подтвержден ML (уверенность: {result[0]['ml_confidence']:.2%})")
```

---

## 8. Часто задаваемые вопросы

### Q: Сколько данных нужно для обучения?

**A:** Минимум 100-200 образцов каждого класса (нет паттерна, бычий, медвежий). Чем больше, тем лучше. Рекомендуется:
- Нет паттерна: 300-500 образцов
- Бычий: 200-300 образцов
- Медвежий: 200-300 образцов

### Q: Как улучшить качество модели?

**A:**
1. **Больше данных** - самый важный фактор
2. **Балансировка классов** - примерно равное количество каждого класса
3. **Качественная разметка** - правильно помечайте паттерны
4. **Больше эпох** - обучайте дольше (но следите за переобучением)
5. **Аугментация данных** - можно добавить трансформации (поворот, масштабирование)

### Q: Что делать если модель переобучается?

**A:** Признаки переобучения:
- Train accuracy растет, Val accuracy падает
- Val loss растет после определенной эпохи

Решения:
- Увеличить dropout (уже 0.5)
- Добавить больше данных
- Уменьшить размер модели
- Использовать early stopping
- Увеличить weight_decay

### Q: Как ускорить обучение?

**A:**
1. Используйте GPU (CUDA)
2. Увеличьте batch_size (если есть память)
3. Уменьшите размер изображения (например, 128x128 вместо 224x224)
4. Используйте mixed precision training (FP16)

### Q: Как часто нужно дообучать модель?

**A:** Рекомендуется:
- При накоплении 50-100 новых размеченных образцов
- Раз в неделю/месяц (в зависимости от активности)
- После значительных изменений в рынке

### Q: Можно ли использовать модель без GPU?

**A:** Да, но обучение будет медленнее. Для предсказаний CPU достаточно.

---

## 📊 Пример полного workflow

```python
import os
from dotenv import load_dotenv
from scanners.combined_scanner import ComplexFlagScanner
from neural_network.annotator import PatternAnnotator
from neural_network.model import create_model
from neural_network.trainer import ModelTrainer
from neural_network.data_loader import create_data_loader
import torch

load_dotenv()

# 1. ИНИЦИАЛИЗАЦИЯ
token = os.environ.get('TINKOFF_INVEST_TOKEN')
scanner = ComplexFlagScanner(token)
annotator = PatternAnnotator()

# 2. РАЗМЕТКА ДАННЫХ (выполнить много раз для накопления данных)
tickers = ['VKCO', 'SBER', 'GAZP', 'LKOH', 'YNDX']
for ticker in tickers:
    df = scanner.get_candles_df(ticker, 'TQBR', days_back=60)
    patterns = scanner.analyze(df, timeframe='1h')
    if patterns:
        annotator.annotate_from_scanner(df, ticker, '1h', patterns[0])

annotator.print_statistics()

# 3. ОБУЧЕНИЕ (когда накопится достаточно данных)
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
model = create_model(num_classes=3)
train_loader, val_loader = create_data_loader('neural_network/data', batch_size=16)
trainer = ModelTrainer(model, device=device)
trainer.train(train_loader, val_loader, epochs=50, save_dir='neural_network/models')

# 4. ИСПОЛЬЗОВАНИЕ ДЛЯ ПРЕДСКАЗАНИЙ
model = create_model(pretrained_path='neural_network/models/best_model.pth')
model.eval()

df_new = scanner.get_candles_df('NEW_TICKER', 'TQBR', days_back=60)
# ... преобразование в изображение и предсказание ...

# 5. ДООБУЧЕНИЕ (после накопления новых данных)
model = create_model(pretrained_path='neural_network/models/best_model.pth')
new_loader, _ = create_data_loader('neural_network/data')
trainer = ModelTrainer(model)
trainer.fine_tune(new_loader, epochs=5, learning_rate=0.0001)
```

---

## 🎯 Рекомендации

1. **Начните с малого** - разметьте 50-100 образцов и попробуйте обучить
2. **Итеративный процесс** - регулярно добавляйте данные и дообучайте
3. **Контролируйте качество** - проверяйте результаты на реальных данных
4. **Комбинируйте подходы** - используйте и правила, и ML вместе
5. **Ведите статистику** - отслеживайте, какие паттерны ML находит лучше/хуже

---

**Удачи в обучении! 🚀**

