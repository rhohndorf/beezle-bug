import React, { useState, useEffect } from 'react';
import { socket } from '../lib/socket';
import { Save, Clock, Zap, Trash2, Pause, Play, Plus, Square, FolderOpen, X } from 'lucide-react';
import AgentCreationDialog from './AgentCreationDialog';

export default function AgentControlTab({ agentStatus, selectedAgentId, onAgentSelect }) {
  const [instancedAgents, setInstancedAgents] = useState([]);
  const [config, setConfig] = useState({
    id: null,
    name: '',
    apiUrl: 'http://127.0.0.1:1234/v1',
    apiKey: '',
    autonomousEnabled: false,
    autonomousInterval: 30,
    systemTemplate: 'agent',
    tools: []
  });

  // Dialog states
  const [showLoadDialog, setShowLoadDialog] = useState(false);
  const [loadDialogAgents, setLoadDialogAgents] = useState([]);
  const [selectedLoadId, setSelectedLoadId] = useState(null);
  const [showCreationDialog, setShowCreationDialog] = useState(false);

  useEffect(() => {
    socket.emit('list_agents');
    
    socket.on('agents_list', (data) => {
      const instanced = data?.instanced || [];
      setInstancedAgents(instanced);
      
      // Update load dialog if open
      if (showLoadDialog) {
        const persisted = data?.persisted || [];
        const instancedIds = instanced.map(a => a.id);
        const availableToLoad = persisted.filter(a => !instancedIds.includes(a.id));
        setLoadDialogAgents(availableToLoad);
      }
      
      // Auto-select first agent if none selected
      if (!selectedAgentId && instanced.length > 0) {
        onAgentSelect(instanced[0].id);
        socket.emit('get_agent_config', { id: instanced[0].id });
      }
    });
    
    socket.on('agent_config', (cfg) => {
      if (cfg) setConfig(prev => ({ ...prev, ...cfg }));
    });
    
    return () => {
      socket.off('agents_list');
      socket.off('agent_config');
    };
  }, [selectedAgentId, showLoadDialog]);

  const handleAgentSelect = (agentId) => {
    onAgentSelect(agentId);
    socket.emit('get_agent_config', { id: agentId });
  };

  // Open Load Dialog
  const openLoadDialog = () => {
    setSelectedLoadId(null);
    setShowLoadDialog(true);
    socket.emit('list_agents');
  };

  // Load selected agent from dialog
  const handleLoadAgent = () => {
    if (!selectedLoadId) return;
    socket.emit('load_agent', { id: selectedLoadId });
    setShowLoadDialog(false);
    setSelectedLoadId(null);
    setTimeout(() => {
      onAgentSelect(selectedLoadId);
      socket.emit('get_agent_config', { id: selectedLoadId });
      socket.emit('list_agents');
    }, 500);
  };

  // Handle agent creation from dialog
  const handleCreateAgent = (agentConfig) => {
    socket.emit('create_agent', agentConfig);
    setTimeout(() => {
      socket.emit('list_agents');
    }, 500);
  };

  const pauseAgent = (agentId) => {
    socket.emit('pause_agent', { id: agentId });
  };

  const resumeAgent = (agentId) => {
    socket.emit('resume_agent', { id: agentId });
  };

  const stopAgent = (agentId) => {
    socket.emit('stop_agent', { id: agentId });
    if (agentId === selectedAgentId) {
      onAgentSelect(null);
    }
  };

  const toggleAutonomous = () => {
    const newEnabled = !config.autonomousEnabled;
    setConfig({ ...config, autonomousEnabled: newEnabled });
    socket.emit('set_autonomous', {
      id: selectedAgentId,
      enabled: newEnabled,
      interval: config.autonomousInterval
    });
  };

  const updateAutonomousInterval = (interval) => {
    setConfig({ ...config, autonomousInterval: interval });
    if (config.autonomousEnabled) {
      socket.emit('set_autonomous', {
        id: selectedAgentId,
        enabled: true,
        interval: interval
      });
    }
  };

  const triggerTick = () => {
    socket.emit('trigger_agent_tick', { id: selectedAgentId });
  };

  const saveConfig = () => {
    socket.emit('save_agent_config', { ...config, id: selectedAgentId });
  };

  const deleteAgent = () => {
    if (!selectedAgentId) return;
    if (window.confirm(`Are you sure you want to delete agent "${config.name}"? This will remove all data including knowledge graph.`)) {
      socket.emit('delete_agent', { id: selectedAgentId });
      onAgentSelect(null);
      setTimeout(() => socket.emit('list_agents'), 500);
    }
  };

  const selectedAgent = instancedAgents.find(a => a.id === selectedAgentId);
  const isRunning = selectedAgent?.state === 'running';

  return (
    <div className="h-full overflow-y-auto p-4 space-y-4">
      {/* Agent Creation Dialog */}
      <AgentCreationDialog
        isOpen={showCreationDialog}
        onClose={() => setShowCreationDialog(false)}
        onCreate={handleCreateAgent}
      />

      {/* Load Agent Dialog */}
      {showLoadDialog && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-[#1a1a1a] border border-[#2b2b2b] rounded-lg w-80 max-h-[400px] flex flex-col">
            {/* Dialog Header */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-[#2b2b2b]">
              <h3 className="text-sm font-medium text-[#e5e5e5]">Load Agent</h3>
              <button
                onClick={() => setShowLoadDialog(false)}
                className="p-1 rounded hover:bg-[#2b2b2b] text-[#666] hover:text-[#e5e5e5] transition-colors"
              >
                <X size={16} />
              </button>
            </div>
            
            {/* Dialog Body */}
            <div className="flex-1 overflow-y-auto p-4">
              {loadDialogAgents.length === 0 ? (
                <div className="text-center text-[#555] text-xs py-8">
                  No saved agents to load.
                </div>
              ) : (
                <div className="space-y-1">
                  <p className="text-[#888] text-xs mb-3">Select an agent to load:</p>
                  {loadDialogAgents.map((agent) => (
                    <label
                      key={agent.id}
                      className={`flex items-center gap-3 px-3 py-2 rounded cursor-pointer transition-colors ${
                        selectedLoadId === agent.id
                          ? 'bg-[#3b82f6]/20 border border-[#3b82f6]/50'
                          : 'hover:bg-[#2b2b2b] border border-transparent'
                      }`}
                    >
                      <input
                        type="radio"
                        name="loadAgent"
                        value={agent.id}
                        checked={selectedLoadId === agent.id}
                        onChange={() => setSelectedLoadId(agent.id)}
                        className="accent-[#3b82f6]"
                      />
                      <div className="flex-1 min-w-0">
                        <div className="text-sm text-[#e5e5e5] truncate">{agent.name}</div>
                        <div className="text-[10px] text-[#555] font-mono">{agent.id}</div>
                      </div>
                    </label>
                  ))}
                </div>
              )}
            </div>
            
            {/* Dialog Footer */}
            <div className="flex gap-2 px-4 py-3 border-t border-[#2b2b2b]">
              <button
                onClick={() => setShowLoadDialog(false)}
                className="flex-1 py-2 bg-[#2b2b2b] hover:bg-[#3b3b3b] text-[#888] hover:text-[#e5e5e5] rounded text-xs font-medium transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleLoadAgent}
                disabled={!selectedLoadId}
                className="flex-1 py-2 bg-[#3b82f6] hover:bg-[#2563eb] disabled:bg-[#2b2b2b] disabled:opacity-50 disabled:text-[#555] text-white rounded text-xs font-medium transition-colors"
              >
                Load
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Instanced Agents Table */}
      <div className="space-y-2">
        <div className="text-[11px] text-[#666] uppercase tracking-wide font-medium">Instanced Agents</div>
        
        <div className="border border-[#2b2b2b] rounded overflow-hidden">
          {/* Table Header */}
          <div className="grid grid-cols-[60px_1fr_70px_80px] gap-2 px-3 py-2 bg-[#1a1a1a] border-b border-[#2b2b2b] text-[10px] text-[#666] uppercase tracking-wide">
            <div>ID</div>
            <div>Name</div>
            <div>State</div>
            <div className="text-right">Actions</div>
          </div>
          
          {/* Table Body */}
          {instancedAgents.length === 0 ? (
            <div className="px-3 py-4 text-center text-[#555] text-xs">
              No agents running. Create or load one below.
            </div>
          ) : (
            instancedAgents.map((agent) => (
              <div
                key={agent.id}
                onClick={() => handleAgentSelect(agent.id)}
                className={`grid grid-cols-[60px_1fr_70px_80px] gap-2 px-3 py-2 text-sm cursor-pointer transition-colors ${
                  selectedAgentId === agent.id 
                    ? 'bg-[#2b2b2b]' 
                    : 'hover:bg-[#1f1f1f]'
                }`}
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
                <div className="flex justify-end gap-1" onClick={(e) => e.stopPropagation()}>
                  {agent.state === 'running' ? (
                    <button
                      onClick={() => pauseAgent(agent.id)}
                      className="p-1.5 rounded hover:bg-[#eab308]/20 text-[#888] hover:text-[#eab308] transition-colors"
                      title="Pause"
                    >
                      <Pause size={14} />
                    </button>
                  ) : (
                    <button
                      onClick={() => resumeAgent(agent.id)}
                      className="p-1.5 rounded hover:bg-[#22c55e]/20 text-[#888] hover:text-[#22c55e] transition-colors"
                      title="Resume"
                    >
                      <Play size={14} />
                    </button>
                  )}
                  <button
                    onClick={() => stopAgent(agent.id)}
                    className="p-1.5 rounded hover:bg-[#ef4444]/20 text-[#888] hover:text-[#ef4444] transition-colors"
                    title="Stop"
                  >
                    <Square size={14} />
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
        
        {/* Create New Agent Button */}
        <button
          onClick={() => setShowCreationDialog(true)}
          className="w-full py-2 rounded flex items-center justify-center gap-2 text-xs font-medium transition-colors bg-[#2b2b2b] hover:bg-[#3b3b3b] text-[#888] hover:text-[#e5e5e5]"
        >
          <Plus size={14} /> Create New Agent
        </button>
        
        {/* Load Agent Button */}
        <button
          onClick={openLoadDialog}
          className="w-full py-2 rounded flex items-center justify-center gap-2 text-xs font-medium transition-colors bg-[#2b2b2b] hover:bg-[#3b3b3b] text-[#888] hover:text-[#e5e5e5]"
        >
          <FolderOpen size={14} /> Load Agent
        </button>
      </div>

      <hr className="border-[#2b2b2b]" />

      {/* Configuration Section - Only for selected instanced agents */}
      {selectedAgentId && selectedAgent && (
        <>
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div className="text-[11px] text-[#666] uppercase tracking-wide font-medium">
                Agent: {config.name || 'Unknown'}
              </div>
              <span className={`text-[10px] px-1.5 py-0.5 rounded ${
                isRunning ? 'bg-[#22c55e]/20 text-[#22c55e]' : 'bg-[#eab308]/20 text-[#eab308]'
              }`}>
                {isRunning ? 'Running' : 'Paused'}
              </span>
            </div>
            
            <div className="text-[10px] text-[#555] font-mono">
              ID: {selectedAgentId}
            </div>
          </div>

          <hr className="border-[#2b2b2b]" />

          {/* Autonomous Mode */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Clock size={14} className="text-[#888]" />
                <span className="text-[#888] text-xs uppercase tracking-wide font-medium">Autonomous Mode</span>
              </div>
              <button
                onClick={toggleAutonomous}
                disabled={!isRunning}
                className={`relative w-10 h-5 rounded-full transition-colors ${
                  config.autonomousEnabled ? 'bg-[#3b82f6]' : 'bg-[#2b2b2b]'
                } ${!isRunning ? 'opacity-50' : ''}`}
              >
                <div className={`absolute top-0.5 w-4 h-4 bg-white rounded-full transition-transform ${
                  config.autonomousEnabled ? 'translate-x-5' : 'translate-x-0.5'
                }`} />
              </button>
            </div>
            
            <p className="text-[10px] text-[#555]">
              Agent will periodically think and act on its own when enabled.
            </p>

            {config.autonomousEnabled && (
              <div className="space-y-2">
                <div className="flex justify-between text-xs">
                  <label className="text-[#888]">Interval</label>
                  <span className="text-[#666] font-mono">{config.autonomousInterval}s</span>
                </div>
                <input
                  type="range"
                  min="5"
                  max="120"
                  step="5"
                  value={config.autonomousInterval}
                  onChange={(e) => updateAutonomousInterval(parseInt(e.target.value))}
                  className="w-full accent-[#3b82f6]"
                />
              </div>
            )}

            {isRunning && (
              <button
                onClick={triggerTick}
                className="w-full py-2 bg-[#2b2b2b] hover:bg-[#3b3b3b] text-[#e5e5e5] rounded flex items-center justify-center gap-2 text-xs"
              >
                <Zap size={14} /> Trigger Manual Tick
              </button>
            )}
          </div>

          <hr className="border-[#2b2b2b]" />

          {/* Action Buttons */}
          <div className="flex gap-2">
            <button
              onClick={saveConfig}
              className="flex-1 py-2 bg-[#3b82f6] hover:bg-[#2563eb] text-white rounded flex items-center justify-center gap-2 text-xs font-medium transition-colors"
            >
              <Save size={14} /> Save Config
            </button>
            <button
              onClick={deleteAgent}
              className="py-2 px-3 bg-[#2b2b2b] hover:bg-[#ef4444] text-[#888] hover:text-white rounded flex items-center justify-center gap-2 text-xs font-medium transition-colors"
              title="Delete agent"
            >
              <Trash2 size={14} />
            </button>
          </div>
        </>
      )}

      {/* Empty State */}
      {!selectedAgentId && (
        <div className="text-center py-8 text-[#555] text-xs">
          Select an agent above or create a new one
        </div>
      )}
    </div>
  );
}
