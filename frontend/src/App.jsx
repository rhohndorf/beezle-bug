import React, { useState, useEffect } from 'react';
import { socket } from './lib/socket';
import Chat from './components/Chat';
import NodeGraph from './components/NodeGraph';
import IntrospectionPanel from './components/IntrospectionPanel';
import SettingsPanel from './components/SettingsPanel';
import KnowledgeGraphPanel from './components/KnowledgeGraphPanel';
import LogPanel from './components/LogPanel';
import { TTSProvider } from './context/TTSContext';
import { Activity, MessageSquare, GitBranch } from 'lucide-react';

function App() {
  const [isConnected, setIsConnected] = useState(socket.connected);
  const [agentStatus, setAgentStatus] = useState({ running: false, name: 'Beezle Bug' });
  const [activeTab, setActiveTab] = useState('chat');
  const [selectedAgentId, setSelectedAgentId] = useState(null);
  
  // Layout State
  const [leftWidth, setLeftWidth] = useState(550);
  const [rightWidth, setRightWidth] = useState(window.innerWidth * 0.2); // 1/5 of window width
  const [topHeight, setTopHeight] = useState(window.innerHeight * 0.5); // IntrospectionPanel ~50%
  const [rightTopHeight, setRightTopHeight] = useState(window.innerHeight * 0.33); // Settings panel ~2/3, LogPanel ~1/3
  const [isResizingLeft, setIsResizingLeft] = useState(false);
  const [isResizingRight, setIsResizingRight] = useState(false);
  const [isResizingVertical, setIsResizingVertical] = useState(false);
  const [isResizingRightVertical, setIsResizingRightVertical] = useState(false);

  useEffect(() => {
    function onConnect() { setIsConnected(true); }
    function onDisconnect() { setIsConnected(false); }
    function onAgentStatus(status) { 
      setAgentStatus({
        ...status,
        running: status.state === 'running'
      }); 
    }

    socket.on('connect', onConnect);
    socket.on('disconnect', onDisconnect);
    socket.on('agent_status', onAgentStatus);
    socket.connect();

    return () => {
      socket.off('connect', onConnect);
      socket.off('disconnect', onDisconnect);
      socket.off('agent_status', onAgentStatus);
      socket.disconnect();
    };
  }, []);

  // Resize Handlers
  useEffect(() => {
    const handleMouseMove = (e) => {
      if (isResizingLeft) setLeftWidth(Math.min(Math.max(300, e.clientX), 800));
      if (isResizingRight) setRightWidth(Math.min(Math.max(300, window.innerWidth - e.clientX), 600));
      if (isResizingVertical) setTopHeight(Math.min(Math.max(150, e.clientY), window.innerHeight - 200));
      if (isResizingRightVertical) {
        const rightPanelTop = window.innerWidth - rightWidth;
        const relativeY = e.clientY;
        setRightTopHeight(Math.min(Math.max(200, relativeY), window.innerHeight - 150));
      }
    };
    const handleMouseUp = () => {
      setIsResizingLeft(false);
      setIsResizingRight(false);
      setIsResizingVertical(false);
      setIsResizingRightVertical(false);
      document.body.style.cursor = 'default';
      document.body.style.userSelect = 'auto';
    };
    if (isResizingLeft || isResizingRight || isResizingVertical || isResizingRightVertical) {
      window.addEventListener('mousemove', handleMouseMove);
      window.addEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = (isResizingVertical || isResizingRightVertical) ? 'row-resize' : 'col-resize';
      document.body.style.userSelect = 'none';
    }
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isResizingLeft, isResizingRight, isResizingVertical, isResizingRightVertical, rightWidth]);

  const tabs = [
    { id: 'chat', label: 'Chat', icon: MessageSquare },
    { id: 'nodes', label: 'Node Graph', icon: GitBranch },
  ];

  return (
    <TTSProvider>
    <div className="flex h-screen w-full bg-[#0c0c0c] text-[#e5e5e5] overflow-hidden font-sans text-[13px]">
      
      {/* Left Column */}
      <div style={{ width: leftWidth }} className="flex-shrink-0 flex flex-col border-r border-[#2b2b2b] relative">
        {/* Neural Stream */}
        <div style={{ height: topHeight }} className="flex flex-col min-h-[150px]">
          <div className="h-10 px-3 border-b border-[#2b2b2b] flex items-center justify-between select-none">
            <div className="flex items-center gap-2 text-[#888888] text-xs uppercase tracking-wide font-medium">
              <Activity size={14} />
              Neural Stream
            </div>
            <div className="flex items-center gap-2">
              <span className={`text-[10px] ${agentStatus.running ? 'text-[#22c55e]' : 'text-[#888888]'}`}>
                {agentStatus.running ? 'RUNNING' : 'STOPPED'}
              </span>
              <div className={`w-1.5 h-1.5 rounded-full ${isConnected ? 'bg-[#3b82f6]' : 'bg-red-500/50'}`}></div>
            </div>
          </div>
          <div className="flex-1 overflow-hidden">
            <IntrospectionPanel />
          </div>
        </div>

        {/* Vertical Resizer */}
        <div 
          className="h-1 bg-[#2b2b2b] cursor-row-resize hover:bg-[#3b82f6] transition-colors flex-shrink-0"
          onMouseDown={() => setIsResizingVertical(true)}
        />

        {/* Log Panel */}
        <div className="flex-1 min-h-[150px] overflow-hidden">
          <LogPanel />
        </div>

        {/* Horizontal Resizer */}
        <div 
          className="absolute top-0 right-0 w-1 h-full cursor-col-resize hover:bg-[#3b82f6] transition-colors z-50 opacity-0 hover:opacity-100"
          onMouseDown={() => setIsResizingLeft(true)}
        />
      </div>

      {/* Center: Tabbed Area */}
      <div className="flex-1 flex flex-col min-w-[300px]">
        {/* Tab Bar */}
        <div className="h-10 border-b border-[#2b2b2b] flex items-center px-2 gap-1 bg-[#0a0a0a]">
          {tabs.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-3 py-1.5 rounded text-xs font-medium transition-colors ${
                activeTab === tab.id 
                  ? 'bg-[#1a1a1a] text-[#e5e5e5] border border-[#2b2b2b]' 
                  : 'text-[#888888] hover:text-[#e5e5e5] hover:bg-[#1a1a1a]/50'
              }`}
            >
              <tab.icon size={14} />
              {tab.label}
            </button>
          ))}
        </div>

        {/* Tab Content */}
        <div className="flex-1 overflow-hidden">
          {activeTab === 'chat' && <Chat agentStatus={agentStatus} />}
          {activeTab === 'nodes' && <NodeGraph />}
        </div>
      </div>

      {/* Right: Settings + Log */}
      <div style={{ width: rightWidth }} className="flex-shrink-0 border-l border-[#2b2b2b] relative flex flex-col">
        <div 
          className="absolute top-0 left-0 w-1 h-full cursor-col-resize hover:bg-[#3b82f6] transition-colors z-50 opacity-0 hover:opacity-100"
          onMouseDown={() => setIsResizingRight(true)}
        />
        
        {/* Settings Panel */}
        <div style={{ height: rightTopHeight }} className="flex-shrink-0 overflow-hidden">
          <SettingsPanel 
            agentStatus={agentStatus} 
            selectedAgentId={selectedAgentId}
            onAgentSelect={setSelectedAgentId}
          />
        </div>
        
        {/* Vertical Resizer */}
        <div 
          className="h-1 bg-[#2b2b2b] cursor-row-resize hover:bg-[#3b82f6] transition-colors flex-shrink-0"
          onMouseDown={() => setIsResizingRightVertical(true)}
        />
        
        {/* Knowledge Graph */}
        <div className="flex-1 min-h-[100px] overflow-hidden">
          <KnowledgeGraphPanel selectedAgentId={selectedAgentId} />
        </div>
      </div>
    </div>
    </TTSProvider>
  );
}

export default App;
