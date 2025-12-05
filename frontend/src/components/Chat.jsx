import React, { useState, useEffect, useRef } from 'react';
import { socket } from '../lib/socket';
import { Send, Terminal, Volume2, Square } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

// Custom components for markdown rendering
const MarkdownComponents = {
  // Code blocks
  code({ node, inline, className, children, ...props }) {
    const match = /language-(\w+)/.exec(className || '');
    const language = match ? match[1] : '';
    
    if (inline) {
      return (
        <code className="bg-[#1a1a1a] px-1.5 py-0.5 rounded text-[#e879f9] text-[12px] font-mono" {...props}>
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
          <code className="text-[12px] text-[#d4d4d4] font-mono" {...props}>
            {children}
          </code>
        </pre>
      </div>
    );
  },
  // Paragraphs
  p({ children }) {
    return <p className="mb-2 last:mb-0">{children}</p>;
  },
  // Headers
  h1({ children }) {
    return <h1 className="text-lg font-bold mb-2 text-[#e5e5e5]">{children}</h1>;
  },
  h2({ children }) {
    return <h2 className="text-base font-bold mb-2 text-[#e5e5e5]">{children}</h2>;
  },
  h3({ children }) {
    return <h3 className="text-sm font-bold mb-1 text-[#e5e5e5]">{children}</h3>;
  },
  // Lists
  ul({ children }) {
    return <ul className="list-disc list-inside mb-2 space-y-1">{children}</ul>;
  },
  ol({ children }) {
    return <ol className="list-decimal list-inside mb-2 space-y-1">{children}</ol>;
  },
  li({ children }) {
    return <li className="text-[#d4d4d4]">{children}</li>;
  },
  // Links
  a({ href, children }) {
    return (
      <a 
        href={href} 
        target="_blank" 
        rel="noopener noreferrer"
        className="text-[#3b82f6] hover:text-[#60a5fa] underline"
      >
        {children}
      </a>
    );
  },
  // Blockquotes
  blockquote({ children }) {
    return (
      <blockquote className="border-l-2 border-[#3b82f6] pl-3 my-2 text-[#888] italic">
        {children}
      </blockquote>
    );
  },
  // Tables
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
    return <th className="px-3 py-2 text-left text-[11px] uppercase tracking-wide text-[#888] border-b border-[#2b2b2b]">{children}</th>;
  },
  td({ children }) {
    return <td className="px-3 py-2 border-b border-[#2b2b2b] text-[#d4d4d4]">{children}</td>;
  },
  // Horizontal rule
  hr() {
    return <hr className="my-3 border-[#2b2b2b]" />;
  },
  // Strong/Bold
  strong({ children }) {
    return <strong className="font-bold text-[#e5e5e5]">{children}</strong>;
  },
  // Emphasis/Italic
  em({ children }) {
    return <em className="italic text-[#d4d4d4]">{children}</em>;
  },
};

export default function Chat({ agentStatus, messages, setMessages }) {
  const [input, setInput] = useState('');
  const [playingMessageId, setPlayingMessageId] = useState(null);
  const messagesEndRef = useRef(null);
  const audioRef = useRef(null);
  const lastMessageCountRef = useRef(0);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Auto-play audio for new messages
  useEffect(() => {
    if (messages.length > lastMessageCountRef.current) {
      const newMessages = messages.slice(lastMessageCountRef.current);
      // Find the last message with audio
      const messageWithAudio = newMessages.reverse().find(m => m.audioUrl);
      if (messageWithAudio) {
        playAudio(messageWithAudio.id, messageWithAudio.audioUrl);
      }
    }
    lastMessageCountRef.current = messages.length;
  }, [messages]);

  // Check if a message is from an agent (not the user)
  const isAgentMessage = (user) => user !== 'User';

  const playAudio = (messageId, audioUrl) => {
    if (audioRef.current) {
      audioRef.current.pause();
    }
    
    // Use URL directly if it's a data URL, otherwise prepend backend URL
    const fullUrl = audioUrl.startsWith('data:') 
      ? audioUrl 
      : `http://localhost:5000${audioUrl}`;
    
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
      socket.emit('send_message', { user: 'User', message: input });
      setInput('');
    }
  };

  // Get initials for the avatar
  const getInitials = (name) => {
    if (name === 'User') return 'U';
    // Get first letter of each word, max 2
    const words = name.split(' ');
    if (words.length >= 2) {
      return (words[0][0] + words[1][0]).toUpperCase();
    }
    return name.substring(0, 2).toUpperCase();
  };

  return (
    <div className="flex flex-col h-full bg-[#0c0c0c]">
      <div className="h-10 border-b border-[#2b2b2b] flex items-center px-4">
        <span className="text-[#888888] text-xs uppercase tracking-wide font-medium flex items-center gap-2">
          <Terminal size={14} />
          Chat
        </span>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4 text-sm">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-[#444444]">
            <Terminal size={32} className="opacity-50 mb-2" />
            <p className="text-xs">Start an agent and say hello!</p>
          </div>
        )}
        {messages.map((msg) => {
          const isAgent = isAgentMessage(msg.user);
          const isPlaying = playingMessageId === msg.id;
          
          return (
            <div key={msg.id} className={`flex gap-3 ${!isAgent ? 'flex-row-reverse' : ''} group`}>
              <div className={`w-6 h-6 rounded-sm flex items-center justify-center text-[10px] font-bold border shrink-0 ${
                !isAgent 
                  ? 'bg-[#1c1c1c] border-[#333] text-[#ccc]' 
                  : 'bg-[#3b82f6] border-[#3b82f6] text-white'
              }`} title={msg.user}>
                {getInitials(msg.user)}
              </div>
              <div className={`max-w-[75%] ${!isAgent ? 'text-right' : ''}`}>
                {isAgent && (
                  <div className="text-[10px] text-[#666] mb-1 flex items-center gap-2">
                    <span>{msg.user}</span>
                    {msg.audioUrl && (
                      <button
                        onClick={() => handleAudioClick(msg.id, msg.audioUrl)}
                        className={`opacity-0 group-hover:opacity-100 transition-opacity p-0.5 rounded hover:bg-[#2b2b2b] ${
                          isPlaying ? 'opacity-100 text-[#3b82f6]' : 'text-[#666] hover:text-[#888]'
                        }`}
                        title={isPlaying ? 'Stop' : 'Play audio'}
                      >
                        {isPlaying ? <Square size={12} /> : <Volume2 size={12} />}
                      </button>
                    )}
                  </div>
                )}
                <div className={`px-3 py-2 text-[13px] rounded inline-block ${
                  !isAgent 
                    ? 'bg-[#1c1c1c] border border-[#2b2b2b] text-[#e5e5e5] font-mono' 
                    : 'text-[#d4d4d4] text-left'
                }`}>
                  {isAgent ? (
                    <ReactMarkdown 
                      remarkPlugins={[remarkGfm]}
                      components={MarkdownComponents}
                    >
                      {msg.text}
                    </ReactMarkdown>
                  ) : (
                    msg.text
                  )}
                </div>
              </div>
            </div>
          );
        })}
        <div ref={messagesEndRef} />
      </div>

      <div className="p-4 border-t border-[#2b2b2b]">
        <form onSubmit={sendMessage} className="flex items-center gap-2">
          <span className="text-[#3b82f6] text-lg">❯</span>
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Type a message..."
            className="flex-1 bg-transparent text-[#e5e5e5] font-mono text-sm focus:outline-none placeholder-[#444444]"
          />
          <button
            type="submit"
            className="p-2 text-[#888] hover:text-[#e5e5e5] transition-colors"
          >
            <Send size={16} />
          </button>
        </form>
      </div>
    </div>
  );
}
