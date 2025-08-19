from typing import Optional
from logger import calendar_logger
from .base_handler import BaseRequestHandler


class ClassificationHandler(BaseRequestHandler):
    
    PROMPT = """
Сlassify text into one of these categories:

- **calendar_event**: mentions specific time, date, meetings, appointments, reminders with time constraints
- **note**: general information to remember, ideas, thoughts, lists, anything without specific time
- **task**: short task/reminder that the user wants to schedule or be reminded about (could have due date/time)
- **unknown**: unclear or ambiguous requests

Respond with ONLY one word: calendar_event, task, note, or unknown
"""
    
    def get_prompt(self) -> str:
        return self.PROMPT
    
    def get_handler_name(self) -> str:
        return "ClassificationHandler"
    
    def parse_response(self, response_content: str, **kwargs) -> Optional[str]:
        if not response_content:
            return None
        
        classification = response_content.strip().lower()
        valid_types = {"calendar_event", "note", "task", "unknown"}
        if classification in valid_types:
            calendar_logger.info(f"Request classified as: {classification}")
            return classification
        else:
            calendar_logger.warning(f"Invalid classification received: {classification}")
            return "unknown"
    
    def classify_request(self, user_message: str) -> str:
        try:
            classification = self.process(user_message, True)
            return classification if classification else "unknown"
            
        except Exception as e:
            calendar_logger.log_error(e, f"{self.get_handler_name()}.classify_request")
            return "unknown"
