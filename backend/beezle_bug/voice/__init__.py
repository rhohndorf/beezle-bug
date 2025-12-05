"""
Voice processing module for Beezle Bug.

Provides speech-to-text transcription using faster-whisper,
voice activity detection using webrtcvad, and text-to-speech
synthesis using Piper TTS.
"""

from beezle_bug.voice.transcriber import Transcriber
from beezle_bug.voice.vad import VoiceActivityDetector
from beezle_bug.voice.tts import PiperTTS, get_tts, VoiceInfo

__all__ = ["Transcriber", "VoiceActivityDetector", "PiperTTS", "get_tts", "VoiceInfo"]



