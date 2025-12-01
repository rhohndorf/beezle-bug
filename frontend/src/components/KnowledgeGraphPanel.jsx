import React, { useState, useEffect } from 'react';
import { socket } from '../lib/socket';
import { Database, Box, Share2, Trash, X } from 'lucide-react';

export default function KnowledgeGraphPanel({ selectedAgentId }) {
  const [entities, setEntities] = useState([]);
  const [relationships, setRelationships] = useState([]);
  const [selectedEntityName, setSelectedEntityName] = useState(null);
  const [selectedRelationshipKey, setSelectedRelationshipKey] = useState(null);

  const selectedEntity = selectedEntityName ? entities.find(e => e.name === selectedEntityName) : null;
  const selectedRelationship = selectedRelationshipKey ? relationships.find(r => 
    `${r.from}-${r.type}-${r.to}` === selectedRelationshipKey
  ) : null;

  // Helper to create relationship key
  const relKey = (r) => `${r.from}-${r.type}-${r.to}`;

  // Clear display and request KG when selected agent changes
  useEffect(() => {
    setEntities([]);
    setRelationships([]);
    setSelectedEntityName(null);
    setSelectedRelationshipKey(null);
    
    if (selectedAgentId) {
      socket.emit('get_knowledge_graph', { id: selectedAgentId });
    }
  }, [selectedAgentId]);

  useEffect(() => {
    // Listen for full knowledge graph state (when agent loads)
    function onKnowledgeGraphState(data) {
      // Only update if it's for the selected agent
      if (data.agentId !== selectedAgentId) return;
      
      if (data.entities && data.relationships) {
        setEntities(data.entities);
        setRelationships(data.relationships);
        setSelectedEntityName(null);
        setSelectedRelationshipKey(null);
      }
    }
    socket.on('knowledge_graph_state', onKnowledgeGraphState);
    
    return () => socket.off('knowledge_graph_state', onKnowledgeGraphState);
  }, [selectedAgentId]);

  useEffect(() => {
    function onAgentEvent(event) {
      // Only process events for the selected agent
      if (event.agentId !== selectedAgentId) return;
      
      if (event.type === 'tool.selected') {
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

        // Add Property to Relationship
        if (tool_name === 'AddPropertyToRelationship' && parsedArgs.entity1 && parsedArgs.entity2) {
          setRelationships(prev => prev.map(r => {
            if (r.from === parsedArgs.entity1 && 
                r.to === parsedArgs.entity2 && 
                r.type === parsedArgs.relationship) {
              return { 
                ...r, 
                properties: { ...r.properties, [parsedArgs.property]: parsedArgs.value } 
              };
            }
            return r;
          }));
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

        // Remove Relationship Property
        if (tool_name === 'RemoveRelationshipProperty' && parsedArgs.entity1 && parsedArgs.entity2) {
          setRelationships(prev => prev.map(r => {
            if (r.from === parsedArgs.entity1 && 
                r.to === parsedArgs.entity2 && 
                r.type === parsedArgs.relationship) {
              const { [parsedArgs.property]: _, ...remainingProps } = r.properties || {};
              return { ...r, properties: remainingProps };
            }
            return r;
          }));
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

        // Remove Entity Property
        if (tool_name === 'RemoveEntityProperty' && parsedArgs.entity && parsedArgs.property) {
          setEntities(prev => prev.map(e => {
            if (e.name === parsedArgs.entity) {
              const { [parsedArgs.property]: _, ...remainingProps } = e.properties;
              return { ...e, properties: remainingProps };
            }
            return e;
          }));
        }
      }
    }
    socket.on('agent_event', onAgentEvent);
    return () => socket.off('agent_event', onAgentEvent);
  }, [selectedAgentId, selectedEntityName, selectedRelationshipKey]);

  const handleRelationshipClick = (r) => {
    const key = relKey(r);
    setSelectedRelationshipKey(selectedRelationshipKey === key ? null : key);
    setSelectedEntityName(null);
  };

  const handleEntityClick = (name) => {
    setSelectedEntityName(name);
    setSelectedRelationshipKey(null);
  };

  return (
    <div className="flex flex-col h-full text-[13px] border-t border-[#2b2b2b]">
      <div className="h-8 px-3 border-b border-[#2b2b2b] flex items-center justify-between text-[#888]">
        <span className="flex items-center gap-2 text-xs uppercase tracking-wide"><Database size={14}/>Knowledge Graph</span>
        <button onClick={() => { setEntities([]); setRelationships([]); setSelectedEntityName(null); setSelectedRelationshipKey(null); }} className="hover:text-white"><Trash size={12}/></button>
      </div>

      <div className="flex-1 overflow-y-auto p-2">
        {/* Selected Entity Details */}
        {selectedEntity && (
          <div className="mb-3 p-2 bg-[#111] rounded border border-[#2b2b2b]">
            <div className="flex justify-between items-center mb-2">
              <span className="text-[#3b82f6] font-medium">{selectedEntity.name}</span>
              <button onClick={() => setSelectedEntityName(null)} className="text-[#666] hover:text-white"><X size={12}/></button>
            </div>
            <div className="text-[10px] text-[#666] mb-1">Type: {selectedEntity.type}</div>
            <div className="text-[11px] text-[#888]">
              {Object.entries(selectedEntity.properties).map(([k, v]) => <div key={k}>{k}: {v}</div>)}
              {Object.keys(selectedEntity.properties).length === 0 && <div className="text-[#555] italic">No properties</div>}
            </div>
          </div>
        )}

        {/* Selected Relationship Details */}
        {selectedRelationship && (
          <div className="mb-3 p-2 bg-[#111] rounded border border-[#eab308]/30">
            <div className="flex justify-between items-center mb-2">
              <span className="text-[#eab308] font-medium text-[11px]">
                {selectedRelationship.from} → {selectedRelationship.type} → {selectedRelationship.to}
              </span>
              <button onClick={() => setSelectedRelationshipKey(null)} className="text-[#666] hover:text-white"><X size={12}/></button>
            </div>
            <div className="text-[10px] text-[#666] mb-1">Relationship Properties:</div>
            <div className="text-[11px] text-[#888]">
              {selectedRelationship.properties && Object.entries(selectedRelationship.properties).map(([k, v]) => (
                <div key={k}>{k}: {v}</div>
              ))}
              {(!selectedRelationship.properties || Object.keys(selectedRelationship.properties).length === 0) && (
                <div className="text-[#555] italic">No properties</div>
              )}
            </div>
          </div>
        )}

        {/* Entities List */}
        <div className="mb-3">
          <div className="text-[10px] text-[#666] uppercase mb-1">Entities ({entities.length})</div>
          {entities.length === 0 && <div className="text-[10px] text-[#555] italic px-2">No entities yet</div>}
          {entities.map((e, i) => (
            <div 
              key={i} 
              onClick={() => handleEntityClick(e.name)} 
              className={`flex items-center gap-2 px-2 py-1 rounded cursor-pointer ${selectedEntityName === e.name ? 'bg-[#3b82f6]/20' : 'hover:bg-[#1a1a1a]'}`}
            >
              <Box size={12} className="text-[#666]"/>
              <span className="truncate flex-1">{e.name}</span>
              <span className="text-[9px] text-[#555]">{e.type}</span>
            </div>
          ))}
        </div>

        {/* Relationships List */}
        <div>
          <div className="text-[10px] text-[#666] uppercase mb-1">Relationships ({relationships.length})</div>
          {relationships.length === 0 && <div className="text-[10px] text-[#555] italic px-2">No relationships yet</div>}
          {relationships.map((r, i) => {
            const key = relKey(r);
            const hasProps = r.properties && Object.keys(r.properties).length > 0;
            return (
              <div 
                key={i} 
                onClick={() => handleRelationshipClick(r)}
                className={`flex items-center gap-1 px-2 py-1 text-[11px] rounded cursor-pointer ${
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
