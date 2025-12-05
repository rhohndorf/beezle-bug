"""
Speech-to-text transcription using faster-whisper.

This module provides a Transcriber class that uses the faster-whisper
library for efficient speech recognition with GPU acceleration.
"""

import io
import tempfile
from typing import Optional
from loguru import logger

from faster_whisper import WhisperModel


class Transcriber:
    """
    Speech-to-text transcriber using faster-whisper.
    
    Uses GPU acceleration when available for fast transcription.
    The model is loaded lazily on first use.
    
    Attributes:
        model_size: Whisper model size (tiny, base, small, medium, large-v3)
        device: Device to run inference on (cuda, cpu, auto)
        compute_type: Compute type for inference (float16, int8, etc.)
    """
    
    def __init__(
        self,
        model_size: str = "base",
        device: str = "cuda",
        compute_type: str = "float16"
    ):
        """
        Initialize the transcriber.
        
        Args:
            model_size: Whisper model size. Options:
                - tiny: Fastest, least accurate
                - base: Good balance for real-time
                - small: Better accuracy, still fast
                - medium: High accuracy
                - large-v3: Best accuracy, slower
            device: Device for inference (cuda, cpu, auto)
            compute_type: Precision (float16 for GPU, int8 for CPU)
        """
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self._model: Optional[WhisperModel] = None
        
    @property
    def model(self) -> WhisperModel:
        """Lazy-load the Whisper model on first access."""
        if self._model is None:
            logger.info(f"Loading Whisper model: {self.model_size} on {self.device}")
            try:
                self._model = WhisperModel(
                    self.model_size,
                    device=self.device,
                    compute_type=self.compute_type
                )
                logger.info("Whisper model loaded successfully")
            except Exception as e:
                # Fallback to CPU if CUDA fails
                logger.warning(f"Failed to load on {self.device}, falling back to CPU: {e}")
                self._model = WhisperModel(
                    self.model_size,
                    device="cpu",
                    compute_type="int8"
                )
        return self._model
    
    def transcribe(
        self,
        audio_bytes: bytes,
        language: Optional[str] = None
    ) -> str:
        """
        Transcribe audio bytes to text.
        
        Args:
            audio_bytes: Raw audio data (WAV format expected)
            language: Optional language code (e.g., 'en', 'es')
                     If None, language is auto-detected
        
        Returns:
            Transcribed text string
        """
        # Write audio to a temporary file (faster-whisper requires file path)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=True) as tmp:
            tmp.write(audio_bytes)
            tmp.flush()
            
            # Transcribe
            segments, info = self.model.transcribe(
                tmp.name,
                language=language,
                beam_size=5,
                vad_filter=True,  # Use built-in VAD to filter silence
                vad_parameters=dict(
                    min_silence_duration_ms=500,
                    speech_pad_ms=200
                )
            )
            
            # Combine all segments into one string
            text = " ".join(segment.text.strip() for segment in segments)
            
            logger.debug(f"Transcribed {len(audio_bytes)} bytes -> '{text[:50]}...'")
            return text
    
    def transcribe_stream(
        self,
        audio_bytes: bytes,
        language: Optional[str] = None
    ):
        """
        Transcribe audio and yield segments as they're processed.
        
        Useful for streaming partial results to the frontend.
        
        Args:
            audio_bytes: Raw audio data (WAV format expected)
            language: Optional language code
            
        Yields:
            Tuples of (segment_text, start_time, end_time)
        """
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=True) as tmp:
            tmp.write(audio_bytes)
            tmp.flush()
            
            segments, info = self.model.transcribe(
                tmp.name,
                language=language,
                beam_size=5,
                vad_filter=True
            )
            
            for segment in segments:
                yield (segment.text.strip(), segment.start, segment.end)


# Global singleton instance (lazy-loaded)
_transcriber: Optional[Transcriber] = None


def get_transcriber(
    model_size: str = "base",
    device: str = "cuda",
    compute_type: str = "float16"
) -> Transcriber:
    """
    Get or create the global transcriber instance.
    
    Args:
        model_size: Whisper model size
        device: Device for inference
        compute_type: Precision type
        
    Returns:
        Transcriber instance
    """
    global _transcriber
    if _transcriber is None:
        _transcriber = Transcriber(model_size, device, compute_type)
    return _transcriber





