/**
 * TTS Hook using kokoro-js
 * 
 * Provides text-to-speech functionality using the Kokoro TTS model
 * running locally in the browser via Transformers.js
 * 
 * The model is cached in IndexedDB by Transformers.js automatically,
 * so subsequent page loads won't re-download the model.
 */

import { useState, useRef, useCallback } from 'react';

// Available voices from Kokoro TTS
export const VOICES = {
  // American English
  'af_heart': { name: 'Heart', accent: 'American', gender: 'Female' },
  'af_alloy': { name: 'Alloy', accent: 'American', gender: 'Female' },
  'af_aoede': { name: 'Aoede', accent: 'American', gender: 'Female' },
  'af_bella': { name: 'Bella', accent: 'American', gender: 'Female' },
  'af_jessica': { name: 'Jessica', accent: 'American', gender: 'Female' },
  'af_kore': { name: 'Kore', accent: 'American', gender: 'Female' },
  'af_nicole': { name: 'Nicole', accent: 'American', gender: 'Female' },
  'af_nova': { name: 'Nova', accent: 'American', gender: 'Female' },
  'af_river': { name: 'River', accent: 'American', gender: 'Female' },
  'af_sarah': { name: 'Sarah', accent: 'American', gender: 'Female' },
  'af_sky': { name: 'Sky', accent: 'American', gender: 'Female' },
  'am_adam': { name: 'Adam', accent: 'American', gender: 'Male' },
  'am_echo': { name: 'Echo', accent: 'American', gender: 'Male' },
  'am_eric': { name: 'Eric', accent: 'American', gender: 'Male' },
  'am_fenrir': { name: 'Fenrir', accent: 'American', gender: 'Male' },
  'am_liam': { name: 'Liam', accent: 'American', gender: 'Male' },
  'am_michael': { name: 'Michael', accent: 'American', gender: 'Male' },
  'am_onyx': { name: 'Onyx', accent: 'American', gender: 'Male' },
  // British English
  'bf_alice': { name: 'Alice', accent: 'British', gender: 'Female' },
  'bf_emma': { name: 'Emma', accent: 'British', gender: 'Female' },
  'bf_isabella': { name: 'Isabella', accent: 'British', gender: 'Female' },
  'bf_lily': { name: 'Lily', accent: 'British', gender: 'Female' },
  'bm_daniel': { name: 'Daniel', accent: 'British', gender: 'Male' },
  'bm_fable': { name: 'Fable', accent: 'British', gender: 'Male' },
  'bm_george': { name: 'George', accent: 'British', gender: 'Male' },
  'bm_lewis': { name: 'Lewis', accent: 'British', gender: 'Male' },
};

// Default voice
const DEFAULT_VOICE = 'af_heart';

// Singleton TTS instance to persist across hot reloads
let globalTTS = null;
let globalAudioContext = null;
let globalDevice = null; // 'webgpu' or 'wasm'

/**
 * Get or create the AudioContext (handles closed state)
 */
function getAudioContext() {
  if (!globalAudioContext || globalAudioContext.state === 'closed') {
    globalAudioContext = new (window.AudioContext || window.webkitAudioContext)();
  }
  return globalAudioContext;
}

/**
 * Custom hook for text-to-speech using Kokoro
 */
export function useTTS() {
  const [isLoading, setIsLoading] = useState(false);
  const [isModelLoaded, setIsModelLoaded] = useState(!!globalTTS);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [error, setError] = useState(null);
  const [loadingProgress, setLoadingProgress] = useState(globalTTS ? 100 : 0);
  const [voice, setVoice] = useState(DEFAULT_VOICE);
  const [enabled, setEnabled] = useState(true);
  const [autoSpeak, setAutoSpeak] = useState(false);
  const [device, setDevice] = useState(globalDevice); // 'webgpu' or 'wasm'
  
  const currentSourceRef = useRef(null);

  /**
   * Initialize the TTS model
   */
  const loadModel = useCallback(async () => {
    // If already loaded globally, just update state
    if (globalTTS) {
      setIsModelLoaded(true);
      setLoadingProgress(100);
      return;
    }
    
    if (isLoading) return;
    
    setIsLoading(true);
    setError(null);
    setLoadingProgress(0);
    
    try {
      // Dynamic import to avoid loading the model until needed
      const { KokoroTTS } = await import('kokoro-js');
      
      // Check if WebGPU is available for hardware acceleration
      let detectedDevice = 'wasm'; // Default to CPU (WebAssembly)
      if (navigator.gpu) {
        try {
          const adapter = await navigator.gpu.requestAdapter();
          if (adapter) {
            detectedDevice = 'webgpu';
            console.log('WebGPU available - using GPU acceleration');
          }
        } catch (e) {
          console.log('WebGPU not available, falling back to CPU');
        }
      } else {
        console.log('WebGPU not supported, using CPU');
      }
      globalDevice = detectedDevice;
      setDevice(detectedDevice);
      
      // Initialize with progress callback
      // The model is automatically cached in IndexedDB by Transformers.js
      const tts = await KokoroTTS.from_pretrained('onnx-community/Kokoro-82M-v1.0-ONNX', {
        dtype: detectedDevice === 'webgpu' ? 'fp32' : 'q8', // Use fp32 for GPU, q8 for CPU
        device: detectedDevice,
        progress_callback: (progress) => {
          if (progress.status === 'progress' && progress.progress !== undefined) {
            setLoadingProgress(Math.round(progress.progress));
          }
        }
      });
      
      globalTTS = tts;
      setIsModelLoaded(true);
      setLoadingProgress(100);
      console.log('Kokoro TTS model loaded successfully');
    } catch (err) {
      console.error('Failed to load TTS model:', err);
      setError(err.message || 'Failed to load TTS model');
    } finally {
      setIsLoading(false);
    }
  }, [isLoading]);

  /**
   * Generate and play speech from text
   */
  const speak = useCallback(async (text, options = {}) => {
    if (!enabled) return;
    if (!text || typeof text !== 'string' || text.trim().length === 0) return;
    
    // Load model if not already loaded
    if (!globalTTS) {
      await loadModel();
    }
    
    if (!globalTTS) {
      console.error('TTS model not available');
      return;
    }
    
    // Stop any current playback
    if (currentSourceRef.current) {
      try {
        currentSourceRef.current.stop();
      } catch (e) {
        // Ignore errors if already stopped
      }
      currentSourceRef.current = null;
    }
    
    setIsSpeaking(true);
    setError(null);
    
    try {
      const selectedVoice = options.voice || voice;
      
      // Generate audio
      const audio = await globalTTS.generate(text, {
        voice: selectedVoice,
      });
      
      // Get AudioContext (creates new one if closed)
      const audioContext = getAudioContext();
      
      // Resume if suspended (browser autoplay policy)
      if (audioContext.state === 'suspended') {
        await audioContext.resume();
      }
      
      // Create audio buffer from Float32Array
      const sampleRate = audio.sampling_rate || 24000;
      const audioData = audio.audio;
      const audioBuffer = audioContext.createBuffer(1, audioData.length, sampleRate);
      audioBuffer.getChannelData(0).set(audioData);
      
      // Create and connect source
      const source = audioContext.createBufferSource();
      source.buffer = audioBuffer;
      source.connect(audioContext.destination);
      
      currentSourceRef.current = source;
      
      // Handle playback end
      source.onended = () => {
        setIsSpeaking(false);
        currentSourceRef.current = null;
      };
      
      source.start(0);
      console.log('TTS playing audio...');
    } catch (err) {
      console.error('TTS generation failed:', err);
      setError(err.message || 'Speech generation failed');
      setIsSpeaking(false);
    }
  }, [enabled, loadModel, voice]);

  /**
   * Stream speech generation (for longer texts)
   */
  const speakStream = useCallback(async (text, options = {}) => {
    if (!enabled) return;
    if (!text || typeof text !== 'string' || text.trim().length === 0) return;
    
    // Load model if not already loaded
    if (!globalTTS) {
      await loadModel();
    }
    
    if (!globalTTS) {
      console.error('TTS model not available');
      return;
    }
    
    // Stop any current playback
    if (currentSourceRef.current) {
      try {
        currentSourceRef.current.stop();
      } catch (e) {
        // Ignore errors if already stopped
      }
      currentSourceRef.current = null;
    }
    
    setIsSpeaking(true);
    setError(null);
    
    try {
      const selectedVoice = options.voice || voice;
      const audioContext = getAudioContext();
      
      if (audioContext.state === 'suspended') {
        await audioContext.resume();
      }
      
      // Use streaming API for longer texts
      const stream = await globalTTS.stream(text, {
        voice: selectedVoice,
      });
      
      let isFirst = true;
      for await (const chunk of stream) {
        if (!currentSourceRef.current && !isFirst) {
          // Playback was stopped
          break;
        }
        isFirst = false;
        
        const sampleRate = chunk.sampling_rate || 24000;
        const audioData = chunk.audio;
        const audioBuffer = audioContext.createBuffer(1, audioData.length, sampleRate);
        audioBuffer.getChannelData(0).set(audioData);
        
        const source = audioContext.createBufferSource();
        source.buffer = audioBuffer;
        source.connect(audioContext.destination);
        currentSourceRef.current = source;
        source.start(0);
      }
      
      setIsSpeaking(false);
    } catch (err) {
      console.error('TTS streaming failed:', err);
      setError(err.message || 'Speech streaming failed');
      setIsSpeaking(false);
    }
  }, [enabled, loadModel, voice]);

  /**
   * Stop current playback
   */
  const stop = useCallback(() => {
    if (currentSourceRef.current) {
      try {
        currentSourceRef.current.stop();
      } catch (e) {
        // Ignore errors if already stopped
      }
      currentSourceRef.current = null;
    }
    setIsSpeaking(false);
  }, []);

  /**
   * Toggle TTS enabled state
   */
  const toggle = useCallback(() => {
    setEnabled(prev => !prev);
  }, []);

  return {
    // State
    isLoading,
    isModelLoaded,
    isSpeaking,
    error,
    loadingProgress,
    voice,
    enabled,
    autoSpeak,
    device, // 'webgpu' (GPU) or 'wasm' (CPU)
    voices: VOICES,
    
    // Actions
    loadModel,
    speak,
    speakStream,
    stop,
    setVoice,
    setEnabled,
    setAutoSpeak,
    toggle,
  };
}

export default useTTS;
