import React, { useState, useEffect } from 'react';
import { socket } from '../lib/socket';
import { Bot, Brain, Database, MessageCircle, Monitor, Wrench, Clock } from 'lucide-react';

const NODE_ICONS = {
  agent: Bot,
  knowledge_graph: Brain,
  memory_stream: Database,
  toolbox: Wrench,
  user_input: MessageCircle,
  user_output: Monitor,
  scheduled_event: Clock,
};

const NODE_COLORS = {
  agent: '#3b82f6',
  knowledge_graph: '#a855f7',
  memory_stream: '#22c55e',
  toolbox: '#f97316',
  user_input: '#eab308',
  user_output: '#ef4444',
  scheduled_event: '#06b6d4',
};

export default function NodeInspectorTab({ selectedNode, isDeployed }) {
  const [templates, setTemplates] = useState([]);
  const [tools, setTools] = useState({ tools: [], presets: {} });

  useEffect(() => {
    socket.emit('get_templates');
    socket.emit('get_tools');

    socket.on('templates_list', (data) => {
      setTemplates(data.templates || []);
    });

    socket.on('tools_list', (data) => {
      setTools(data);
    });

    return () => {
      socket.off('templates_list');
      socket.off('tools_list');
    };
  }, []);

  const updateConfig = (key, value) => {
    if (!selectedNode || isDeployed) return;
    socket.emit('update_node_config', { 
      id: selectedNode.id, 
      config: { [key]: value } 
    });
  };

  if (!selectedNode) {
    return (
      <div className="flex items-center justify-center h-full text-[#555] text-xs">
        Select a node to configure
      </div>
    );
  }

  const Icon = NODE_ICONS[selectedNode.type] || Bot;
  const color = NODE_COLORS[selectedNode.type] || '#666';
  const config = selectedNode.config || {};

  return (
    <div className="h-full overflow-y-auto">
      {/* Node Header */}
      <div 
        className="px-4 py-3 border-b border-[#2b2b2b]"
        style={{ backgroundColor: color + '10' }}
      >
        <div className="flex items-center gap-2">
          <Icon size={16} style={{ color }} />
          <span className="text-sm font-medium text-[#e5e5e5]">
            {config.name || selectedNode.type}
          </span>
        </div>
        <div className="text-[10px] text-[#555] font-mono mt-1">
          {selectedNode.id}
        </div>
      </div>

      {isDeployed && (
        <div className="px-4 py-2 bg-[#ef4444]/10 border-b border-[#2b2b2b] text-[10px] text-[#ef4444]">
          Undeploy to edit configuration
        </div>
      )}

      <div className="p-4 space-y-4">
        {/* Common: Name */}
        <div>
          <label className="text-[10px] text-[#666] uppercase tracking-wide block mb-1">Name</label>
          <input
            type="text"
            value={config.name || ''}
            onChange={(e) => updateConfig('name', e.target.value)}
            disabled={isDeployed}
            className="w-full px-3 py-2 bg-[#0a0a0a] border border-[#2b2b2b] rounded text-xs text-[#e5e5e5] disabled:opacity-50 focus:outline-none focus:border-[#3b82f6]"
          />
        </div>

        {/* Agent-specific fields */}
        {selectedNode.type === 'agent' && (
          <>
            <div>
              <label className="text-[10px] text-[#666] uppercase tracking-wide block mb-1">Model</label>
              <input
                type="text"
                value={config.model || ''}
                onChange={(e) => updateConfig('model', e.target.value)}
                disabled={isDeployed}
                className="w-full px-3 py-2 bg-[#0a0a0a] border border-[#2b2b2b] rounded text-xs text-[#e5e5e5] disabled:opacity-50 focus:outline-none focus:border-[#3b82f6]"
              />
            </div>

            <div>
              <label className="text-[10px] text-[#666] uppercase tracking-wide block mb-1">API URL</label>
              <input
                type="text"
                value={config.api_url || ''}
                onChange={(e) => updateConfig('api_url', e.target.value)}
                disabled={isDeployed}
                className="w-full px-3 py-2 bg-[#0a0a0a] border border-[#2b2b2b] rounded text-xs text-[#e5e5e5] disabled:opacity-50 focus:outline-none focus:border-[#3b82f6]"
              />
            </div>

            <div>
              <label className="text-[10px] text-[#666] uppercase tracking-wide block mb-1">API Key</label>
              <input
                type="password"
                value={config.api_key || ''}
                onChange={(e) => updateConfig('api_key', e.target.value)}
                disabled={isDeployed}
                placeholder="Optional"
                className="w-full px-3 py-2 bg-[#0a0a0a] border border-[#2b2b2b] rounded text-xs text-[#e5e5e5] disabled:opacity-50 focus:outline-none focus:border-[#3b82f6]"
              />
            </div>

            <div>
              <label className="text-[10px] text-[#666] uppercase tracking-wide block mb-1">System Template</label>
              <select
                value={config.system_template || 'agent'}
                onChange={(e) => updateConfig('system_template', e.target.value)}
                disabled={isDeployed}
                className="w-full px-3 py-2 bg-[#0a0a0a] border border-[#2b2b2b] rounded text-xs text-[#e5e5e5] disabled:opacity-50 focus:outline-none focus:border-[#3b82f6]"
              >
                {templates.map(t => (
                  <option key={t} value={t}>{t}</option>
                ))}
              </select>
            </div>

            <div className="text-xs text-[#555] p-3 bg-[#1a1a1a] rounded border border-[#2b2b2b]">
              Connect a <span className="text-[#f97316]">Toolbox</span> node to give this agent access to tools.
              <br /><br />
              Connect a <span className="text-[#06b6d4]">Scheduled Event</span> node to trigger this agent on a schedule.
            </div>
          </>
        )}

        {/* Memory Stream specific fields */}
        {selectedNode.type === 'memory_stream' && (
          <div>
            <label className="text-[10px] text-[#666] uppercase tracking-wide block mb-1">Max Observations</label>
            <input
              type="number"
              value={config.max_observations || 1000}
              onChange={(e) => updateConfig('max_observations', parseInt(e.target.value))}
              disabled={isDeployed}
              className="w-full px-3 py-2 bg-[#0a0a0a] border border-[#2b2b2b] rounded text-xs text-[#e5e5e5] disabled:opacity-50 focus:outline-none focus:border-[#3b82f6]"
            />
          </div>
        )}

        {/* User Input/Output - minimal config */}
        {(selectedNode.type === 'user_input' || selectedNode.type === 'user_output') && (
          <div className="text-xs text-[#555]">
            This node connects the agent graph to the chat interface.
          </div>
        )}

        {/* Knowledge Graph - minimal config */}
        {selectedNode.type === 'knowledge_graph' && (
          <div className="text-xs text-[#555]">
            Connect agents to this node to share a knowledge graph.
          </div>
        )}

        {/* Toolbox - tool selection */}
        {selectedNode.type === 'toolbox' && (
          <>
            <div>
              <label className="text-[10px] text-[#666] uppercase tracking-wide block mb-1">Tool Preset</label>
              <select
                onChange={(e) => {
                  const preset = e.target.value;
                  if (preset && tools.presets[preset]) {
                    updateConfig('tools', tools.presets[preset]);
                  }
                }}
                disabled={isDeployed}
                className="w-full px-3 py-2 bg-[#0a0a0a] border border-[#2b2b2b] rounded text-xs text-[#e5e5e5] disabled:opacity-50 focus:outline-none focus:border-[#3b82f6]"
              >
                <option value="">Select preset...</option>
                {Object.keys(tools.presets || {}).map(p => (
                  <option key={p} value={p}>{p}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="text-[10px] text-[#666] uppercase tracking-wide block mb-1">
                Tools ({(config.tools || []).length} selected)
              </label>
              <div className="max-h-48 overflow-y-auto bg-[#0a0a0a] border border-[#2b2b2b] rounded p-2 space-y-1">
                {(tools.tools || []).map(tool => (
                  <label key={tool} className="flex items-center gap-2 text-xs text-[#888] hover:text-[#e5e5e5] cursor-pointer">
                    <input
                      type="checkbox"
                      checked={(config.tools || []).includes(tool)}
                      onChange={(e) => {
                        const currentTools = config.tools || [];
                        const newTools = e.target.checked
                          ? [...currentTools, tool]
                          : currentTools.filter(t => t !== tool);
                        updateConfig('tools', newTools);
                      }}
                      disabled={isDeployed}
                      className="accent-[#f97316]"
                    />
                    {tool}
                  </label>
                ))}
              </div>
            </div>

            <div className="text-xs text-[#555] p-3 bg-[#1a1a1a] rounded border border-[#2b2b2b]">
              Connect this toolbox to <span className="text-[#3b82f6]">Agent</span> nodes to give them access to these tools.
            </div>
          </>
        )}

        {/* Scheduled Event config */}
        {selectedNode.type === 'scheduled_event' && (
          <>
            <div>
              <label className="text-[10px] text-[#666] uppercase tracking-wide block mb-1">Trigger Type</label>
              <select
                value={config.trigger_type || 'interval'}
                onChange={(e) => updateConfig('trigger_type', e.target.value)}
                disabled={isDeployed}
                className="w-full px-3 py-2 bg-[#0a0a0a] border border-[#2b2b2b] rounded text-xs text-[#e5e5e5] disabled:opacity-50 focus:outline-none focus:border-[#06b6d4]"
              >
                <option value="once">Once (at specific time)</option>
                <option value="interval">Interval (repeating)</option>
              </select>
            </div>

            {config.trigger_type === 'once' && (
              <div>
                <label className="text-[10px] text-[#666] uppercase tracking-wide block mb-1">Run At</label>
                <input
                  type="datetime-local"
                  value={config.run_at ? config.run_at.slice(0, 16) : ''}
                  onChange={(e) => updateConfig('run_at', e.target.value ? new Date(e.target.value).toISOString() : null)}
                  disabled={isDeployed}
                  className="w-full px-3 py-2 bg-[#0a0a0a] border border-[#2b2b2b] rounded text-xs text-[#e5e5e5] disabled:opacity-50 focus:outline-none focus:border-[#06b6d4]"
                />
                <p className="text-[10px] text-[#555] mt-1">
                  The event will trigger once at this time after deployment.
                </p>
              </div>
            )}

            {(config.trigger_type === 'interval' || !config.trigger_type) && (
              <div>
                <label className="text-[10px] text-[#666] uppercase tracking-wide block mb-1">
                  Interval: {config.interval_seconds || 30} seconds
                </label>
                <input
                  type="range"
                  min="5"
                  max="300"
                  step="5"
                  value={config.interval_seconds || 30}
                  onChange={(e) => updateConfig('interval_seconds', parseInt(e.target.value))}
                  disabled={isDeployed}
                  className="w-full accent-[#06b6d4]"
                />
                <div className="flex justify-between text-[9px] text-[#555] mt-1">
                  <span>5s</span>
                  <span>5 min</span>
                </div>
              </div>
            )}

            <div className="text-xs text-[#555] p-3 bg-[#1a1a1a] rounded border border-[#2b2b2b]">
              Connect the <span className="text-[#eab308]">trigger_out</span> port to an <span className="text-[#3b82f6]">Agent's</span> <span className="text-[#eab308]">trigger_in</span> port to schedule agent activation.
            </div>
          </>
        )}
      </div>
    </div>
  );
}

