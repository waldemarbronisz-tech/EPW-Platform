// feat/tank-language-and-media commit 1, point (b)/(c): shown the
// instant a wire endpoint would land on a terminal or an existing
// wire of an incompatible medium - the connection is never created at
// all. One button, per this task's own spec ("jeden przycisk
// zamkniecia") - closing it never cancels the wire tool itself, the
// user is free to keep drawing elsewhere. Modeled on AddLocationDialog.tsx's
// own backdrop+centered-box convention (this project's established
// plain-dialog pattern), not a new one.

import React from 'react';
import type { MediaConflict } from '../project/NetResolver';

// Exported so Canvas.tsx's own Messages-panel notice (point d - the
// SAME conflict, reported a second way, not a second wording of it)
// reads the identical labels this dialog shows.
// oxlint-disable-next-line react/only-export-components -- shared with Canvas.tsx, same convention other symbol files already use for a constant kept beside the component it belongs to.
export const MEDIUM_LABEL: Record<MediaConflict['drawnMedium'], string> = {
  ELECTRICAL: 'Electrical',
  WATER: 'Water',
  VENTILATION: 'Ventilation'
};

/**
 * The one line this conflict produces in the Messages panel (point d) -
 * exported so Canvas.tsx builds it here, once, rather than composing
 * its own second wording of the same fact this dialog already shows.
 */
// oxlint-disable-next-line react/only-export-components -- shared with Canvas.tsx, same convention as MEDIUM_LABEL above.
export function mediaConflictMessage(conflict: MediaConflict): string {
  return `[ERROR] Cannot connect: this wire is ${MEDIUM_LABEL[conflict.drawnMedium]}, the ${conflict.source} is ${MEDIUM_LABEL[conflict.otherMedium]} - connection not created.`;
}

export interface MediaMismatchDialogProps {
  conflict: MediaConflict;
  onClose: () => void;
}

export const MediaMismatchDialog: React.FC<MediaMismatchDialogProps> = ({ conflict, onClose }) => {
  const target = conflict.source === 'terminal' ? 'terminal' : 'wire';
  return (
    <>
      <div style={backdropStyle} onClick={onClose} />
      <div style={dialogStyle} onClick={(e) => e.stopPropagation()}>
        <div style={headerStyle}>Incompatible medium</div>
        <div style={bodyStyle}>
          <p style={{ margin: 0 }}>
            This wire is {MEDIUM_LABEL[conflict.drawnMedium]}. The {target} is {MEDIUM_LABEL[conflict.otherMedium]}.
          </p>
          <p style={{ margin: '8px 0 0' }}>Connection not created.</p>
        </div>
        <div style={footerStyle}>
          <button autoFocus onClick={onClose}>Close</button>
        </div>
      </div>
    </>
  );
};

const backdropStyle: React.CSSProperties = {
  position: 'fixed', inset: 0, background: 'var(--scada-outline)', opacity: 0.5, zIndex: 1010
};

const dialogStyle: React.CSSProperties = {
  position: 'fixed', top: '50%', left: '50%', transform: 'translate(-50%, -50%)',
  zIndex: 1011, width: '320px', display: 'flex', flexDirection: 'column',
  background: 'var(--scada-panel)', border: '2px solid var(--scada-outline)', color: 'var(--scada-outline)',
  fontFamily: 'var(--scada-font-ui)', fontSize: 'var(--scada-font-size-base)'
};

const headerStyle: React.CSSProperties = {
  padding: '8px 12px', borderBottom: '1px solid var(--scada-outline)', fontWeight: 'bold'
};

const bodyStyle: React.CSSProperties = { padding: '8px 12px' };

const footerStyle: React.CSSProperties = {
  display: 'flex', justifyContent: 'flex-end', gap: '8px', padding: '8px 12px', borderTop: '1px solid var(--scada-outline)'
};
