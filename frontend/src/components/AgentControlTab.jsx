import React, { useState, useEffect } from 'react';
import { socket } from '../lib/socket';
import { Pause, Play, Square } from 'lucide-react';

export default function AgentControlTab() {
  const [agents, setAgents] = useState([]);

  useEffect(() => {
    // Request initial agent list
    socket.emit('list_agents');
    socket.emit('get_agent_graph_state');
    
    // Listen for agent list updates (from AgentManager - standalone agents)
    socket.on('agents_list', (data) => {
      const instanced = data?.instanced || [];
      setAgents(prev => {
        const agentGraphAgents = prev.filter(a => a.source === 'agent_graph');
        const standaloneAgents = instanced.map(a => ({ ...a, source: 'standalone' }));
        return [...standaloneAgents, ...agentGraphAgents];
      });
    });
    
    // Listen for agent graph agents updates (from AgentGraphManager - deployed agent graph agents)
    socket.on('agent_graph_agents', (agentGraphAgentsList) => {
      const agentGraphAgents = (agentGraphAgentsList || []).map(a => ({ ...a, source: 'agent_graph' }));
      setAgents(prev => {
        const standaloneAgents = prev.filter(a => a.source === 'standalone');
        return [...standaloneAgents, ...agentGraphAgents];
      });
    });
    
    return () => {
      socket.off('agents_list');
      socket.off('agent_graph_agents');
    };
  }, []);

  const pauseAgent = (agentId, source) => {
    if (source === 'agent_graph') {
      // Agent graph agents can't be individually paused yet
      return;
    }
    socket.emit('pause_agent', { id: agentId });
  };

  const resumeAgent = (agentId, source) => {
    if (source === 'agent_graph') {
      return;
    }
    socket.emit('resume_agent', { id: agentId });
  };

  const stopAgent = (agentId, source) => {
    if (source === 'agent_graph') {
      // Can't stop individual agent graph agents
      return;
    }
    socket.emit('stop_agent', { id: agentId });
  };

  return (
    <div className="h-full overflow-y-auto p-4">
      <div>
        {/* Table Header */}
        <div className="grid grid-cols-[60px_1fr_70px_60px] gap-2 px-3 py-2 text-[10px] text-[#666] uppercase tracking-wide border-b border-[#2b2b2b]">
          <div>ID</div>
          <div>Name</div>
          <div>State</div>
          <div className="text-right">Actions</div>
        </div>
        
        {/* Table Body */}
        {agents.length === 0 ? (
          <div className="px-3 py-4 text-center text-[#555] text-xs">
            No agents running. Deploy an agent graph or create standalone agents.
          </div>
        ) : (
          agents.map((agent) => (
            <div
              key={agent.id}
              className="grid grid-cols-[60px_1fr_70px_60px] gap-2 px-3 py-2 text-sm hover:bg-[#1f1f1f] transition-colors"
            >
              <div className="font-mono text-[#666] text-xs truncate" title={agent.id}>
                {agent.id}
              </div>
              <div className="text-[#e5e5e5] truncate">
                {agent.name}
              </div>
                <div>
                  <span className={`text-[10px] px-1.5 py-0.5 rounded ${
                    agent.state === 'running' 
                      ? 'bg-[#22c55e]/20 text-[#22c55e]' 
                      : 'bg-[#eab308]/20 text-[#eab308]'
                  }`}>
                    {agent.state === 'running' ? 'Running' : 'Paused'}
                  </span>
                </div>
                <div className="flex justify-end gap-1">
                  {agent.source !== 'agent_graph' && (
                    <>
                      {agent.state === 'running' ? (
                        <button
                          onClick={() => pauseAgent(agent.id, agent.source)}
                          className="p-1 rounded hover:bg-[#eab308]/20 text-[#888] hover:text-[#eab308] transition-colors"
                          title="Pause"
                        >
                          <Pause size={12} />
                        </button>
                      ) : (
                        <button
                          onClick={() => resumeAgent(agent.id, agent.source)}
                          className="p-1 rounded hover:bg-[#22c55e]/20 text-[#888] hover:text-[#22c55e] transition-colors"
                          title="Resume"
                        >
                          <Play size={12} />
                        </button>
                      )}
                      <button
                        onClick={() => stopAgent(agent.id, agent.source)}
                        className="p-1 rounded hover:bg-[#ef4444]/20 text-[#888] hover:text-[#ef4444] transition-colors"
                        title="Stop"
                      >
                        <Square size={12} />
                      </button>
                    </>
                  )}
                </div>
              </div>
            ))
          )}
      </div>
    </div>
  );
}
