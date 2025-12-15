import React, { useState, useEffect, useRef } from 'react';
import { socket } from '../lib/socket';
import { Bot, Brain, Database, MessageCircle, Monitor, Wrench, Clock, Box, Share2, X, GitMerge, Mic } from 'lucide-react';

const NODE_ICONS = {
  agent: Bot,
  knowledge_graph: Brain,
  memory_stream: Database,
  toolbox: Wrench,
  text_input: MessageCircle,
  voice_input: Mic,
  text_output: Monitor,
  scheduled_event: Clock,
  wait_and_combine: GitMerge,
};

const NODE_COLORS = {
  agent: '#3b82f6',
  knowledge_graph: '#a855f7',
  memory_stream: '#22c55e',
  toolbox: '#f97316',
  text_input: '#eab308',
  voice_input: '#8b5cf6',
  text_output: '#ef4444',
  scheduled_event: '#06b6d4',
  wait_and_combine: '#ec4899',
};

// Knowledge Graph display component
function KnowledgeGraphDisplay({ nodeId, isDeployed }) {
  const [entities, setEntities] = useState([]);
  const [relationships, setRelationships] = useState([]);
  const [selectedEntityName, setSelectedEntityName] = useState(null);
  const [selectedRelationshipKey, setSelectedRelationshipKey] = useState(null);
  const currentNodeId = useRef(nodeId);

  const selectedEntity = selectedEntityName ? entities.find(e => e.name === selectedEntityName) : null;
  const selectedRelationship = selectedRelationshipKey ? relationships.find(r => 
    `${r.from}-${r.type}-${r.to}` === selectedRelationshipKey
  ) : null;

  const relKey = (r) => `${r.from}-${r.type}-${r.to}`;

  useEffect(() => {
    currentNodeId.current = nodeId;
    
    // Request KG data when node is selected
    if (nodeId && isDeployed) {
      socket.emit('get_node_kg_data', { node_id: nodeId });
    } else {
      setEntities([]);
      setRelationships([]);
    }
    
    // Clear selection when node changes
    setSelectedEntityName(null);
    setSelectedRelationshipKey(null);
  }, [nodeId, isDeployed]);

  useEffect(() => {
    // Listen for KG data response
    const handleNodeKgData = (data) => {
      if (data.node_id === currentNodeId.current) {
        setEntities(data.entities || []);
        setRelationships(data.relationships || []);
      }
    };

    // Listen for real-time updates via agent_event
    const handleAgentEvent = (event) => {
      if (event.type !== 'tool.selected') return;
      
      const { tool_name, arguments: args } = event.data;
      const parsedArgs = typeof args === 'string' ? JSON.parse(args) : args;

      // Add Entity
      if (tool_name === 'AddEntity' && parsedArgs.name) {
        setEntities(prev => prev.find(e => e.name === parsedArgs.name) 
          ? prev 
          : [...prev, { name: parsedArgs.name, type: parsedArgs.type || 'Entity', properties: {} }]
        );
      }

      // Add Property to Entity
      if (tool_name === 'AddPropertyToEntity' && parsedArgs.entity) {
        setEntities(prev => {
          const exists = prev.find(e => e.name === parsedArgs.entity);
          if (exists) {
            return prev.map(e => e.name === parsedArgs.entity 
              ? { ...e, properties: { ...e.properties, [parsedArgs.property]: parsedArgs.value } } 
              : e
            );
          }
          return [...prev, { name: parsedArgs.entity, type: 'Entity', properties: { [parsedArgs.property]: parsedArgs.value } }];
        });
      }

      // Add Relationship
      if (tool_name === 'AddRelationship' && parsedArgs.entity1 && parsedArgs.entity2) {
        setEntities(prev => {
          let updated = [...prev];
          if (!updated.find(e => e.name === parsedArgs.entity1)) {
            updated.push({ name: parsedArgs.entity1, type: 'Entity', properties: {} });
          }
          if (!updated.find(e => e.name === parsedArgs.entity2)) {
            updated.push({ name: parsedArgs.entity2, type: 'Entity', properties: {} });
          }
          return updated;
        });
        setRelationships(prev => {
          const exists = prev.find(r => 
            r.from === parsedArgs.entity1 && 
            r.to === parsedArgs.entity2 && 
            r.type === parsedArgs.relationship
          );
          return exists ? prev : [...prev, { 
            from: parsedArgs.entity1, 
            to: parsedArgs.entity2, 
            type: parsedArgs.relationship,
            properties: {}
          }];
        });
      }

      // Remove Entity
      if (tool_name === 'RemoveEntity' && parsedArgs.entity) {
        setEntities(prev => prev.filter(e => e.name !== parsedArgs.entity));
        setRelationships(prev => prev.filter(r => 
          r.from !== parsedArgs.entity && r.to !== parsedArgs.entity
        ));
        if (selectedEntityName === parsedArgs.entity) {
          setSelectedEntityName(null);
        }
      }

      // Remove Relationship
      if (tool_name === 'RemoveRelationship' && parsedArgs.entity1 && parsedArgs.entity2) {
        const keyToRemove = `${parsedArgs.entity1}-${parsedArgs.relationship}-${parsedArgs.entity2}`;
        if (selectedRelationshipKey === keyToRemove) {
          setSelectedRelationshipKey(null);
        }
        setRelationships(prev => prev.filter(r => 
          !(r.from === parsedArgs.entity1 && 
            r.to === parsedArgs.entity2 && 
            r.type === parsedArgs.relationship)
        ));
      }
    };

    socket.on('node_kg_data', handleNodeKgData);
    socket.on('agent_event', handleAgentEvent);

    return () => {
      socket.off('node_kg_data', handleNodeKgData);
      socket.off('agent_event', handleAgentEvent);
    };
  }, [selectedEntityName, selectedRelationshipKey]);

  const handleEntityClick = (name) => {
    setSelectedEntityName(name);
    setSelectedRelationshipKey(null);
  };

  const handleRelationshipClick = (r) => {
    const key = relKey(r);
    setSelectedRelationshipKey(selectedRelationshipKey === key ? null : key);
    setSelectedEntityName(null);
  };

  if (!isDeployed) {
    return (
      <div className="text-xs text-[#555] p-3 bg-[#1a1a1a] rounded border border-[#2b2b2b]">
        Deploy the project to view knowledge graph contents.
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {/* Selected Entity Details */}
      {selectedEntity && (
        <div className="p-2 bg-[#111] rounded border border-[#2b2b2b]">
          <div className="flex justify-between items-center mb-2">
            <span className="text-[#a855f7] font-medium text-xs">{selectedEntity.name}</span>
            <button onClick={() => setSelectedEntityName(null)} className="text-[#666] hover:text-white"><X size={12}/></button>
          </div>
          <div className="text-[10px] text-[#666] mb-1">Type: {selectedEntity.type}</div>
          <div className="text-[11px] text-[#888]">
            {Object.entries(selectedEntity.properties || {}).map(([k, v]) => <div key={k}>{k}: {String(v)}</div>)}
            {Object.keys(selectedEntity.properties || {}).length === 0 && <div className="text-[#555] italic">No properties</div>}
          </div>
        </div>
      )}

      {/* Selected Relationship Details */}
      {selectedRelationship && (
        <div className="p-2 bg-[#111] rounded border border-[#eab308]/30">
          <div className="flex justify-between items-center mb-2">
            <span className="text-[#eab308] font-medium text-[11px]">
              {selectedRelationship.from} → {selectedRelationship.type} → {selectedRelationship.to}
            </span>
            <button onClick={() => setSelectedRelationshipKey(null)} className="text-[#666] hover:text-white"><X size={12}/></button>
          </div>
          <div className="text-[11px] text-[#888]">
            {selectedRelationship.properties && Object.entries(selectedRelationship.properties).map(([k, v]) => (
              <div key={k}>{k}: {String(v)}</div>
            ))}
            {(!selectedRelationship.properties || Object.keys(selectedRelationship.properties).length === 0) && (
              <div className="text-[#555] italic">No properties</div>
            )}
          </div>
        </div>
      )}

      {/* Entities List */}
      <div>
        <div className="text-[10px] text-[#666] uppercase mb-1">Entities ({entities.length})</div>
        <div className="max-h-32 overflow-y-auto bg-[#0a0a0a] border border-[#2b2b2b] rounded">
          {entities.length === 0 && <div className="text-[10px] text-[#555] italic px-2 py-2">No entities yet</div>}
          {entities.map((e, i) => (
            <div 
              key={i} 
              onClick={() => handleEntityClick(e.name)} 
              className={`flex items-center gap-2 px-2 py-1 cursor-pointer ${selectedEntityName === e.name ? 'bg-[#a855f7]/20' : 'hover:bg-[#1a1a1a]'}`}
            >
              <Box size={10} className="text-[#666] flex-shrink-0"/>
              <span className="text-xs truncate flex-1">{e.name}</span>
              <span className="text-[9px] text-[#555]">{e.type}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Relationships List */}
      <div>
        <div className="text-[10px] text-[#666] uppercase mb-1">Relationships ({relationships.length})</div>
        <div className="max-h-32 overflow-y-auto bg-[#0a0a0a] border border-[#2b2b2b] rounded">
          {relationships.length === 0 && <div className="text-[10px] text-[#555] italic px-2 py-2">No relationships yet</div>}
          {relationships.map((r, i) => {
            const key = relKey(r);
            const hasProps = r.properties && Object.keys(r.properties).length > 0;
            return (
              <div 
                key={i} 
                onClick={() => handleRelationshipClick(r)}
                className={`flex items-center gap-1 px-2 py-1 text-[11px] cursor-pointer ${
                  selectedRelationshipKey === key ? 'bg-[#eab308]/20' : 'hover:bg-[#1a1a1a]'
                }`}
              >
                <Share2 size={10} className="text-[#eab308] shrink-0"/>
                <span className="truncate">{r.from}</span>
                <span className="text-[#555]">→</span>
                <span className="text-[#888]">{r.type}</span>
                <span className="text-[#555]">→</span>
                <span className="truncate">{r.to}</span>
                {hasProps && <span className="text-[9px] text-[#eab308] ml-1">●</span>}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

export default function NodeInspectorTab({ selectedNode, isDeployed }) {
  const [templates, setTemplates] = useState([]);
  const [tools, setTools] = useState({ tools: [], presets: {} });

  useEffect(() => {
    socket.emit('get_templates');
    socket.emit('get_tools');

    const handleTemplatesList = (data) => {
      setTemplates(data.templates || []);
    };

    const handleToolsList = (data) => {
      setTools(data);
    };

    socket.on('templates_list', handleTemplatesList);
    socket.on('tools_list', handleToolsList);

    return () => {
      socket.off('templates_list', handleTemplatesList);
      socket.off('tools_list', handleToolsList);
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

        {/* Text/Voice Input/Output - minimal config */}
        {(selectedNode.type === 'text_input' || selectedNode.type === 'voice_input' || selectedNode.type === 'text_output') && (
          <div className="text-xs text-[#555]">
            {selectedNode.type === 'text_input' && 'Routes typed text from the chat input field.'}
            {selectedNode.type === 'voice_input' && 'Routes voice-transcribed text from speech input.'}
            {selectedNode.type === 'text_output' && 'Displays agent responses in the chat.'}
          </div>
        )}

        {/* Knowledge Graph - show entities and relationships */}
        {selectedNode.type === 'knowledge_graph' && (
          <KnowledgeGraphDisplay nodeId={selectedNode.id} isDeployed={isDeployed} />
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

            <div>
              <label className="text-[10px] text-[#666] uppercase tracking-wide block mb-1">Message Content</label>
              <textarea
                value={config.message_content || 'Review your current state and pending tasks.'}
                onChange={(e) => updateConfig('message_content', e.target.value)}
                disabled={isDeployed}
                rows={3}
                className="w-full px-3 py-2 bg-[#0a0a0a] border border-[#2b2b2b] rounded text-xs text-[#e5e5e5] disabled:opacity-50 focus:outline-none focus:border-[#06b6d4] resize-none"
                placeholder="Message to send to the agent..."
              />
              <p className="text-[10px] text-[#555] mt-1">
                This message will be sent to the connected agent when the event fires.
              </p>
            </div>

            <div className="text-xs text-[#555] p-3 bg-[#1a1a1a] rounded border border-[#2b2b2b]">
              Connect the <span className="text-[#06b6d4]">message_out</span> port to an <span className="text-[#3b82f6]">Agent's</span> <span className="text-[#3b82f6]">message_in</span> port to schedule message delivery.
            </div>
          </>
        )}

        {/* Wait and Combine config */}
        {selectedNode.type === 'wait_and_combine' && (
          <>
            <div className="text-xs text-[#555] p-3 bg-[#1a1a1a] rounded border border-[#2b2b2b]">
              <p className="mb-2">
                <strong className="text-[#ec4899]">Rendezvous Point</strong>
              </p>
              <p className="mb-2">
                This node waits for messages from <strong>all</strong> connected senders before forwarding them as a combined batch.
              </p>
              <p>
                Connect multiple <span className="text-[#3b82f6]">message_out</span> ports to this node's <span className="text-[#ec4899]">message_in</span>, then connect <span className="text-[#ec4899]">message_out</span> to an <span className="text-[#3b82f6]">Agent</span> to receive the combined messages.
              </p>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
