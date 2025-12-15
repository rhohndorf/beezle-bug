import React, { useState, useRef, useCallback, useEffect } from 'react';
import { socket } from '../lib/socket';
import { 
  Plus, Trash2, Bot, Database, 
  MessageCircle, Monitor, Brain, Maximize2, ZoomIn, ZoomOut,
  Wrench, Clock, GitMerge, Mic
} from 'lucide-react';

// Node type definitions for the agent graph
const NODE_TYPES = {
  agent: { 
    label: 'Agent', 
    color: '#3b82f6', 
    icon: Bot,
    category: 'Agents',
    defaultConfig: { name: 'New Agent', model: 'gpt-4', api_url: 'http://127.0.0.1:1234/v1', api_key: '', system_template: 'agent' }
  },
  knowledge_graph: { 
    label: 'Knowledge Graph', 
    color: '#a855f7', 
    icon: Brain,
    category: 'Memory',
    defaultConfig: { name: 'Knowledge Graph' }
  },
  memory_stream: { 
    label: 'Memory Stream', 
    color: '#22c55e', 
    icon: Database,
    category: 'Memory',
    defaultConfig: { name: 'Memory Stream', max_observations: 1000 }
  },
  toolbox: { 
    label: 'Toolbox', 
    color: '#f97316', 
    icon: Wrench,
    category: 'Resources',
    defaultConfig: { name: 'Toolbox', tools: [] }
  },
  text_input: { 
    label: 'Text Input', 
    color: '#eab308', 
    icon: MessageCircle,
    category: 'Inputs',
    defaultConfig: { name: 'Text Input' }
  },
  voice_input: { 
    label: 'Voice Input', 
    color: '#8b5cf6', 
    icon: Mic,
    category: 'Inputs',
    defaultConfig: { name: 'Voice Input' }
  },
  text_output: { 
    label: 'Text Output', 
    color: '#ef4444', 
    icon: Monitor,
    category: 'Outputs',
    defaultConfig: { name: 'Text Output' }
  },
  scheduled_event: { 
    label: 'Scheduled Event', 
    color: '#06b6d4', 
    icon: Clock,
    category: 'Flow Control',
    defaultConfig: { name: 'Scheduled Event', trigger_type: 'interval', interval_seconds: 30 }
  },
  wait_and_combine: { 
    label: 'Wait & Combine', 
    color: '#ec4899', 
    icon: GitMerge,
    category: 'Flow Control',
    defaultConfig: { name: 'Wait and Combine' }
  },
};

// Categories for grouping nodes in the palette
const NODE_CATEGORIES = [
  'Agents',
  'Inputs',
  'Outputs',
  'Memory',
  'Resources',
  'Flow Control',
];

// Edge type definitions
const EDGE_TYPES = {
  message: { label: 'Message', color: '#3b82f6' },
  pipeline: { label: 'Pipeline', color: '#22c55e' },
  resource: { label: 'Resource', color: '#a855f7', dashed: true },
  delegate: { label: 'Delegate', color: '#f97316', dashed: true },
};

export default function NodeGraph({ onSelectNode, selectedNodeId }) {
  // Agent graph state from server
  const [projectId, setProjectId] = useState(null);
  const [nodes, setNodes] = useState([]);
  const [edges, setEdges] = useState([]);
  const [isDeployed, setIsDeployed] = useState(false);
  
  // UI state
  const [selectedNode, setSelectedNode] = useState(null);
  const [dragging, setDragging] = useState(null);
  const [offset, setOffset] = useState({ x: 0, y: 0 });
  const [showPalette, setShowPalette] = useState(false);
  
  // Connection dragging state
  const [dragConnection, setDragConnection] = useState(null); // { nodeId, portId, portType, isOutput }
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 });
  
  // Pan and zoom state
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [zoom, setZoom] = useState(1);
  const [isPanning, setIsPanning] = useState(false);
  const [panStart, setPanStart] = useState({ x: 0, y: 0 });
  
  const canvasRef = useRef(null);
  const NODE_WIDTH = 200;
  const PORT_SIZE = 12;
  const HEADER_HEIGHT = 36;
  const PORT_SPACING = 24;

  // Notify parent when selection changes
  useEffect(() => {
    if (onSelectNode && selectedNode) {
      const node = nodes.find(n => n.id === selectedNode);
      onSelectNode(node || null);
    } else if (onSelectNode) {
      onSelectNode(null);
    }
  }, [selectedNode, nodes, onSelectNode]);

  // Socket listeners
  useEffect(() => {
    const handleAgentGraphState = (data) => {
      setProjectId(data.project_id || null);
      setIsDeployed(data.is_deployed || false);
      setNodes(data.nodes || []);
      setEdges(data.edges || []);
    };

    const handleProjectStopped = () => {
      setProjectId(null);
      setNodes([]);
      setEdges([]);
    };

    socket.on('agent_graph_state', handleAgentGraphState);
    socket.on('project_stopped', handleProjectStopped);

    // Request current state
    socket.emit('get_agent_graph_state');

    return () => {
      socket.off('agent_graph_state', handleAgentGraphState);
      socket.off('project_stopped', handleProjectStopped);
    };
  }, []);

  // Add a new node
  const addNode = (type, x = 200 + Math.random() * 200, y = 150 + Math.random() * 200) => {
    if (!projectId) {
      alert('Please create or load a project first');
      return;
    }
    
    const nodeType = NODE_TYPES[type];
    if (!nodeType) return;

    socket.emit('add_node', {
      type,
      x,
      y,
      config: { ...nodeType.defaultConfig }
    });
    
    setShowPalette(false);
  };

  // Delete selected node
  const deleteNode = () => {
    if (!selectedNode) return;
    socket.emit('remove_node', { id: selectedNode });
    setSelectedNode(null);
  };

  // Update node configuration
  const updateNodeConfig = (nodeId, updates) => {
    setNodes(prev => prev.map(n => 
      n.id === nodeId 
        ? { ...n, config: { ...n.config, ...updates } }
        : n
    ));
    socket.emit('update_node_config', { id: nodeId, config: updates });
  };

  // Handle node drag
  const handleMouseDown = (e, nodeId) => {
    if (e.target.closest('.port')) return;
    const node = nodes.find(n => n.id === nodeId);
    if (node) {
      setDragging(nodeId);
      setOffset({ x: e.clientX - node.position.x, y: e.clientY - node.position.y });
      setSelectedNode(nodeId);
    }
  };

  const handleMouseMove = useCallback((e) => {
    if (dragging) {
      const newX = e.clientX - offset.x;
      const newY = e.clientY - offset.y;
      
      setNodes(prev => prev.map(n => 
        n.id === dragging 
          ? { ...n, position: { x: newX, y: newY } }
          : n
      ));
    }
  }, [dragging, offset]);

  const handleMouseUp = useCallback(() => {
    if (dragging) {
      const node = nodes.find(n => n.id === dragging);
      if (node) {
        socket.emit('update_node_position', {
          id: dragging,
          x: node.position.x,
          y: node.position.y
        });
      }
    }
    setDragging(null);
    setIsPanning(false);
  }, [dragging, nodes]);

  // Handle canvas pan (middle mouse or space+drag)
  const handleCanvasMouseDown = (e) => {
    if (e.button === 1 || (e.button === 0 && e.shiftKey)) {
      // Middle mouse button or shift+left click to pan
      setIsPanning(true);
      setPanStart({ x: e.clientX - pan.x, y: e.clientY - pan.y });
      e.preventDefault();
    }
  };

  const handleCanvasMouseMove = useCallback((e) => {
    if (isPanning) {
      setPan({
        x: e.clientX - panStart.x,
        y: e.clientY - panStart.y
      });
    }
  }, [isPanning, panStart]);

  // Handle zoom (mouse wheel)
  const handleWheel = useCallback((e) => {
    e.preventDefault();
    
    // Calculate zoom factor
    const delta = e.deltaY > 0 ? 0.9 : 1.1;
    const newZoom = Math.min(Math.max(zoom * delta, 0.25), 2);
    
    // Zoom toward mouse cursor
    if (canvasRef.current) {
      const rect = canvasRef.current.getBoundingClientRect();
      const mouseX = e.clientX - rect.left;
      const mouseY = e.clientY - rect.top;
      
      // Adjust pan to keep mouse position stable
      const scale = newZoom / zoom;
      setPan(p => ({
        x: mouseX - (mouseX - p.x) * scale,
        y: mouseY - (mouseY - p.y) * scale
      }));
    }
    
    setZoom(newZoom);
  }, [zoom]);

  // Reset view
  const resetView = () => {
    setPan({ x: 0, y: 0 });
    setZoom(1);
  };

  useEffect(() => {
    if (dragging) {
      window.addEventListener('mousemove', handleMouseMove);
      window.addEventListener('mouseup', handleMouseUp);
      return () => {
        window.removeEventListener('mousemove', handleMouseMove);
        window.removeEventListener('mouseup', handleMouseUp);
      };
    }
  }, [dragging, handleMouseMove, handleMouseUp]);

  // Pan event listeners
  useEffect(() => {
    if (isPanning) {
      window.addEventListener('mousemove', handleCanvasMouseMove);
      window.addEventListener('mouseup', handleMouseUp);
      return () => {
        window.removeEventListener('mousemove', handleCanvasMouseMove);
        window.removeEventListener('mouseup', handleMouseUp);
      };
    }
  }, [isPanning, handleCanvasMouseMove, handleMouseUp]);

  // Start dragging a connection from a port
  const handlePortMouseDown = (e, nodeId, portId, portType, isOutput) => {
    e.stopPropagation();
    e.preventDefault();
    
    const rect = canvasRef.current.getBoundingClientRect();
    const x = (e.clientX - rect.left - pan.x) / zoom;
    const y = (e.clientY - rect.top - pan.y) / zoom;
    
    setDragConnection({ nodeId, portId, portType, isOutput });
    setMousePos({ x, y });
  };

  // Handle mouse move for connection dragging
  const handleConnectionDrag = useCallback((e) => {
    if (!dragConnection || !canvasRef.current) return;
    
    const rect = canvasRef.current.getBoundingClientRect();
    const x = (e.clientX - rect.left - pan.x) / zoom;
    const y = (e.clientY - rect.top - pan.y) / zoom;
    setMousePos({ x, y });
  }, [dragConnection, pan, zoom]);

  // Complete connection on mouse up
  const handleConnectionEnd = useCallback((e) => {
    if (!dragConnection) return;
    
    // Find if we're over a port
    const target = e.target.closest('[data-port]');
    if (target) {
      const targetNodeId = target.dataset.nodeId;
      const targetPortId = target.dataset.portId;
      const targetPortType = target.dataset.portType;
      const targetIsOutput = target.dataset.isOutput === 'true';
      
      // Don't connect to same node or same port type
      if (targetNodeId !== dragConnection.nodeId && targetIsOutput !== dragConnection.isOutput) {
        const sourceNode = nodes.find(n => n.id === dragConnection.nodeId);
        const targetNode = nodes.find(n => n.id === targetNodeId);
        
        // Source is always the output side
        const srcNodeId = dragConnection.isOutput ? dragConnection.nodeId : targetNodeId;
        const srcPortId = dragConnection.isOutput ? dragConnection.portId : targetPortId;
        const tgtNodeId = dragConnection.isOutput ? targetNodeId : dragConnection.nodeId;
        const tgtPortId = dragConnection.isOutput ? targetPortId : dragConnection.portId;
        
        // Determine edge type based on ports and node types
        // Get the actual source and target nodes (based on connection direction)
        const actualSourceNode = nodes.find(n => n.id === srcNodeId);
        const actualTargetNode = nodes.find(n => n.id === tgtNodeId);
        
        let edgeType = 'message';
        if (sourceNode?.type === 'knowledge_graph' || targetNode?.type === 'knowledge_graph' ||
            sourceNode?.type === 'memory_stream' || targetNode?.type === 'memory_stream' ||
            sourceNode?.type === 'toolbox' || targetNode?.type === 'toolbox') {
          edgeType = 'resource';
        } else if (srcPortId === 'ask' && tgtPortId === 'answer') {
          // Agent-to-agent delegate connection
          edgeType = 'delegate';
        }
        // scheduled_event message_out -> agent message_in uses MESSAGE edge type (default)
        
        socket.emit('add_edge', {
          source_node: srcNodeId,
          source_port: srcPortId,
          target_node: tgtNodeId,
          target_port: tgtPortId,
          edge_type: edgeType
        });
      }
    }
    
    setDragConnection(null);
  }, [dragConnection, nodes]);

  // Listen for connection drag events
  useEffect(() => {
    if (dragConnection) {
      window.addEventListener('mousemove', handleConnectionDrag);
      window.addEventListener('mouseup', handleConnectionEnd);
      return () => {
        window.removeEventListener('mousemove', handleConnectionDrag);
        window.removeEventListener('mouseup', handleConnectionEnd);
      };
    }
  }, [dragConnection, handleConnectionDrag, handleConnectionEnd]);

  // Delete edge
  const deleteEdge = (edgeId) => {
    socket.emit('remove_edge', { id: edgeId });
  };

  // Get port position for drawing connections (returns center of port circle on node edge)
  const getPortPosition = useCallback((nodeId, portId, isOutput) => {
    const node = nodes.find(n => n.id === nodeId);
    if (!node) return { x: 0, y: 0 };
    
    const ports = node.ports || {};
    
    // Calculate port index based on which list it's in and position within that list
    let portIndex = 0;
    let found = false;
    
    // Check inputs
    const inputIdx = (ports.inputs || []).indexOf(portId);
    if (inputIdx !== -1 && !isOutput) {
      portIndex = inputIdx;
      found = true;
    }
    
    // Check bidirectional
    if (!found) {
      const biIdx = (ports.bidirectional || []).indexOf(portId);
      if (biIdx !== -1) {
        portIndex = (ports.inputs || []).length + biIdx;
        found = true;
      }
    }
    
    // Check outputs  
    if (!found) {
      const outIdx = (ports.outputs || []).indexOf(portId);
      if (outIdx !== -1) {
        portIndex = (ports.inputs || []).length + (ports.bidirectional || []).length + outIdx;
      }
    }
    
    // Position on edge
    const x = node.position.x + (isOutput ? NODE_WIDTH : 0);
    const y = node.position.y + HEADER_HEIGHT + PORT_SPACING / 2 + portIndex * PORT_SPACING;
    
    return { x, y };
  }, [nodes]);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        setDragConnection(null);
        setShowPalette(false);
      }
      if (e.key === 'Delete' && selectedNode && !isDeployed) {
        deleteNode();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [selectedNode, isDeployed]);

  return (
    <div className="flex flex-col h-full bg-[#0a0a0a]">
      {/* Toolbar */}
      <div className="h-10 border-b border-[#2b2b2b] flex items-center justify-between px-3">
        <div className="flex items-center gap-3">
          {projectId ? (
            <>
              {/* Add node button */}
              <div className="relative">
                <button
                  onClick={() => !isDeployed && setShowPalette(!showPalette)}
                  disabled={isDeployed}
                  className="flex items-center gap-2 px-3 py-1.5 text-xs rounded bg-[#3b82f6] hover:bg-[#2563eb] disabled:bg-[#2b2b2b] disabled:text-[#555] text-white transition-colors"
                  title={isDeployed ? "Undeploy to add nodes" : "Add a node to the agent graph"}
                >
                  <Plus size={14} />
                  Add Node
                </button>
                
                {/* Node palette dropdown grouped by category */}
                {showPalette && !isDeployed && (
                  <div className="absolute top-full left-0 mt-1 bg-[#1a1a1a] border border-[#2b2b2b] rounded-lg shadow-xl z-50 min-w-[200px] max-h-[400px] overflow-y-auto">
                    {NODE_CATEGORIES.map((category, catIndex) => {
                      const nodesInCategory = Object.entries(NODE_TYPES).filter(([, def]) => def.category === category);
                      if (nodesInCategory.length === 0) return null;
                      return (
                        <div key={category}>
                          {catIndex > 0 && <div className="border-t border-[#2b2b2b]" />}
                          <div className="px-3 py-1.5 text-[10px] uppercase tracking-wider text-[#666] font-medium">
                            {category}
                          </div>
                          {nodesInCategory.map(([type, def]) => {
                            const Icon = def.icon;
                            return (
                              <button
                                key={type}
                                onClick={() => addNode(type)}
                                className="w-full flex items-center gap-3 px-4 py-2 text-xs hover:bg-[#2b2b2b] transition-colors"
                                style={{ color: def.color }}
                              >
                                <Icon size={14} />
                                {def.label}
                              </button>
                            );
                          })}
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </>
          ) : (
            <span className="text-xs text-[#555]">Create or load a project to add nodes</span>
          )}
        </div>
        
        <div className="flex items-center gap-2">
          {projectId && (
            <>
              {/* Zoom controls */}
              <div className="flex items-center gap-1 mr-2">
                <button
                  onClick={() => setZoom(z => Math.max(z * 0.9, 0.25))}
                  className="p-1.5 text-[#888] hover:text-[#e5e5e5] transition-colors"
                  title="Zoom out"
                >
                  <ZoomOut size={14} />
                </button>
                <span className="text-[10px] text-[#666] w-10 text-center">{Math.round(zoom * 100)}%</span>
                <button
                  onClick={() => setZoom(z => Math.min(z * 1.1, 2))}
                  className="p-1.5 text-[#888] hover:text-[#e5e5e5] transition-colors"
                  title="Zoom in"
                >
                  <ZoomIn size={14} />
                </button>
                <button
                  onClick={resetView}
                  className="p-1.5 text-[#888] hover:text-[#e5e5e5] transition-colors"
                  title="Reset view"
                >
                  <Maximize2 size={14} />
                </button>
              </div>
              
              <div className="h-4 w-px bg-[#2b2b2b]" />
              
              <button
                onClick={deleteNode}
                disabled={!selectedNode || isDeployed}
                className="p-1.5 text-[#888] hover:text-[#ef4444] disabled:opacity-30 disabled:hover:text-[#888] transition-colors"
                title="Delete selected node"
              >
                <Trash2 size={14} />
              </button>
            </>
          )}
        </div>
      </div>

      {/* Canvas */}
      <div 
        ref={canvasRef}
        className="flex-1 relative overflow-hidden"
        onClick={(e) => { 
          if (e.target === canvasRef.current || e.target.classList.contains('canvas-transform')) { 
            setSelectedNode(null); 
            setShowPalette(false);
          } 
        }}
        onMouseDown={handleCanvasMouseDown}
        onWheel={handleWheel}
        style={{ 
          backgroundImage: 'radial-gradient(circle, #222 1px, transparent 1px)',
          backgroundSize: `${20 * zoom}px ${20 * zoom}px`,
          backgroundPosition: `${pan.x}px ${pan.y}px`,
          cursor: isPanning ? 'grabbing' : 'default'
        }}
      >
        {/* Transform container for pan/zoom */}
        <div 
          className="canvas-transform absolute inset-0"
          style={{
            transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
            transformOrigin: '0 0'
          }}
        >
        {/* Edges SVG - positioned at 0,0 relative to transform container */}
        <svg className="absolute inset-0 w-full h-full overflow-visible pointer-events-none" style={{ minWidth: '5000px', minHeight: '5000px' }}>
          <defs>
            <marker id="arrowhead" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
              <polygon points="0 0, 10 3.5, 0 7" fill="#3b82f6" />
            </marker>
            <marker id="arrowhead-purple" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
              <polygon points="0 0, 10 3.5, 0 7" fill="#a855f7" />
            </marker>
            <marker id="arrowhead-orange" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
              <polygon points="0 0, 10 3.5, 0 7" fill="#f97316" />
            </marker>
          </defs>
          
          {/* Existing edges */}
          {edges.map((edge) => {
            const from = getPortPosition(edge.source_node, edge.source_port, true);
            const to = getPortPosition(edge.target_node, edge.target_port, false);
            const midX = (from.x + to.x) / 2;
            const edgeStyle = EDGE_TYPES[edge.edge_type] || EDGE_TYPES.message;
            
            return (
              <g key={edge.id} className={isDeployed ? '' : 'pointer-events-auto cursor-pointer'} onClick={() => !isDeployed && deleteEdge(edge.id)}>
                <path
                  d={`M ${from.x} ${from.y} C ${midX} ${from.y}, ${midX} ${to.y}, ${to.x} ${to.y}`}
                  fill="none"
                  stroke={edgeStyle.color}
                  strokeWidth="2"
                  strokeDasharray={edgeStyle.dashed ? "5,5" : "none"}
                  markerEnd={
                    edge.edge_type === 'delegate' ? "url(#arrowhead-orange)" :
                    edge.edge_type === 'resource' ? "url(#arrowhead-purple)" :
                    "url(#arrowhead)"
                  }
                  className={isDeployed ? '' : 'hover:stroke-[#ef4444] transition-colors'}
                />
              </g>
            );
          })}
          
          {/* Dragging connection line */}
          {dragConnection && (() => {
            const from = getPortPosition(dragConnection.nodeId, dragConnection.portId, dragConnection.isOutput);
            const to = mousePos;
            const midX = (from.x + to.x) / 2;
            
            return (
              <path
                d={dragConnection.isOutput 
                  ? `M ${from.x} ${from.y} C ${midX} ${from.y}, ${midX} ${to.y}, ${to.x} ${to.y}`
                  : `M ${to.x} ${to.y} C ${midX} ${to.y}, ${midX} ${from.y}, ${from.x} ${from.y}`
                }
                fill="none"
                stroke="#3b82f6"
                strokeWidth="2"
                strokeDasharray="5,5"
                opacity="0.7"
              />
            );
          })()}
        </svg>

        {/* Nodes */}
        {nodes.map(node => {
          const nodeType = NODE_TYPES[node.type] || { label: node.type, color: '#666', icon: Bot };
          const Icon = nodeType.icon;
          const ports = node.ports || {};
          const allPorts = [
            ...(ports.inputs || []).map((id, i) => ({ id, type: 'input', index: i })),
            ...(ports.bidirectional || []).map((id, i) => ({ id, type: 'bidirectional', index: (ports.inputs || []).length + i })),
            ...(ports.outputs || []).map((id, i) => ({ id, type: 'output', index: (ports.inputs || []).length + (ports.bidirectional || []).length + i })),
          ];
          const nodeHeight = HEADER_HEIGHT + Math.max(allPorts.length, 1) * PORT_SPACING;
          
          return (
            <div
              key={node.id}
              className={`absolute select-none rounded-lg border-2 bg-[#1a1a1a] shadow-lg ${
                selectedNode === node.id ? 'ring-2 ring-white/30' : ''
              }`}
              style={{
                left: node.position.x,
                top: node.position.y,
                width: NODE_WIDTH,
                minHeight: nodeHeight,
                borderColor: nodeType.color + '80',
                cursor: dragging === node.id ? 'grabbing' : 'grab'
              }}
              onMouseDown={(e) => handleMouseDown(e, node.id)}
            >
              {/* Header */}
              <div 
                className="px-3 py-2 flex items-center gap-2 text-xs font-medium border-b border-[#2b2b2b] rounded-t-lg"
                style={{ backgroundColor: nodeType.color + '20', color: nodeType.color, height: HEADER_HEIGHT }}
              >
                <Icon size={14} />
                {node.config?.name || nodeType.label}
              </div>

              {/* Port labels (inside node) */}
              <div className="relative">
                {allPorts.map((port, idx) => (
                  <div 
                    key={port.id} 
                    className="flex items-center text-[10px] text-[#666] px-4"
                    style={{ 
                      height: PORT_SPACING,
                      justifyContent: port.type === 'output' ? 'flex-end' : port.type === 'bidirectional' ? 'center' : 'flex-start'
                    }}
                  >
                    {port.id}
                  </div>
                ))}
              </div>

              {/* Input ports (left edge) */}
              {(ports.inputs || []).map((portId, idx) => (
                <div
                  key={`in-${portId}`}
                  data-port="true"
                  data-node-id={node.id}
                  data-port-id={portId}
                  data-port-type="input"
                  data-is-output="false"
                  className="absolute rounded-full border-2 cursor-crosshair hover:scale-150 transition-transform z-10"
                  style={{
                    width: PORT_SIZE,
                    height: PORT_SIZE,
                    left: -PORT_SIZE / 2,
                    top: HEADER_HEIGHT + idx * PORT_SPACING + (PORT_SPACING - PORT_SIZE) / 2,
                    borderColor: dragConnection && !dragConnection.isOutput ? '#666' : '#3b82f6',
                    backgroundColor: dragConnection?.nodeId === node.id && dragConnection?.portId === portId ? '#3b82f6' : '#1a1a1a'
                  }}
                  onMouseDown={(e) => !isDeployed && handlePortMouseDown(e, node.id, portId, 'input', false)}
                />
              ))}

              {/* Bidirectional ports (both edges) */}
              {(ports.bidirectional || []).map((portId, idx) => {
                const portY = HEADER_HEIGHT + ((ports.inputs || []).length + idx) * PORT_SPACING + (PORT_SPACING - PORT_SIZE) / 2;
                return (
                  <React.Fragment key={`bi-${portId}`}>
                    {/* Left side */}
                    <div
                      data-port="true"
                      data-node-id={node.id}
                      data-port-id={portId}
                      data-port-type="bidirectional"
                      data-is-output="false"
                      className="absolute rounded-full border-2 cursor-crosshair hover:scale-150 transition-transform z-10"
                      style={{
                        width: PORT_SIZE,
                        height: PORT_SIZE,
                        left: -PORT_SIZE / 2,
                        top: portY,
                        borderColor: '#a855f7',
                        backgroundColor: dragConnection?.nodeId === node.id && dragConnection?.portId === portId ? '#a855f7' : '#1a1a1a'
                      }}
                      onMouseDown={(e) => !isDeployed && handlePortMouseDown(e, node.id, portId, 'bidirectional', false)}
                    />
                    {/* Right side */}
                    <div
                      data-port="true"
                      data-node-id={node.id}
                      data-port-id={portId}
                      data-port-type="bidirectional"
                      data-is-output="true"
                      className="absolute rounded-full border-2 cursor-crosshair hover:scale-150 transition-transform z-10"
                      style={{
                        width: PORT_SIZE,
                        height: PORT_SIZE,
                        right: -PORT_SIZE / 2,
                        top: portY,
                        borderColor: '#a855f7',
                        backgroundColor: dragConnection?.nodeId === node.id && dragConnection?.portId === portId ? '#a855f7' : '#1a1a1a'
                      }}
                      onMouseDown={(e) => !isDeployed && handlePortMouseDown(e, node.id, portId, 'bidirectional', true)}
                    />
                  </React.Fragment>
                );
              })}

              {/* Output ports (right edge) */}
              {(ports.outputs || []).map((portId, idx) => (
                <div
                  key={`out-${portId}`}
                  data-port="true"
                  data-node-id={node.id}
                  data-port-id={portId}
                  data-port-type="output"
                  data-is-output="true"
                  className="absolute rounded-full border-2 cursor-crosshair hover:scale-150 transition-transform z-10"
                  style={{
                    width: PORT_SIZE,
                    height: PORT_SIZE,
                    right: -PORT_SIZE / 2,
                    top: HEADER_HEIGHT + ((ports.inputs || []).length + (ports.bidirectional || []).length + idx) * PORT_SPACING + (PORT_SPACING - PORT_SIZE) / 2,
                    borderColor: dragConnection && dragConnection.isOutput ? '#666' : '#3b82f6',
                    backgroundColor: dragConnection?.nodeId === node.id && dragConnection?.portId === portId ? '#3b82f6' : '#1a1a1a'
                  }}
                  onMouseDown={(e) => !isDeployed && handlePortMouseDown(e, node.id, portId, 'output', true)}
                />
              ))}
            </div>
          );
        })}
        </div> {/* End transform container */}

        {/* Empty state */}
        {!projectId && (
          <div className="absolute inset-0 flex items-center justify-center text-[#444] text-sm">
            <div className="text-center">
              <p className="mb-2">No project loaded</p>
              <p className="text-xs text-[#555]">Use the project menu at the top to create or open a project</p>
            </div>
          </div>
        )}

        {projectId && nodes.length === 0 && (
          <div className="absolute inset-0 flex items-center justify-center text-[#444] text-sm">
            <div className="text-center">
              <p>Click "Add Node" to add nodes to your agent graph</p>
              <p className="text-xs mt-1">Drag nodes to move • Click ports to connect</p>
            </div>
          </div>
        )}

        {/* Connection mode indicator */}
        {dragConnection && (
          <div className="absolute top-2 left-1/2 -translate-x-1/2 px-3 py-1 bg-[#3b82f6] text-white text-xs rounded pointer-events-none">
            Release on a port to connect
          </div>
        )}
      </div>

      {/* Status bar */}
      <div className="h-6 border-t border-[#2b2b2b] flex items-center justify-between px-3 text-[10px] text-[#666]">
        <div className="flex items-center">
          {projectId ? (
            <>
              <span>{nodes.length} nodes</span>
              <span className="mx-2">•</span>
              <span>{edges.length} edges</span>
              {selectedNode && (
                <>
                  <span className="mx-2">•</span>
                  <span>Selected: {nodes.find(n => n.id === selectedNode)?.config?.name}</span>
                </>
              )}
            </>
          ) : (
            <span>No project loaded</span>
          )}
        </div>
        {projectId && (
          <div className="flex items-center gap-2">
            {isDeployed ? (
              <span className="flex items-center gap-1 text-[#22c55e]">
                <span className="w-2 h-2 rounded-full bg-[#22c55e] animate-pulse" />
                Running
              </span>
            ) : (
              <span className="text-[#666]">Design Mode</span>
            )}
          </div>
        )}
      </div>

    </div>
  );
}
