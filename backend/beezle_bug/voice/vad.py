"""
Voice Activity Detection using webrtcvad.

This module provides a VoiceActivityDetector class that detects speech
segments in audio streams to avoid transcribing silence.
"""

import collections
import webrtcvad
from typing import Generator, Optional
from loguru import logger


class VoiceActivityDetector:
    """
    Voice Activity Detector using webrtcvad.
    
    Detects speech segments in audio streams and buffers audio until
    a speech pause is detected. This helps avoid sending silence to
    the transcriber and improves response time.
    
    Attributes:
        sample_rate: Audio sample rate (8000, 16000, 32000, or 48000)
        frame_duration_ms: Frame duration in ms (10, 20, or 30)
        aggressiveness: VAD aggressiveness (0-3, higher = more aggressive)
        padding_duration_ms: Duration of silence to pad around speech
    """
    
    VALID_SAMPLE_RATES = [8000, 16000, 32000, 48000]
    VALID_FRAME_DURATIONS = [10, 20, 30]
    
    def __init__(
        self,
        sample_rate: int = 16000,
        frame_duration_ms: int = 30,
        aggressiveness: int = 2,
        padding_duration_ms: int = 300
    ):
        """
        Initialize the VAD.
        
        Args:
            sample_rate: Audio sample rate in Hz
            frame_duration_ms: Frame duration (10, 20, or 30 ms)
            aggressiveness: VAD aggressiveness level (0-3)
            padding_duration_ms: Padding duration for speech boundaries
        """
        if sample_rate not in self.VALID_SAMPLE_RATES:
            raise ValueError(f"Sample rate must be one of {self.VALID_SAMPLE_RATES}")
        if frame_duration_ms not in self.VALID_FRAME_DURATIONS:
            raise ValueError(f"Frame duration must be one of {self.VALID_FRAME_DURATIONS}")
        if not 0 <= aggressiveness <= 3:
            raise ValueError("Aggressiveness must be 0-3")
        
        self.sample_rate = sample_rate
        self.frame_duration_ms = frame_duration_ms
        self.aggressiveness = aggressiveness
        self.padding_duration_ms = padding_duration_ms
        
        # Calculate frame size in bytes (16-bit audio = 2 bytes per sample)
        self.frame_size = int(sample_rate * frame_duration_ms / 1000) * 2
        
        # Number of frames to pad speech segments
        self.num_padding_frames = int(padding_duration_ms / frame_duration_ms)
        
        # Initialize VAD
        self.vad = webrtcvad.Vad(aggressiveness)
        
        # Ring buffer for padding
        self._ring_buffer = collections.deque(maxlen=self.num_padding_frames)
        self._triggered = False
        self._voiced_frames = []
        
    def reset(self):
        """Reset the VAD state for a new audio stream."""
        self._ring_buffer.clear()
        self._triggered = False
        self._voiced_frames = []
        
    def is_speech(self, frame: bytes) -> bool:
        """
        Check if a single frame contains speech.
        
        Args:
            frame: Audio frame (must match frame_size)
            
        Returns:
            True if speech is detected
        """
        if len(frame) != self.frame_size:
            return False
        return self.vad.is_speech(frame, self.sample_rate)
    
    def process_frame(self, frame: bytes) -> Optional[bytes]:
        """
        Process a single audio frame.
        
        Returns speech audio when a complete utterance is detected
        (speech followed by silence).
        
        Args:
            frame: Audio frame to process
            
        Returns:
            Complete speech segment bytes, or None if still collecting
        """
        if len(frame) != self.frame_size:
            return None
            
        is_speech = self.vad.is_speech(frame, self.sample_rate)
        
        if not self._triggered:
            self._ring_buffer.append((frame, is_speech))
            num_voiced = len([f for f, speech in self._ring_buffer if speech])
            
            # Start triggered state if enough voiced frames
            if num_voiced > 0.9 * self._ring_buffer.maxlen:
                self._triggered = True
                # Add buffered frames
                for f, s in self._ring_buffer:
                    self._voiced_frames.append(f)
                self._ring_buffer.clear()
        else:
            self._voiced_frames.append(frame)
            self._ring_buffer.append((frame, is_speech))
            num_unvoiced = len([f for f, speech in self._ring_buffer if not speech])
            
            # End triggered state if enough silence
            if num_unvoiced > 0.9 * self._ring_buffer.maxlen:
                self._triggered = False
                # Return the speech segment
                speech_bytes = b''.join(self._voiced_frames)
                self._voiced_frames = []
                self._ring_buffer.clear()
                return speech_bytes
                
        return None
    
    def process_audio(self, audio_bytes: bytes) -> Generator[bytes, None, None]:
        """
        Process audio bytes and yield speech segments.
        
        Args:
            audio_bytes: Raw audio data
            
        Yields:
            Speech segment bytes when detected
        """
        # Split audio into frames
        offset = 0
        while offset + self.frame_size <= len(audio_bytes):
            frame = audio_bytes[offset:offset + self.frame_size]
            result = self.process_frame(frame)
            if result:
                yield result
            offset += self.frame_size
    
    def flush(self) -> Optional[bytes]:
        """
        Flush any remaining buffered speech.
        
        Call this when the audio stream ends to get any remaining speech.
        
        Returns:
            Remaining speech bytes, or None
        """
        if self._voiced_frames:
            speech_bytes = b''.join(self._voiced_frames)
            self._voiced_frames = []
            self._ring_buffer.clear()
            self._triggered = False
            return speech_bytes
        return None


class AudioBuffer:
    """
    Simple audio buffer for accumulating chunks.
    
    Used to collect audio from WebSocket until ready to process.
    """
    
    def __init__(self, max_duration_seconds: float = 30.0, sample_rate: int = 16000):
        """
        Initialize the buffer.
        
        Args:
            max_duration_seconds: Maximum buffer duration
            sample_rate: Audio sample rate
        """
        self.max_duration_seconds = max_duration_seconds
        self.sample_rate = sample_rate
        self.max_bytes = int(max_duration_seconds * sample_rate * 2)  # 16-bit audio
        self._buffer = bytearray()
        
    def append(self, chunk: bytes) -> None:
        """Add audio chunk to buffer."""
        self._buffer.extend(chunk)
        # Trim if exceeds max
        if len(self._buffer) > self.max_bytes:
            self._buffer = self._buffer[-self.max_bytes:]
    
    def get_audio(self) -> bytes:
        """Get all buffered audio."""
        return bytes(self._buffer)
    
    def clear(self) -> None:
        """Clear the buffer."""
        self._buffer.clear()
    
    @property
    def duration_seconds(self) -> float:
        """Get current buffer duration in seconds."""
        return len(self._buffer) / (self.sample_rate * 2)
    
    def __len__(self) -> int:
        return len(self._buffer)





