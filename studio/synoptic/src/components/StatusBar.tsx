// feat/editing-and-signal-panel commit 4: the canvas's current zoom,
// visible somewhere permanent rather than only guessable from how big
// things look. canvasState.zoom is a session-only setting (never
// written to the project file - see ProjectManager.ts's own comment),
// so this simply reflects whatever the store currently holds.

import React from 'react';
import { useStore } from '../store';

export const StatusBar: React.FC = () => {
  const zoom = useStore(state => state.canvasState.zoom);
  return (
    <div className="status-bar">
      <span>{Math.round(zoom * 100)}%</span>
    </div>
  );
};
