import pandas as pd
import numpy as np
import joblib
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
# import matplotlib.pyplot as plt
# import seaborn as sns

# Настройки
DATASET_FILE = Path("neural_network/data/ml_trading_dataset.csv")
MODEL_FILE = Path("neural_network/models/trading_model_rf.pkl")
MODEL_FILE.parent.mkdir(parents=True, exist_ok=True)

def train_model():
    print("🚀 Обучение модели фильтрации сделок...")
    
    if not DATASET_FILE.exists():
        print(f"❌ Файл датасета не найден: {DATASET_FILE}")
        return

    # 1. Загрузка данных
    df = pd.read_csv(DATASET_FILE)
    print(f"   Загружено записей: {len(df)}")
    
    # 2. Подготовка признаков (Features)
    # Нам нужно превратить сырые данные в числа, понятные модели
    
    # Целевая переменная: 1 = WIN, 0 = LOSS/HOLD
    # HOLD считаем за LOSS для строгости (не дошли до цели)
    df['target'] = (df['outcome'] == 'WIN').astype(int)
    
    # Фичи
    # correction_ratio: Отношение коррекции к древку (0.3-0.5 обычно хорошо)
    # slope_channel: Наклон канала
    
    # Добавим производные фичи, если их нет
    # Например, Risk/Reward ratio (потенциальный)
    df['risk_reward_ratio'] = abs(df['take_profit'] - df['entry_price']) / abs(df['entry_price'] - df['stop_loss'])
    
    # Выбираем колонки для обучения
    feature_cols = [
        'correction_ratio', 
        'slope_channel', 
        'risk_reward_ratio'
    ]
    
    # Проверяем на NaN и чистим
    df_clean = df.dropna(subset=feature_cols + ['target'])
    
    X = df_clean[feature_cols]
    y = df_clean['target']
    
    print(f"   Данных для обучения после очистки: {len(X)}")
    print(f"   Базовый Win Rate: {y.mean()*100:.1f}%")
    
    # 3. Разделение на Train/Test
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    
    # 4. Обучение модели (Random Forest)
    # Используем class_weight='balanced', чтобы учесть дисбаланс классов (если Win Rate низкий)
    clf = RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42, class_weight='balanced')
    clf.fit(X_train, y_train)
    
    # 5. Оценка качества
    y_pred = clf.predict(X_test)
    
    print("\n📊 Результаты на тестовой выборке:")
    print(classification_report(y_test, y_pred))
    
    acc = accuracy_score(y_test, y_pred)
    print(f"   Accuracy: {acc:.2f}")
    
    # Проверка на "боевых" примерах
    # Допустим, модель предсказала 1 (WIN). Какова реальная точность таких прогнозов?
    # Это Precision для класса 1.
    cm = confusion_matrix(y_test, y_pred)
    tn, fp, fn, tp = cm.ravel()
    precision_win = tp / (tp + fp) if (tp + fp) > 0 else 0
    
    print(f"\n🎯 Точность прогноза WIN (Precision): {precision_win*100:.1f}%")
    print("   (Это вероятность успеха сделки, если модель сказала 'ВХОДИ')")
    
    # 6. Важность признаков
    importances = clf.feature_importances_
    feature_imp = pd.DataFrame(sorted(zip(importances, feature_cols)), columns=['Value','Feature'])
    
    print("\n🔑 Важность признаков:")
    print(feature_imp.sort_values(by="Value", ascending=False).to_string(index=False))
    
    # 7. Сохранение
    joblib.dump(clf, MODEL_FILE)
    print(f"\n✅ Модель сохранена в {MODEL_FILE}")
    
    # Пример использования
    print("\n💡 Пример работы фильтра:")
    # Берем случайный пример из теста
    sample = X_test.iloc[0:1]
    prediction = clf.predict(sample)[0]
    proba = clf.predict_proba(sample)[0][1]
    
    print(f"   Входные данные: {sample.to_dict(orient='records')[0]}")
    print(f"   Предсказание: {'WIN' if prediction==1 else 'SKIP'} (Вероятность успеха: {proba:.2f})")

if __name__ == "__main__":
    train_model()
