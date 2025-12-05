import React, { useState, useEffect } from 'react';
import { socket } from '../lib/socket';
import { Volume2, Download, Check, Loader2, AlertCircle } from 'lucide-react';

export default function TTSSettingsTab() {
  const [settings, setSettings] = useState({
    enabled: false,
    available: false,
    voice: null,
    speed: 1.0,
    speaker: 0,
  });
  const [voices, setVoices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [downloadingVoice, setDownloadingVoice] = useState(null);

  useEffect(() => {
    socket.emit('get_tts_settings');
    socket.emit('get_tts_voices');

    socket.on('tts_settings', (data) => {
      setSettings(data);
      setLoading(false);
    });

    socket.on('tts_voices', (data) => {
      setVoices(data.voices || []);
    });

    socket.on('tts_download_progress', (data) => {
      if (data.status === 'complete' || data.status === 'failed') {
        setDownloadingVoice(null);
        // Refresh settings to get the newly selected voice
        if (data.status === 'complete') {
          socket.emit('get_tts_settings');
        }
      }
    });

    return () => {
      socket.off('tts_settings');
      socket.off('tts_voices');
      socket.off('tts_download_progress');
    };
  }, []);

  const updateSettings = (updates) => {
    socket.emit('set_tts_settings', updates);
  };

  const downloadVoice = (voiceKey) => {
    setDownloadingVoice(voiceKey);
    socket.emit('download_tts_voice', { voice: voiceKey });
  };

  const selectVoice = (voiceKey) => {
    const voice = voices.find(v => v.key === voiceKey);
    if (voice && !voice.downloaded) {
      downloadVoice(voiceKey);
    } else {
      updateSettings({ voice: voiceKey });
    }
  };

  // Get current voice info
  const currentVoice = voices.find(v => v.key === settings.voice);

  // Group voices by language
  const voicesByLanguage = voices.reduce((acc, voice) => {
    const lang = voice.language || 'unknown';
    if (!acc[lang]) acc[lang] = [];
    acc[lang].push(voice);
    return acc;
  }, {});

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <Loader2 size={20} className="animate-spin text-[#555]" />
      </div>
    );
  }

  if (!settings.available) {
    return (
      <div className="h-full flex flex-col items-center justify-center p-4 text-center">
        <AlertCircle size={24} className="text-[#ef4444] mb-2" />
        <p className="text-xs text-[#888]">Piper TTS not available</p>
        <p className="text-[10px] text-[#666] mt-1">Install with: pip install piper-tts</p>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col p-4">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="text-[11px] text-[#666] uppercase tracking-wide font-medium">
          Text-to-Speech
        </div>
      </div>

      {/* Settings Section - Fixed height */}
      <div className="space-y-3 flex-shrink-0">
        {/* Enable Toggle */}
        <div className="flex items-center justify-between p-3 rounded border border-[#2b2b2b] bg-[#1a1a1a]">
          <div>
            <div className="text-xs font-medium text-[#e5e5e5]">Voice Output</div>
            <div className="text-[10px] text-[#666] mt-0.5">
              Generate audio for agent responses
            </div>
          </div>
          <button
            onClick={() => updateSettings({ enabled: !settings.enabled })}
            className={`w-10 h-5 rounded-full transition-colors relative ${
              settings.enabled ? 'bg-[#3b82f6]' : 'bg-[#333]'
            }`}
          >
            <div
              className={`absolute top-0.5 w-4 h-4 rounded-full bg-white transition-transform ${
                settings.enabled ? 'translate-x-5' : 'translate-x-0.5'
              }`}
            />
          </button>
        </div>

        {/* Speed Slider */}
        <div className="p-3 rounded border border-[#2b2b2b] bg-[#1a1a1a]">
          <div className="flex items-center justify-between mb-2">
            <div className="text-xs font-medium text-[#e5e5e5]">Speed</div>
            <span className="text-[10px] text-[#888] font-mono">{settings.speed.toFixed(1)}x</span>
          </div>
          <input
            type="range"
            min="0.5"
            max="2.0"
            step="0.1"
            value={settings.speed}
            onChange={(e) => updateSettings({ speed: parseFloat(e.target.value) })}
            className="w-full h-1 bg-[#333] rounded-lg appearance-none cursor-pointer accent-[#3b82f6]"
            disabled={!settings.enabled}
          />
          <div className="flex justify-between text-[9px] text-[#555] mt-1">
            <span>0.5x</span>
            <span>1.0x</span>
            <span>2.0x</span>
          </div>
        </div>

        {/* Current Voice */}
        {currentVoice && (
          <div className="p-3 rounded border border-[#3b82f6]/30 bg-[#3b82f6]/10">
            <div className="text-[10px] text-[#3b82f6] uppercase tracking-wide mb-1">Current Voice</div>
            <div className="text-xs font-medium text-[#e5e5e5]">{currentVoice.name || currentVoice.key}</div>
            <div className="text-[10px] text-[#888] mt-0.5">
              {currentVoice.language} • {currentVoice.quality}
            </div>
            
            {/* Speaker Selection (for multi-speaker voices) */}
            {currentVoice.num_speakers > 1 && (
              <div className="flex items-center justify-between mt-2 pt-2 border-t border-[#3b82f6]/20">
                <div className="text-[10px] text-[#888]">Speaker</div>
                <select
                  value={settings.speaker}
                  onChange={(e) => {
                    e.stopPropagation();
                    updateSettings({ speaker: parseInt(e.target.value) });
                  }}
                  onClick={(e) => e.stopPropagation()}
                  className="bg-[#1a1a1a] border border-[#3b82f6]/30 rounded px-2 py-1 text-xs text-[#e5e5e5] cursor-pointer focus:outline-none focus:border-[#3b82f6] hover:border-[#3b82f6]"
                >
                  {(() => {
                    // Build speaker options from speaker_id_map if available
                    const speakerMap = currentVoice.speaker_id_map;
                    if (speakerMap && Object.keys(speakerMap).length > 0) {
                      // Sort by speaker ID and create options with names
                      return Object.entries(speakerMap)
                        .sort(([, a], [, b]) => a - b)
                        .map(([name, id]) => (
                          <option key={id} value={id}>
                            {name}
                          </option>
                        ));
                    } else {
                      // Fallback to numbered speakers
                      return Array.from({ length: currentVoice.num_speakers }, (_, i) => (
                        <option key={i} value={i}>
                          Speaker {i + 1}
                        </option>
                      ));
                    }
                  })()}
                </select>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Voice Selection - Expandable */}
      <div className="flex-1 flex flex-col min-h-0 mt-4">
        <div className="text-[11px] text-[#666] uppercase tracking-wide font-medium mb-2 flex-shrink-0">
          Available Voices
        </div>
        
        <div className="flex-1 overflow-y-auto space-y-3">
          {Object.entries(voicesByLanguage).map(([language, langVoices]) => (
            <div key={language}>
              <div className="text-[10px] text-[#555] uppercase tracking-wide mb-1 sticky top-0 bg-[#0c0c0c] py-1">
                {language}
              </div>
              <div className="space-y-1">
                {langVoices.map((voice) => {
                  const isSelected = settings.voice === voice.key;
                  const isDownloading = downloadingVoice === voice.key;
                  
                  return (
                    <button
                      key={voice.key}
                      onClick={() => selectVoice(voice.key)}
                      disabled={isDownloading}
                      className={`w-full p-2 rounded border text-left transition-colors ${
                        isSelected
                          ? 'border-[#3b82f6] bg-[#3b82f6]/10'
                          : 'border-[#2b2b2b] bg-[#1a1a1a] hover:border-[#333]'
                      } ${isDownloading ? 'opacity-50' : ''}`}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          {isSelected && <Check size={12} className="text-[#3b82f6]" />}
                          <span className="text-xs text-[#e5e5e5]">
                            {voice.name || voice.key}
                          </span>
                        </div>
                        <div className="flex items-center gap-1">
                          {isDownloading ? (
                            <Loader2 size={12} className="animate-spin text-[#3b82f6]" />
                          ) : !voice.downloaded ? (
                            <Download size={12} className="text-[#666]" />
                          ) : null}
                        </div>
                      </div>
                      <div className="text-[10px] text-[#666] mt-0.5 ml-5">
                        {voice.quality}
                        {voice.num_speakers > 1 && ` • ${voice.num_speakers} speakers`}
                        {!voice.downloaded && ' • Click to download'}
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>
          ))}
          
          {voices.length === 0 && (
            <div className="text-center text-[#555] py-4">
              <Volume2 size={20} className="mx-auto mb-2 opacity-50" />
              <p className="text-xs">No voices available</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
