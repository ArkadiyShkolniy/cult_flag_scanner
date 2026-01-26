#!/usr/bin/env python3
"""
Тестирование всех правил для LONG и SHORT паттернов
"""

from neural_network.check_annotations_geometry import check_long_constraints, check_short_constraints

def test_long_rules():
    """Тестирование правил для LONG"""
    print("=" * 80)
    print("ТЕСТИРОВАНИЕ ПРАВИЛ ДЛЯ LONG (БЫЧИЙ) ПАТТЕРНА")
    print("=" * 80)
    print()
    
    # Пример: T0=100, T1=200, T2=180, T3=195, T4=187
    T0, T1, T2, T3, T4 = 100, 200, 180, 195, 187
    t0_idx, t1_idx, t2_idx, t3_idx, t4_idx = 0, 10, 15, 25, 30
    
    print(f"Тестовые данные:")
    print(f"  T0={T0}, T1={T1}, T2={T2}, T3={T3}, T4={T4}")
    print()
    
    # Проверяем каждое правило
    print("1. T0 - нет ограничений ✓")
    print("2. T1 - нет ограничений ✓")
    print()
    
    # T2 >= T1 - 0.62 * (T1 - T0)
    min_t2 = T1 - 0.62 * (T1 - T0)
    print(f"3. T2 - не ниже фиба 0.62 хода T0-T1")
    print(f"   Правило: T2 >= T1 - 0.62 * (T1 - T0)")
    print(f"   min_t2 = {T1} - 0.62 * ({T1} - {T0}) = {min_t2:.2f}")
    print(f"   T2 = {T2:.2f} >= {min_t2:.2f}? {'✓' if T2 >= min_t2 else '✗'}")
    print()
    
    # T3 в диапазоне фиба 0.5 хода T1-T2, но не выше T1
    move_12 = T1 - T2
    fib_50_t3 = T2 + 0.5 * move_12
    print(f"4. T3 - в диапазоне фиба 0.5 хода T1-T2, но не выше T1")
    print(f"   Правило: T2 + 0.5 * (T1 - T2) <= T3 <= T1")
    print(f"   fib_50_t3 = {T2} + 0.5 * ({T1} - {T2}) = {fib_50_t3:.2f}")
    print(f"   Диапазон: [{fib_50_t3:.2f}, {T1:.2f}]")
    print(f"   T3 = {T3:.2f} в диапазоне? {'✓' if fib_50_t3 <= T3 <= T1 else '✗'}")
    print()
    
    # T4 в диапазоне фиба 0.5 хода T2-T3, но не ниже фиба 0.62 хода T0-T1
    move_23 = T3 - T2
    max_t4_from_t3 = T3 - 0.5 * move_23
    min_t4_from_pole = T1 - 0.62 * (T1 - T0)
    print(f"5. T4 - в диапазоне фиба 0.5 хода T2-T3, но не ниже фиба 0.62 хода T0-T1")
    print(f"   Правило: T4 <= T3 - 0.5 * (T3 - T2), T4 >= T1 - 0.62 * (T1 - T0)")
    print(f"   max_t4_from_t3 = {T3} - 0.5 * ({T3} - {T2}) = {max_t4_from_t3:.2f}")
    print(f"   min_t4_from_pole = {T1} - 0.62 * ({T1} - {T0}) = {min_t4_from_pole:.2f}")
    print(f"   Диапазон: [{min_t4_from_pole:.2f}, {max_t4_from_t3:.2f}]")
    print(f"   T4 = {T4:.2f} в диапазоне? {'✓' if min_t4_from_pole <= T4 <= max_t4_from_t3 else '✗'}")
    print()
    
    # Проверка через функцию
    violations = check_long_constraints(T0, T1, T2, T3, T4, '1h', t0_idx, t1_idx, t2_idx, t3_idx, t4_idx)
    print("Результат проверки функцией:")
    if violations:
        print("  ❌ Нарушения:")
        for v in violations:
            print(f"     - {v}")
    else:
        print("  ✅ Все правила соблюдены")
    print()


def test_short_rules():
    """Тестирование правил для SHORT"""
    print("=" * 80)
    print("ТЕСТИРОВАНИЕ ПРАВИЛ ДЛЯ SHORT (МЕДВЕЖИЙ) ПАТТЕРНА")
    print("=" * 80)
    print()
    
    # Пример: T0=200, T1=100, T2=138, T3=115, T4=130
    T0, T1, T2, T3, T4 = 200, 100, 138, 115, 130
    t0_idx, t1_idx, t2_idx, t3_idx, t4_idx = 0, 10, 15, 25, 30
    
    print(f"Тестовые данные:")
    print(f"  T0={T0}, T1={T1}, T2={T2}, T3={T3}, T4={T4}")
    print()
    
    # Проверяем каждое правило
    print("1. T0 - нет ограничений ✓")
    print("2. T1 - нет ограничений ✓")
    print()
    
    # T2 <= T1 + 0.62 * (T0 - T1)
    max_t2 = T1 + 0.62 * (T0 - T1)
    print(f"3. T2 - не выше фиба 0.62 хода T0-T1")
    print(f"   Правило: T2 <= T1 + 0.62 * (T0 - T1)")
    print(f"   max_t2 = {T1} + 0.62 * ({T0} - {T1}) = {max_t2:.2f}")
    print(f"   T2 = {T2:.2f} <= {max_t2:.2f}? {'✓' if T2 <= max_t2 else '✗'}")
    print()
    
    # T3 в диапазоне фиба 0.5 хода T1-T2, но не ниже T1
    move_12 = T2 - T1
    fib_50_t3 = T1 + 0.5 * move_12
    print(f"4. T3 - в диапазоне фиба 0.5 хода T1-T2, но не ниже T1")
    print(f"   Правило: T1 <= T3 <= T1 + 0.5 * (T2 - T1)")
    print(f"   fib_50_t3 = {T1} + 0.5 * ({T2} - {T1}) = {fib_50_t3:.2f}")
    print(f"   Диапазон: [{T1:.2f}, {fib_50_t3:.2f}]")
    print(f"   T3 = {T3:.2f} в диапазоне? {'✓' if T1 <= T3 <= fib_50_t3 else '✗'}")
    print()
    
    # T4 в диапазоне фиба 0.5 хода T2-T3, но не выше фиба 0.62 хода T0-T1
    move_23 = T2 - T3
    min_t4_from_t3 = T3 + 0.5 * move_23
    max_t4_from_pole = T1 + 0.62 * (T0 - T1)
    print(f"5. T4 - в диапазоне фиба 0.5 хода T2-T3, но не выше фиба 0.62 хода T0-T1")
    print(f"   Правило: T4 >= T3 + 0.5 * (T2 - T3), T4 <= T1 + 0.62 * (T0 - T1)")
    print(f"   min_t4_from_t3 = {T3} + 0.5 * ({T2} - {T3}) = {min_t4_from_t3:.2f}")
    print(f"   max_t4_from_pole = {T1} + 0.62 * ({T0} - {T1}) = {max_t4_from_pole:.2f}")
    print(f"   Диапазон: [{min_t4_from_t3:.2f}, {max_t4_from_pole:.2f}]")
    print(f"   T4 = {T4:.2f} в диапазоне? {'✓' if min_t4_from_t3 <= T4 <= max_t4_from_pole else '✗'}")
    print()
    
    # Проверка через функцию
    violations = check_short_constraints(T0, T1, T2, T3, T4, '1h', t0_idx, t1_idx, t2_idx, t3_idx, t4_idx)
    print("Результат проверки функцией:")
    if violations:
        print("  ❌ Нарушения:")
        for v in violations:
            print(f"     - {v}")
    else:
        print("  ✅ Все правила соблюдены")
    print()


if __name__ == "__main__":
    test_long_rules()
    print()
    test_short_rules()
    print()
    print("=" * 80)
    print("СВОДКА ПРАВИЛ")
    print("=" * 80)
    print()
    print("LONG (Бычий):")
    print("  T0 - нет ограничений")
    print("  T1 - нет ограничений")
    print("  T2 - не ниже фиба 0.62 хода T0-T1")
    print("  T3 - в диапазоне фиба 0.5 хода T1-T2, но не выше T1")
    print("  T4 - в диапазоне фиба 0.5 хода T2-T3, но не ниже фиба 0.62 хода T0-T1")
    print("  Линии T1-T3 и T2-T4 могут быть параллельны или сходиться, но не могут расходиться")
    print()
    print("SHORT (Медвежий):")
    print("  T0 - нет ограничений")
    print("  T1 - нет ограничений")
    print("  T2 - не выше фиба 0.62 хода T0-T1")
    print("  T3 - в диапазоне фиба 0.5 хода T1-T2, но не ниже T1")
    print("  T4 - в диапазоне фиба 0.5 хода T2-T3, но не выше фиба 0.62 хода T0-T1")
    print("  Линии T1-T3 и T2-T4 могут быть параллельны или сходиться, но не могут расходиться")
