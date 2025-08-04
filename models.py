from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel


class CalendarEvent(BaseModel):
    title: str
    description: Optional[str] = None
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    recurrence: Optional[Dict[str, Any]] = None
    timezone: str = "Europe/Moscow"

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
            event['recurrence'] = [
                self.recurrence.get('rule', 'RRULE:FREQ=DAILY')]

        return event
