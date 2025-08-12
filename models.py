from typing import Optional, Dict, Any, Union
from datetime import datetime
from pydantic import BaseModel, validator, Field
from dateutil.parser import parse as parse_date
from logger import calendar_logger
import os


class CalendarEvent(BaseModel):
    title: str
    description: Optional[str] = None
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    recurrence: Optional[str] = None
    timezone: str = Field(default_factory=lambda: os.getenv("TIMEZONE", "Europe/Moscow"))

    @validator('start_time', pre=True)
    def parse_start_time(cls, v):
        if isinstance(v, str):
            return parse_date(v)
        return v

    @validator('end_time', pre=True)
    def parse_end_time(cls, v):
        if v is None:
            return v
        if isinstance(v, str):
            return parse_date(v)
        return v

    def to_google_event(self) -> Dict[str, Any]:
        """Преобразует в формат Google Calendar API"""
        if self.end_time:
            end_datetime = self.end_time
        elif self.duration_minutes:
            from datetime import timedelta
            end_datetime = self.start_time + \
                timedelta(minutes=self.duration_minutes)
        else:
            from datetime import timedelta
            end_datetime = self.start_time + timedelta(hours=1)

        event = {
            'summary': self.title,
            'start': {
                'dateTime': self.start_time.isoformat(),
                'timeZone': self.timezone,
            },
            'end': {
                'dateTime': end_datetime.isoformat(),
                'timeZone': self.timezone,
            },
        }

        if self.description:
            event['description'] = self.description

        if self.recurrence:
            # Преобразуем строку recurrence в правило RRULE
            rrule = self._parse_recurrence_to_rrule(self.recurrence)
            if rrule:
                event['recurrence'] = [rrule]

        return event

    def _parse_recurrence_to_rrule(self, recurrence: str) -> Optional[str]:
        """Преобразует текстовое описание повторения в RRULE"""
        recurrence_lower = recurrence.lower()
        
        if recurrence_lower == "daily":
            return "RRULE:FREQ=DAILY"
        elif recurrence_lower.startswith("weekly on"):
            # Извлекаем день недели
            days_map = {
                "monday": "MO", "tuesday": "TU", "wednesday": "WE",
                "thursday": "TH", "friday": "FR", "saturday": "SA", "sunday": "SU"
            }
            for day_name, day_code in days_map.items():
                if day_name in recurrence_lower:
                    return f"RRULE:FREQ=WEEKLY;BYDAY={day_code}"
        elif recurrence_lower.startswith("monthly"):
            return "RRULE:FREQ=MONTHLY"
        elif recurrence_lower.startswith("annually"):
            return "RRULE:FREQ=YEARLY"
        elif "weekday" in recurrence_lower and "monday to friday" in recurrence_lower:
            return "RRULE:FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR"
        
        # Если не удалось распарсить, но строка не пустая - логируем
        if recurrence.strip():
            calendar_logger.warning(f"Could not parse recurrence pattern: '{recurrence}'")
        
        return None


class Note(BaseModel):
    title: str
    content: str
    created_at: str
    tags: Optional[list] = None
