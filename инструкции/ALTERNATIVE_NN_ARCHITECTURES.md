# Альтернативные архитектуры нейронных сетей без преобразования в изображение

## Текущий подход: CNN на изображениях

**Проблема:** Текущая реализация преобразует свечи в изображение 224x224, что:
- Теряет точность данных (дискретизация)
- Требует дополнительных вычислений (matplotlib)
- Увеличивает размер модели
- Может терять важные детали при масштабировании

## Альтернативные подходы

---

## 1. LSTM/GRU (Long Short-Term Memory / Gated Recurrent Unit)

### Описание
Рекуррентные нейронные сети для работы с временными рядами напрямую.

### Архитектура
```python
class FlagPatternLSTM(nn.Module):
    def __init__(self, input_size=5, hidden_size=128, num_layers=2, num_classes=3, num_keypoints=5):
        super().__init__()
        # Вход: [batch, sequence_length, features]
        # features = [open, high, low, close, volume] или больше
        
        self.lstm = nn.LSTM(
            input_size=input_size,      # 5 признаков на свечу
            hidden_size=hidden_size,     # Размер скрытого состояния
            num_layers=num_layers,       # Количество слоев
            batch_first=True,            # Первый размер = batch
            bidirectional=True           # Двунаправленный LSTM
        )
        
        # Выход LSTM: [batch, sequence_length, hidden_size * 2] (bidirectional)
        self.fc_class = nn.Linear(hidden_size * 2, num_classes)
        self.fc_keypoints = nn.Linear(hidden_size * 2, num_keypoints * 2)
    
    def forward(self, x):
        # x: [batch, sequence_length, features]
        lstm_out, (h_n, c_n) = self.lstm(x)
        
        # Используем последний выход (или можно использовать attention)
        last_output = lstm_out[:, -1, :]  # [batch, hidden_size * 2]
        
        class_logits = self.fc_class(last_output)
        keypoints = self.fc_keypoint(last_output).view(-1, num_keypoints, 2)
        
        return class_logits, keypoints
```

### Преимущества
✅ **Работает напрямую с данными:** Нет потери информации при преобразовании  
✅ **Учитывает последовательность:** LSTM помнит контекст  
✅ **Эффективность:** Быстрее чем CNN на изображениях  
✅ **Меньше параметров:** Обычно компактнее чем CNN  

### Недостатки
❌ **Последовательная обработка:** Медленнее чем CNN (но можно распараллелить)  
❌ **Длинные последовательности:** Проблемы с градиентами на длинных последовательностях  
❌ **Меньше пространственной информации:** Может хуже видеть геометрию паттерна  

### Когда использовать
- Когда важна временная последовательность
- Когда нужно работать с сырыми данными
- Когда важна скорость обучения

---

## 2. Transformer (Attention-based)

### Описание
Архитектура на основе механизма внимания (attention), как в BERT/GPT.

### Архитектура
```python
class FlagPatternTransformer(nn.Module):
    def __init__(self, d_model=128, nhead=8, num_layers=4, num_classes=3, num_keypoints=5):
        super().__init__()
        
        # Входное проецирование: [batch, seq_len, features] -> [batch, seq_len, d_model]
        self.input_projection = nn.Linear(5, d_model)  # 5 признаков на свечу
        
        # Позиционное кодирование (опционально, можно использовать learnable)
        self.pos_encoder = PositionalEncoding(d_model)
        
        # Transformer encoder
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=nhead,
            num_layers=num_layers,
            dim_feedforward=512,
            dropout=0.1
        )
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
        
        # Выходные головы
        self.fc_class = nn.Linear(d_model, num_classes)
        self.fc_keypoints = nn.Linear(d_model, num_keypoints * 2)
    
    def forward(self, x):
        # x: [batch, sequence_length, features]
        x = self.input_projection(x)  # [batch, seq_len, d_model]
        x = self.pos_encoder(x)
        x = x.transpose(0, 1)  # Transformer ожидает [seq_len, batch, d_model]
        
        encoded = self.transformer(x)  # [seq_len, batch, d_model]
        
        # Используем последний токен (или можно использовать pooling)
        last_token = encoded[-1]  # [batch, d_model]
        
        class_logits = self.fc_class(last_token)
        keypoints = self.fc_keypoints(last_token).view(-1, num_keypoints, 2)
        
        return class_logits, keypoints
```

### Преимущества
✅ **Attention механизм:** Может фокусироваться на важных частях последовательности  
✅ **Параллелизация:** Полностью параллельная обработка  
✅ **Длинные последовательности:** Хорошо работает с длинными последовательностями  
✅ **Современный подход:** State-of-the-art для многих задач  

### Недостатки
❌ **Больше параметров:** Обычно больше чем LSTM  
❌ **Сложность:** Более сложная архитектура  
❌ **Требует больше данных:** Может переобучиться на малых данных  

### Когда использовать
- Когда нужна максимальная точность
- Когда есть достаточно данных для обучения
- Когда важна параллелизация

---

## 3. 1D CNN (Temporal Convolutional Networks)

### Описание
Сверточные сети для временных рядов, работают напрямую с последовательностями.

### Архитектура
```python
class FlagPattern1DCNN(nn.Module):
    def __init__(self, num_classes=3, num_keypoints=5, input_features=5):
        super().__init__()
        
        # 1D свертки по временной оси
        # Вход: [batch, features, sequence_length]
        
        self.conv1 = nn.Conv1d(input_features, 64, kernel_size=3, padding=1)
        self.bn1 = nn.BatchNorm1d(64)
        self.pool1 = nn.MaxPool1d(2)
        
        self.conv2 = nn.Conv1d(64, 128, kernel_size=3, padding=1)
        self.bn2 = nn.BatchNorm1d(128)
        self.pool2 = nn.MaxPool1d(2)
        
        self.conv3 = nn.Conv1d(128, 256, kernel_size=3, padding=1)
        self.bn3 = nn.BatchNorm1d(256)
        self.pool3 = nn.MaxPool1d(2)
        
        # Глобальный pooling
        self.global_pool = nn.AdaptiveAvgPool1d(1)
        
        # Выходные головы
        self.fc_class = nn.Linear(256, num_classes)
        self.fc_keypoints = nn.Linear(256, num_keypoints * 2)
    
    def forward(self, x):
        # x: [batch, sequence_length, features]
        x = x.transpose(1, 2)  # [batch, features, sequence_length]
        
        x = F.relu(self.bn1(self.conv1(x)))
        x = self.pool1(x)
        
        x = F.relu(self.bn2(self.conv2(x)))
        x = self.pool2(x)
        
        x = F.relu(self.bn3(self.conv3(x)))
        x = self.pool3(x)
        
        # Глобальный pooling
        x = self.global_pool(x).squeeze(-1)  # [batch, 256]
        
        class_logits = self.fc_class(x)
        keypoints = self.fc_keypoints(x).view(-1, num_keypoints, 2)
        
        return class_logits, keypoints
```

### Преимущества
✅ **Быстрая обработка:** Параллельная обработка всей последовательности  
✅ **Локальные паттерны:** Хорошо улавливает локальные закономерности  
✅ **Эффективность:** Обычно быстрее чем LSTM  
✅ **Простота:** Проще чем Transformer  

### Недостатки
❌ **Ограниченный контекст:** Зависит от размера ядра свертки  
❌ **Меньше глобального контекста:** Может хуже видеть длинные зависимости  

### Когда использовать
- Когда важны локальные паттерны
- Когда нужна скорость
- Когда последовательности не очень длинные

---

## 4. MLP с извлечением признаков (Feature Engineering)

### Описание
Многослойный перцептрон на предварительно извлеченных признаках.

### Архитектура
```python
class FlagPatternMLP(nn.Module):
    def __init__(self, num_classes=3, num_keypoints=5):
        super().__init__()
        
        # Извлеченные признаки (можно добавить больше):
        # - Цены: OHLC нормализованные
        # - Технические индикаторы: RSI, MACD, MA
        # - Геометрические: экстремумы, тренды, углы
        # - Статистические: волатильность, корреляции
        
        input_size = 50  # Количество признаков
        
        self.fc1 = nn.Linear(input_size, 256)
        self.dropout1 = nn.Dropout(0.3)
        self.fc2 = nn.Linear(256, 128)
        self.dropout2 = nn.Dropout(0.3)
        self.fc3 = nn.Linear(128, 64)
        
        # Выходные головы
        self.fc_class = nn.Linear(64, num_classes)
        self.fc_keypoints = nn.Linear(64, num_keypoints * 2)
    
    def forward(self, x):
        # x: [batch, features]
        x = F.relu(self.fc1(x))
        x = self.dropout1(x)
        x = F.relu(self.fc2(x))
        x = self.dropout2(x)
        x = F.relu(self.fc3(x))
        
        class_logits = self.fc_class(x)
        keypoints = self.fc_keypoints(x).view(-1, num_keypoints, 2)
        
        return class_logits, keypoints
```

### Извлечение признаков
```python
def extract_features(df_window):
    """Извлекает признаки из окна свечей"""
    features = []
    
    # 1. Нормализованные цены
    price_min = df_window['low'].min()
    price_max = df_window['high'].max()
    price_range = price_max - price_min
    
    for col in ['open', 'high', 'low', 'close']:
        features.append((df_window[col] - price_min) / price_range)
    
    # 2. Технические индикаторы
    features.append(calculate_rsi(df_window['close']))
    features.append(calculate_macd(df_window['close']))
    features.append(calculate_ma(df_window['close'], 20))
    
    # 3. Геометрические признаки
    features.append(find_extrema(df_window))
    features.append(calculate_trend_angles(df_window))
    
    # 4. Статистические
    features.append(df_window['close'].std())
    features.append(df_window['volume'].mean())
    
    return np.concatenate(features)
```

### Преимущества
✅ **Интерпретируемость:** Можно понять, какие признаки важны  
✅ **Быстрота:** Очень быстрая обработка  
✅ **Контроль:** Полный контроль над признаками  
✅ **Меньше данных:** Может работать с меньшим количеством данных  

### Недостатки
❌ **Ручная работа:** Нужно вручную извлекать признаки  
❌ **Ограниченность:** Зависит от качества признаков  
❌ **Может пропустить:** Может не уловить сложные закономерности  

### Когда использовать
- Когда есть экспертные знания о признаках
- Когда нужна интерпретируемость
- Когда данных мало

---

## 5. Гибридные архитектуры

### Комбинация подходов
```python
class FlagPatternHybrid(nn.Module):
    def __init__(self):
        super().__init__()
        
        # 1D CNN для локальных паттернов
        self.cnn = TemporalCNN()
        
        # LSTM для глобального контекста
        self.lstm = LSTM()
        
        # MLP для извлеченных признаков
        self.mlp = FeatureMLP()
        
        # Объединение
        self.fusion = nn.Linear(256 + 128 + 64, 256)
        self.fc_class = nn.Linear(256, 3)
        self.fc_keypoints = nn.Linear(256, 10)
    
    def forward(self, x_raw, x_features):
        cnn_out = self.cnn(x_raw)
        lstm_out = self.lstm(x_raw)
        mlp_out = self.mlp(x_features)
        
        # Объединение
        combined = torch.cat([cnn_out, lstm_out, mlp_out], dim=1)
        fused = self.fusion(combined)
        
        class_logits = self.fc_class(fused)
        keypoints = self.fc_keypoints(fused).view(-1, 5, 2)
        
        return class_logits, keypoints
```

---

## Сравнение подходов

| Метод | Скорость | Точность | Параметры | Интерпретируемость | Сложность |
|-------|----------|----------|-----------|-------------------|-----------|
| CNN (текущий) | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ |
| LSTM | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |
| Transformer | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ |
| 1D CNN | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ |
| MLP + Features | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ |
| Гибридный | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |

---

## Рекомендации

### Для замены текущего подхода:

**1. 1D CNN** - лучший баланс:
- Работает напрямую с данными
- Быстрее чем текущий подход
- Хорошо улавливает паттерны
- Проще реализовать

**2. LSTM** - если важна последовательность:
- Хорошо для временных рядов
- Учитывает контекст
- Может быть медленнее

**3. Transformer** - для максимальной точности:
- State-of-the-art подход
- Требует больше данных
- Сложнее реализовать

### Пример реализации 1D CNN:

```python
# data_loader_1d.py
class FlagPattern1DDataset(Dataset):
    def __getitem__(self, idx):
        # Загружаем свечи
        df = pd.read_csv(file_path)
        
        # Нормализуем данные
        df_normalized = normalize_candles(df)
        
        # Преобразуем в тензор: [sequence_length, features]
        # features = [open, high, low, close, volume]
        data = torch.tensor(df_normalized[['open', 'high', 'low', 'close', 'volume']].values, 
                           dtype=torch.float32)
        
        # Загружаем ключевые точки
        keypoints = load_keypoints(row, df)
        
        return data, label, keypoints
```

---

## Миграция с текущего подхода

### Шаги:

1. **Создать новый data loader:**
   - Убрать преобразование в изображение
   - Работать напрямую с числовыми данными

2. **Создать новую модель:**
   - Выбрать архитектуру (1D CNN, LSTM, Transformer)
   - Адаптировать под задачу

3. **Переобучить модель:**
   - Использовать существующие данные
   - Возможно потребуется переразметка

4. **Обновить predict:**
   - Убрать преобразование в изображение
   - Работать напрямую с DataFrame

### Преимущества миграции:

✅ **Скорость:** Быстрее обработка (нет matplotlib)  
✅ **Точность:** Нет потери информации при преобразовании  
✅ **Эффективность:** Меньше памяти, меньше вычислений  
✅ **Гибкость:** Легче добавлять новые признаки  

---

## Заключение

**Да, можно использовать нейросеть без преобразования в изображение!**

Рекомендуемые альтернативы:
1. **1D CNN** - для быстрого старта
2. **LSTM** - для учета последовательности
3. **Transformer** - для максимальной точности

Все эти подходы работают напрямую с числовыми данными свечей и могут быть более эффективными чем текущий подход с изображениями.
