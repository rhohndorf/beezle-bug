"""
Text-to-speech synthesis using Piper TTS.

This module provides a PiperTTS class that uses the piper-tts
library for fast, local neural text-to-speech synthesis.
"""

import io
import os
import re
import uuid
import wave
import json
import urllib.request
from pathlib import Path
from typing import Optional, Dict, List, Any
from dataclasses import dataclass

from loguru import logger


def clean_text_for_tts(text: str) -> str:
    """
    Clean text for TTS by removing markdown formatting and special characters.
    
    Args:
        text: Raw text potentially containing markdown
        
    Returns:
        Cleaned text suitable for speech synthesis
    """
    if not text:
        return ""
    
    # Remove code blocks (```...```)
    text = re.sub(r'```[\s\S]*?```', '', text)
    
    # Remove inline code (`...`)
    text = re.sub(r'`([^`]+)`', r'\1', text)
    
    # Remove markdown links [text](url) -> text
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    
    # Remove plain URLs
    text = re.sub(r'https?://\S+', '', text)
    
    # Remove markdown headers (# ## ### etc)
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
    
    # Remove bold/italic markers (**, *, __, _)
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)  # **bold**
    text = re.sub(r'\*([^*]+)\*', r'\1', text)      # *italic*
    text = re.sub(r'__([^_]+)__', r'\1', text)      # __bold__
    text = re.sub(r'_([^_]+)_', r'\1', text)        # _italic_
    
    # Remove strikethrough (~~text~~)
    text = re.sub(r'~~([^~]+)~~', r'\1', text)
    
    # Remove blockquotes (> )
    text = re.sub(r'^>\s+', '', text, flags=re.MULTILINE)
    
    # Remove horizontal rules (---, ***, ___)
    text = re.sub(r'^[-*_]{3,}\s*$', '', text, flags=re.MULTILINE)
    
    # Remove list markers (-, *, +, 1., 2., etc)
    text = re.sub(r'^\s*[-*+]\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\s*\d+\.\s+', '', text, flags=re.MULTILINE)
    
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    
    # Remove multiple newlines, replace with single space
    text = re.sub(r'\n+', ' ', text)
    
    # Remove multiple spaces
    text = re.sub(r'\s+', ' ', text)
    
    # Remove special characters that don't speak well
    text = re.sub(r'[•●◦▪▸►]', '', text)
    
    # Replace em dash and en dash with regular dash
    text = text.replace('—', '; ')  # em dash
    text = text.replace('–', '; ')  # en dash
    
    return text.strip()

# Piper TTS imports
try:
    from piper import PiperVoice, SynthesisConfig
    PIPER_AVAILABLE = True
except ImportError:
    PIPER_AVAILABLE = False
    logger.warning("piper-tts not installed. TTS functionality will be disabled.")


# Default voices directory - use environment variable or relative to module
_data_dir = os.environ.get("BEEZLE_DATA_DIR", None)
if _data_dir:
    VOICES_DIR = Path(_data_dir) / "voices"
else:
    VOICES_DIR = Path(__file__).parent.parent.parent.parent / "data" / "voices"

# Hugging Face URL for piper voices
HF_BASE_URL = "https://huggingface.co/rhasspy/piper-voices/resolve/main"
VOICES_JSON_URL = f"{HF_BASE_URL}/voices.json"

# Cache for voice catalog
_voice_catalog_cache: Optional[Dict] = None
_voice_catalog_cache_path: Optional[Path] = None


@dataclass
class VoiceInfo:
    """Information about a voice model."""
    key: str
    name: str
    language: str
    quality: str
    downloaded: bool
    num_speakers: int = 1
    speaker_id_map: Dict[str, int] = None  # Maps speaker name -> speaker ID


def _fetch_voice_catalog(voices_dir: Path) -> Dict:
    """Fetch the voice catalog from Hugging Face or cache."""
    global _voice_catalog_cache, _voice_catalog_cache_path
    
    cache_path = voices_dir / "voices.json"
    _voice_catalog_cache_path = cache_path
    
    # Return cached if available
    if _voice_catalog_cache is not None:
        return _voice_catalog_cache
    
    # Try to load from local cache first
    if cache_path.exists():
        try:
            with open(cache_path, "r") as f:
                _voice_catalog_cache = json.load(f)
                logger.debug(f"Loaded {len(_voice_catalog_cache)} voices from cache")
                return _voice_catalog_cache
        except Exception as e:
            logger.warning(f"Failed to load voice cache: {e}")
    
    # Fetch from Hugging Face
    try:
        logger.info("Fetching voice catalog from Hugging Face...")
        with urllib.request.urlopen(VOICES_JSON_URL, timeout=10) as response:
            _voice_catalog_cache = json.load(response)
        
        # Save to cache
        voices_dir.mkdir(parents=True, exist_ok=True)
        with open(cache_path, "w") as f:
            json.dump(_voice_catalog_cache, f)
        
        logger.info(f"Fetched {len(_voice_catalog_cache)} voices from Hugging Face")
        return _voice_catalog_cache
        
    except Exception as e:
        logger.error(f"Failed to fetch voice catalog: {e}")
        return {}


def refresh_voice_catalog(voices_dir: Path) -> Dict:
    """Force refresh the voice catalog from Hugging Face."""
    global _voice_catalog_cache
    _voice_catalog_cache = None
    
    cache_path = voices_dir / "voices.json"
    if cache_path.exists():
        cache_path.unlink()
    
    return _fetch_voice_catalog(voices_dir)


class PiperTTS:
    """
    Text-to-speech synthesizer using Piper TTS.
    
    Uses local neural TTS models for fast, high-quality synthesis.
    Models are downloaded on-demand and cached locally.
    
    Attributes:
        voices_dir: Directory for storing voice models
        current_voice: Currently loaded voice model name
        speed: Speech rate multiplier (0.5 - 2.0)
        speaker: Speaker ID for multi-speaker models
    """
    
    def __init__(
        self,
        voices_dir: Optional[Path] = None,
        default_voice: str = "en_US-lessac-medium",
        speed: float = 1.0,
        speaker: int = 0
    ):
        """
        Initialize the TTS synthesizer.
        
        Args:
            voices_dir: Directory for voice models (default: data/voices)
            default_voice: Default voice model to use
            speed: Speech rate multiplier (0.5 - 2.0)
            speaker: Speaker ID for multi-speaker models
        """
        self.voices_dir = voices_dir or VOICES_DIR
        self.voices_dir.mkdir(parents=True, exist_ok=True)
        
        self.current_voice_name = default_voice
        self.speed = max(0.5, min(2.0, speed))
        self.speaker = speaker
        
        self._voice: Optional["PiperVoice"] = None
        
        if not PIPER_AVAILABLE:
            logger.error("Piper TTS is not available. Install with: pip install piper-tts")
    
    def _get_voice_catalog(self) -> Dict:
        """Get the voice catalog."""
        return _fetch_voice_catalog(self.voices_dir)
    
    def _get_voice_paths(self, voice_key: str) -> tuple[Path, Path]:
        """Get the model and config paths for a voice."""
        model_path = self.voices_dir / f"{voice_key}.onnx"
        config_path = self.voices_dir / f"{voice_key}.onnx.json"
        return model_path, config_path
    
    def _is_voice_downloaded(self, voice_key: str) -> bool:
        """Check if a voice model is downloaded."""
        model_path, config_path = self._get_voice_paths(voice_key)
        return model_path.exists() and config_path.exists()
    
    def _load_voice(self, voice_name: str) -> bool:
        """
        Load a voice model.
        
        Args:
            voice_name: Name of the voice model to load
            
        Returns:
            True if voice was loaded successfully
        """
        if not PIPER_AVAILABLE:
            return False
        
        if not self._is_voice_downloaded(voice_name):
            logger.warning(f"Voice {voice_name} not downloaded")
            return False
            
        try:
            model_path, config_path = self._get_voice_paths(voice_name)
            
            logger.info(f"Loading Piper voice: {voice_name}")
            self._voice = PiperVoice.load(str(model_path), str(config_path))
            self.current_voice_name = voice_name
            logger.info(f"Piper voice loaded: {voice_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load voice {voice_name}: {e}")
            self._voice = None
            return False
    
    @property
    def voice(self) -> Optional["PiperVoice"]:
        """Get the currently loaded voice, loading it if necessary."""
        if not PIPER_AVAILABLE:
            return None
            
        if self._voice is None and self.current_voice_name:
            if self._is_voice_downloaded(self.current_voice_name):
                self._load_voice(self.current_voice_name)
        return self._voice
    
    def set_voice(self, voice_name: str) -> bool:
        """
        Set the current voice model.
        
        Args:
            voice_name: Name of the voice model to use
            
        Returns:
            True if voice was set successfully
        """
        if voice_name == self.current_voice_name and self._voice is not None:
            return True
        
        if not self._is_voice_downloaded(voice_name):
            logger.warning(f"Voice {voice_name} not downloaded, cannot set")
            return False
            
        self._voice = None  # Clear current voice
        self.current_voice_name = voice_name
        return self._load_voice(voice_name)
    
    def set_speed(self, speed: float) -> None:
        """Set the speech rate multiplier (0.5 - 2.0)."""
        self.speed = max(0.5, min(2.0, speed))
    
    def set_speaker(self, speaker: int) -> None:
        """Set the speaker ID for multi-speaker models."""
        self.speaker = max(0, speaker)
    
    def download_voice(self, voice_key: str, callback: Optional[callable] = None) -> bool:
        """
        Download a voice model from Hugging Face.
        
        Args:
            voice_key: Key of the voice to download
            callback: Optional progress callback function
            
        Returns:
            True if download was successful
        """
        catalog = self._get_voice_catalog()
        
        if voice_key not in catalog:
            logger.error(f"Unknown voice: {voice_key}")
            return False
        
        voice_info = catalog[voice_key]
        model_path, config_path = self._get_voice_paths(voice_key)
        
        try:
            # Get the file paths from the catalog
            # In voices.json, file paths are the keys (not values)
            files = voice_info.get("files", {})
            
            # Find model and config file paths (they are the keys)
            model_file_path = None
            config_file_path = None
            for file_path in files.keys():
                if file_path.endswith(".onnx") and not file_path.endswith(".onnx.json"):
                    model_file_path = file_path
                elif file_path.endswith(".onnx.json"):
                    config_file_path = file_path
            
            if not model_file_path or not config_file_path:
                logger.error(f"Could not find model/config files for {voice_key}")
                return False
            
            # Download model file
            model_url = f"{HF_BASE_URL}/{model_file_path}"
            logger.info(f"Downloading model: {voice_key} from {model_url}")
            urllib.request.urlretrieve(model_url, model_path)
            
            # Download config file
            config_url = f"{HF_BASE_URL}/{config_file_path}"
            logger.info(f"Downloading config: {voice_key}")
            urllib.request.urlretrieve(config_url, config_path)
            
            logger.info(f"Voice downloaded: {voice_key}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to download voice {voice_key}: {e}")
            # Clean up partial downloads
            if model_path.exists():
                model_path.unlink()
            if config_path.exists():
                config_path.unlink()
            return False
    
    def list_voices(self) -> List[VoiceInfo]:
        """
        List available voice models.
        
        Returns:
            List of VoiceInfo objects for available voices
        """
        voices = []
        catalog = self._get_voice_catalog()
        
        for key, info in catalog.items():
            downloaded = self._is_voice_downloaded(key)
            
            # Parse language info
            lang_info = info.get("language", {})
            language = f"{lang_info.get('family', 'unknown')}_{lang_info.get('region', 'XX')}"
            
            # Get quality from key (e.g., "en_US-lessac-medium" -> "medium")
            quality = info.get("quality", "unknown")
            
            # Get speaker count and speaker names
            num_speakers = info.get("num_speakers", 1)
            speaker_id_map = info.get("speaker_id_map", {})
            
            # Get display name
            name = info.get("name", key)
            
            voices.append(VoiceInfo(
                key=key,
                name=name,
                language=language,
                quality=quality,
                downloaded=downloaded,
                num_speakers=num_speakers,
                speaker_id_map=speaker_id_map if speaker_id_map else None,
            ))
        
        # Sort: downloaded first, then by language, then by name
        voices.sort(key=lambda v: (not v.downloaded, v.language, v.key))
        return voices
    
    def list_downloaded_voices(self) -> List[VoiceInfo]:
        """List only downloaded voice models."""
        return [v for v in self.list_voices() if v.downloaded]
    
    def synthesize(self, text: str) -> Optional[bytes]:
        """
        Synthesize speech from text.
        
        Args:
            text: Text to synthesize (markdown and special chars will be cleaned)
            
        Returns:
            WAV audio bytes, or None if synthesis failed
        """
        if not PIPER_AVAILABLE:
            logger.warning("TTS not available")
            return None
        
        if not self.voice:
            logger.warning("No voice loaded")
            return None
        
        if not text or not text.strip():
            return None
        
        # Clean text for TTS (remove markdown, URLs, special chars)
        clean_text = clean_text_for_tts(text)
        
        if not clean_text:
            logger.debug("Text was empty after cleaning")
            return None
            
        try:
            # Create in-memory WAV file
            wav_buffer = io.BytesIO()
            
            with wave.open(wav_buffer, "wb") as wav_file:
                # Create synthesis config with speed (length_scale) and speaker
                length_scale = 1.0 / self.speed
                syn_config = SynthesisConfig(
                    speaker_id=self.speaker if self.voice.config.num_speakers > 1 else None,
                    length_scale=length_scale,
                )
                
                # Synthesize directly to WAV file
                self.voice.synthesize_wav(clean_text, wav_file, syn_config)
            
            wav_buffer.seek(0)
            return wav_buffer.read()
            
        except Exception as e:
            logger.error(f"TTS synthesis failed: {e}")
            return None
    
    def synthesize_to_file(self, text: str, output_dir: Path) -> Optional[Path]:
        """
        Synthesize speech and save to a file.
        
        Args:
            text: Text to synthesize
            output_dir: Directory to save the audio file
            
        Returns:
            Path to the generated audio file, or None if failed
        """
        audio_bytes = self.synthesize(text)
        if audio_bytes is None:
            return None
        
        output_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{uuid.uuid4().hex[:12]}.wav"
        output_path = output_dir / filename
        
        try:
            output_path.write_bytes(audio_bytes)
            logger.debug(f"Audio saved: {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"Failed to save audio: {e}")
            return None
    
    def get_settings(self) -> Dict[str, Any]:
        """Get current TTS settings."""
        return {
            "voice": self.current_voice_name,
            "speed": self.speed,
            "speaker": self.speaker,
            "available": PIPER_AVAILABLE,
        }


# Global singleton instance
_tts: Optional[PiperTTS] = None


def get_tts(
    voices_dir: Optional[Path] = None,
    default_voice: str = "en_US-lessac-medium"
) -> PiperTTS:
    """
    Get or create the global TTS instance.
    
    Args:
        voices_dir: Directory for voice models
        default_voice: Default voice to use
        
    Returns:
        PiperTTS instance
    """
    global _tts
    if _tts is None:
        _tts = PiperTTS(voices_dir=voices_dir, default_voice=default_voice)
    return _tts
