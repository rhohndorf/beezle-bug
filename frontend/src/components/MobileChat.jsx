import React, { useState, useEffect, useRef, useCallback } from 'react';
import { socket } from '../lib/socket';
import { Send, Volume2, VolumeX, Square, Mic, MicOff, Wifi, WifiOff } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

// Media URL detection patterns
const IMAGE_PATTERN = /\.(jpg|jpeg|png|gif|webp|svg)(\?.*)?$/i;
const VIDEO_PATTERN = /\.(mp4|webm|mov)(\?.*)?$/i;
const YOUTUBE_PATTERN = /(?:youtube\.com\/(?:watch\?v=|embed\/|shorts\/)|youtu\.be\/)([a-zA-Z0-9_-]{11})/;
const VIMEO_PATTERN = /vimeo\.com\/(\d+)/;

// Helper to render embedded media from a URL string
const renderMediaEmbed = (url) => {
  // Check for YouTube URL
  const ytMatch = url.match(YOUTUBE_PATTERN);
  if (ytMatch) {
    return (
      <div className="my-2 aspect-video max-w-full">
        <iframe
          src={`https://www.youtube.com/embed/${ytMatch[1]}`}
          title="YouTube video"
          className="w-full h-full rounded-lg"
          frameBorder="0"
          allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
          allowFullScreen
        />
      </div>
    );
  }
  
  // Check for Vimeo URL
  const vimeoMatch = url.match(VIMEO_PATTERN);
  if (vimeoMatch) {
    return (
      <div className="my-2 aspect-video max-w-full">
        <iframe
          src={`https://player.vimeo.com/video/${vimeoMatch[1]}`}
          title="Vimeo video"
          className="w-full h-full rounded-lg"
          frameBorder="0"
          allow="autoplay; fullscreen; picture-in-picture"
          allowFullScreen
        />
      </div>
    );
  }
  
  // Check for image URL
  if (IMAGE_PATTERN.test(url)) {
    return (
      <img 
        src={url} 
        alt="" 
        className="max-w-full rounded-lg my-2 max-h-64 object-contain"
        loading="lazy"
      />
    );
  }
  
  // Check for video URL
  if (VIDEO_PATTERN.test(url)) {
    return (
      <video 
        src={url} 
        controls 
        className="max-w-full rounded-lg my-2 max-h-64"
        preload="metadata"
      />
    );
  }
  
  return null;
};

// Process text content for bare URLs and embed media
const processTextForMedia = (text) => {
  if (typeof text !== 'string') return text;
  
  // Pattern to find URLs in text
  const urlPattern = /(https?:\/\/[^\s<>"{}|\\^`\[\]]+)/g;
  const parts = [];
  let lastIndex = 0;
  let match;
  
  while ((match = urlPattern.exec(text)) !== null) {
    // Add text before the URL
    if (match.index > lastIndex) {
      parts.push(text.slice(lastIndex, match.index));
    }
    
    const url = match[1];
    const embed = renderMediaEmbed(url);
    
    if (embed) {
      parts.push(embed);
    } else {
      // Regular link for non-media URLs
      parts.push(
        <a 
          key={match.index}
          href={url} 
          target="_blank" 
          rel="noopener noreferrer"
          className="text-[#3b82f6] underline"
        >
          {url}
        </a>
      );
    }
    
    lastIndex = match.index + match[0].length;
  }
  
  // Add remaining text
  if (lastIndex < text.length) {
    parts.push(text.slice(lastIndex));
  }
  
  return parts.length > 0 ? parts : text;
};

// Simplified markdown components for mobile
const MarkdownComponents = {
  code({ node, inline, className, children, ...props }) {
    const match = /language-(\w+)/.exec(className || '');
    const language = match ? match[1] : '';
    
    if (inline) {
      return (
        <code className="bg-[#1a1a1a] px-1.5 py-0.5 rounded text-[#e879f9] text-sm font-mono" {...props}>
          {children}
        </code>
      );
    }
    
    return (
      <div className="my-2 rounded overflow-hidden">
        {language && (
          <div className="bg-[#252525] px-3 py-1 text-[10px] text-[#888] uppercase tracking-wide">
            {language}
          </div>
        )}
        <pre className="bg-[#1a1a1a] p-3 overflow-x-auto">
          <code className="text-sm text-[#d4d4d4] font-mono" {...props}>
            {children}
          </code>
        </pre>
      </div>
    );
  },
  p({ children }) {
    return <p className="mb-2 last:mb-0">{children}</p>;
  },
  ul({ children }) {
    return <ul className="list-disc list-inside mb-2 space-y-1">{children}</ul>;
  },
  ol({ children }) {
    return <ol className="list-decimal list-inside mb-2 space-y-1">{children}</ol>;
  },
  // Images
  img({ src, alt }) {
    return (
      <img 
        src={src} 
        alt={alt || ''} 
        className="max-w-full rounded-lg my-2 max-h-64 object-contain"
        loading="lazy"
      />
    );
  },
  // Links - detect and embed media
  a({ href, children }) {
    if (!href) {
      return <span>{children}</span>;
    }
    
    // Check for image URL
    if (IMAGE_PATTERN.test(href)) {
      return (
        <img 
          src={href} 
          alt="" 
          className="max-w-full rounded-lg my-2 max-h-64 object-contain"
          loading="lazy"
        />
      );
    }
    
    // Check for video URL
    if (VIDEO_PATTERN.test(href)) {
      return (
        <video 
          src={href} 
          controls 
          className="max-w-full rounded-lg my-2 max-h-64"
          preload="metadata"
        />
      );
    }
    
    // Check for YouTube URL
    const ytMatch = href.match(YOUTUBE_PATTERN);
    if (ytMatch) {
      return (
        <div className="my-2 aspect-video max-w-full">
          <iframe
            src={`https://www.youtube.com/embed/${ytMatch[1]}`}
            title="YouTube video"
            className="w-full h-full rounded-lg"
            frameBorder="0"
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
            allowFullScreen
          />
        </div>
      );
    }
    
    // Check for Vimeo URL
    const vimeoMatch = href.match(VIMEO_PATTERN);
    if (vimeoMatch) {
      return (
        <div className="my-2 aspect-video max-w-full">
          <iframe
            src={`https://player.vimeo.com/video/${vimeoMatch[1]}`}
            title="Vimeo video"
            className="w-full h-full rounded-lg"
            frameBorder="0"
            allow="autoplay; fullscreen; picture-in-picture"
            allowFullScreen
          />
        </div>
      );
    }
    
    // Regular link
    return (
      <a href={href} target="_blank" rel="noopener noreferrer" className="text-[#3b82f6] underline">
        {children}
      </a>
    );
  },
  strong({ children }) {
    return <strong className="font-bold text-[#e5e5e5]">{children}</strong>;
  },
  // Table support with media embedding
  table({ children }) {
    return (
      <div className="overflow-x-auto my-2">
        <table className="min-w-full border border-[#2b2b2b]">{children}</table>
      </div>
    );
  },
  thead({ children }) {
    return <thead className="bg-[#1a1a1a]">{children}</thead>;
  },
  th({ children }) {
    return <th className="px-3 py-2 text-left text-[10px] uppercase tracking-wide text-[#888] border-b border-[#2b2b2b]">{children}</th>;
  },
  td({ children }) {
    // Process children for bare URLs that should be embedded
    const processedChildren = React.Children.map(children, child => {
      if (typeof child === 'string') {
        return processTextForMedia(child);
      }
      return child;
    });
    return <td className="px-3 py-2 border-b border-[#2b2b2b] text-[#d4d4d4]">{processedChildren}</td>;
  },
};

export default function MobileChat() {
  const [isConnected, setIsConnected] = useState(socket.connected);
  const [isDeployed, setIsDeployed] = useState(false);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [playingMessageId, setPlayingMessageId] = useState(null);
  const messagesEndRef = useRef(null);
  const audioRef = useRef(null);
  const lastMessageCountRef = useRef(0);
  
  // Voice state
  const [voiceState, setVoiceState] = useState('idle');
  const [sttEnabled, setSttEnabled] = useState(false);
  const [ttsEnabled, setTtsEnabled] = useState(false);
  const [skipWakeWord, setSkipWakeWord] = useState(true); // Default true on mobile
  const [sttSettings, setSttSettings] = useState(null);
  const mediaRecorderRef = useRef(null);
  const audioContextRef = useRef(null);
  const streamRef = useRef(null);
  const processorRef = useRef(null);

  // Socket connection and event handling
  useEffect(() => {
    function onConnect() { setIsConnected(true); }
    function onDisconnect() { setIsConnected(false); }
    
    function onAgentGraphState(data) {
      setIsDeployed(data.is_deployed || false);
    }
    
    function onChatMessage(data) {
      // Stop TTS audio when user message arrives (typed or voice)
      if (data.user === 'User' && audioRef.current) {
        audioRef.current.pause();
        audioRef.current = null;
      }
      
      const newMessage = { 
        id: Date.now(), 
        user: data.user, 
        text: data.message,
        audioUrl: data.audioUrl || null,
      };
      setMessages(prev => [...prev, newMessage]);
    }
    
    function onSttSettings(data) {
      setSttSettings(data);
      // Don't sync sttEnabled from global - mobile controls its own toggle
    }
    
    function onTtsSettings(data) {
      // Don't sync from global settings - mobile TTS is per-client
      // User needs to explicitly enable it via toggle
    }
    
    function onSttStatus(data) {
      if (data.state === 'active') {
        setVoiceState('active');
      } else if (data.state === 'idle') {
        setVoiceState('listening');
      }
    }
    
    function onSttActivated() {
      setVoiceState('active');
    }
    
    function onSttDeactivated() {
      setVoiceState('listening');
    }
    
    function onTtsAudio(data) {
      // Play audio directly when received (per-client TTS)
      if (data.audioUrl) {
        // Stop any currently playing audio first
        if (audioRef.current) {
          audioRef.current.pause();
        }
        const audio = new Audio(data.audioUrl);
        audioRef.current = audio;
        audio.onended = () => { audioRef.current = null; };
        audio.play().catch(err => console.error('Failed to play TTS audio:', err));
      }
    }

    socket.on('connect', onConnect);
    socket.on('disconnect', onDisconnect);
    socket.on('agent_graph_state', onAgentGraphState);
    socket.on('chat_message', onChatMessage);
    socket.on('stt_settings', onSttSettings);
    socket.on('tts_settings', onTtsSettings);
    socket.on('stt_status', onSttStatus);
    socket.on('stt_activated', onSttActivated);
    socket.on('stt_deactivated', onSttDeactivated);
    socket.on('tts_audio', onTtsAudio);
    
    socket.connect();
    socket.emit('get_agent_graph_state');
    socket.emit('get_stt_settings');
    socket.emit('get_tts_settings');

    return () => {
      socket.off('connect', onConnect);
      socket.off('disconnect', onDisconnect);
      socket.off('agent_graph_state', onAgentGraphState);
      socket.off('chat_message', onChatMessage);
      socket.off('stt_settings', onSttSettings);
      socket.off('tts_settings', onTtsSettings);
      socket.off('stt_status', onSttStatus);
      socket.off('stt_activated', onSttActivated);
      socket.off('stt_deactivated', onSttDeactivated);
      socket.off('tts_audio', onTtsAudio);
    };
  }, []);

  // Scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const startAudioCapture = useCallback(async () => {
    try {
      const constraints = {
        audio: sttSettings?.device_id 
          ? { deviceId: { exact: sttSettings.device_id } }
          : true
      };
      
      const stream = await navigator.mediaDevices.getUserMedia(constraints);
      streamRef.current = stream;
      
      const audioContext = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 16000 });
      audioContextRef.current = audioContext;
      
      const source = audioContext.createMediaStreamSource(stream);
      const processor = audioContext.createScriptProcessor(4096, 1, 1);
      processorRef.current = processor;
      
      socket.emit('stt_stream_start', { skip_wake_word: skipWakeWord });
      setVoiceState(skipWakeWord ? 'active' : 'listening');
      
      let silenceFrames = 0;
      const SILENCE_THRESHOLD = 0.01;
      const SILENCE_FRAMES_TO_STOP = 8;
      
      processor.onaudioprocess = (e) => {
        const inputData = e.inputBuffer.getChannelData(0);
        
        let sum = 0;
        for (let i = 0; i < inputData.length; i++) {
          sum += inputData[i] * inputData[i];
        }
        const rms = Math.sqrt(sum / inputData.length);
        const isSpeech = rms > SILENCE_THRESHOLD;
        
        if (isSpeech) {
          silenceFrames = 0;
        } else {
          silenceFrames++;
        }
        
        const int16Data = new Int16Array(inputData.length);
        for (let i = 0; i < inputData.length; i++) {
          const s = Math.max(-1, Math.min(1, inputData[i]));
          int16Data[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
        }
        const base64 = btoa(String.fromCharCode(...new Uint8Array(int16Data.buffer)));
        
        socket.emit('stt_stream_chunk', { 
          audio: base64, 
          speech: isSpeech || silenceFrames < SILENCE_FRAMES_TO_STOP 
        });
      };
      
      source.connect(processor);
      processor.connect(audioContext.destination);
      
    } catch (err) {
      console.error('Failed to start audio capture:', err);
      setSttEnabled(false);
    }
  }, [sttSettings, skipWakeWord]);

  const stopAudioCapture = useCallback(() => {
    const wasCapturing = processorRef.current != null;
    
    if (processorRef.current) {
      processorRef.current.disconnect();
      processorRef.current = null;
    }
    if (audioContextRef.current) {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    }
    
    if (wasCapturing) {
      socket.emit('stt_stream_stop');
    }
    setVoiceState('idle');
  }, []);

  // Audio capture for STT
  useEffect(() => {
    if (sttEnabled && sttSettings && isDeployed) {
      startAudioCapture();
    } else {
      stopAudioCapture();
    }
    return () => stopAudioCapture();
  }, [sttEnabled, sttSettings, isDeployed, startAudioCapture, stopAudioCapture]);

  // Track message count (audio now comes via tts_audio event, not in messages)
  useEffect(() => {
    lastMessageCountRef.current = messages.length;
  }, [messages]);

  const playAudio = (messageId, audioUrl) => {
    if (audioRef.current) {
      audioRef.current.pause();
    }
    
    const fullUrl = audioUrl.startsWith('data:') 
      ? audioUrl 
      : `http://${window.location.hostname}:5000${audioUrl}`;
    
    const audio = new Audio(fullUrl);
    audioRef.current = audio;
    setPlayingMessageId(messageId);
    
    audio.onended = () => {
      setPlayingMessageId(null);
      audioRef.current = null;
    };
    
    audio.onerror = () => {
      setPlayingMessageId(null);
      audioRef.current = null;
    };
    
    audio.play().catch(() => {
      setPlayingMessageId(null);
      audioRef.current = null;
    });
  };

  const stopAudio = () => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
    }
    setPlayingMessageId(null);
  };

  const handleAudioClick = (messageId, audioUrl) => {
    if (playingMessageId === messageId) {
      stopAudio();
    } else {
      playAudio(messageId, audioUrl);
    }
  };

  const sendMessage = (e) => {
    e.preventDefault();
    if (input.trim()) {
      // Stop any currently playing TTS audio
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current = null;
      }
      socket.emit('send_message', { user: 'User', message: input });
      setInput('');
    }
  };

  const toggleSTT = () => {
    const newEnabled = !sttEnabled;
    setSttEnabled(newEnabled);
    socket.emit('set_stt_enabled', { enabled: newEnabled });
  };

  const toggleTTS = () => {
    const newEnabled = !ttsEnabled;
    setTtsEnabled(newEnabled);
    socket.emit('set_tts_enabled', { enabled: newEnabled });
  };

  const isAgentMessage = (user) => user !== 'User';

  const getInitials = (name) => {
    if (name === 'User') return 'U';
    const words = name.split(' ');
    if (words.length >= 2) {
      return (words[0][0] + words[1][0]).toUpperCase();
    }
    return name.substring(0, 2).toUpperCase();
  };

  return (
    <div className="flex flex-col h-[100dvh] bg-[#0c0c0c] text-[#e5e5e5]">
      {/* Header */}
      <header className="flex-shrink-0 h-14 px-4 border-b border-[#2b2b2b] flex items-center justify-between bg-[#0a0a0a] safe-area-top">
        <div className="flex items-center gap-3">
          <span className="text-lg font-semibold text-[#3b82f6]">beezlebug</span>
          <div className={`flex items-center gap-1.5 text-xs px-2 py-1 rounded ${
            isDeployed ? 'bg-[#22c55e]/20 text-[#22c55e]' : 'bg-[#666]/20 text-[#888]'
          }`}>
            {isConnected ? <Wifi size={12} /> : <WifiOff size={12} />}
            {isDeployed ? 'Live' : 'Offline'}
          </div>
        </div>
        
        <div className="flex items-center gap-3">
          {/* Voice Input Status Indicator */}
          {sttEnabled && isDeployed && (
            <div className={`flex items-center gap-1.5 text-xs px-2 py-1 rounded ${
              voiceState === 'active' 
                ? 'bg-[#22c55e]/20 text-[#22c55e]' 
                : 'bg-[#f59e0b]/20 text-[#f59e0b]'
            }`}>
              <Mic size={12} className={voiceState === 'active' ? 'animate-pulse' : ''} />
              {voiceState === 'active' ? 'Speaking' : 'Listening'}
            </div>
          )}
          
          {/* Skip Wake Word Toggle */}
          <button
            onClick={() => setSkipWakeWord(!skipWakeWord)}
            className="flex items-center gap-1.5 text-[10px] text-[#666] active:text-[#888]"
          >
            <span>Skip wake word activation</span>
            <div className={`w-7 h-3.5 rounded-full transition-colors relative ${
              skipWakeWord ? 'bg-[#22c55e]' : 'bg-[#333]'
            }`}>
              <div className={`absolute top-0.5 w-2.5 h-2.5 rounded-full bg-white transition-transform ${
                skipWakeWord ? 'translate-x-3.5' : 'translate-x-0.5'
              }`} />
            </div>
          </button>
        </div>
      </header>

      {/* Messages */}
      <main className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-[#444]">
            <p className="text-sm">
              {isDeployed ? 'Say hello!' : 'Waiting for deployment...'}
            </p>
          </div>
        )}
        
        {messages.map((msg) => {
          const isAgent = isAgentMessage(msg.user);
          const isPlaying = playingMessageId === msg.id;
          
          return (
            <div key={msg.id} className={`flex gap-3 ${!isAgent ? 'flex-row-reverse' : ''}`}>
              <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold shrink-0 ${
                !isAgent 
                  ? 'bg-[#1c1c1c] border border-[#333] text-[#ccc]' 
                  : 'bg-[#3b82f6] text-white'
              }`}>
                {getInitials(msg.user)}
              </div>
              <div className={`max-w-[80%] ${!isAgent ? 'text-right' : ''}`}>
                {isAgent && (
                  <div className="text-xs text-[#666] mb-1 flex items-center gap-2">
                    <span>{msg.user}</span>
                    {msg.audioUrl && (
                      <button
                        onClick={() => handleAudioClick(msg.id, msg.audioUrl)}
                        className={`p-1 rounded active:bg-[#2b2b2b] ${
                          isPlaying ? 'text-[#3b82f6]' : 'text-[#666]'
                        }`}
                      >
                        {isPlaying ? <Square size={14} /> : <Volume2 size={14} />}
                      </button>
                    )}
                  </div>
                )}
                <div className={`px-4 py-3 text-[15px] leading-relaxed rounded-2xl inline-block ${
                  !isAgent 
                    ? 'bg-[#3b82f6] text-white rounded-br-sm' 
                    : 'bg-[#1a1a1a] text-[#e5e5e5] rounded-bl-sm'
                }`}>
                  {isAgent ? (
                    <ReactMarkdown remarkPlugins={[remarkGfm]} components={MarkdownComponents}>
                      {msg.text}
                    </ReactMarkdown>
                  ) : (
                    processTextForMedia(msg.text)
                  )}
                </div>
              </div>
            </div>
          );
        })}
        <div ref={messagesEndRef} />
      </main>

      {/* Footer with input and voice controls */}
      <footer className="flex-shrink-0 border-t border-[#2b2b2b] bg-[#0a0a0a] safe-area-bottom">
        {/* Voice Toggle Buttons */}
        <div className="flex items-center justify-center gap-4 py-3 border-b border-[#2b2b2b]">
          <button
            onClick={toggleSTT}
            disabled={!isDeployed}
            className={`flex items-center gap-2 px-4 py-2.5 rounded-full text-sm font-medium transition-all min-h-[44px] ${
              !isDeployed
                ? 'bg-[#1a1a1a] text-[#555] cursor-not-allowed'
                : sttEnabled
                  ? 'bg-[#22c55e] text-white active:bg-[#16a34a]'
                  : 'bg-[#1a1a1a] text-[#888] active:bg-[#252525]'
            }`}
          >
            {sttEnabled ? <Mic size={18} /> : <MicOff size={18} />}
            Voice In
          </button>
          
          <button
            onClick={toggleTTS}
            disabled={!isDeployed}
            className={`flex items-center gap-2 px-4 py-2.5 rounded-full text-sm font-medium transition-all min-h-[44px] ${
              !isDeployed
                ? 'bg-[#1a1a1a] text-[#555] cursor-not-allowed'
                : ttsEnabled
                  ? 'bg-[#3b82f6] text-white active:bg-[#2563eb]'
                  : 'bg-[#1a1a1a] text-[#888] active:bg-[#252525]'
            }`}
          >
            {ttsEnabled ? <Volume2 size={18} /> : <VolumeX size={18} />}
            Voice Out
          </button>
        </div>
        
        {/* Input field */}
        <form onSubmit={sendMessage} className="flex items-center gap-2 p-3">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={isDeployed ? "Type a message..." : "Deploy agents first..."}
            disabled={!isDeployed}
            className="flex-1 bg-[#1a1a1a] text-[#e5e5e5] text-base px-4 py-3 rounded-full focus:outline-none focus:ring-2 focus:ring-[#3b82f6] placeholder-[#555] disabled:opacity-50 min-h-[48px]"
          />
          <button
            type="submit"
            disabled={!isDeployed || !input.trim()}
            className="w-12 h-12 flex items-center justify-center bg-[#3b82f6] text-white rounded-full disabled:opacity-50 disabled:bg-[#1a1a1a] active:bg-[#2563eb] transition-colors"
          >
            <Send size={20} />
          </button>
        </form>
      </footer>
    </div>
  );
}

