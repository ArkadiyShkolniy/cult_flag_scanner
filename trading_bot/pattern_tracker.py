"""
Трекер истории паттернов для отслеживания перерисовки
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional


class PatternTracker:
    """
    Класс для отслеживания истории паттернов и определения перерисовки
    """
    
    def __init__(self, history_file: Optional[str] = None):
        """
        Args:
            history_file: Путь к файлу с историей паттернов
        """
        if history_file is None:
            base_dir = Path(__file__).parent
            history_file = base_dir / "pattern_history.json"
        
        self.history_file = Path(history_file)
        self.pattern_history: Dict[str, List[dict]] = {}
        
        # Загружаем существующую историю
        self._load_history()
    
    def _load_history(self):
        """Загружает историю из файла"""
        if self.history_file.exists():
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    self.pattern_history = json.load(f)
            except Exception as e:
                print(f"⚠️ Ошибка загрузки истории паттернов: {e}")
                self.pattern_history = {}
        else:
            self.pattern_history = {}
    
    def _save_history(self):
        """Сохраняет историю в файл"""
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(self.pattern_history, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"⚠️ Ошибка сохранения истории паттернов: {e}")
    
    def add_pattern(self, ticker: str, timeframe: str, pattern: dict):
        """
        Добавляет паттерн в историю
        
        Args:
            ticker: Тикер инструмента
            timeframe: Таймфрейм (например, '1h', '1d')
            pattern: Словарь с данными паттерна
        """
        key = f"{ticker}_{timeframe}"
        
        if key not in self.pattern_history:
            self.pattern_history[key] = []
        
        # Создаем запись о паттерне
        t4 = pattern.get('t4', {})
        t4_time = t4.get('time', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        
        # Генерируем подпись паттерна для определения перерисовки
        signature = self._generate_signature(pattern)
        
        # Проверяем, является ли это перерисовкой
        is_repaint = self._check_repaint(key, signature, t4_time)
        
        record = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            't4_time': t4_time,
            'pattern': pattern,
            'signature': signature,
            'is_repaint': is_repaint
        }
        
        self.pattern_history[key].append(record)
        
        # Ограничиваем размер истории (храним последние 100 записей)
        if len(self.pattern_history[key]) > 100:
            self.pattern_history[key] = self.pattern_history[key][-100:]
        
        # Сохраняем историю
        self._save_history()
    
    def _generate_signature(self, pattern: dict) -> str:
        """
        Генерирует подпись паттерна для сравнения
        
        Args:
            pattern: Словарь с данными паттерна
        
        Returns:
            str: Подпись паттерна
        """
        # Используем индексы точек T0-T4 для создания подписи
        points = []
        for point_name in ['t0', 't1', 't2', 't3', 't4']:
            point = pattern.get(point_name, {})
            idx = point.get('idx', 0)
            points.append(str(idx))
        
        return '_'.join(points)
    
    def _check_repaint(self, key: str, signature: str, t4_time: str) -> bool:
        """
        Проверяет, является ли паттерн перерисовкой
        
        Args:
            key: Ключ истории (ticker_timeframe)
            signature: Подпись текущего паттерна
            t4_time: Время точки T4
        
        Returns:
            bool: True если это перерисовка
        """
        if key not in self.pattern_history or len(self.pattern_history[key]) == 0:
            return False
        
        # Проверяем последние записи с тем же временем T4
        history = self.pattern_history[key]
        for record in reversed(history[-10:]):  # Проверяем последние 10 записей
            if record.get('t4_time') == t4_time:
                # Если подпись отличается, значит паттерн перерисовался
                if record.get('signature') != signature:
                    return True
        
        return False
    
    def get_pattern_history(self, ticker: str, timeframe: str, limit: int = 20) -> List[dict]:
        """
        Получает историю паттернов для указанного инструмента и таймфрейма
        
        Args:
            ticker: Тикер инструмента
            timeframe: Таймфрейм
            limit: Максимальное количество записей
        
        Returns:
            list: Список записей истории
        """
        key = f"{ticker}_{timeframe}"
        
        if key not in self.pattern_history:
            return []
        
        history = self.pattern_history[key]
        
        # Возвращаем последние limit записей
        return history[-limit:] if len(history) > limit else history
    
    def clear_history(self, ticker: Optional[str] = None, timeframe: Optional[str] = None):
        """
        Очищает историю паттернов
        
        Args:
            ticker: Тикер (если None, очищает всю историю)
            timeframe: Таймфрейм (если None, очищает все таймфреймы для тикера)
        """
        if ticker is None:
            self.pattern_history = {}
        elif timeframe is None:
            # Удаляем все таймфреймы для тикера
            keys_to_remove = [k for k in self.pattern_history.keys() if k.startswith(f"{ticker}_")]
            for key in keys_to_remove:
                del self.pattern_history[key]
        else:
            key = f"{ticker}_{timeframe}"
            if key in self.pattern_history:
                del self.pattern_history[key]
        
        self._save_history()
