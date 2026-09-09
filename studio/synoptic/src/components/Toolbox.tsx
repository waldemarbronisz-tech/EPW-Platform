import React, { useState, useMemo } from 'react';
import { getSymbolsByCategory } from '../symbols/SymbolRegistry';

export const Toolbox: React.FC = () => {
  const library = useMemo(() => getSymbolsByCategory(), []);

  // feat/appearance-selection-frames commit 4a: this used to be a
  // literal three-category object (Electrical/Water/SCADA) written
  // before HVAC and Instrumentation existed - both silently defaulted
  // to collapsed ever since, hiding seven symbols until a user
  // happened to click their folders. Every category the registry
  // actually returns now starts expanded, derived directly from
  // `library` itself so a future category can never repeat this same
  // bug by omission.
  const [expanded, setExpanded] = useState<Record<string, boolean>>(
    () => Object.fromEntries(Object.keys(library).map(category => [category, true]))
  );

  const toggleFolder = (folder: string) => {
    setExpanded(prev => ({ ...prev, [folder]: !prev[folder] }));
  };

  const handleDragStart = (e: React.DragEvent, type: string, category: string) => {
    e.dataTransfer.setData('application/reactflow', JSON.stringify({ type, category }));
    e.dataTransfer.effectAllowed = 'move';
  };

  return (
    <div className="toolbox">
      <div className="toolbox-header">Object Library</div>
      <div className="toolbox-content">
        {Object.entries(library).map(([category, items]) => (
          <div key={category} className="folder">
            <div
              className="folder-header"
              onClick={() => toggleFolder(category)}
            >
              <span className="folder-icon">{expanded[category] !== false ? '📂' : '📁'}</span>
              <span className="folder-name">{category.replace('_', ' ')}</span>
            </div>
            {expanded[category] !== false && (
              <div className="folder-items">
                {items.map(def => (
                  <div
                    key={def.type}
                    className="library-item"
                    draggable
                    onDragStart={(e) => handleDragStart(e, def.type, category)}
                  >
                    📄 {def.label}
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};
