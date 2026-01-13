#!/usr/bin/env python3
"""
Анализатор статистики Polisher

Читает файл polisher_statistics.jsonl и выводит статистику по успешности
переходов между уровнями.
"""

import json
import os
from collections import defaultdict
from config import STATISTICS_FILE


def load_statistics():
    """Загружает статистику из JSONL файла"""
    stats = []

    if not os.path.exists(STATISTICS_FILE):
        print(f"Файл статистики {STATISTICS_FILE} не найден!")
        return stats

    with open(STATISTICS_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    stats.append(json.loads(line))
                except json.JSONDecodeError as e:
                    print(f"Ошибка чтения строки: {e}")

    return stats


def analyze_success_rates(stats):
    """Анализирует успешность переходов между уровнями"""

    # Структура: level -> action -> {success: count, failed: count}
    transitions = defaultdict(lambda: defaultdict(lambda: {'success': 0, 'failed': 0}))

    # Отдельно считаем переходы с падением на 0 (поломки)
    breaks_to_zero = defaultdict(int)  # action -> count

    for entry in stats:
        from_level = entry['from_level']
        to_level = entry['to_level']
        action = entry['action']
        result = entry['result']

        transitions[from_level][action][result] += 1

        # Если упало на 0 (поломка), считаем отдельно
        if result == 'success' and to_level == 0 and from_level > 0:
            breaks_to_zero[action] += 1

    return transitions, breaks_to_zero


def print_statistics(transitions, breaks_to_zero):
    """Выводит статистику в читаемом формате"""

    print("\n" + "="*70)
    print("СТАТИСТИКА УСПЕШНОСТИ ПЕРЕХОДОВ МЕЖДУ УРОВНЯМИ")
    print("="*70)

    if not transitions:
        print("\nСтатистика отсутствует.")
        return

    # Разделяем безопасные уровни (0-2) и опасные (3+)
    safe_levels = [0, 1, 2]

    print("\n--- БЕЗОПАСНЫЕ ПЕРЕХОДЫ (0→1, 1→2, 2→3) ---")
    print("Эти переходы всегда 100% успешны, заточка не может сломаться")

    safe_total_attempts = 0
    safe_total_successes = 0

    for level in safe_levels:
        if level not in transitions:
            continue

        for action in ['F1', 'F5']:
            if action not in transitions[level]:
                continue

            stats = transitions[level][action]
            success_count = stats['success']
            failed_count = stats['failed']
            total = success_count + failed_count

            if total == 0:
                continue

            success_rate = (success_count / total) * 100
            safe_total_attempts += total
            safe_total_successes += success_count

            print(f"  +{level} ({action}): {success_count}/{total} успехов "
                  f"({success_rate:.1f}%)")

    print("\n--- ОПАСНЫЕ ПЕРЕХОДЫ (+3 и выше) ---")
    print("F1 флоу - безопасный (не может сломаться)")
    print("F5 флоу - опасный (может сломаться и упасть на 0)")

    risky_total_attempts = 0
    risky_total_successes = 0
    f1_attempts = 0
    f1_successes = 0
    f5_attempts = 0
    f5_successes = 0

    for level in sorted(transitions.keys()):
        if level in safe_levels:
            continue

        print(f"\n  Уровень +{level}:")

        for action in ['F1', 'F5']:
            if action not in transitions[level]:
                continue

            stats = transitions[level][action]
            success_count = stats['success']
            failed_count = stats['failed']
            total = success_count + failed_count

            if total == 0:
                continue

            success_rate = (success_count / total) * 100
            risky_total_attempts += total
            risky_total_successes += success_count

            if action == 'F1':
                f1_attempts += total
                f1_successes += success_count
            else:
                f5_attempts += total
                f5_successes += success_count

            flow_type = "безопасный" if action == 'F1' else "опасный"
            print(f"    {action} ({flow_type}): {success_count}/{total} успехов "
                  f"({success_rate:.1f}%)")

    # Показываем поломки (падения на 0)
    if breaks_to_zero:
        print("\n--- ПОЛОМКИ (падение на 0) ---")
        for action in ['F1', 'F5']:
            if action in breaks_to_zero:
                count = breaks_to_zero[action]
                print(f"  {action}: {count} поломок(и)")
                if action == 'F1':
                    print(f"    ⚠ ВНИМАНИЕ: F1 не должен ломаться! Возможно ошибка в логике.")

    # Общая статистика
    print("\n" + "="*70)
    print("ОБЩАЯ СТАТИСТИКА")
    print("="*70)

    if safe_total_attempts > 0:
        safe_rate = (safe_total_successes / safe_total_attempts) * 100
        print(f"Безопасные переходы (0-2): {safe_total_successes}/{safe_total_attempts} "
              f"({safe_rate:.1f}%)")

    if f1_attempts > 0:
        f1_rate = (f1_successes / f1_attempts) * 100
        print(f"F1 флоу (безопасный): {f1_successes}/{f1_attempts} "
              f"({f1_rate:.1f}%)")

    if f5_attempts > 0:
        f5_rate = (f5_successes / f5_attempts) * 100
        print(f"F5 флоу (опасный): {f5_successes}/{f5_attempts} "
              f"({f5_rate:.1f}%)")

    total_attempts = safe_total_attempts + risky_total_attempts
    total_successes = safe_total_successes + risky_total_successes

    if total_attempts > 0:
        overall_rate = (total_successes / total_attempts) * 100
        print(f"\nВСЕГО: {total_successes}/{total_attempts} успехов "
              f"({overall_rate:.1f}%)")
    print("="*70 + "\n")


def print_detailed_transitions(stats):
    """Выводит детальную статистику переходов"""

    # Структура: (from_level, to_level) -> action -> count
    upgrades = defaultdict(lambda: defaultdict(int))  # Успешные повышения
    breaks = defaultdict(lambda: defaultdict(int))  # Поломки (падения на 0)

    for entry in stats:
        from_level = entry['from_level']
        to_level = entry['to_level']
        action = entry['action']
        result = entry['result']

        if result == 'success':
            if to_level > from_level:
                # Успешное повышение уровня
                key = (from_level, to_level)
                upgrades[key][action] += 1
            elif to_level == 0 and from_level > 0:
                # Поломка (падение на 0)
                breaks[from_level][action] += 1

    print("\n" + "="*70)
    print("ДЕТАЛЬНАЯ СТАТИСТИКА ПЕРЕХОДОВ")
    print("="*70)

    # Успешные повышения
    if upgrades:
        print("\n--- УСПЕШНЫЕ ПОВЫШЕНИЯ УРОВНЯ ---\n")
        for (from_level, to_level) in sorted(upgrades.keys()):
            print(f"+{from_level} → +{to_level}:")
            for action in ['F1', 'F5']:
                if action in upgrades[(from_level, to_level)]:
                    count = upgrades[(from_level, to_level)][action]
                    flow_type = "безопасный" if action == 'F1' else "опасный"
                    print(f"  {action} ({flow_type}): {count} раз(а)")

    # Поломки
    if breaks:
        print("\n--- ПОЛОМКИ (падение на 0) ---\n")
        for from_level in sorted(breaks.keys()):
            print(f"+{from_level} → 0 (поломка):")
            for action in ['F1', 'F5']:
                if action in breaks[from_level]:
                    count = breaks[from_level][action]
                    if action == 'F1':
                        print(f"  {action}: {count} раз(а) ⚠ ОШИБКА: F1 не должен ломаться!")
                    else:
                        print(f"  {action}: {count} раз(а)")

    print()


def print_session_summary(stats):
    """Выводит сводку по завершенным сессиям (до +10)"""

    sessions_completed = sum(1 for entry in stats
                            if entry['result'] == 'success' and entry['to_level'] == 10)

    if sessions_completed > 0:
        print("\n" + "="*70)
        print(f"ЗАВЕРШЕНО СЕССИЙ (достигнут +10): {sessions_completed}")
        print("="*70 + "\n")


def main():
    print("Загрузка статистики...")
    stats = load_statistics()

    if not stats:
        print("Нет данных для анализа.")
        return

    print(f"Загружено {len(stats)} записей.\n")

    # Анализируем и выводим статистику
    transitions, breaks_to_zero = analyze_success_rates(stats)
    print_statistics(transitions, breaks_to_zero)
    print_detailed_transitions(stats)
    print_session_summary(stats)


if __name__ == '__main__':
    main()
