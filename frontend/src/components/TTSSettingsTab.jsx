/**
 * TTS Settings Tab Component
 * 
 * Provides controls for text-to-speech settings including:
 * - Enable/disable TTS
 * - Voice selection
 * - Model loading status
 */

import React from 'react';
import { Volume2, VolumeX, Loader2, Download, Check } from 'lucide-react';
import { useTTSContext, VOICES } from '../context/TTSContext';

export default function TTSSettingsTab() {
  const {
    isLoading,
    isModelLoaded,
    loadingProgress,
    voice,
    enabled,
    autoSpeak,
    device,
    error,
    loadModel,
    setVoice,
    setEnabled,
    setAutoSpeak,
  } = useTTSContext();

  // Group voices by accent
  const voicesByAccent = Object.entries(VOICES).reduce((acc, [id, info]) => {
    if (!acc[info.accent]) {
      acc[info.accent] = [];
    }
    acc[info.accent].push({ id, ...info });
    return acc;
  }, {});

  return (
    <div className="p-4 space-y-6 overflow-y-auto h-full">
      {/* Header */}
      <div className="flex items-center gap-2 text-[#888] text-xs uppercase tracking-wide font-medium">
        <Volume2 size={14} />
        Text-to-Speech
      </div>

      {/* Enable/Disable Toggle */}
      <div className="space-y-2">
        <label className="text-[11px] text-[#666] uppercase tracking-wide">Enable TTS</label>
        <div className="flex items-center justify-between">
          <span className="text-[13px] text-[#888]">
            {enabled ? 'Voice output enabled' : 'Voice output disabled'}
          </span>
          <button
            onClick={() => setEnabled(!enabled)}
            className={`relative w-10 h-5 rounded-full transition-colors ${
              enabled ? 'bg-[#3b82f6]' : 'bg-[#2b2b2b]'
            }`}
          >
            <span
              className={`absolute top-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform ${
                enabled ? 'translate-x-5' : 'translate-x-0.5'
              }`}
            />
          </button>
        </div>
      </div>

      {/* Auto-speak Toggle */}
      <div className="space-y-2">
        <label className="text-[11px] text-[#666] uppercase tracking-wide">Auto-speak</label>
        <div className="flex items-center justify-between">
          <span className="text-[13px] text-[#888]">
            {autoSpeak ? 'Read new messages aloud' : 'Click to speak'}
          </span>
          <button
            onClick={() => setAutoSpeak(!autoSpeak)}
            disabled={!enabled}
            className={`relative w-10 h-5 rounded-full transition-colors disabled:opacity-50 ${
              autoSpeak && enabled ? 'bg-[#3b82f6]' : 'bg-[#2b2b2b]'
            }`}
          >
            <span
              className={`absolute top-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform ${
                autoSpeak && enabled ? 'translate-x-5' : 'translate-x-0.5'
              }`}
            />
          </button>
        </div>
      </div>

      {/* Model Status */}
      <div className="space-y-2">
        <label className="text-[11px] text-[#666] uppercase tracking-wide">Model Status</label>
        <div className="flex items-center gap-3">
          {isModelLoaded ? (
            <>
              <div className="flex items-center gap-2 text-[#22c55e]">
                <Check size={14} />
                <span className="text-[13px]">Model loaded</span>
                <span className={`text-[10px] px-1.5 py-0.5 rounded ${
                  device === 'webgpu' 
                    ? 'bg-[#22c55e]/20 text-[#22c55e]' 
                    : 'bg-[#888]/20 text-[#888]'
                }`}>
                  {device === 'webgpu' ? 'GPU' : 'CPU'}
                </span>
              </div>
            </>
          ) : isLoading ? (
            <>
              <Loader2 size={14} className="animate-spin text-[#3b82f6]" />
              <span className="text-[13px] text-[#888]">
                Loading model... {loadingProgress}%
              </span>
            </>
          ) : (
            <>
              <button
                onClick={loadModel}
                disabled={!enabled}
                className="flex items-center gap-2 px-3 py-1.5 bg-[#1a1a1a] border border-[#2b2b2b] rounded text-[12px] text-[#888] hover:text-[#e5e5e5] hover:border-[#3b82f6] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Download size={12} />
                Load Model (~80MB)
              </button>
              <span className="text-[11px] text-[#555]">
                Model loads on first use
              </span>
            </>
          )}
        </div>
        {error && (
          <div className="text-[12px] text-red-400 mt-1">
            Error: {error}
          </div>
        )}
      </div>

      {/* Voice Selection */}
      <div className="space-y-2">
        <label className="text-[11px] text-[#666] uppercase tracking-wide">Voice</label>
        <div className="space-y-3">
          {Object.entries(voicesByAccent).map(([accent, voices]) => (
            <div key={accent}>
              <div className="text-[10px] text-[#555] uppercase tracking-wide mb-1.5">
                {accent} English
              </div>
              <div className="grid grid-cols-2 gap-1">
                {voices.map(({ id, name, gender }) => (
                  <button
                    key={id}
                    onClick={() => setVoice(id)}
                    disabled={!enabled}
                    className={`px-2 py-1.5 text-[12px] rounded text-left transition-colors ${
                      voice === id
                        ? 'bg-[#3b82f6] text-white'
                        : 'bg-[#1a1a1a] text-[#888] hover:bg-[#252525] hover:text-[#e5e5e5] disabled:opacity-50 disabled:cursor-not-allowed'
                    }`}
                  >
                    <span className="font-medium">{name}</span>
                    <span className="text-[10px] opacity-70 ml-1">
                      {gender === 'Male' ? '♂' : '♀'}
                    </span>
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Info */}
      <div className="pt-4 border-t border-[#2b2b2b]">
        <div className="text-[11px] text-[#555] space-y-1">
          <p>
            <span className="text-[#666]">Powered by</span>{' '}
            <a 
              href="https://github.com/hexgrad/kokoro" 
              target="_blank" 
              rel="noopener noreferrer"
              className="text-[#3b82f6] hover:underline"
            >
              Kokoro TTS
            </a>
          </p>
          <p>
            Runs 100% locally in your browser using Transformers.js
          </p>
        </div>
      </div>
    </div>
  );
}

