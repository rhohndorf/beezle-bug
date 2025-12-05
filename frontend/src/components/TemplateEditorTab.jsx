import React, { useState, useEffect, useCallback } from 'react';
import { socket } from '../lib/socket';
import { FileText, Plus, Save, Trash2, X, AlertCircle, Check } from 'lucide-react';

export default function TemplateEditorTab() {
  const [templates, setTemplates] = useState([]);
  const [selectedTemplate, setSelectedTemplate] = useState(null);
  const [content, setContent] = useState('');
  const [originalContent, setOriginalContent] = useState('');
  const [isCreating, setIsCreating] = useState(false);
  const [newTemplateName, setNewTemplateName] = useState('');
  const [error, setError] = useState(null);

  const hasUnsavedChanges = content !== originalContent;

  // Load template list on mount
  useEffect(() => {
    socket.emit('get_templates');

    const handleTemplatesList = (data) => {
      setTemplates(data.templates || []);
    };

    const handleTemplateContent = (data) => {
      if (data.name === selectedTemplate) {
        setContent(data.content);
        setOriginalContent(data.content);
      }
    };

    const handleTemplateSaved = (data) => {
      // Refresh original content after save
      setOriginalContent(content);
      setIsCreating(false);
      setNewTemplateName('');
      setError(null);
    };

    const handleTemplateDeleted = (data) => {
      if (data.name === selectedTemplate) {
        setSelectedTemplate(null);
        setContent('');
        setOriginalContent('');
      }
    };

    const handleError = (data) => {
      setError(data.message);
      setTimeout(() => setError(null), 5000);
    };

    socket.on('templates_list', handleTemplatesList);
    socket.on('template_content', handleTemplateContent);
    socket.on('template_saved', handleTemplateSaved);
    socket.on('template_deleted', handleTemplateDeleted);
    socket.on('error', handleError);

    return () => {
      socket.off('templates_list', handleTemplatesList);
      socket.off('template_content', handleTemplateContent);
      socket.off('template_saved', handleTemplateSaved);
      socket.off('template_deleted', handleTemplateDeleted);
      socket.off('error', handleError);
    };
  }, [selectedTemplate, content]);

  // Load content when template is selected
  useEffect(() => {
    if (selectedTemplate && !isCreating) {
      socket.emit('get_template_content', { name: selectedTemplate });
    }
  }, [selectedTemplate, isCreating]);

  const selectTemplate = (name) => {
    if (hasUnsavedChanges) {
      if (!confirm('You have unsaved changes. Discard them?')) {
        return;
      }
    }
    setIsCreating(false);
    setSelectedTemplate(name);
    setError(null);
  };

  const startCreating = () => {
    if (hasUnsavedChanges) {
      if (!confirm('You have unsaved changes. Discard them?')) {
        return;
      }
    }
    setIsCreating(true);
    setSelectedTemplate(null);
    setContent('');
    setOriginalContent('');
    setNewTemplateName('');
    setError(null);
  };

  const cancelCreating = () => {
    setIsCreating(false);
    setNewTemplateName('');
    setContent('');
    setOriginalContent('');
  };

  const saveTemplate = () => {
    const name = isCreating ? newTemplateName.trim() : selectedTemplate;
    if (!name) {
      setError('Template name is required');
      return;
    }
    
    // Validate name (alphanumeric, underscore, dash only)
    if (!/^[a-zA-Z0-9_-]+$/.test(name)) {
      setError('Template name can only contain letters, numbers, underscores, and dashes');
      return;
    }

    socket.emit('save_template', { name, content });
    
    if (isCreating) {
      setSelectedTemplate(name);
    }
  };

  const deleteTemplate = () => {
    if (!selectedTemplate) return;
    if (!confirm(`Delete template "${selectedTemplate}"? This cannot be undone.`)) {
      return;
    }
    socket.emit('delete_template', { name: selectedTemplate });
  };

  const handleKeyDown = useCallback((e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 's') {
      e.preventDefault();
      if (hasUnsavedChanges || isCreating) {
        saveTemplate();
      }
    }
  }, [hasUnsavedChanges, isCreating, content, selectedTemplate, newTemplateName]);

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);

  return (
    <div className="flex h-full">
      {/* Left sidebar - template list */}
      <div className="w-48 flex-shrink-0 border-r border-[#2b2b2b] flex flex-col">
        <div className="p-2 border-b border-[#2b2b2b]">
          <button
            onClick={startCreating}
            className="w-full flex items-center justify-center gap-1.5 px-3 py-1.5 bg-[#1a1a1a] hover:bg-[#252525] border border-[#2b2b2b] rounded text-xs text-[#e5e5e5] transition-colors"
          >
            <Plus size={12} />
            New Template
          </button>
        </div>
        
        <div className="flex-1 overflow-y-auto">
          {templates.map((name) => (
            <button
              key={name}
              onClick={() => selectTemplate(name)}
              className={`w-full flex items-center gap-2 px-3 py-2 text-xs text-left transition-colors ${
                selectedTemplate === name
                  ? 'bg-[#1f3a5f] text-[#e5e5e5] border-l-2 border-[#3b82f6]'
                  : 'text-[#888] hover:bg-[#1a1a1a] hover:text-[#e5e5e5] border-l-2 border-transparent'
              }`}
            >
              <FileText size={12} className="flex-shrink-0 opacity-50" />
              <span className="truncate">{name}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Right side - editor */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Toolbar */}
        <div className="h-10 px-3 border-b border-[#2b2b2b] flex items-center justify-between bg-[#0a0a0a]">
          <div className="flex items-center gap-2">
            {isCreating ? (
              <div className="flex items-center gap-2">
                <input
                  type="text"
                  value={newTemplateName}
                  onChange={(e) => setNewTemplateName(e.target.value)}
                  placeholder="template_name"
                  className="px-2 py-1 bg-[#0a0a0a] border border-[#2b2b2b] rounded text-xs text-[#e5e5e5] w-40 focus:outline-none focus:border-[#3b82f6]"
                  autoFocus
                />
                <button
                  onClick={cancelCreating}
                  className="p-1 text-[#666] hover:text-[#e5e5e5] transition-colors"
                  title="Cancel"
                >
                  <X size={14} />
                </button>
              </div>
            ) : selectedTemplate ? (
              <div className="flex items-center gap-2">
                <FileText size={14} className="text-[#3b82f6]" />
                <span className="text-xs text-[#e5e5e5] font-medium">{selectedTemplate}.j2</span>
                {hasUnsavedChanges && (
                  <span className="text-[10px] text-[#f59e0b] flex items-center gap-1">
                    <AlertCircle size={10} />
                    Unsaved
                  </span>
                )}
              </div>
            ) : (
              <span className="text-xs text-[#555]">Select a template to edit</span>
            )}
          </div>

          <div className="flex items-center gap-1">
            {(selectedTemplate || isCreating) && (
              <>
                <button
                  onClick={saveTemplate}
                  disabled={!hasUnsavedChanges && !isCreating}
                  className={`flex items-center gap-1.5 px-2.5 py-1 rounded text-xs transition-colors ${
                    hasUnsavedChanges || isCreating
                      ? 'bg-[#3b82f6] hover:bg-[#2563eb] text-white'
                      : 'bg-[#1a1a1a] text-[#555] cursor-not-allowed'
                  }`}
                  title="Save (Ctrl+S)"
                >
                  <Save size={12} />
                  Save
                </button>
                {selectedTemplate && !isCreating && (
                  <button
                    onClick={deleteTemplate}
                    className="flex items-center gap-1.5 px-2.5 py-1 rounded text-xs bg-[#1a1a1a] hover:bg-[#7f1d1d] text-[#888] hover:text-[#ef4444] transition-colors"
                    title="Delete template"
                  >
                    <Trash2 size={12} />
                  </button>
                )}
              </>
            )}
          </div>
        </div>

        {/* Error banner */}
        {error && (
          <div className="px-3 py-2 bg-[#7f1d1d]/30 border-b border-[#7f1d1d] text-xs text-[#fca5a5] flex items-center gap-2">
            <AlertCircle size={12} />
            {error}
          </div>
        )}

        {/* Editor area */}
        <div className="flex-1 overflow-hidden">
          {(selectedTemplate || isCreating) ? (
            <textarea
              value={content}
              onChange={(e) => setContent(e.target.value)}
              className="w-full h-full p-4 bg-[#0a0a0a] text-[#e5e5e5] text-xs font-mono resize-none focus:outline-none leading-relaxed"
              placeholder={isCreating ? 'Enter template content...\n\nJinja2 syntax is supported:\n{{ variable }}\n{% for item in items %}\n{% if condition %}' : ''}
              spellCheck={false}
            />
          ) : (
            <div className="flex flex-col items-center justify-center h-full text-[#555] text-xs gap-4">
              <FileText size={48} className="opacity-20" />
              <div className="text-center">
                <p>Select a template from the list</p>
                <p className="text-[#444] mt-1">or create a new one</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}







