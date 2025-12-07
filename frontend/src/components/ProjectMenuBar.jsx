import React, { useState, useEffect, useRef, useCallback } from 'react';
import { socket } from '../lib/socket';
import { FolderOpen, Plus, ChevronDown, X, Trash2, AlertTriangle, Save, Play, Square } from 'lucide-react';

export default function ProjectMenuBar({ 
  projectId, 
  projectName, 
  isDeployed: isDeployedProp,
  onProjectChange 
}) {
  const [showProjectMenu, setShowProjectMenu] = useState(false);
  const [showNewProjectDialog, setShowNewProjectDialog] = useState(false);
  const [showUnsavedDialog, setShowUnsavedDialog] = useState(false);
  const [projects, setProjects] = useState([]);
  const [newProjectName, setNewProjectName] = useState('');
  const [hasUnsaved, setHasUnsaved] = useState(false);
  const [isDeployed, setIsDeployed] = useState(isDeployedProp);
  
  // Track saved vs current TTS settings for unsaved changes detection
  const savedTtsSettings = useRef(null);
  const currentTtsSettings = useRef(null);
  const pendingAction = useRef(null); // Store the action to perform after save/discard
  const hasReceivedProjectSettings = useRef(false); // Track if we've set settings from project

  // Check if TTS settings have changed since last save
  const hasUnsavedChanges = useCallback(() => {
    return hasUnsaved;
  }, [hasUnsaved]);

  // Sync local state with prop when prop changes
  useEffect(() => {
    setIsDeployed(isDeployedProp);
  }, [isDeployedProp]);

  useEffect(() => {
    const handleProjectsList = (data) => {
      setProjects(data.projects || []);
    };

    const handleProjectCreated = (data) => {
      setNewProjectName('');
      setShowNewProjectDialog(false);
      socket.emit('load_project', { id: data.id });
    };

    // Listen to agent_graph_state for real-time deploy/undeploy updates
    const handleAgentGraphState = (data) => {
      setIsDeployed(data.is_deployed || false);
    };

    // Track TTS settings from project load (the "saved" state)
    const handleProjectLoaded = (data) => {
      const ttsSettings = data.tts_settings || {
        enabled: false,
        voice: null,
        speed: 1.0,
        speaker: 0,
      };
      savedTtsSettings.current = { ...ttsSettings };
      currentTtsSettings.current = { ...ttsSettings };
      hasReceivedProjectSettings.current = true;
      setHasUnsaved(false);
    };

    // Track current TTS settings changes
    const handleTtsSettings = (data) => {
      const newSettings = {
        enabled: data.enabled,
        voice: data.voice,
        speed: data.speed,
        speaker: data.speaker,
      };
      currentTtsSettings.current = newSettings;
      
      // If we haven't received project settings yet, use server settings as baseline
      // This handles the case where page loads with a project already loaded
      if (!hasReceivedProjectSettings.current && !savedTtsSettings.current) {
        savedTtsSettings.current = { ...newSettings };
        // Don't mark as unsaved since this is just initialization
        return;
      }
      
      // Update hasUnsaved state by comparing to saved settings
      const saved = savedTtsSettings.current;
      if (saved) {
        const hasChanges = (
          saved.enabled !== newSettings.enabled ||
          saved.voice !== newSettings.voice ||
          saved.speed !== newSettings.speed ||
          saved.speaker !== newSettings.speaker
        );
        setHasUnsaved(hasChanges);
      }
    };

    socket.on('projects_list', handleProjectsList);
    socket.on('project_created', handleProjectCreated);
    socket.on('agent_graph_state', handleAgentGraphState);
    socket.on('project_loaded', handleProjectLoaded);
    socket.on('tts_settings', handleTtsSettings);

    socket.emit('list_projects');
    // Request initial TTS settings on mount
    socket.emit('get_tts_settings');

    return () => {
      socket.off('projects_list', handleProjectsList);
      socket.off('project_created', handleProjectCreated);
      socket.off('project_loaded', handleProjectLoaded);
      socket.off('tts_settings', handleTtsSettings);
      socket.off('agent_graph_state', handleAgentGraphState);
    };
  }, []);

  const doCreateProject = () => {
    if (newProjectName.trim()) {
      socket.emit('create_project', { name: newProjectName.trim() });
    }
  };

  const doLoadProject = (id) => {
    socket.emit('load_project', { id });
    setShowProjectMenu(false);
  };

  const createProject = () => {
    if (projectId && hasUnsavedChanges()) {
      pendingAction.current = { type: 'create' };
      setShowUnsavedDialog(true);
    } else {
      doCreateProject();
    }
  };

  const loadProject = (id) => {
    if (projectId && projectId !== id && hasUnsavedChanges()) {
      pendingAction.current = { type: 'load', id };
      setShowUnsavedDialog(true);
      setShowProjectMenu(false);
    } else {
      doLoadProject(id);
    }
  };

  const closeProject = () => {
    if (projectId && hasUnsavedChanges()) {
      pendingAction.current = { type: 'close' };
      setShowUnsavedDialog(true);
      setShowProjectMenu(false);
    } else {
      socket.emit('stop_project');
      setShowProjectMenu(false);
    }
  };

  const handleUnsavedSaveAndContinue = () => {
    socket.emit('save_project');
    // Update saved settings to match current
    savedTtsSettings.current = { ...currentTtsSettings.current };
    setHasUnsaved(false);
    executePendingAction();
  };

  const handleUnsavedDiscard = () => {
    executePendingAction();
  };

  const handleUnsavedCancel = () => {
    setShowUnsavedDialog(false);
    pendingAction.current = null;
  };

  const executePendingAction = () => {
    setShowUnsavedDialog(false);
    const action = pendingAction.current;
    pendingAction.current = null;
    
    if (!action) return;
    
    switch (action.type) {
      case 'create':
        doCreateProject();
        break;
      case 'load':
        doLoadProject(action.id);
        break;
      case 'close':
        socket.emit('stop_project');
        break;
    }
  };

  const deleteProject = (e, id) => {
    e.stopPropagation();
    if (confirm('Are you sure you want to delete this project?')) {
      socket.emit('delete_project', { id });
      if (projectId === id) {
        socket.emit('stop_project');
      }
    }
  };

  return (
    <>
      <div className="h-9 bg-[#0a0a0a] border-b border-[#2b2b2b] flex items-center justify-between px-3 flex-shrink-0">
        <div className="flex items-center gap-3">
          {/* App title / logo */}
          <span className="text-[#3b82f6] font-bold text-sm tracking-tight">
            beezle<span className="text-[#888]">bug</span>
          </span>
          
          <div className="h-4 w-px bg-[#2b2b2b]" />
          
          {/* Project dropdown */}
          <div className="relative">
            <button
              onClick={() => setShowProjectMenu(!showProjectMenu)}
              className="flex items-center gap-2 px-2.5 py-1 text-xs rounded hover:bg-[#1a1a1a] text-[#888] hover:text-[#e5e5e5] transition-colors"
            >
              <FolderOpen size={14} />
              <span className="max-w-[150px] truncate">
                {projectName || 'No Project'}
              </span>
              {hasUnsaved && projectId && (
                <span className="w-2 h-2 rounded-full bg-[#f59e0b]" title="Unsaved changes" />
              )}
              <ChevronDown size={12} className={`transition-transform ${showProjectMenu ? 'rotate-180' : ''}`} />
            </button>
            
            {/* Project dropdown menu */}
            {showProjectMenu && (
              <div className="absolute top-full left-0 mt-1 bg-[#1a1a1a] border border-[#2b2b2b] rounded-lg shadow-xl z-50 min-w-[220px]">
                {/* New project option */}
                <button
                  onClick={() => {
                    setShowProjectMenu(false);
                    setShowNewProjectDialog(true);
                  }}
                  className="w-full flex items-center gap-2 px-3 py-2 text-xs hover:bg-[#2b2b2b] text-[#3b82f6] transition-colors rounded-t-lg"
                >
                  <Plus size={14} />
                  New Project
                </button>
                
                <div className="border-t border-[#2b2b2b]" />
                
                {/* Recent projects */}
                <div className="max-h-[200px] overflow-y-auto">
                  {projects.length === 0 ? (
                    <div className="px-3 py-3 text-[10px] text-[#555] text-center">
                      No projects yet
                    </div>
                  ) : (
                    projects.map((project) => (
                      <button
                        key={project.id}
                        onClick={() => loadProject(project.id)}
                        className={`w-full flex items-center justify-between px-3 py-2 text-xs hover:bg-[#2b2b2b] transition-colors group ${
                          projectId === project.id ? 'bg-[#3b82f6]/10' : ''
                        }`}
                      >
                        <div className="flex items-center gap-2 min-w-0">
                          <FolderOpen size={12} className={projectId === project.id ? 'text-[#3b82f6]' : 'text-[#666]'} />
                          <span className={`truncate ${projectId === project.id ? 'text-[#3b82f6]' : 'text-[#e5e5e5]'}`}>
                            {project.name}
                          </span>
                        </div>
                        <button
                          onClick={(e) => deleteProject(e, project.id)}
                          className="p-1 text-[#555] hover:text-[#ef4444] opacity-0 group-hover:opacity-100 transition-opacity"
                          title="Delete project"
                        >
                          <Trash2 size={12} />
                        </button>
                      </button>
                    ))
                  )}
                </div>
                
                {projectId && (
                  <>
                    <div className="border-t border-[#2b2b2b]" />
                    <button
                      onClick={closeProject}
                      className="w-full flex items-center gap-2 px-3 py-2 text-xs hover:bg-[#2b2b2b] text-[#888] transition-colors rounded-b-lg"
                    >
                      <X size={14} />
                      Close Project
                    </button>
                  </>
                )}
              </div>
            )}
          </div>
          
          {/* Save and Delete buttons */}
          {projectId && (
            <div className="flex items-center gap-1">
              <button
                onClick={() => {
                  socket.emit('save_project');
                  savedTtsSettings.current = { ...currentTtsSettings.current };
                  setHasUnsaved(false);
                }}
                className="p-1.5 text-[#888] hover:text-[#22c55e] transition-colors"
                title="Save project"
              >
                <Save size={14} />
              </button>
              <button
                onClick={(e) => deleteProject(e, projectId)}
                disabled={isDeployed}
                className="p-1.5 text-[#888] hover:text-[#ef4444] disabled:opacity-30 disabled:hover:text-[#888] transition-colors"
                title={isDeployed ? "Stop project before deleting" : "Delete project"}
              >
                <Trash2 size={14} />
              </button>
            </div>
          )}
        </div>
        
        <div className="flex items-center gap-3">
          {/* Deploy/Undeploy button */}
          {projectId && (
            <>
              {isDeployed ? (
                <button
                  onClick={() => socket.emit('undeploy_project')}
                  className="flex items-center gap-1.5 px-3 py-1 bg-[#ef4444] hover:bg-[#dc2626] text-white text-xs rounded transition-colors"
                  title="Stop running agent graph"
                >
                  <Square size={12} />
                  Stop
                </button>
              ) : (
                <button
                  onClick={() => socket.emit('deploy_project')}
                  className="flex items-center gap-1.5 px-3 py-1 bg-[#22c55e] hover:bg-[#16a34a] text-white text-xs rounded transition-colors"
                  title="Deploy and run agent graph"
                >
                  <Play size={12} />
                  Deploy
                </button>
              )}
            </>
          )}
        </div>
      </div>
      
      {/* Click outside to close menu */}
      {showProjectMenu && (
        <div 
          className="fixed inset-0 z-40" 
          onClick={() => setShowProjectMenu(false)}
        />
      )}
      
      {/* New Project Dialog */}
      {showNewProjectDialog && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-[#1a1a1a] border border-[#2b2b2b] rounded-lg w-80">
            <div className="flex items-center justify-between px-4 py-3 border-b border-[#2b2b2b]">
              <h3 className="text-sm font-medium text-[#e5e5e5]">New Project</h3>
              <button
                onClick={() => setShowNewProjectDialog(false)}
                className="p-1 rounded hover:bg-[#2b2b2b] text-[#666] hover:text-[#e5e5e5] transition-colors"
              >
                <X size={16} />
              </button>
            </div>
            
            <div className="p-4">
              <label className="text-[11px] text-[#666] uppercase tracking-wide block mb-2">
                Project Name
              </label>
              <input
                type="text"
                value={newProjectName}
                onChange={(e) => setNewProjectName(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && doCreateProject()}
                placeholder="My Agent Graph..."
                autoFocus
                className="w-full px-3 py-2 bg-[#0a0a0a] border border-[#2b2b2b] rounded text-sm text-[#e5e5e5] placeholder-[#555] focus:outline-none focus:border-[#3b82f6]"
              />
              
              <div className="flex justify-end gap-2 mt-4">
                <button
                  onClick={() => setShowNewProjectDialog(false)}
                  className="px-3 py-1.5 text-xs text-[#888] hover:text-[#e5e5e5] transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={doCreateProject}
                  disabled={!newProjectName.trim()}
                  className="px-4 py-1.5 bg-[#3b82f6] hover:bg-[#2563eb] disabled:bg-[#2b2b2b] disabled:text-[#555] text-white text-xs rounded transition-colors"
                >
                  Create
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Unsaved Changes Dialog */}
      {showUnsavedDialog && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-[#1a1a1a] border border-[#2b2b2b] rounded-lg w-96">
            <div className="flex items-center gap-3 px-4 py-3 border-b border-[#2b2b2b]">
              <AlertTriangle size={18} className="text-[#f59e0b]" />
              <h3 className="text-sm font-medium text-[#e5e5e5]">Unsaved Changes</h3>
            </div>
            
            <div className="p-4">
              <p className="text-xs text-[#888] mb-4">
                You have unsaved changes to your TTS settings. Would you like to save them before continuing?
              </p>
              
              <div className="flex justify-end gap-2">
                <button
                  onClick={handleUnsavedCancel}
                  className="px-3 py-1.5 text-xs text-[#888] hover:text-[#e5e5e5] transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={handleUnsavedDiscard}
                  className="px-3 py-1.5 text-xs text-[#ef4444] hover:text-[#f87171] transition-colors"
                >
                  Don't Save
                </button>
                <button
                  onClick={handleUnsavedSaveAndContinue}
                  className="px-4 py-1.5 bg-[#3b82f6] hover:bg-[#2563eb] text-white text-xs rounded transition-colors"
                >
                  Save & Continue
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

