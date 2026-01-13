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

    for entry in stats:
        from_level = entry['from_level']
        action = entry['action']
        result = entry['result']

        transitions[from_level][action][result] += 1

    return transitions


def print_statistics(transitions):
    """Выводит статистику в читаемом формате"""

    print("\n" + "="*70)
    print("СТАТИСТИКА УСПЕШНОСТИ ПЕРЕХОДОВ МЕЖДУ УРОВНЯМИ")
    print("="*70)

    if not transitions:
        print("\nСтатистика отсутствует.")
        return

    total_attempts = 0
    total_successes = 0

    for level in sorted(transitions.keys()):
        print(f"\n--- Уровень +{level} ---")

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

            total_attempts += total
            total_successes += success_count

            print(f"  {action}: {success_count}/{total} успехов "
                  f"({success_rate:.1f}% успешность)")

    print("\n" + "="*70)
    if total_attempts > 0:
        overall_rate = (total_successes / total_attempts) * 100
        print(f"ОБЩАЯ СТАТИСТИКА: {total_successes}/{total_attempts} успехов "
              f"({overall_rate:.1f}% успешность)")
    print("="*70 + "\n")


def print_detailed_transitions(stats):
    """Выводит детальную статистику переходов"""

    # Структура: (from_level, to_level) -> action -> count
    detailed = defaultdict(lambda: defaultdict(int))

    for entry in stats:
        if entry['result'] == 'success' and entry['from_level'] != entry['to_level']:
            key = (entry['from_level'], entry['to_level'])
            detailed[key][entry['action']] += 1

    if not detailed:
        return

    print("\n" + "="*70)
    print("ДЕТАЛЬНАЯ СТАТИСТИКА УСПЕШНЫХ ПЕРЕХОДОВ")
    print("="*70 + "\n")

    for (from_level, to_level) in sorted(detailed.keys()):
        print(f"+{from_level} → +{to_level}:")
        for action in ['F1', 'F5']:
            if action in detailed[(from_level, to_level)]:
                count = detailed[(from_level, to_level)][action]
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
    transitions = analyze_success_rates(stats)
    print_statistics(transitions)
    print_detailed_transitions(stats)
    print_session_summary(stats)


if __name__ == '__main__':
    main()
