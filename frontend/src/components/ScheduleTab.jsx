import React, { useState, useEffect } from 'react';
import { socket } from '../lib/socket';
import { Calendar, Trash2, Pause, RotateCcw } from 'lucide-react';

export default function ScheduleTab() {
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    socket.emit('get_schedule');
    
    socket.on('schedule_update', (data) => {
      setTasks(data.tasks || []);
      setLoading(false);
    });

    const interval = setInterval(() => {
      socket.emit('get_schedule');
    }, 2000);

    return () => {
      socket.off('schedule_update');
      clearInterval(interval);
    };
  }, []);

  const pauseTask = (taskId) => {
    socket.emit('pause_schedule_task', { taskId });
  };

  const resumeTask = (taskId) => {
    socket.emit('resume_schedule_task', { taskId });
  };

  const cancelTask = (taskId) => {
    socket.emit('cancel_schedule_task', { taskId });
  };

  const formatTime = (isoString) => {
    if (!isoString) return '-';
    const date = new Date(isoString);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  };

  return (
    <div className="h-full overflow-y-auto p-4">
      <div className="flex items-center justify-between mb-4">
        <div className="text-[11px] text-[#666] uppercase tracking-wide font-medium">
          Scheduled Tasks
        </div>
        <span className="text-[10px] text-[#555]">{tasks.length} tasks</span>
      </div>

      {loading ? (
        <div className="text-center text-[#555] py-8">Loading...</div>
      ) : tasks.length === 0 ? (
        <div className="text-center text-[#555] py-8">
          <Calendar size={24} className="mx-auto mb-2 opacity-50" />
          <p className="text-xs">No scheduled tasks</p>
          <p className="text-[10px] mt-1">Enable autonomous mode to create tasks</p>
        </div>
      ) : (
        <div className="space-y-2">
          {tasks.map((task) => (
            <div 
              key={task.id} 
              className={`p-3 rounded border ${
                task.enabled ? 'border-[#2b2b2b] bg-[#1a1a1a]' : 'border-[#2b2b2b] bg-[#151515] opacity-60'
              }`}
            >
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <div className={`w-2 h-2 rounded-full ${task.enabled ? 'bg-[#22c55e]' : 'bg-[#888]'}`} />
                  <span className="text-xs font-medium text-[#e5e5e5]">{task.id}</span>
                </div>
                <div className="flex items-center gap-1">
                  {task.enabled ? (
                    <button 
                      onClick={() => pauseTask(task.id)}
                      className="p-1 text-[#888] hover:text-[#eab308]"
                      title="Pause"
                    >
                      <Pause size={12} />
                    </button>
                  ) : (
                    <button 
                      onClick={() => resumeTask(task.id)}
                      className="p-1 text-[#888] hover:text-[#22c55e]"
                      title="Resume"
                    >
                      <RotateCcw size={12} />
                    </button>
                  )}
                  <button 
                    onClick={() => cancelTask(task.id)}
                    className="p-1 text-[#888] hover:text-[#ef4444]"
                    title="Cancel"
                  >
                    <Trash2 size={12} />
                  </button>
                </div>
              </div>
              
              <div className="grid grid-cols-2 gap-2 text-[10px]">
                <div>
                  <span className="text-[#666]">Agent: </span>
                  <span className="text-[#888]">{task.agent_name}</span>
                </div>
                <div>
                  <span className="text-[#666]">Type: </span>
                  <span className="text-[#888]">{task.trigger_type}</span>
                </div>
                {task.trigger_type === 'interval' && (
                  <>
                    <div>
                      <span className="text-[#666]">Interval: </span>
                      <span className="text-[#888]">{task.interval_seconds}s</span>
                    </div>
                    <div>
                      <span className="text-[#666]">Last Run: </span>
                      <span className="text-[#888]">{formatTime(task.last_run)}</span>
                    </div>
                  </>
                )}
                {task.trigger_type === 'once' && (
                  <div>
                    <span className="text-[#666]">Run At: </span>
                    <span className="text-[#888]">{formatTime(task.run_at)}</span>
                  </div>
                )}
                <div>
                  <span className="text-[#666]">Run Count: </span>
                  <span className="text-[#888]">{task.run_count}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

