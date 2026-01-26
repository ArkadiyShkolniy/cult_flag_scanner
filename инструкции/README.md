# Модуль нейронной сети для распознавания паттернов "Флаг"

Этот модуль содержит нейронную сеть (CNN) для распознавания паттернов "Флаг" на графиках свечей.

## Структура модуля

```
neural_network/
├── __init__.py          # Экспорты модуля
├── model.py             # Архитектура CNN
├── trainer.py           # Обучение и дообучение
├── data_loader.py       # Загрузка и подготовка данных
├── annotator.py         # Разметка паттернов
├── train.py             # Скрипт для обучения (TODO)
└── predict.py           # Скрипт для предсказаний (TODO)
```

## Компоненты

### 1. FlagPatternCNN (`model.py`)
Сверточная нейронная сеть для классификации паттернов:
- Вход: изображение графика свечей (224x224x3)
- Выход: вероятность класса (0=нет паттерна, 1=бычий, 2=медвежий)

### 2. PatternAnnotator (`annotator.py`)
Инструмент для разметки данных:
- Сохранение свечей в CSV
- Добавление меток (label)
- Статистика по аннотациям

### 3. DataLoader (`data_loader.py`)
Подготовка данных для обучения:
- Преобразование свечей в изображения
- Создание датасета
- Train/Val разделение

### 4. ModelTrainer (`trainer.py`)
Обучение модели:
- Полное обучение
- Дообучение на новых данных
- Сохранение чекпоинтов
- История обучения

## Использование

### 1. Разметка данных

```python
from neural_network.annotator import PatternAnnotator
import pandas as pd

annotator = PatternAnnotator()

# Сохраняем свечи из сканера
df = scanner.get_candles_df('VKCO', 'TQBR')
pattern_info = scanner.analyze(df)[0]  # Результат сканера

# Автоматическая аннотация
annotator.annotate_from_scanner(df, 'VKCO', '1h', pattern_info)

# Или ручная разметка
annotator.annotate_pattern(
    candles_file='candles/vkco_1h_20240101.csv',
    label=1,  # 1=бычий
    ticker='VKCO',
    timeframe='1h'
)

# Статистика
annotator.print_statistics()
```

### 2. Обучение модели

```python
from neural_network.model import create_model
from neural_network.trainer import ModelTrainer
from neural_network.data_loader import create_data_loader

# Создаем модель
model = create_model(num_classes=3)

# Загружаем данные
train_loader, val_loader = create_data_loader('neural_network/data')

# Создаем тренировщик
trainer = ModelTrainer(model)

# Обучаем
trainer.train(
    train_loader=train_loader,
    val_loader=val_loader,
    epochs=50,
    learning_rate=0.001,
    save_dir='neural_network/models'
)
```

### 3. Дообучение на новых данных

```python
# Загружаем предобученную модель
model = create_model(
    num_classes=3,
    pretrained_path='neural_network/models/best_model.pth'
)

trainer = ModelTrainer(model)

# Загружаем новые размеченные данные
new_data_loader, _ = create_data_loader('neural_network/new_data')

# Дообучаем
trainer.fine_tune(new_data_loader, epochs=5, learning_rate=0.0001)

# Сохраняем
trainer.save_checkpoint('neural_network/models/finetuned_model.pth', epoch=0, best_val_acc=0)
```

### 4. Использование для предсказаний

```python
from neural_network.model import create_model
from neural_network.data_loader import FlagPatternDataset

# Загружаем модель
model = create_model(pretrained_path='neural_network/models/best_model.pth')
model.eval()

# Загружаем данные
dataset = FlagPatternDataset('neural_network/data')
image, _ = dataset[0]

# Предсказание
pred_class, probabilities = model.predict(image.unsqueeze(0))
print(f"Предсказанный класс: {pred_class.item()}")
print(f"Вероятности: {probabilities}")
```

## Интеграция со сканером

Модуль может использоваться для:
1. **Валидации результатов сканера** - проверка найденных паттернов нейросетью
2. **Фильтрации сигналов** - отсеивание ложных срабатываний
3. **Дополнительной уверенности** - комбинирование правил и ML

## Требования

```bash
pip install torch torchvision pandas numpy matplotlib pillow tqdm
```

## Планы развития

- [ ] Скрипт для обучения (`train.py`)
- [ ] Скрипт для предсказаний (`predict.py`)
- [ ] Интеграция с дашбордом
- [ ] Автоматическая разметка из результатов сканера
- [ ] Аугментация данных
- [ ] Transfer learning с предобученными моделями

