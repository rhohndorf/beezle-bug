import React, { useState, useEffect } from 'react';
import { socket } from '../lib/socket';
import { Database, AlertTriangle } from 'lucide-react';

// Storage backend options (expandable in future)
const STORAGE_OPTIONS = [
  { value: 'sqlite', label: 'SQLite' },
];

export default function GeneralSettingsTab() {
  const [storageBackend, setStorageBackend] = useState('sqlite');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const requestSettings = () => {
      socket.emit('get_general_settings');
    };

    requestSettings();

    const timeout = setTimeout(() => {
      setLoading(false);
    }, 3000);

    const handleGeneralSettings = (data) => {
      if (data.storage_backend) {
        setStorageBackend(data.storage_backend);
      }
      setLoading(false);
      clearTimeout(timeout);
    };

    const handleConnect = () => {
      requestSettings();
    };

    socket.on('general_settings', handleGeneralSettings);
    socket.on('connect', handleConnect);

    return () => {
      socket.off('general_settings', handleGeneralSettings);
      socket.off('connect', handleConnect);
      clearTimeout(timeout);
    };
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full text-[#666]">
        Loading settings...
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto p-4 space-y-6">
      {/* Storage Section */}
      <div className="space-y-3">
        <div className="flex items-center gap-2 text-sm font-medium text-[#e5e5e5]">
          <Database size={16} />
          Storage
        </div>

        <div className="p-3 rounded border border-[#2b2b2b] bg-[#1a1a1a] space-y-3">
          {/* Backend Selection */}
          <div>
            <label className="block text-xs text-[#888] mb-1.5">Backend</label>
            <select
              value={storageBackend}
              disabled
              className="w-full bg-[#0d0d0d] border border-[#2b2b2b] rounded px-3 py-2 text-sm text-[#e5e5e5] focus:outline-none focus:border-[#3b82f6] disabled:opacity-60 disabled:cursor-not-allowed"
            >
              {STORAGE_OPTIONS.map(opt => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>

          {/* Info/Warning */}
          <div className="flex items-start gap-2 text-[10px] text-[#666] bg-[#0d0d0d] rounded p-2">
            <AlertTriangle size={12} className="text-[#f59e0b] mt-0.5 flex-shrink-0" />
            <span>
              Storage backend is configured via environment variable. 
              Changes require server restart.
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}

