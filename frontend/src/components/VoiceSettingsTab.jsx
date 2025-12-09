import React, { useState, useEffect } from 'react';
import { socket } from '../lib/socket';
import { Volume2, Download, Check, Loader2, AlertCircle, Mic, Plus, X } from 'lucide-react';

export default function VoiceSettingsTab({ isDeployed = false }) {
  // TTS State
  const [ttsSettings, setTtsSettings] = useState({
    enabled: false,
    available: false,
    voice: null,
    speed: 1.0,
    speaker: 0,
  });
  const [voices, setVoices] = useState([]);
  const [downloadingVoice, setDownloadingVoice] = useState(null);
  
  // STT State
  const [sttSettings, setSttSettings] = useState({
    enabled: false,
    device_id: null,
    device_label: null,
    wake_words: ['hey beezle', 'ok beezle'],
    stop_words: ['stop listening', 'goodbye', "that's all"],
    max_duration: 30.0,
  });
  const [microphones, setMicrophones] = useState([]);
  const [newWakeWord, setNewWakeWord] = useState('');
  const [newStopWord, setNewStopWord] = useState('');
  const [skipWakeWord, setSkipWakeWord] = useState(false); // Default false on desktop
  
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const requestSettings = () => {
      // Request TTS settings
      socket.emit('get_tts_settings');
      socket.emit('get_tts_voices');
      // Request STT settings
      socket.emit('get_stt_settings');
    };
    
    // Request settings immediately
    requestSettings();
    
    // Fallback timeout - stop loading after 5s even if no response
    const timeout = setTimeout(() => {
      setLoading(false);
    }, 5000);

    // TTS listeners
    const handleTtsSettings = (data) => {
      setTtsSettings(data);
      setLoading(false);
      clearTimeout(timeout);
    };
    
    const handleTtsVoices = (data) => {
      setVoices(data.voices || []);
    };
    
    const handleTtsDownloadProgress = (data) => {
      if (data.status === 'complete' || data.status === 'failed') {
        setDownloadingVoice(null);
        if (data.status === 'complete') {
          socket.emit('get_tts_settings');
        }
      }
    };
    
    // STT listeners
    const handleSttSettings = (data) => {
      setSttSettings(data);
    };
    
    // Re-request settings on reconnect
    const handleConnect = () => {
      requestSettings();
    };
    
    // Re-request settings on project load
    const handleProjectLoaded = () => {
      socket.emit('get_stt_settings');
    };

    socket.on('tts_settings', handleTtsSettings);
    socket.on('tts_voices', handleTtsVoices);
    socket.on('tts_download_progress', handleTtsDownloadProgress);
    socket.on('stt_settings', handleSttSettings);
    socket.on('connect', handleConnect);
    socket.on('project_loaded', handleProjectLoaded);

    // Get available microphones
    loadMicrophones();

    return () => {
      socket.off('tts_settings', handleTtsSettings);
      socket.off('tts_voices', handleTtsVoices);
      socket.off('tts_download_progress', handleTtsDownloadProgress);
      socket.off('stt_settings', handleSttSettings);
      socket.off('connect', handleConnect);
      socket.off('project_loaded', handleProjectLoaded);
    };
  }, []);
  
  const loadMicrophones = async () => {
    try {
      // Request permission first
      await navigator.mediaDevices.getUserMedia({ audio: true });
      const devices = await navigator.mediaDevices.enumerateDevices();
      const audioInputs = devices.filter(d => d.kind === 'audioinput');
      setMicrophones(audioInputs);
    } catch (err) {
      console.error('Could not access microphones:', err);
    }
  };

  const updateTtsSettings = (updates) => {
    socket.emit('set_tts_settings', updates);
  };
  
  const updateSttSettings = (updates) => {
    const newSettings = { ...sttSettings, ...updates };
    setSttSettings(newSettings);
    socket.emit('set_stt_settings', updates);
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
      updateTtsSettings({ voice: voiceKey });
    }
  };
  
  const selectMicrophone = (deviceId) => {
    const device = microphones.find(m => m.deviceId === deviceId);
    updateSttSettings({
      device_id: deviceId,
      device_label: device?.label || null,
    });
  };
  
  const addWakeWord = () => {
    if (newWakeWord.trim() && !sttSettings.wake_words.includes(newWakeWord.trim().toLowerCase())) {
      const updated = [...sttSettings.wake_words, newWakeWord.trim().toLowerCase()];
      updateSttSettings({ wake_words: updated });
      setNewWakeWord('');
    }
  };
  
  const removeWakeWord = (word) => {
    if (sttSettings.wake_words.length > 1) {
      const updated = sttSettings.wake_words.filter(w => w !== word);
      updateSttSettings({ wake_words: updated });
    }
  };
  
  const addStopWord = () => {
    if (newStopWord.trim() && !sttSettings.stop_words.includes(newStopWord.trim().toLowerCase())) {
      const updated = [...sttSettings.stop_words, newStopWord.trim().toLowerCase()];
      updateSttSettings({ stop_words: updated });
      setNewStopWord('');
    }
  };
  
  const removeStopWord = (word) => {
    if (sttSettings.stop_words.length > 1) {
      const updated = sttSettings.stop_words.filter(w => w !== word);
      updateSttSettings({ stop_words: updated });
    }
  };

  // Get current voice info
  const currentVoice = voices.find(v => v.key === ttsSettings.voice);

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

  return (
    <div className="h-full flex flex-col p-4 overflow-y-auto">
      {/* Voice Input Section */}
      <div className="mb-6">
        <div className="text-[11px] text-[#666] uppercase tracking-wide font-medium mb-3">
          Voice Input (STT)
        </div>
        
        <div className="space-y-3">
          {/* Enable Toggle */}
          <div className={`flex items-center justify-between p-3 rounded border bg-[#1a1a1a] ${
            !isDeployed ? 'border-[#2b2b2b] opacity-50' : 'border-[#2b2b2b]'
          }`}>
            <div>
              <div className="text-xs font-medium text-[#e5e5e5]">Continuous Listening</div>
              <div className="text-[10px] text-[#666] mt-0.5">
                {!isDeployed 
                  ? 'Deploy a project to enable voice input'
                  : 'Listen for wake words to activate voice input'
                }
              </div>
            </div>
            <button
              onClick={() => isDeployed && updateSttSettings({ enabled: !sttSettings.enabled })}
              disabled={!isDeployed}
              className={`w-10 h-5 rounded-full transition-colors relative ${
                sttSettings.enabled && isDeployed ? 'bg-[#22c55e]' : 'bg-[#333]'
              } ${!isDeployed ? 'cursor-not-allowed' : 'cursor-pointer'}`}
            >
              <div
                className={`absolute top-0.5 w-4 h-4 rounded-full bg-white transition-transform ${
                  sttSettings.enabled && isDeployed ? 'translate-x-5' : 'translate-x-0.5'
                }`}
              />
            </button>
          </div>
          
          {/* Microphone Selection */}
          <div className="p-3 rounded border border-[#2b2b2b] bg-[#1a1a1a]">
            <div className="flex items-center gap-2 mb-2">
              <Mic size={14} className="text-[#888]" />
              <div className="text-xs font-medium text-[#e5e5e5]">Microphone</div>
            </div>
            <select
              value={sttSettings.device_id || ''}
              onChange={(e) => selectMicrophone(e.target.value)}
              className="w-full bg-[#0c0c0c] border border-[#333] rounded px-2 py-1.5 text-xs text-[#e5e5e5] focus:outline-none focus:border-[#22c55e]"
            >
              <option value="">Default microphone</option>
              {microphones.map((mic) => (
                <option key={mic.deviceId} value={mic.deviceId}>
                  {mic.label || `Microphone ${mic.deviceId.slice(0, 8)}`}
                </option>
              ))}
            </select>
            {microphones.length === 0 && (
              <div className="text-[10px] text-[#ef4444] mt-1">
                No microphones found. Grant permission to access.
              </div>
            )}
          </div>
          
          {/* Skip Wake Word Toggle */}
          <div className="flex items-center justify-between p-3 rounded border border-[#2b2b2b] bg-[#1a1a1a]">
            <div>
              <div className="text-xs font-medium text-[#e5e5e5]">Skip Wake Word</div>
              <div className="text-[10px] text-[#666] mt-0.5">
                Go directly to active listening without wake word
              </div>
            </div>
            <button
              onClick={() => {
                setSkipWakeWord(!skipWakeWord);
                // Emit to socket so Chat.jsx can access it
                socket.emit('set_skip_wake_word', { enabled: !skipWakeWord });
              }}
              className={`w-10 h-5 rounded-full transition-colors relative cursor-pointer ${
                skipWakeWord ? 'bg-[#22c55e]' : 'bg-[#333]'
              }`}
            >
              <div
                className={`absolute top-0.5 w-4 h-4 rounded-full bg-white transition-transform ${
                  skipWakeWord ? 'translate-x-5' : 'translate-x-0.5'
                }`}
              />
            </button>
          </div>
          
          {/* Wake Words */}
          <div className={`p-3 rounded border border-[#2b2b2b] bg-[#1a1a1a] ${skipWakeWord ? 'opacity-50' : ''}`}>
            <div className="text-xs font-medium text-[#e5e5e5] mb-2">Wake Words</div>
            <div className="text-[10px] text-[#666] mb-2">
              Say any of these to start sending messages
            </div>
            <div className="flex flex-wrap gap-1 mb-2">
              {sttSettings.wake_words.map((word) => (
                <span
                  key={word}
                  className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-[#22c55e]/20 text-[#22c55e] text-[10px]"
                >
                  "{word}"
                  {sttSettings.wake_words.length > 1 && (
                    <button
                      onClick={() => removeWakeWord(word)}
                      className="hover:text-white"
                    >
                      <X size={10} />
                    </button>
                  )}
                </span>
              ))}
            </div>
            <div className="flex gap-1">
              <input
                type="text"
                value={newWakeWord}
                onChange={(e) => setNewWakeWord(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && addWakeWord()}
                placeholder="Add wake word..."
                className="flex-1 bg-[#0c0c0c] border border-[#333] rounded px-2 py-1 text-xs text-[#e5e5e5] placeholder-[#555] focus:outline-none focus:border-[#22c55e]"
              />
              <button
                onClick={addWakeWord}
                className="px-2 py-1 rounded bg-[#22c55e]/20 text-[#22c55e] hover:bg-[#22c55e]/30"
              >
                <Plus size={14} />
              </button>
            </div>
          </div>
          
          {/* Stop Words */}
          <div className={`p-3 rounded border border-[#2b2b2b] bg-[#1a1a1a] ${skipWakeWord ? 'opacity-50' : ''}`}>
            <div className="text-xs font-medium text-[#e5e5e5] mb-2">Stop Words</div>
            <div className="text-[10px] text-[#666] mb-2">
              Say any of these to stop sending messages
            </div>
            <div className="flex flex-wrap gap-1 mb-2">
              {sttSettings.stop_words.map((word) => (
                <span
                  key={word}
                  className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-[#ef4444]/20 text-[#ef4444] text-[10px]"
                >
                  "{word}"
                  {sttSettings.stop_words.length > 1 && (
                    <button
                      onClick={() => removeStopWord(word)}
                      className="hover:text-white"
                    >
                      <X size={10} />
                    </button>
                  )}
                </span>
              ))}
            </div>
            <div className="flex gap-1">
              <input
                type="text"
                value={newStopWord}
                onChange={(e) => setNewStopWord(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && addStopWord()}
                placeholder="Add stop word..."
                className="flex-1 bg-[#0c0c0c] border border-[#333] rounded px-2 py-1 text-xs text-[#e5e5e5] placeholder-[#555] focus:outline-none focus:border-[#ef4444]"
              />
              <button
                onClick={addStopWord}
                className="px-2 py-1 rounded bg-[#ef4444]/20 text-[#ef4444] hover:bg-[#ef4444]/30"
              >
                <Plus size={14} />
              </button>
            </div>
          </div>
          
          {/* Max Recording Duration */}
          <div className="p-3 rounded border border-[#2b2b2b] bg-[#1a1a1a]">
            <div className="flex items-center justify-between mb-2">
              <div className="text-xs font-medium text-[#e5e5e5]">Max Recording Duration</div>
              <span className="text-[10px] text-[#888] font-mono">{sttSettings.max_duration || 30}s</span>
            </div>
            <input
              type="range"
              min="5"
              max="60"
              step="5"
              value={sttSettings.max_duration || 30}
              onChange={(e) => updateSttSettings({ max_duration: parseFloat(e.target.value) })}
              className="w-full h-1 bg-[#333] rounded-lg appearance-none cursor-pointer accent-[#22c55e]"
            />
            <div className="flex justify-between text-[9px] text-[#555] mt-1">
              <span>5s</span>
              <span>30s</span>
              <span>60s</span>
            </div>
            <div className="text-[10px] text-[#666] mt-2">
              Maximum length of a single voice message
            </div>
          </div>
        </div>
      </div>
      
      {/* Divider */}
      <div className="border-t border-[#2b2b2b] my-2" />

      {/* Text-to-Speech Section */}
      <div className="mb-4">
        <div className="text-[11px] text-[#666] uppercase tracking-wide font-medium mb-3">
          Voice Output (TTS)
        </div>

        {!ttsSettings.available ? (
          <div className="flex flex-col items-center justify-center p-4 text-center border border-[#2b2b2b] rounded bg-[#1a1a1a]">
            <AlertCircle size={24} className="text-[#ef4444] mb-2" />
            <p className="text-xs text-[#888]">Piper TTS not available</p>
            <p className="text-[10px] text-[#666] mt-1">Install with: pip install piper-tts</p>
          </div>
        ) : (
          <div className="space-y-3">
            {/* Enable Toggle */}
            <div className="flex items-center justify-between p-3 rounded border border-[#2b2b2b] bg-[#1a1a1a]">
              <div>
                <div className="text-xs font-medium text-[#e5e5e5]">Voice Output</div>
                <div className="text-[10px] text-[#666] mt-0.5">
                  Generate audio for agent responses
                </div>
              </div>
              <button
                onClick={() => updateTtsSettings({ enabled: !ttsSettings.enabled })}
                className={`w-10 h-5 rounded-full transition-colors relative ${
                  ttsSettings.enabled ? 'bg-[#3b82f6]' : 'bg-[#333]'
                }`}
              >
                <div
                  className={`absolute top-0.5 w-4 h-4 rounded-full bg-white transition-transform ${
                    ttsSettings.enabled ? 'translate-x-5' : 'translate-x-0.5'
                  }`}
                />
              </button>
            </div>

            {/* Speed Slider */}
            <div className="p-3 rounded border border-[#2b2b2b] bg-[#1a1a1a]">
              <div className="flex items-center justify-between mb-2">
                <div className="text-xs font-medium text-[#e5e5e5]">Speed</div>
                <span className="text-[10px] text-[#888] font-mono">{ttsSettings.speed.toFixed(1)}x</span>
              </div>
              <input
                type="range"
                min="0.5"
                max="2.0"
                step="0.1"
                value={ttsSettings.speed}
                onChange={(e) => updateTtsSettings({ speed: parseFloat(e.target.value) })}
                className="w-full h-1 bg-[#333] rounded-lg appearance-none cursor-pointer accent-[#3b82f6]"
                disabled={!ttsSettings.enabled}
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
                      value={ttsSettings.speaker}
                      onChange={(e) => {
                        e.stopPropagation();
                        updateTtsSettings({ speaker: parseInt(e.target.value) });
                      }}
                      onClick={(e) => e.stopPropagation()}
                      className="bg-[#1a1a1a] border border-[#3b82f6]/30 rounded px-2 py-1 text-xs text-[#e5e5e5] cursor-pointer focus:outline-none focus:border-[#3b82f6] hover:border-[#3b82f6]"
                    >
                      {(() => {
                        const speakerMap = currentVoice.speaker_id_map;
                        if (speakerMap && Object.keys(speakerMap).length > 0) {
                          return Object.entries(speakerMap)
                            .sort(([, a], [, b]) => a - b)
                            .map(([name, id]) => (
                              <option key={id} value={id}>
                                {name}
                              </option>
                            ));
                        } else {
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

            {/* Voice Selection */}
            <div>
              <div className="text-[10px] text-[#555] uppercase tracking-wide mb-2">
                Available Voices
              </div>
              
              <div className="space-y-3 max-h-48 overflow-y-auto">
                {Object.entries(voicesByLanguage).map(([language, langVoices]) => (
                  <div key={language}>
                    <div className="text-[10px] text-[#555] uppercase tracking-wide mb-1 sticky top-0 bg-[#0c0c0c] py-1">
                      {language}
                    </div>
                    <div className="space-y-1">
                      {langVoices.map((voice) => {
                        const isSelected = ttsSettings.voice === voice.key;
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
        )}
      </div>
    </div>
  );
}

