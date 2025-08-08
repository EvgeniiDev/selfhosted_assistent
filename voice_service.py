import io
import torch
import tempfile
import os
from typing import Union, Optional
from telegram import File

# Применяем патч для PyTorch перед импортом gigaam
from pytorch_patch import *

# Импортируем GigaAM из локальной папки
import sys
gigaam_path = os.path.join(os.path.dirname(__file__), 'GigaAM-upgraded')
if gigaam_path not in sys.path:
    sys.path.insert(0, gigaam_path)
import gigaam


from logger import calendar_logger


class VoiceService:
    """Сервис для обработки голосовых сообщений"""
    
    def __init__(self, device: str = "cpu"):
        """
        Инициализация сервиса обработки голоса
        
        Args:
            device: устройство для инференса ("cpu" или "cuda")
        """
        self.device = device
        self.model = None
        self._load_model()
    
    def _load_model(self):
        """Загружает модель GigaAM для распознавания речи"""
        try:
            torch.serialization.safe_globals([omegaconf.base.ContainerMetadata])
            torch.serialization.add_safe_globals([omegaconf.base.ContainerMetadata])
            calendar_logger.info("Загрузка модели GigaAM...")
            self.model = gigaam.load_model(
                "v1_ctc",  # GigaAM-V1 CTC model
                device=self.device
            )
            calendar_logger.info("Модель GigaAM успешно загружена")
        except Exception as e:
            calendar_logger.log_error(e, "voice_service._load_model")
            print(f"Ошибка загрузки модели GigaAM: {str(e)}")
            self.model = None
    
    async def transcribe_voice_message(self, voice_file: File) -> Optional[str]:
        """
        Транскрибирует голосовое сообщение в текст
        
        Args:
            voice_file: объект файла голосового сообщения из Telegram
            
        Returns:
            str: транскрибированный текст или None в случае ошибки
        """
        try:
            # Скачиваем файл в память
            file_bytes = await voice_file.download_as_bytearray()
            
            # Конвертируем в аудио формат, который понимает модель
            audio_data = self._convert_ogg_to_wav(file_bytes)
            
            # Передаем байты напрямую в модель (sample_rate уже 16000 после конвертации)
            transcription = self.model.transcribe(audio_data, sample_rate=16000)
            
            calendar_logger.info(f"Голосовое сообщение транскрибировано: {transcription}")
            return transcription.strip() if transcription.strip() else None
            
        except Exception as e:
            calendar_logger.log_error(e, "voice_service.transcribe_voice_message")
            return None
    
    def _convert_ogg_to_wav(self, ogg_bytes: bytearray) -> torch.Tensor:
        """
        Конвертирует OGG аудио в WAV формат и возвращает torch.Tensor
        
        Args:
            ogg_bytes: байты OGG файла
            
        Returns:
            torch.Tensor: аудио данные
        """
        import torchaudio
        
        try:
            # Создаем временный файл для OGG
            with tempfile.NamedTemporaryFile(suffix='.ogg', delete=False) as temp_ogg:
                temp_ogg.write(ogg_bytes)
                temp_ogg_path = temp_ogg.name
            
            try:
                # Загружаем аудио файл с помощью torchaudio
                waveform, sample_rate = torchaudio.load(temp_ogg_path)
                
                # Преобразуем в моно если нужно
                if waveform.shape[0] > 1:
                    waveform = torch.mean(waveform, dim=0, keepdim=True)
                
                # Убираем лишнюю размерность
                waveform = waveform.squeeze(0)
                
                # Ресемплируем до 16kHz для модели
                if sample_rate != 16000:
                    resampler = torchaudio.transforms.Resample(sample_rate, 16000)
                    waveform = resampler(waveform)
                
                calendar_logger.info(f"Аудио конвертировано: sample_rate={sample_rate}, shape={waveform.shape}")
                return waveform
                
            finally:
                # Удаляем временный файл
                try:
                    os.unlink(temp_ogg_path)
                except OSError:
                    pass
                    
        except Exception as e:
            calendar_logger.log_error(e, "voice_service._convert_ogg_to_wav")
            raise
    
    def is_model_loaded(self) -> bool:
        """Проверяет, загружена ли модель"""
        return self.model is not None
