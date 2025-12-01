/**
 * TTS Context for sharing text-to-speech state across components
 */

import React, { createContext, useContext } from 'react';
import { useTTS, VOICES } from '../hooks/useTTS';

const TTSContext = createContext(null);

/**
 * TTS Provider component
 */
export function TTSProvider({ children }) {
  const tts = useTTS();
  
  return (
    <TTSContext.Provider value={tts}>
      {children}
    </TTSContext.Provider>
  );
}

/**
 * Hook to access TTS context
 */
export function useTTSContext() {
  const context = useContext(TTSContext);
  if (!context) {
    throw new Error('useTTSContext must be used within a TTSProvider');
  }
  return context;
}

export { VOICES };
export default TTSContext;

