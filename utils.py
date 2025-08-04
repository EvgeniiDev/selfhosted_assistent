from typing import Optional
from datetime import datetime, timedelta
import re


def parse_duration(duration_text: str) -> Optional[int]:
    """Парсит текстовое описание длительности в минуты"""
    duration_text = duration_text.lower()

    # Паттерны для разных форматов времени
    patterns = [
        (r'(\d+)\s*ч(?:ас)?(?:а|ов)?', 60),  # часы
        (r'(\d+)\s*м(?:ин)?(?:ут)?(?:ы)?', 1),  # минуты
        (r'(\d+)\s*hour?s?', 60),  # hours
        (r'(\d+)\s*min(?:ute)?s?', 1),  # minutes
    ]

    total_minutes = 0

    for pattern, multiplier in patterns:
        matches = re.findall(pattern, duration_text)
        for match in matches:
            total_minutes += int(match) * multiplier

    return total_minutes if total_minutes > 0 else None


def get_default_end_time(start_time: datetime, duration_minutes: Optional[int] = None) -> datetime:
    """Возвращает время окончания по умолчанию"""
    if duration_minutes:
        return start_time + timedelta(minutes=duration_minutes)
    else:
        return start_time + timedelta(hours=1)


def parse_recurrence_rule(recurrence_text: str) -> Optional[str]:
    """Преобразует текстовое описание повторения в RRULE"""
    recurrence_text = recurrence_text.lower()

    if 'каждый день' in recurrence_text or 'ежедневно' in recurrence_text:
        return 'RRULE:FREQ=DAILY'
    elif 'каждую неделю' in recurrence_text or 'еженедельно' in recurrence_text:
        return 'RRULE:FREQ=WEEKLY'
    elif 'каждый месяц' in recurrence_text or 'ежемесячно' in recurrence_text:
        return 'RRULE:FREQ=MONTHLY'
    elif 'каждый год' in recurrence_text or 'ежегодно' in recurrence_text:
        return 'RRULE:FREQ=YEARLY'
    elif 'рабочие дни' in recurrence_text or 'по будням' in recurrence_text:
        return 'RRULE:FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR'

    return None
