import logging
import os
import sys
import importlib
from io import BytesIO
from typing import List, Tuple, Union
import time

# Добавляем путь к silero-vad в sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
silero_vad_path = os.path.join(current_dir, '..', '..', 'silero-vad', 'src')
silero_vad_path = os.path.abspath(silero_vad_path)
if silero_vad_path not in sys.path:
    sys.path.insert(0, silero_vad_path)

import torch
from pyannote.audio import Pipeline
from pydub import AudioSegment

_PIPELINE = None
_SILERO_MODEL = None


def get_pipeline(device: Union[str, torch.device]) -> Pipeline:
    """
    Retrieves a PyAnnote voice activity detection pipeline and move it to the specified device.
    The pipeline is loaded only once and reused across subsequent calls.
    It requires the Hugging Face API token to be set in the HF_TOKEN environment variable.
    """
    global _PIPELINE
    if _PIPELINE is not None:
        return _PIPELINE.to(device)

    try:
        hf_token = os.environ["HF_TOKEN"]
    except KeyError as exc:
        raise ValueError("HF_TOKEN environment variable is not set") from exc

    _PIPELINE = Pipeline.from_pretrained(
        "pyannote/voice-activity-detection", use_auth_token=hf_token
    )

    return _PIPELINE.to(device)


def get_silero_vad(device: Union[str, torch.device]):
    """
    Retrieves a SileroVAD model and moves it to the specified device.
    """
    global _SILERO_MODEL

    if _SILERO_MODEL is None:
        try:
            silero_mod = importlib.import_module("silero_vad")
        except ModuleNotFoundError as exc:
            logging.error(
                "silero_vad package not found. Ensure 'silero-vad/src' is on sys.path: %s",
                silero_vad_path,
            )
            raise exc

        _SILERO_MODEL = silero_mod.load_silero_vad()

    return _SILERO_MODEL.to(device)


def audiosegment_to_tensor(audiosegment: AudioSegment) -> torch.Tensor:
    """
    Converts an AudioSegment object to a PyTorch tensor.
    """
    samples = torch.tensor(audiosegment.get_array_of_samples(), dtype=torch.float32)
    if audiosegment.channels == 2:
        samples = samples.view(-1, 2)

    samples = samples / 32768.0  # Normalize to [-1, 1] range
    return samples


def segment_audio(
    wav_tensor: torch.Tensor,
    sample_rate: int,
    max_duration: float = 22.0,
    min_duration: float = 15.0,
    new_chunk_threshold: float = 0.2,
    device: Union[str, torch.device] = "cpu",
) -> Tuple[List[torch.Tensor], List[Tuple[float, float]]]:
    """
    Segments an audio waveform into smaller chunks based on speech activity.
    The segmentation is performed using a PyAnnote voice activity detection pipeline.
    If the HF_TOKEN environment variable is not set, the segmentation is performed using SileroVAD.
    """

    # --- Предобработка аудио для VAD ---
    def _preprocess_for_vad(wav: torch.Tensor, sr: int) -> torch.Tensor:
        # Приводим к float32 в диапазон [-1, 1]
        if wav.dtype.is_floating_point:
            x = wav.to(torch.float32)
            # Если это шкала int16 (по логике load_audio("int") может быть), нормализуем
            if x.abs().max() > 1.5:
                x = (x / 32768.0).clamp_(-1.0, 1.0)
        else:
            x = (wav.to(torch.float32) / 32768.0).clamp_(-1.0, 1.0)

        # Удаление DC-смещения
        x = x - x.mean()

        # Pre-emphasis (легкий ВЧ-фильтр)
        pre = 0.97
        if x.numel() > 1:
            y = x.clone()
            y[1:] = x[1:] - pre * x[:-1]
            x = y

        # Нормализация пика до 0.99
        peak = x.abs().max()
        if peak > 0:
            x = (x / peak) * 0.99

        # Обратно к int16 для pydub.AudioSegment
        x_int16 = (x * 32768.0).round().to(torch.int16)
        return x_int16

    processed = _preprocess_for_vad(wav_tensor, sample_rate)
    processed_float = (processed.to(torch.float32) / 32768.0).clamp_(-1.0, 1.0)

    audio = AudioSegment(
        processed.numpy().tobytes(),
        frame_rate=sample_rate,
        sample_width=processed.dtype.itemsize,
        channels=1,
    )

    try:
        t0 = time.perf_counter()
        audio_bytes = BytesIO()
        audio.export(audio_bytes, format="wav")
        audio_bytes.seek(0)

        # Process audio with pipeline to obtain segments with speech activity
        pipeline = get_pipeline(device)

        pipeline_result = pipeline(
            {"uri": "filename", "audio": audio_bytes}
        ).get_timeline().support()
        sad_segments = list(map(lambda x: {"start": x.start, "end": x.end}, pipeline_result))
    # минимальные логи
    except ValueError:
        logging.warning(
            "HF_TOKEN environment variable is not set so using local Silero VAD instead of PyAnnote pipeline"
        )

        # Process audio with Silero VAD to obtain segments with speech activity
        t2 = time.perf_counter()
        silero_model = get_silero_vad(device)

        silero_mod = importlib.import_module("silero_vad")
        sad_segments = silero_mod.get_speech_timestamps(
            processed_float.to(device),
            model=silero_model,
            sampling_rate=sample_rate,
            return_seconds=True,
        )
    # минимальные логи

    segments: List[torch.Tensor] = []
    curr_duration = 0.0
    curr_start = -1.0
    curr_end = 0.0
    boundaries: List[Tuple[float, float]] = []

    # Concat segments from pipeline into chunks for asr according to max/min duration
    for segment in sad_segments:
        start = max(0, segment["start"])
        end = min(len(audio) / 1000, segment["end"])

        if int(curr_start) == -1:
            curr_start, curr_end, curr_duration = start, end, end - start
            continue

        if (
            curr_duration > min_duration and start - curr_end > new_chunk_threshold
        ) or (curr_duration + (end - curr_end) > max_duration):

            start_ms = int(curr_start * 1000)
            end_ms = int(curr_end * 1000)
            segments.append(audiosegment_to_tensor(audio[start_ms:end_ms]))
            boundaries.append((curr_start, curr_end))
            curr_start = start

        curr_end = end
        curr_duration = curr_end - curr_start

    if curr_duration != 0:
        start_ms = int(curr_start * 1000)
        end_ms = int(curr_end * 1000)
        segments.append(audiosegment_to_tensor(audio[start_ms:end_ms]))
        boundaries.append((curr_start, curr_end))

    # минимальные логи: можно убрать вовсе, оставляем как ориентир
    logging.info("VAD(chunks) | chunks=%d", len(segments))
    return segments, boundaries
