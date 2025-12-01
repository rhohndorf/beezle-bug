import React, { useState, useEffect, useRef } from 'react';
import { socket } from '../lib/socket';
import { ScrollText, Trash2, CheckCircle, XCircle, Info } from 'lucide-react';

export default function LogPanel() {
  const [logs, setLogs] = useState([]);
  const scrollRef = useRef(null);

  useEffect(() => {
    // Listen for log messages (success, info)
    socket.on('log', (data) => {
      const entry = {
        id: Date.now(),
        timestamp: new Date().toLocaleTimeString(),
        type: data.type || 'info', // 'success', 'info', 'warning'
        message: data.message
      };
      setLogs(prev => [...prev.slice(-99), entry]); // Keep last 100 entries
    });

    // Listen for error messages
    socket.on('error', (data) => {
      const entry = {
        id: Date.now(),
        timestamp: new Date().toLocaleTimeString(),
        type: 'error',
        message: data.message
      };
      setLogs(prev => [...prev.slice(-99), entry]);
    });

    return () => {
      socket.off('log');
      socket.off('error');
    };
  }, []);

  // Auto-scroll to bottom on new logs
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [logs]);

  const clearLogs = () => {
    setLogs([]);
  };

  const getIcon = (type) => {
    switch (type) {
      case 'success':
        return <CheckCircle size={12} className="text-[#22c55e]" />;
      case 'error':
        return <XCircle size={12} className="text-[#ef4444]" />;
      case 'warning':
        return <Info size={12} className="text-[#eab308]" />;
      default:
        return <Info size={12} className="text-[#3b82f6]" />;
    }
  };

  const getTextColor = (type) => {
    switch (type) {
      case 'success':
        return 'text-[#22c55e]';
      case 'error':
        return 'text-[#ef4444]';
      case 'warning':
        return 'text-[#eab308]';
      default:
        return 'text-[#888]';
    }
  };

  return (
    <div className="h-full flex flex-col bg-[#0c0c0c]">
      {/* Header */}
      <div className="h-10 px-3 border-b border-[#2b2b2b] flex items-center justify-between select-none flex-shrink-0">
        <div className="flex items-center gap-2 text-[#888888] text-xs uppercase tracking-wide font-medium">
          <ScrollText size={14} />
          Log
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[10px] text-[#555]">{logs.length} entries</span>
          <button
            onClick={clearLogs}
            className="p-1 rounded hover:bg-[#2b2b2b] text-[#666] hover:text-[#e5e5e5] transition-colors"
            title="Clear logs"
          >
            <Trash2 size={12} />
          </button>
        </div>
      </div>

      {/* Log Entries */}
      <div 
        ref={scrollRef}
        className="flex-1 overflow-y-auto overflow-x-hidden p-2 space-y-1 font-mono text-[11px]"
      >
        {logs.length === 0 ? (
          <div className="text-center text-[#444] py-4">
            No log entries yet
          </div>
        ) : (
          logs.map((log) => (
            <div
              key={log.id}
              className="flex items-start gap-2 py-1 px-2 rounded hover:bg-[#1a1a1a] transition-colors"
            >
              <span className="text-[#555] flex-shrink-0">{log.timestamp}</span>
              <span className="flex-shrink-0">{getIcon(log.type)}</span>
              <span className={`${getTextColor(log.type)} break-words`}>
                {log.message}
              </span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

