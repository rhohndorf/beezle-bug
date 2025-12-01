import React, { useState, useEffect, useRef, useMemo } from 'react';
import { socket } from '../lib/socket';
import { Brain, Terminal, MessageSquare, AlertCircle, Zap, ChevronDown, ChevronRight, Trash, Pause, Play, Filter, X } from 'lucide-react';

// Event type definitions with icons and colors
const EVENT_TYPES = {
  'message.received': { icon: MessageSquare, label: 'Message', color: '#22c55e' },
  'llm.call.started': { icon: Brain, label: 'Thinking', color: '#a855f7', animate: true },
  'llm.call.completed': { icon: Brain, label: 'Thought', color: '#a855f7' },
  'tool.selected': { icon: Terminal, label: 'Tool', color: '#eab308' },
  'tool.execution.completed': { icon: Zap, label: 'Tool Result', color: '#22c55e' },
  'error.occurred': { icon: AlertCircle, label: 'Error', color: '#ef4444' },
};

export default function IntrospectionPanel() {
  const [events, setEvents] = useState([]);
  const [paused, setPaused] = useState(false);
  const [selectedAgents, setSelectedAgents] = useState(new Set());
  const [selectedTypes, setSelectedTypes] = useState(new Set());
  const [showFilter, setShowFilter] = useState(false);
  const scrollRef = useRef(null);

  // Get unique agent names from events
  const agentNames = useMemo(() => {
    const names = new Set();
    events.forEach(e => {
      if (e.agent_name) names.add(e.agent_name);
    });
    return Array.from(names).sort();
  }, [events]);

  // Get unique event types from events
  const eventTypes = useMemo(() => {
    const types = new Set();
    events.forEach(e => {
      if (e.type) types.add(e.type);
    });
    return Array.from(types).sort();
  }, [events]);

  // Filter events based on selected agents and types
  const filteredEvents = useMemo(() => {
    return events.filter(e => {
      const agentMatch = selectedAgents.size === 0 || selectedAgents.has(e.agent_name);
      const typeMatch = selectedTypes.size === 0 || selectedTypes.has(e.type);
      return agentMatch && typeMatch;
    });
  }, [events, selectedAgents, selectedTypes]);

  const hasActiveFilters = selectedAgents.size > 0 || selectedTypes.size > 0;

  useEffect(() => {
    if (!paused && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [filteredEvents, paused]);

  useEffect(() => {
    function onAgentEvent(event) {
      setEvents(prev => {
        const newEvents = [...prev, event];
        return newEvents.length > 100 ? newEvents.slice(-100) : newEvents;
      });
    }
    socket.on('agent_event', onAgentEvent);
    return () => socket.off('agent_event', onAgentEvent);
  }, []);

  const toggleAgent = (name) => {
    setSelectedAgents(prev => {
      const next = new Set(prev);
      if (next.has(name)) next.delete(name);
      else next.add(name);
      return next;
    });
  };

  const toggleType = (type) => {
    setSelectedTypes(prev => {
      const next = new Set(prev);
      if (next.has(type)) next.delete(type);
      else next.add(type);
      return next;
    });
  };

  const clearFilters = () => {
    setSelectedAgents(new Set());
    setSelectedTypes(new Set());
  };

  const getEventTypeInfo = (type) => {
    return EVENT_TYPES[type] || { icon: Zap, label: type.split('.').pop(), color: '#888888' };
  };

  return (
    <div className="flex flex-col h-full text-[13px]">
      {/* Header */}
      <div className="flex items-center justify-between px-3 h-8 border-b border-[#2b2b2b] text-[#888888]">
        <div className="flex items-center gap-2">
          <span className="text-[10px]">{filteredEvents.length} events</span>
          {hasActiveFilters && (
            <span className="text-[10px] text-[#3b82f6]">(filtered)</span>
          )}
        </div>
        <div className="flex gap-1">
          <button 
            onClick={() => setShowFilter(!showFilter)} 
            className={`p-1 rounded ${showFilter || hasActiveFilters ? 'text-[#3b82f6]' : 'hover:text-white'}`}
            title="Filter events"
          >
            <Filter size={12} />
          </button>
          <button 
            onClick={() => setPaused(!paused)} 
            className={`p-1 rounded ${paused ? 'text-[#3b82f6]' : 'hover:text-white'}`}
            title={paused ? 'Resume' : 'Pause'}
          >
            {paused ? <Play size={12} /> : <Pause size={12} />}
          </button>
          <button 
            onClick={() => setEvents([])} 
            className="p-1 hover:text-white"
            title="Clear events"
          >
            <Trash size={12} />
          </button>
        </div>
      </div>

      {/* Filter Panel */}
      {showFilter && (
        <div className="px-3 py-2 bg-[#1a1a1a] border-b border-[#2b2b2b] space-y-3">
          {/* Clear All */}
          {hasActiveFilters && (
            <div className="flex justify-end">
              <button 
                onClick={clearFilters}
                className="text-[10px] text-[#3b82f6] hover:text-[#60a5fa] flex items-center gap-1"
              >
                <X size={10} /> Clear All Filters
              </button>
            </div>
          )}

          {/* Agent Filter */}
          <div>
            <span className="text-[10px] text-[#666] uppercase tracking-wide block mb-1">Agents</span>
            {agentNames.length === 0 ? (
              <p className="text-[10px] text-[#555]">No agents yet</p>
            ) : (
              <div className="flex flex-wrap gap-1">
                {agentNames.map(name => (
                  <button
                    key={name}
                    onClick={() => toggleAgent(name)}
                    className={`px-2 py-1 rounded text-[10px] transition-colors ${
                      selectedAgents.size === 0 || selectedAgents.has(name)
                        ? 'bg-[#2b2b2b] text-[#e5e5e5]'
                        : 'bg-[#151515] text-[#555]'
                    }`}
                  >
                    {name}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Event Type Filter */}
          <div>
            <span className="text-[10px] text-[#666] uppercase tracking-wide block mb-1">Event Types</span>
            {eventTypes.length === 0 ? (
              <p className="text-[10px] text-[#555]">No events yet</p>
            ) : (
              <div className="flex flex-wrap gap-1">
                {eventTypes.map(type => {
                  const info = getEventTypeInfo(type);
                  const Icon = info.icon;
                  return (
                    <button
                      key={type}
                      onClick={() => toggleType(type)}
                      className={`px-2 py-1 rounded text-[10px] transition-colors flex items-center gap-1 ${
                        selectedTypes.size === 0 || selectedTypes.has(type)
                          ? 'bg-[#2b2b2b] text-[#e5e5e5]'
                          : 'bg-[#151515] text-[#555]'
                      }`}
                    >
                      <Icon size={10} style={{ color: info.color }} />
                      {info.label}
                    </button>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      )}
      
      {paused && <div className="px-3 py-1 bg-[#3b82f6]/10 text-[10px] text-[#3b82f6]">Paused</div>}

      <div className="flex-1 overflow-y-auto" ref={scrollRef}>
        {filteredEvents.map((event, i) => <EventItem key={i} event={event} />)}
      </div>
    </div>
  );
}

function EventItem({ event }) {
  const [expanded, setExpanded] = useState(event.type === 'tool.selected' || event.data?.thinking);
  
  const typeInfo = EVENT_TYPES[event.type] || { icon: Zap, label: event.type.split('.').pop(), color: '#888888' };
  const Icon = typeInfo.icon;
  const color = event.type === 'tool.execution.completed' && event.data?.success === false ? '#ef4444' : typeInfo.color;
  
  // Build the label: for tools, show tool name
  let label = typeInfo.label;
  if (event.type === 'tool.selected' || event.type === 'tool.execution.completed') {
    label = event.data?.tool_name || label;
  }

  const hasDetails = event.data && Object.keys(event.data).length > 0;
  const hasThinking = event.data?.thinking;
  const agentName = event.agent_name || 'Unknown';

  return (
    <div className="border-b border-[#1e1e1e] hover:bg-[#1a1a1a]">
      <div 
        className="flex items-center px-3 py-2 gap-2 cursor-pointer" 
        onClick={() => hasDetails && setExpanded(!expanded)}
      >
        <span style={{ color }}><Icon size={14} className={typeInfo.animate ? 'animate-pulse' : ''} /></span>
        <div className="flex-1 min-w-0">
          <span className="text-[12px]">
            <span className="text-[#888]">{agentName}</span>
            <span className="text-[#444] mx-1">:</span>
            <span className="font-medium" style={{ color }}>{label}</span>
            {hasThinking && <span className="ml-2 text-[10px] text-[#a855f7]">💭</span>}
          </span>
        </div>
        {hasDetails && (
          <span className="text-[#444]">
            {expanded ? <ChevronDown size={12}/> : <ChevronRight size={12}/>}
          </span>
        )}
      </div>
      {expanded && hasDetails && (
        <div className="px-3 py-2 bg-[#111] text-[11px] font-mono">
          {/* Show thinking prominently if present */}
          {hasThinking && (
            <div className="mb-2 p-2 bg-[#a855f7]/10 rounded border border-[#a855f7]/30">
              <div className="text-[10px] text-[#a855f7] uppercase mb-1 font-sans">Thinking</div>
              <div className="text-[#c4b5fd] whitespace-pre-wrap">{event.data.thinking}</div>
            </div>
          )}
          {/* Show other data */}
          <div className="text-[#888]">
            {Object.entries(event.data)
              .filter(([k]) => k !== 'thinking')
              .map(([k, v]) => (
                <div key={k}>
                  <span className="text-[#666]">{k}:</span>{' '}
                  {typeof v === 'object' ? JSON.stringify(v) : String(v)}
                </div>
              ))}
          </div>
        </div>
      )}
    </div>
  );
}
