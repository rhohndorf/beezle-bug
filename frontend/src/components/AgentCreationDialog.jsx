import React, { useState, useEffect } from 'react';
import { socket } from '../lib/socket';
import { X, ChevronDown, ChevronRight, Settings, Wrench, Cpu } from 'lucide-react';

export default function AgentCreationDialog({ isOpen, onClose, onCreate }) {
  // Form state
  const [name, setName] = useState('');
  const [systemTemplate, setSystemTemplate] = useState('agent');
  const [autonomous, setAutonomous] = useState(false);
  const [interval, setInterval] = useState(15);
  const [selectedPreset, setSelectedPreset] = useState('standard');
  const [selectedTools, setSelectedTools] = useState([]);
  const [model, setModel] = useState('local-model');
  const [apiUrl, setApiUrl] = useState('http://127.0.0.1:1234/v1');
  const [apiKey, setApiKey] = useState('');

  // Data from server
  const [templates, setTemplates] = useState([]);
  const [tools, setTools] = useState([]);
  const [presets, setPresets] = useState({});

  // Section visibility
  const [showGeneral, setShowGeneral] = useState(true);
  const [showTools, setShowTools] = useState(true);
  const [showLLM, setShowLLM] = useState(true);

  // Fetch tools and templates when dialog opens
  useEffect(() => {
    if (isOpen) {
      socket.emit('get_tools');
      socket.emit('get_templates');
    }
  }, [isOpen]);

  // Listen for tools and templates data
  useEffect(() => {
    const handleToolsList = (data) => {
      setTools(data.tools || []);
      setPresets(data.presets || {});
      // Set default tools from 'standard' preset
      if (data.presets?.standard) {
        setSelectedTools(data.presets.standard);
      }
    };

    const handleTemplatesList = (data) => {
      setTemplates(data.templates || []);
      if (data.templates?.length > 0 && !data.templates.includes(systemTemplate)) {
        setSystemTemplate(data.templates[0]);
      }
    };

    socket.on('tools_list', handleToolsList);
    socket.on('templates_list', handleTemplatesList);

    return () => {
      socket.off('tools_list', handleToolsList);
      socket.off('templates_list', handleTemplatesList);
    };
  }, [systemTemplate]);

  // Handle preset selection
  const handlePresetChange = (presetName) => {
    setSelectedPreset(presetName);
    if (presets[presetName]) {
      setSelectedTools(presets[presetName]);
    }
  };

  // Handle individual tool toggle
  const handleToolToggle = (toolName) => {
    setSelectedTools(prev => {
      if (prev.includes(toolName)) {
        return prev.filter(t => t !== toolName);
      } else {
        return [...prev, toolName];
      }
    });
    setSelectedPreset(''); // Clear preset when manually changing tools
  };

  // Handle form submission
  const handleCreate = () => {
    if (!name.trim()) return;

    const config = {
      name: name.trim(),
      systemTemplate,
      autonomousEnabled: autonomous,
      autonomousInterval: interval,
      tools: selectedTools,
      model,
      apiUrl,
      apiKey
    };

    onCreate(config);
    handleClose();
  };

  // Reset form and close
  const handleClose = () => {
    setName('');
    setSystemTemplate('agent');
    setAutonomous(false);
    setInterval(15);
    setSelectedPreset('standard');
    setModel('local-model');
    setApiUrl('http://127.0.0.1:1234/v1');
    setApiKey('');
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
      <div className="bg-[#141414] border border-[#2b2b2b] rounded-lg w-[540px] max-h-[85vh] flex flex-col shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-[#2b2b2b]">
          <h2 className="text-base font-semibold text-[#e5e5e5]">Create New Agent</h2>
          <button
            onClick={handleClose}
            className="p-1.5 rounded hover:bg-[#2b2b2b] text-[#666] hover:text-[#e5e5e5] transition-colors"
          >
            <X size={18} />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-5 space-y-4">
          
          {/* Block: General */}
          <div className="border border-[#2b2b2b] rounded-lg overflow-hidden">
            <button
              onClick={() => setShowGeneral(!showGeneral)}
              className="w-full flex items-center gap-2 px-4 py-3 bg-[#1a1a1a] hover:bg-[#222] transition-colors"
            >
              {showGeneral ? <ChevronDown size={16} className="text-[#666]" /> : <ChevronRight size={16} className="text-[#666]" />}
              <Settings size={16} className="text-[#3b82f6]" />
              <span className="text-sm font-medium text-[#e5e5e5]">General</span>
            </button>
            
            {showGeneral && (
              <div className="p-4 space-y-4 bg-[#0f0f0f]">
                {/* Name */}
                <div className="space-y-1.5">
                  <label className="text-xs text-[#888] uppercase tracking-wide">Name</label>
                  <input
                    type="text"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="Enter agent name"
                    className="w-full bg-[#1a1a1a] border border-[#2b2b2b] rounded px-3 py-2 text-sm text-[#e5e5e5] focus:border-[#3b82f6] focus:outline-none"
                  />
                </div>

                {/* System Template */}
                <div className="space-y-1.5">
                  <label className="text-xs text-[#888] uppercase tracking-wide">System Template</label>
                  <select
                    value={systemTemplate}
                    onChange={(e) => setSystemTemplate(e.target.value)}
                    className="w-full bg-[#1a1a1a] border border-[#2b2b2b] rounded px-3 py-2 text-sm text-[#e5e5e5] focus:border-[#3b82f6] focus:outline-none cursor-pointer"
                  >
                    {templates.map(t => (
                      <option key={t} value={t}>{t}</option>
                    ))}
                  </select>
                </div>

                {/* Autonomous */}
                <div className="flex items-center justify-between">
                  <label className="text-xs text-[#888] uppercase tracking-wide">Autonomous Mode</label>
                  <button
                    onClick={() => setAutonomous(!autonomous)}
                    className={`relative w-10 h-5 rounded-full transition-colors ${
                      autonomous ? 'bg-[#3b82f6]' : 'bg-[#2b2b2b]'
                    }`}
                  >
                    <div className={`absolute top-0.5 w-4 h-4 bg-white rounded-full transition-transform ${
                      autonomous ? 'translate-x-5' : 'translate-x-0.5'
                    }`} />
                  </button>
                </div>

                {/* Interval */}
                <div className={`space-y-2 ${!autonomous ? 'opacity-40' : ''}`}>
                  <div className="flex justify-between items-center">
                    <label className="text-xs text-[#888] uppercase tracking-wide">Interval (seconds)</label>
                    <span className="text-xs text-[#666] font-mono">{interval}s</span>
                  </div>
                  <input
                    type="range"
                    min="1"
                    max="100"
                    value={interval}
                    onChange={(e) => setInterval(parseInt(e.target.value))}
                    disabled={!autonomous}
                    className="w-full accent-[#3b82f6]"
                  />
                </div>
              </div>
            )}
          </div>

          {/* Block: Tools */}
          <div className="border border-[#2b2b2b] rounded-lg overflow-hidden">
            <button
              onClick={() => setShowTools(!showTools)}
              className="w-full flex items-center gap-2 px-4 py-3 bg-[#1a1a1a] hover:bg-[#222] transition-colors"
            >
              {showTools ? <ChevronDown size={16} className="text-[#666]" /> : <ChevronRight size={16} className="text-[#666]" />}
              <Wrench size={16} className="text-[#22c55e]" />
              <span className="text-sm font-medium text-[#e5e5e5]">Tools</span>
              <span className="ml-auto text-xs text-[#555]">{selectedTools.length} selected</span>
            </button>
            
            {showTools && (
              <div className="p-4 space-y-4 bg-[#0f0f0f]">
                {/* Presets */}
                <div className="space-y-1.5">
                  <label className="text-xs text-[#888] uppercase tracking-wide">Tool Preset</label>
                  <select
                    value={selectedPreset}
                    onChange={(e) => handlePresetChange(e.target.value)}
                    className="w-full bg-[#1a1a1a] border border-[#2b2b2b] rounded px-3 py-2 text-sm text-[#e5e5e5] focus:border-[#3b82f6] focus:outline-none cursor-pointer"
                  >
                    <option value="">Custom</option>
                    {Object.keys(presets).map(p => (
                      <option key={p} value={p}>{p}</option>
                    ))}
                  </select>
                </div>

                {/* Tool List */}
                <div className="space-y-1.5">
                  <label className="text-xs text-[#888] uppercase tracking-wide">Available Tools</label>
                  <div className="max-h-48 overflow-y-auto border border-[#2b2b2b] rounded bg-[#1a1a1a] p-2 space-y-1">
                    {tools.map(tool => (
                      <label
                        key={tool}
                        className="flex items-center gap-2 px-2 py-1.5 rounded hover:bg-[#252525] cursor-pointer transition-colors"
                      >
                        <input
                          type="checkbox"
                          checked={selectedTools.includes(tool)}
                          onChange={() => handleToolToggle(tool)}
                          className="accent-[#3b82f6]"
                        />
                        <span className="text-xs text-[#ccc] font-mono">{tool}</span>
                      </label>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Block: LLM */}
          <div className="border border-[#2b2b2b] rounded-lg overflow-hidden">
            <button
              onClick={() => setShowLLM(!showLLM)}
              className="w-full flex items-center gap-2 px-4 py-3 bg-[#1a1a1a] hover:bg-[#222] transition-colors"
            >
              {showLLM ? <ChevronDown size={16} className="text-[#666]" /> : <ChevronRight size={16} className="text-[#666]" />}
              <Cpu size={16} className="text-[#f59e0b]" />
              <span className="text-sm font-medium text-[#e5e5e5]">LLM Configuration</span>
            </button>
            
            {showLLM && (
              <div className="p-4 space-y-4 bg-[#0f0f0f]">
                {/* Model */}
                <div className="space-y-1.5">
                  <label className="text-xs text-[#888] uppercase tracking-wide">Model</label>
                  <input
                    type="text"
                    value={model}
                    onChange={(e) => setModel(e.target.value)}
                    placeholder="local-model"
                    className="w-full bg-[#1a1a1a] border border-[#2b2b2b] rounded px-3 py-2 text-sm text-[#e5e5e5] font-mono focus:border-[#3b82f6] focus:outline-none"
                  />
                </div>

                {/* API URL */}
                <div className="space-y-1.5">
                  <label className="text-xs text-[#888] uppercase tracking-wide">API URL</label>
                  <input
                    type="text"
                    value={apiUrl}
                    onChange={(e) => setApiUrl(e.target.value)}
                    placeholder="http://127.0.0.1:1234/v1"
                    className="w-full bg-[#1a1a1a] border border-[#2b2b2b] rounded px-3 py-2 text-sm text-[#e5e5e5] font-mono focus:border-[#3b82f6] focus:outline-none"
                  />
                </div>

                {/* API Key */}
                <div className="space-y-1.5">
                  <label className="text-xs text-[#888] uppercase tracking-wide">API Key</label>
                  <input
                    type="password"
                    value={apiKey}
                    onChange={(e) => setApiKey(e.target.value)}
                    placeholder="Optional - leave empty for local models"
                    className="w-full bg-[#1a1a1a] border border-[#2b2b2b] rounded px-3 py-2 text-sm text-[#e5e5e5] focus:border-[#3b82f6] focus:outline-none"
                  />
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="flex justify-end gap-3 px-5 py-4 border-t border-[#2b2b2b]">
          <button
            onClick={handleClose}
            className="px-4 py-2 text-sm rounded bg-[#2b2b2b] hover:bg-[#3b3b3b] text-[#888] hover:text-[#e5e5e5] transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleCreate}
            disabled={!name.trim()}
            className="px-4 py-2 text-sm rounded bg-[#3b82f6] hover:bg-[#2563eb] disabled:bg-[#2b2b2b] disabled:text-[#555] text-white font-medium transition-colors"
          >
            Create Agent
          </button>
        </div>
      </div>
    </div>
  );
}

