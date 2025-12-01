import React, { useState } from 'react';
import { Settings, Calendar, Volume2 } from 'lucide-react';
import AgentControlTab from './AgentControlTab';
import ScheduleTab from './ScheduleTab';
import TTSSettingsTab from './TTSSettingsTab';

export default function SettingsPanel({ agentStatus, selectedAgentId, onAgentSelect }) {
  const [activeTab, setActiveTab] = useState('agent');

  return (
    <div className="flex flex-col h-full text-[13px]">
      {/* Tab Bar */}
      <div className="h-10 border-b border-[#2b2b2b] flex items-center px-2 gap-1">
        <button
          onClick={() => setActiveTab('agent')}
          className={`flex items-center gap-2 px-3 py-1.5 rounded text-xs font-medium transition-colors ${
            activeTab === 'agent' 
              ? 'bg-[#1a1a1a] text-[#e5e5e5] border border-[#2b2b2b]' 
              : 'text-[#888] hover:text-[#e5e5e5]'
          }`}
        >
          <Settings size={14} />
          Agent
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
        {activeTab === 'agent' && <AgentControlTab agentStatus={agentStatus} selectedAgentId={selectedAgentId} onAgentSelect={onAgentSelect} />}
        {activeTab === 'schedule' && <ScheduleTab />}
        {activeTab === 'voice' && <TTSSettingsTab />}
      </div>
    </div>
  );
}
