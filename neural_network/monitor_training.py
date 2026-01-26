#!/usr/bin/env python3
"""
Скрипт для мониторинга процесса обучения и уведомления о завершении
"""
import time
import subprocess
import os
import sys
from pathlib import Path
from datetime import datetime

def check_process(pid):
    """Проверяет, работает ли процесс"""
    try:
        result = subprocess.run(['ps', '-p', str(pid)], 
                              capture_output=True, text=True)
        return result.returncode == 0
    except:
        return False

def get_model_info():
    """Получает информацию о модели"""
    model_path = Path('neural_network/models/keypoint_model_best.pth')
    if model_path.exists():
        stat = model_path.stat()
        size_mb = stat.st_size / (1024 * 1024)
        mtime = datetime.fromtimestamp(stat.st_mtime)
        return {
            'exists': True,
            'size_mb': size_mb,
            'mtime': mtime,
            'path': str(model_path)
        }
    return {'exists': False}

def main():
    print("=" * 60)
    print("🔍 МОНИТОРИНГ ОБУЧЕНИЯ")
    print("=" * 60)
    print()
    
    # Ищем PID процесса обучения
    result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
    processes = [p for p in result.stdout.split('\n') 
                 if 'train_keypoints.py' in p and 'grep' not in p and 'monitor' not in p]
    
    if not processes:
        print("⚠️  Процесс обучения не найден!")
        print("   Возможно, обучение уже завершилось или еще не началось.")
        return
    
    parts = processes[0].split()
    pid = parts[1]
    start_time_str = ' '.join(parts[8:10]) if len(parts) > 9 else 'неизвестно'
    
    print(f"✅ Процесс найден: PID {pid}")
    print(f"📅 Время запуска: {start_time_str}")
    print()
    print("⏳ Мониторинг процесса обучения...")
    print("   (Нажмите Ctrl+C для остановки мониторинга)")
    print()
    
    last_model_update = None
    check_interval = 30  # Проверка каждые 30 секунд
    no_update_timeout = 600  # 10 минут без обновлений = завершение
    
    try:
        while True:
            if not check_process(pid):
                print()
                print("=" * 60)
                print("✅ ОБУЧЕНИЕ ЗАВЕРШЕНО!")
                print("=" * 60)
                print()
                
                model_info = get_model_info()
                if model_info['exists']:
                    print("💾 Финальная модель:")
                    print(f"   Путь: {model_info['path']}")
                    print(f"   Размер: {model_info['size_mb']:.1f} MB")
                    print(f"   Время сохранения: {model_info['mtime'].strftime('%Y-%m-%d %H:%M:%S')}")
                
                print()
                print("📊 Проверьте результаты:")
                print("   • neural_network/models/keypoint_model_best.pth")
                print("   • neural_network/models/keypoint_model_last.pth")
                print()
                print("🔍 Проверьте метрики:")
                print("   • Order penalty должен быть близок к 0")
                print("   • Порядок точек должен соблюдаться")
                print()
                break
            
            # Проверяем обновление модели
            model_info = get_model_info()
            if model_info['exists']:
                current_update = model_info['mtime']
                if last_model_update != current_update:
                    if last_model_update is not None:
                        elapsed = (datetime.now() - current_update).total_seconds()
                        print(f"✅ Модель обновлена ({current_update.strftime('%H:%M:%S')}) - "
                              f"размер: {model_info['size_mb']:.1f} MB")
                    last_model_update = current_update
                else:
                    # Проверяем, не завершилось ли обучение (нет обновлений долгое время)
                    time_since_update = (datetime.now() - current_update).total_seconds()
                    if time_since_update > no_update_timeout:
                        print()
                        print("⚠️  Модель не обновлялась более 10 минут.")
                        print("   Возможно, обучение завершилось или зависло.")
                        print("   Проверьте процесс вручную.")
                        break
            
            time.sleep(check_interval)
            
    except KeyboardInterrupt:
        print()
        print()
        print("⏸️  Мониторинг остановлен пользователем")
        print()
        if check_process(pid):
            print("ℹ️  Обучение все еще продолжается.")
            print(f"   PID: {pid}")
            print("   Вы можете продолжить мониторинг позже.")

if __name__ == '__main__':
    main()

