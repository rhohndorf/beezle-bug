import React, { useState, useRef, useCallback, useEffect } from 'react';
import { Plus, Trash2, Play, Circle } from 'lucide-react';

// Node types available
const NODE_TYPES = [
  { type: 'input', label: 'Input', color: '#22c55e' },
  { type: 'output', label: 'Output', color: '#ef4444' },
  { type: 'process', label: 'Process', color: '#3b82f6' },
  { type: 'condition', label: 'Condition', color: '#eab308' },
  { type: 'llm', label: 'LLM Call', color: '#a855f7' },
  { type: 'tool', label: 'Tool', color: '#f97316' },
];

export default function NodeGraph() {
  const [nodes, setNodes] = useState([]);
  const [connections, setConnections] = useState([]);
  const [selectedNode, setSelectedNode] = useState(null);
  const [connecting, setConnecting] = useState(null); // { nodeId, portType: 'output' | 'input' }
  const [dragging, setDragging] = useState(null);
  const [offset, setOffset] = useState({ x: 0, y: 0 });
  const canvasRef = useRef(null);

  // Add a new node
  const addNode = (type) => {
    const nodeType = NODE_TYPES.find(n => n.type === type) || NODE_TYPES[2];
    const newNode = {
      id: `node-${Date.now()}`,
      type: nodeType.type,
      label: nodeType.label,
      color: nodeType.color,
      x: 200 + Math.random() * 200,
      y: 150 + Math.random() * 200,
      inputs: type !== 'input' ? [{ id: 'in-1', label: 'In' }] : [],
      outputs: type !== 'output' ? [{ id: 'out-1', label: 'Out' }] : [],
      data: {}
    };
    setNodes([...nodes, newNode]);
    setSelectedNode(newNode.id);
  };

  // Delete selected node
  const deleteNode = () => {
    if (!selectedNode) return;
    setNodes(nodes.filter(n => n.id !== selectedNode));
    setConnections(connections.filter(c => c.from.nodeId !== selectedNode && c.to.nodeId !== selectedNode));
    setSelectedNode(null);
  };

  // Handle node drag
  const handleMouseDown = (e, nodeId) => {
    if (e.target.closest('.port')) return; // Don't drag when clicking ports
    const node = nodes.find(n => n.id === nodeId);
    if (node) {
      setDragging(nodeId);
      setOffset({ x: e.clientX - node.x, y: e.clientY - node.y });
      setSelectedNode(nodeId);
    }
  };

  const handleMouseMove = useCallback((e) => {
    if (dragging) {
      setNodes(nodes.map(n => 
        n.id === dragging 
          ? { ...n, x: e.clientX - offset.x, y: e.clientY - offset.y }
          : n
      ));
    }
  }, [dragging, offset, nodes]);

  const handleMouseUp = () => {
    setDragging(null);
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
  }, [dragging, handleMouseMove]);

  // Handle port click for connections
  const handlePortClick = (nodeId, portId, portType) => {
    if (!connecting) {
      // Start connection
      setConnecting({ nodeId, portId, portType });
    } else {
      // Complete connection
      if (connecting.portType !== portType && connecting.nodeId !== nodeId) {
        const newConnection = connecting.portType === 'output'
          ? { from: { nodeId: connecting.nodeId, portId: connecting.portId }, to: { nodeId, portId } }
          : { from: { nodeId, portId }, to: { nodeId: connecting.nodeId, portId: connecting.portId } };
        
        // Check if connection already exists
        const exists = connections.some(c => 
          c.from.nodeId === newConnection.from.nodeId && 
          c.from.portId === newConnection.from.portId &&
          c.to.nodeId === newConnection.to.nodeId &&
          c.to.portId === newConnection.to.portId
        );
        
        if (!exists) {
          setConnections([...connections, newConnection]);
        }
      }
      setConnecting(null);
    }
  };

  // Delete connection
  const deleteConnection = (index) => {
    setConnections(connections.filter((_, i) => i !== index));
  };

  // Get port position for drawing connections
  const getPortPosition = (nodeId, portId, portType) => {
    const node = nodes.find(n => n.id === nodeId);
    if (!node) return { x: 0, y: 0 };
    
    const portIndex = portType === 'input' 
      ? node.inputs.findIndex(p => p.id === portId)
      : node.outputs.findIndex(p => p.id === portId);
    
    return {
      x: portType === 'input' ? node.x : node.x + 180,
      y: node.y + 40 + portIndex * 24
    };
  };

  return (
    <div className="flex flex-col h-full bg-[#0a0a0a]">
      {/* Toolbar */}
      <div className="h-10 border-b border-[#2b2b2b] flex items-center justify-between px-3">
        <div className="flex items-center gap-2">
          <span className="text-[#888] text-xs uppercase tracking-wide">Add Node:</span>
          {NODE_TYPES.map(nt => (
            <button
              key={nt.type}
              onClick={() => addNode(nt.type)}
              className="px-2 py-1 text-[10px] rounded border border-[#2b2b2b] hover:bg-[#1a1a1a] transition-colors"
              style={{ borderColor: nt.color + '40', color: nt.color }}
            >
              {nt.label}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={deleteNode}
            disabled={!selectedNode}
            className="p-1.5 text-[#888] hover:text-[#ef4444] disabled:opacity-30 disabled:hover:text-[#888]"
            title="Delete selected node"
          >
            <Trash2 size={14} />
          </button>
        </div>
      </div>

      {/* Canvas */}
      <div 
        ref={canvasRef}
        className="flex-1 relative overflow-hidden"
        onClick={(e) => { if (e.target === canvasRef.current) { setSelectedNode(null); setConnecting(null); } }}
        style={{ 
          backgroundImage: 'radial-gradient(circle, #222 1px, transparent 1px)',
          backgroundSize: '20px 20px'
        }}
      >
        {/* Connections */}
        <svg className="absolute inset-0 w-full h-full pointer-events-none">
          {connections.map((conn, i) => {
            const from = getPortPosition(conn.from.nodeId, conn.from.portId, 'output');
            const to = getPortPosition(conn.to.nodeId, conn.to.portId, 'input');
            const midX = (from.x + to.x) / 2;
            return (
              <g key={i} className="pointer-events-auto cursor-pointer" onClick={() => deleteConnection(i)}>
                <path
                  d={`M ${from.x} ${from.y} C ${midX} ${from.y}, ${midX} ${to.y}, ${to.x} ${to.y}`}
                  fill="none"
                  stroke="#3b82f6"
                  strokeWidth="2"
                  className="hover:stroke-[#ef4444]"
                />
              </g>
            );
          })}
        </svg>

        {/* Nodes */}
        {nodes.map(node => (
          <div
            key={node.id}
            className={`absolute select-none rounded-lg border-2 bg-[#1a1a1a] shadow-lg ${
              selectedNode === node.id ? 'ring-2 ring-[#3b82f6]' : ''
            }`}
            style={{
              left: node.x,
              top: node.y,
              width: 180,
              borderColor: node.color + '60',
              cursor: dragging === node.id ? 'grabbing' : 'grab'
            }}
            onMouseDown={(e) => handleMouseDown(e, node.id)}
          >
            {/* Header */}
            <div 
              className="px-3 py-2 text-xs font-medium border-b border-[#2b2b2b] rounded-t-lg"
              style={{ backgroundColor: node.color + '20', color: node.color }}
            >
              {node.label}
            </div>

            {/* Ports */}
            <div className="py-2">
              {/* Input ports */}
              {node.inputs.map((port, i) => (
                <div key={port.id} className="flex items-center gap-2 px-2 py-1 text-[11px]">
                  <div 
                    className="port w-3 h-3 rounded-full border-2 cursor-crosshair hover:scale-125 transition-transform"
                    style={{ 
                      borderColor: connecting?.portType === 'output' ? '#3b82f6' : '#666',
                      backgroundColor: connecting?.nodeId === node.id && connecting?.portId === port.id ? '#3b82f6' : 'transparent'
                    }}
                    onClick={(e) => { e.stopPropagation(); handlePortClick(node.id, port.id, 'input'); }}
                  />
                  <span className="text-[#888]">{port.label}</span>
                </div>
              ))}
              
              {/* Output ports */}
              {node.outputs.map((port, i) => (
                <div key={port.id} className="flex items-center justify-end gap-2 px-2 py-1 text-[11px]">
                  <span className="text-[#888]">{port.label}</span>
                  <div 
                    className="port w-3 h-3 rounded-full border-2 cursor-crosshair hover:scale-125 transition-transform"
                    style={{ 
                      borderColor: connecting?.portType === 'input' ? '#3b82f6' : '#666',
                      backgroundColor: connecting?.nodeId === node.id && connecting?.portId === port.id ? '#3b82f6' : 'transparent'
                    }}
                    onClick={(e) => { e.stopPropagation(); handlePortClick(node.id, port.id, 'output'); }}
                  />
                </div>
              ))}
            </div>
          </div>
        ))}

        {/* Empty state */}
        {nodes.length === 0 && (
          <div className="absolute inset-0 flex items-center justify-center text-[#444] text-sm">
            <div className="text-center">
              <p>Click a node type above to add nodes</p>
              <p className="text-xs mt-1">Drag nodes to move • Click ports to connect</p>
            </div>
          </div>
        )}

        {/* Connection mode indicator */}
        {connecting && (
          <div className="absolute top-2 left-1/2 -translate-x-1/2 px-3 py-1 bg-[#3b82f6] text-white text-xs rounded">
            Click another port to connect (ESC to cancel)
          </div>
        )}
      </div>

      {/* Status bar */}
      <div className="h-6 border-t border-[#2b2b2b] flex items-center px-3 text-[10px] text-[#666]">
        <span>{nodes.length} nodes</span>
        <span className="mx-2">•</span>
        <span>{connections.length} connections</span>
        {selectedNode && (
          <>
            <span className="mx-2">•</span>
            <span>Selected: {nodes.find(n => n.id === selectedNode)?.label}</span>
          </>
        )}
      </div>
    </div>
  );
}

