import React, { useState, useEffect, useRef } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { socket } from './lib/socket';
import Chat from './components/Chat';
import NodeGraph from './components/NodeGraph';
import TemplateEditorTab from './components/TemplateEditorTab';
import IntrospectionPanel from './components/IntrospectionPanel';
import SettingsPanel from './components/SettingsPanel';
import LogPanel from './components/LogPanel';
import ProjectMenuBar from './components/ProjectMenuBar';
import MobileChat from './components/MobileChat';
import { Activity, MessageSquare, GitBranch, FileText } from 'lucide-react';

function DesktopApp() {
  const [isConnected, setIsConnected] = useState(socket.connected);
  const [agentStatus, setAgentStatus] = useState({ running: false, name: 'Beezle Bug' });
  const [activeTab, setActiveTab] = useState('chat');
  
  // Chat messages - lifted up so they persist across tab switches
  const [chatMessages, setChatMessages] = useState([]);
  
  // Project state - lifted to App level for menu bar
  const [projectId, setProjectId] = useState(null);
  const [projectName, setProjectName] = useState('');
  
  // Agent Graph state
  const [selectedAgentGraphNode, setSelectedAgentGraphNode] = useState(null);
  const [isAgentGraphDeployed, setIsAgentGraphDeployed] = useState(false);
  const wasDeployedRef = useRef(false);
  
  // TTS audio ref for stopping playback
  const ttsAudioRef = useRef(null);
  
  // Layout State
  const [leftWidth, setLeftWidth] = useState(550);
  const [rightWidth, setRightWidth] = useState(window.innerWidth * 0.2); // 1/5 of window width
  const [topHeight, setTopHeight] = useState(window.innerHeight * 0.5); // IntrospectionPanel ~50%
  const [isResizingLeft, setIsResizingLeft] = useState(false);
  const [isResizingRight, setIsResizingRight] = useState(false);
  const [isResizingVertical, setIsResizingVertical] = useState(false);

  useEffect(() => {
    function onConnect() { setIsConnected(true); }
    function onDisconnect() { setIsConnected(false); }
    function onAgentStatus(status) { 
      setAgentStatus({
        ...status,
        running: status.state === 'running'
      }); 
    }

    function onAgentGraphState(data) {
      const nowDeployed = data.is_deployed || false;
      
      // Update project info
      setProjectId(data.project_id || null);
      setProjectName(data.project_name || '');
      
      // Clear chat when deployment stops
      if (wasDeployedRef.current && !nowDeployed) {
        setChatMessages([]);
      }
      
      wasDeployedRef.current = nowDeployed;
      setIsAgentGraphDeployed(nowDeployed);
    }

    function onProjectLoaded(data) {
      setProjectId(data.id);
      setProjectName(data.name);
    }

    function onProjectStopped() {
      setProjectId(null);
      setProjectName('');
    }

    function onChatMessage(data) {
      // Stop TTS audio when user message arrives (typed or voice)
      if (data.user === 'User' && ttsAudioRef.current) {
        ttsAudioRef.current.pause();
        ttsAudioRef.current = null;
      }
      
      const newMessage = { 
        id: Date.now(), 
        user: data.user, 
        text: data.message,
        audioUrl: data.audioUrl || null,
      };
      setChatMessages(prev => [...prev, newMessage]);
    }
    
    function onTtsAudio(data) {
      // Play audio directly when received (per-client TTS)
      if (data.audioUrl) {
        // Stop any currently playing audio first
        if (ttsAudioRef.current) {
          ttsAudioRef.current.pause();
        }
        const audio = new Audio(data.audioUrl);
        ttsAudioRef.current = audio;
        audio.onended = () => { ttsAudioRef.current = null; };
        audio.play().catch(err => console.error('Failed to play TTS audio:', err));
      }
    }
    
    function onSttActivated() {
      // Stop TTS audio immediately when VAD detects user is speaking
      if (ttsAudioRef.current) {
        ttsAudioRef.current.pause();
        ttsAudioRef.current = null;
      }
    }

    socket.on('connect', onConnect);
    socket.on('disconnect', onDisconnect);
    socket.on('agent_status', onAgentStatus);
    socket.on('agent_graph_state', onAgentGraphState);
    socket.on('project_loaded', onProjectLoaded);
    socket.on('project_stopped', onProjectStopped);
    socket.on('chat_message', onChatMessage);
    socket.on('tts_audio', onTtsAudio);
    socket.on('stt_activated', onSttActivated);
    socket.connect();

    return () => {
      socket.off('connect', onConnect);
      socket.off('disconnect', onDisconnect);
      socket.off('agent_status', onAgentStatus);
      socket.off('agent_graph_state', onAgentGraphState);
      socket.off('project_loaded', onProjectLoaded);
      socket.off('project_stopped', onProjectStopped);
      socket.off('chat_message', onChatMessage);
      socket.off('tts_audio', onTtsAudio);
      socket.off('stt_activated', onSttActivated);
      socket.disconnect();
    };
  }, []);

  // Resize Handlers
  useEffect(() => {
    const handleMouseMove = (e) => {
      if (isResizingLeft) setLeftWidth(Math.min(Math.max(300, e.clientX), 800));
      if (isResizingRight) setRightWidth(Math.min(Math.max(300, window.innerWidth - e.clientX), 600));
      if (isResizingVertical) setTopHeight(Math.min(Math.max(150, e.clientY - 36), window.innerHeight - 236)); // Account for menu bar
    };
    const handleMouseUp = () => {
      setIsResizingLeft(false);
      setIsResizingRight(false);
      setIsResizingVertical(false);
      document.body.style.cursor = 'default';
      document.body.style.userSelect = 'auto';
    };
    if (isResizingLeft || isResizingRight || isResizingVertical) {
      window.addEventListener('mousemove', handleMouseMove);
      window.addEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = isResizingVertical ? 'row-resize' : 'col-resize';
      document.body.style.userSelect = 'none';
    }
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isResizingLeft, isResizingRight, isResizingVertical, rightWidth]);

  const tabs = [
    { id: 'chat', label: 'Chat', icon: MessageSquare },
    { id: 'nodes', label: 'Node Graph', icon: GitBranch },
    { id: 'templates', label: 'Templates', icon: FileText },
  ];

  return (
    <div className="flex flex-col h-screen w-full bg-[#0c0c0c] text-[#e5e5e5] overflow-hidden font-sans text-[13px]">
      {/* Top Menu Bar */}
      <ProjectMenuBar 
        projectId={projectId}
        projectName={projectName}
        isDeployed={isAgentGraphDeployed}
      />
      
      {/* Main Content */}
      <div className="flex flex-1 overflow-hidden">
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
            {activeTab === 'chat' && <Chat agentStatus={agentStatus} messages={chatMessages} setMessages={setChatMessages} isDeployed={isAgentGraphDeployed} onSendMessage={() => { if (ttsAudioRef.current) { ttsAudioRef.current.pause(); ttsAudioRef.current = null; } }} />}
            {activeTab === 'nodes' && <NodeGraph onSelectNode={setSelectedAgentGraphNode} />}
            {activeTab === 'templates' && <TemplateEditorTab />}
          </div>
        </div>

        {/* Right: Settings Panel */}
        <div style={{ width: rightWidth }} className="flex-shrink-0 border-l border-[#2b2b2b] relative flex flex-col">
          <div 
            className="absolute top-0 left-0 w-1 h-full cursor-col-resize hover:bg-[#3b82f6] transition-colors z-50 opacity-0 hover:opacity-100"
            onMouseDown={() => setIsResizingRight(true)}
          />
          
          {/* Settings Panel - Full Height */}
          <div className="flex-1 overflow-hidden">
            <SettingsPanel 
              selectedAgentGraphNode={selectedAgentGraphNode}
              isAgentGraphDeployed={isAgentGraphDeployed}
            />
          </div>
        </div>
      </div>
    </div>
  );
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<DesktopApp />} />
        <Route path="/mobile" element={<MobileChat />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
