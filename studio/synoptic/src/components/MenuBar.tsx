import React from 'react';
import { useStore } from '../store';
import { ProjectManager } from '../project/ProjectManager';
import { ProjectFileService } from '../project/ProjectFileService';

export interface MenuBarProps {
  onOpenScadaPreview?: () => void;
  // feat/device-list-ui commit 1: opens the "Rejestry projektu" dialog
  // (locations + cards) - a new top-level menu, same lazy-dialog-owned-
  // by-App.tsx convention as onOpenScadaPreview above.
  onOpenDeviceRegistries?: () => void;
  // feat/device-list-ui commit 2: opens the "Lista aparatow" window.
  onOpenDeviceList?: () => void;
  // feat/help-system commit 2: opens the Help window on whatever
  // getContextualHelpTopic resolves right now - same as pressing F1.
  onOpenHelp?: () => void;
}

export const MenuBar: React.FC<MenuBarProps> = ({ onOpenScadaPreview, onOpenDeviceRegistries, onOpenDeviceList, onOpenHelp }) => {
  const { undo, redo, copySelected, paste, deleteObjects, selectedIds, isDirty, snapToGridEnabled, toggleSnapToGrid } = useStore();
  // feat/wire-routing-around-obstacles commit 3, point (f): PRZELICZ
  // TRASE - on demand only, never automatic.
  const { selectedConnectionIds, recalculateConnectionRoutes } = useStore();

  const handleMenuClick = (action: () => void) => {
    action();
  };

  const handleNew = () => {
    if (isDirty) {
      if (!confirm('Current project has unsaved changes. Are you sure you want to create a new project and lose them?')) {
        return;
      }
    }
    const name = prompt('Enter new project name:', 'New Project');
    if (name) {
      ProjectManager.newProject(name);
    }
  };

  const handleSave = () => {
    ProjectFileService.saveFile();
  };

  const handleSaveAs = () => {
    ProjectFileService.saveFileAs();
  };

  const handleOpen = () => {
    if (isDirty) {
      if (!confirm('Current project has unsaved changes. Are you sure you want to open a different project and lose them?')) {
        return;
      }
    }
    ProjectFileService.openFile();
  };

  const handleExit = () => {
    if (isDirty) {
      if (!confirm('Are you sure you want to exit? All unsaved progress will be lost.')) {
        return;
      }
    }
    window.close();
  }

  return (
    <div className="menu-bar">
      <div className="menu-item">
        <span>File</span>
        <div className="dropdown">
          <div className="dropdown-item" onClick={handleNew}>New</div>
          <div className="dropdown-item" onClick={handleOpen}>Open...</div>
          <div className="dropdown-item" onClick={handleSave}>Save</div>
          <div className="dropdown-item" onClick={handleSaveAs}>Save As...</div>
          <div className="dropdown-item" onClick={handleExit}>Exit</div>
        </div>
      </div>
      <div className="menu-item">
        <span>Edit</span>
        <div className="dropdown">
          <div className="dropdown-item" onClick={() => handleMenuClick(undo)}>Undo</div>
          <div className="dropdown-item" onClick={() => handleMenuClick(redo)}>Redo</div>
          <div className="dropdown-item" onClick={() => handleMenuClick(copySelected)}>Copy</div>
          <div className="dropdown-item" onClick={() => handleMenuClick(paste)}>Paste</div>
          <div className="dropdown-item" onClick={() => handleMenuClick(() => deleteObjects(selectedIds))}>Delete</div>
          <div className="dropdown-item" onClick={() => handleMenuClick(() => recalculateConnectionRoutes(selectedConnectionIds))}>Przelicz trase</div>
        </div>
      </div>
      <div className="menu-item">
        <span>View</span>
        <div className="dropdown">
          <div className="dropdown-item" onClick={toggleSnapToGrid}>
            {snapToGridEnabled ? '✓ ' : '   '}Snap to Grid
          </div>
          <div className="dropdown-item" onClick={() => onOpenScadaPreview?.()}>SCADA Style Preview...</div>
        </div>
      </div>
      <div className="menu-item">
        <span>Aparaty</span>
        <div className="dropdown">
          <div className="dropdown-item" onClick={() => onOpenDeviceRegistries?.()}>Rejestry projektu...</div>
          <div className="dropdown-item" onClick={() => onOpenDeviceList?.()}>Lista aparatow...</div>
        </div>
      </div>
      <div className="menu-item">
        <span>Pomoc</span>
        <div className="dropdown">
          <div className="dropdown-item" onClick={() => onOpenHelp?.()}>Tematy pomocy...  F1</div>
        </div>
      </div>
    </div>
  );
};
