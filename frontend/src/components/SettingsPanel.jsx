import React, { useState, useEffect } from 'react';
import { Bot, Calendar, Box, Volume2 } from 'lucide-react';
import AgentControlTab from './AgentControlTab';
import ScheduleTab from './ScheduleTab';
import NodeInspectorTab from './NodeInspectorTab';
import VoiceSettingsTab from './VoiceSettingsTab';

export default function SettingsPanel({ selectedAgentGraphNode, isAgentGraphDeployed }) {
  const [activeTab, setActiveTab] = useState('agents');

  // Auto-switch to Node tab when an agent graph node is selected
  useEffect(() => {
    if (selectedAgentGraphNode) {
      setActiveTab('node');
    }
  }, [selectedAgentGraphNode]);

  return (
    <div className="flex flex-col h-full text-[13px]">
      {/* Tab Bar */}
      <div className="h-10 border-b border-[#2b2b2b] flex items-center px-2 gap-1">
        <button
          onClick={() => setActiveTab('agents')}
          className={`flex items-center gap-2 px-3 py-1.5 rounded text-xs font-medium transition-colors ${
            activeTab === 'agents' 
              ? 'bg-[#1a1a1a] text-[#e5e5e5] border border-[#2b2b2b]' 
              : 'text-[#888] hover:text-[#e5e5e5]'
          }`}
        >
          <Bot size={14} />
          Agents
        </button>
        <button
          onClick={() => setActiveTab('node')}
          className={`flex items-center gap-2 px-3 py-1.5 rounded text-xs font-medium transition-colors ${
            activeTab === 'node' 
              ? 'bg-[#1a1a1a] text-[#e5e5e5] border border-[#2b2b2b]' 
              : 'text-[#888] hover:text-[#e5e5e5]'
          }`}
        >
          <Box size={14} />
          Node
        </button>
        <button
          onClick={() => setActiveTab('schedule')}
          className={`flex items-center gap-2 px-3 py-1.5 rounded text-xs font-medium transition-colors ${
            activeTab === 'schedule' 
              ? 'bg-[#1a1a1a] text-[#e5e5e5] border border-[#2b2b2b]' 
              : 'text-[#888] hover:text-[#e5e5e5]'
          }`}
        >
          <Calendar size={14} />
          Schedule
        </button>
        <button
          onClick={() => setActiveTab('voice')}
          className={`flex items-center gap-2 px-3 py-1.5 rounded text-xs font-medium transition-colors ${
            activeTab === 'voice' 
              ? 'bg-[#1a1a1a] text-[#e5e5e5] border border-[#2b2b2b]' 
              : 'text-[#888] hover:text-[#e5e5e5]'
          }`}
        >
          <Volume2 size={14} />
          Voice
        </button>
      </div>

      {/* Tab Content */}
      <div className="flex-1 overflow-hidden">
        {activeTab === 'agents' && <AgentControlTab />}
        {activeTab === 'node' && <NodeInspectorTab selectedNode={selectedAgentGraphNode} isDeployed={isAgentGraphDeployed} />}
        {activeTab === 'schedule' && <ScheduleTab />}
        {activeTab === 'voice' && <VoiceSettingsTab isDeployed={isAgentGraphDeployed} />}
      </div>
    </div>
  );
}
