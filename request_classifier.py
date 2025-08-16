from typing import Optional, Union
from datetime import datetime
from logger import calendar_logger
from models import CalendarEvent, Note
from llm_inference import ModelRouter
from request_handlers import (
    ClassificationHandler,
    CalendarEventHandler, 
    NoteHandler
)

class RequestClassifier:
    def __init__(self):
        self.router = ModelRouter()
        
        self.classification_handler = ClassificationHandler(self.router)
        self.calendar_handler = CalendarEventHandler(self.router)
        self.note_handler = NoteHandler(self.router)
        
        calendar_logger.info('RequestClassifier initialized with notes support')
        
        status = self.router.get_status()
        calendar_logger.info(f"Local model available: {status['local_available']}")
        calendar_logger.info(f"OpenRouter available: {status['openrouter_available']}")
        calendar_logger.info(f"Configured models: {status['models_count']}")

    def process_request(self, user_message: str) -> Optional[Union[CalendarEvent, Note]]:
        current_time = datetime.now()
        current_time_str = current_time.strftime("%Y-%m-%d %H:%M:%S (%A)")
        
        try:
            classification = self.classification_handler.classify_request(user_message)
            
            if classification == "unknown":
                calendar_logger.warning(f"Unknown request type for: {user_message} request_classifier.classify - unknown type")
                classification = "note"
            
            enhanced_message = f"""
            ## Input Data
            - Current date: {current_time_str}
            - User query: {user_message}
            """
            
            match classification:
                case "calendar_event":
                    return self.calendar_handler.create_calendar_event(enhanced_message)
                case "note":
                    return self.note_handler.create_note(enhanced_message, current_time)
                case _:
                    calendar_logger.log_error(
                        Exception(f"Unexpected classification: {classification}"),
                        "request_classifier.process_request - classification"
                    )
                    return None
                    
        except Exception as e:
            calendar_logger.log_error(e, "request_classifier.process_request - General exception")
            return None
