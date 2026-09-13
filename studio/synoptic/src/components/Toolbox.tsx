import { ScadaTools } from './ScadaTools';
import React, { useState, useMemo } from 'react';
import { getSymbolsByCategory, getSymbolDefinition } from '../symbols/SymbolRegistry';
import { matchesQuery, RECENT_LABEL } from '../project/RecentSymbols';
import { RoomTakeoffDialog } from './RoomTakeoffDialog';
import { useStore } from '../store';
import {
  WALL_MIN_THICKNESS, WALL_MAX_THICKNESS,
  WALL_MIN_HEIGHT, WALL_MAX_HEIGHT,
} from '../elements/WallElement';
import {
  FLOOR_MATERIALS, WALL_MATERIALS,
  DEFAULT_FLOOR_MATERIAL,
} from '../theme/Materials';
import type { FloorMaterialId, WallMaterialId } from '../theme/Materials';

// feat/room-plan: the BUDYNEK department. Walls, luminaires and sockets
// belong to ONE section of this tree, and the wall TOOL belongs there
// with them - it is the third way of putting a building element on the
// canvas, not a global drawing mode that happens to live in the
// toolbar. The room's own surfaces (wall material, floor material) are
// here too, for the same reason: everything needed to build a room is
// in the one place you go to build one.
//
// The tool is a CLICK entry, not a draggable one: you arm it and then
// click corners on the canvas. Every other entry in this tree is
// dragged onto the canvas. Both live in the same folder because they
// answer the same question ("what do I want to add?"), and the two
// behave visibly differently - an armed tool stays highlighted.
const BUILDING_CATEGORY = 'BUILDING';

// feat/toolbar-grouping: inserting meters, panels, text and drawing
// wires/frames now lives in the SCADA department (ScadaTools.tsx)
// instead of the top toolbar.
const SCADA_CATEGORY = 'SCADA';

// feat/library-recent-and-search: two things the Logic editor's own
// library has always had and this one did not - a search box, and the
// symbols you last used kept at the top.
//
// Both matter more here than they look. The library is past sixty
// symbols across seven departments, which is well past the point where
// scrolling to find one is slower than typing three letters of its name;
// and a working session uses the same handful over and over, so the list
// of those IS the shortest path to most of what gets drawn.
//
// The search is deliberately the same rule as the Logic editor's: it
// matches the label and the type, case- and accent-insensitively, hides
// what does not match, and opens any folder that still has something in
// it. A search that leaves its results inside a collapsed folder is a
// search that looks like it found nothing.

export const Toolbox: React.FC = () => {
  const library = useMemo(() => getSymbolsByCategory(), []);
  const recentSymbols = useStore(s => s.recentSymbols);
  const [query, setQuery] = useState('');

  const isDrawingWall = useStore(s => s.isDrawingWall);
  const setDrawingWallMode = useStore(s => s.setDrawingWallMode);
  const isDrawingRoom = useStore(s => s.isDrawingRoom);
  const setDrawingRoomMode = useStore(s => s.setDrawingRoomMode);
  const wallDrawThickness = useStore(s => s.wallDrawThickness);
  const setWallDrawThickness = useStore(s => s.setWallDrawThickness);
  const wallDrawHeight = useStore(s => s.wallDrawHeight);
  const setWallDrawHeight = useStore(s => s.setWallDrawHeight);
  const wallDrawMaterial = useStore(s => s.wallDrawMaterial);
  const setWallDrawMaterial = useStore(s => s.setWallDrawMaterial);
  const floorMaterial = useStore(s => s.canvasConfig.floorMaterial);
  const setFloorMaterial = useStore(s => s.setFloorMaterial);
  const showIlluminance = useStore(s => s.showIlluminance);
  const setShowIlluminance = useStore(s => s.setShowIlluminance);

  // feat/appearance-selection-frames commit 4a: this used to be a
  // literal three-category object (Electrical/Water/SCADA) written
  // before HVAC and Instrumentation existed - both silently defaulted
  // to collapsed ever since, hiding seven symbols until a user
  // happened to click their folders. Every category the registry
  // actually returns now starts expanded, derived directly from
  // `library` itself so a future category can never repeat this same
  // bug by omission.
  const [showTakeoff, setShowTakeoff] = useState(false);

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

  const renderBuildingTools = () => (
    <>
      <div
        className="library-item"
        onClick={() => setDrawingWallMode(!isDrawingWall)}
        style={{
          cursor: 'pointer',
          fontWeight: isDrawingWall ? 'bold' : undefined,
          background: isDrawingWall ? '#00A800' : undefined,
          color: isDrawingWall ? '#FFFFFF' : undefined,
        }}
        title="Click the room's corners - each new wall starts where the previous one ended. Esc finishes."
      >
        {isDrawingWall ? '■' : '□'} Draw wall
      </div>

      <div
        className="library-item"
        onClick={() => setDrawingRoomMode(!isDrawingRoom)}
        style={{
          cursor: 'pointer',
          fontWeight: isDrawingRoom ? 'bold' : undefined,
          background: isDrawingRoom ? '#00A800' : undefined,
          color: isDrawingRoom ? '#FFFFFF' : undefined,
        }}
        title="Drag a rectangle - four walls are created at once, closed into a room."
      >
        {isDrawingRoom ? '■' : '□'} Draw room (rectangle)
      </div>

      {/* The tool's own options, shown only while it is armed - they
          describe the NEXT wall, so they are noise when no wall is
          about to be drawn. An already-placed wall is re-edited by
          selecting it and using Properties instead. */}
      {(isDrawingWall || isDrawingRoom) && (
        <div style={{ padding: '4px 8px 6px 20px', fontSize: 11 }}>
          <label style={{ display: 'block', marginBottom: 4 }}>
            Thickness: {wallDrawThickness}
            <input
              type="range"
              min={WALL_MIN_THICKNESS}
              max={WALL_MAX_THICKNESS}
              value={wallDrawThickness}
              onChange={e => setWallDrawThickness(Number(e.target.value))}
              style={{ width: '100%' }}
            />
          </label>
          {/* Labelled as a VIEW property on purpose. Everything else
              in this department is to scale (theme/Scale.ts), but a
              real 2.5 m wall would extrude 200 px here and bury the
              room it encloses - so this one number is a depth cue, not
              a dimension, and the label must not pretend otherwise. */}
          <label style={{ display: 'block', marginBottom: 4 }}>
            Wall height (3D view): {wallDrawHeight}
            <input
              type="range"
              min={WALL_MIN_HEIGHT}
              max={WALL_MAX_HEIGHT}
              value={wallDrawHeight}
              onChange={e => setWallDrawHeight(Number(e.target.value))}
              style={{ width: '100%' }}
            />
          </label>
          <label style={{ display: 'block' }}>
            Wall material
            <select
              value={wallDrawMaterial}
              onChange={e => setWallDrawMaterial(e.target.value as WallMaterialId)}
              style={{ width: '100%' }}
            >
              {Object.entries(WALL_MATERIALS).map(([id, m]) => (
                <option key={id} value={id}>{m.label}</option>
              ))}
            </select>
          </label>
        </div>
      )}

      {/* The lighting calculation. A VIEW of the room rather than
          something added to it, which is why it toggles like the wall
          tool rather than being dragged onto the canvas. */}
      <div
        className="library-item"
        onClick={() => setShowIlluminance(!showIlluminance)}
        style={{
          cursor: 'pointer',
          fontWeight: showIlluminance ? 'bold' : undefined,
          background: showIlluminance ? '#00A800' : undefined,
          color: showIlluminance ? '#FFFFFF' : undefined,
        }}
        title="Illuminance on the working plane - false colours and isolux lines. Direct component only."
      >
        {showIlluminance ? '■' : '□'} Illuminance
      </div>

      {/* The schedule. Lives in this department because it counts what
          this department draws, and because the moment you have drawn a
          room the next question is how much of everything is in it. */}
      <div
        className="library-item"
        onClick={() => setShowTakeoff(true)}
        style={{ cursor: 'pointer' }}
        title="How much wall, floor, luminaires and sockets - counted from the drawing."
      >
        &#931; Quantities
      </div>

      {/* The floor is a property of the room, not of any one element -
          it is derived from whatever walls enclose an area (see
          RoomFloors.ts), so this is the only place it can be set. */}
      <div style={{ padding: '4px 8px 6px 20px', fontSize: 11 }}>
        <label style={{ display: 'block' }}>
          Floor
          <select
            value={floorMaterial ?? DEFAULT_FLOOR_MATERIAL}
            onChange={e => setFloorMaterial(e.target.value as FloorMaterialId)}
            style={{ width: '100%' }}
          >
            {Object.entries(FLOOR_MATERIALS).map(([id, m]) => (
              <option key={id} value={id}>{m.label}</option>
            ))}
          </select>
        </label>
      </div>
    </>
  );

  const searching = query.trim().length > 0;

  /** The entries of one category that survive the current search. */
  const visibleItems = (items: { type: string; label: string }[]) =>
    searching ? items.filter(def => matchesQuery(def.label, def.type, query)) : items;

  /** The recently-used entries, resolved back to definitions - a type that has since been removed from the registry is dropped rather than drawn as a blank row. */
  const recentItems = recentSymbols
    .map(type => {
      const def = getSymbolDefinition(type);
      return def ? { type, label: def.label, category: def.category } : null;
    })
    .filter((entry): entry is { type: string; label: string; category: string } => entry !== null)
    .filter(entry => !searching || matchesQuery(entry.label, entry.type, query));

  const anyResult = recentItems.length > 0
    || Object.values(library).some(items => visibleItems(items).length > 0);

  return (
    <div className="toolbox">
      {showTakeoff && <RoomTakeoffDialog onClose={() => setShowTakeoff(false)} />}
      <div className="toolbox-header">Object Library</div>

      <div style={{ padding: 4, display: 'flex', gap: 4 }}>
        <input
          type="search"
          value={query}
          onChange={e => setQuery(e.target.value)}
          placeholder="Search..."
          title="Search by symbol name or type"
          style={{ flex: 1, minWidth: 0 }}
        />
        {searching && (
          <button onClick={() => setQuery('')} title="Clear search" style={{ padding: '0 6px' }}>
            x
          </button>
        )}
      </div>

      <div className="toolbox-content">
        {/* Ostatnio uzywane, first - the same section the Logic editor's
            library opens with. Hidden when empty rather than shown as an
            empty folder: on a fresh install there is nothing to say. */}
        {recentItems.length > 0 && (
          <div className="folder">
            <div className="folder-header" onClick={() => toggleFolder(RECENT_LABEL)}>
              <span className="folder-icon">{expanded[RECENT_LABEL] !== false ? '📂' : '📁'}</span>
              <span className="folder-name">{RECENT_LABEL}</span>
            </div>
            {expanded[RECENT_LABEL] !== false && (
              <div className="folder-items">
                {recentItems.map(entry => (
                  <div
                    key={`recent-${entry.type}`}
                    className="library-item"
                    draggable
                    onDragStart={(e) => handleDragStart(e, entry.type, entry.category)}
                    title={`${entry.label} (${entry.category})`}
                  >
                    📄 {entry.label}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {Object.entries(library).map(([category, items]) => {
          const shown = visibleItems(items);
          // While searching, a department with nothing matching in it is
          // hidden entirely - seven empty folders is not a result list.
          if (searching && shown.length === 0) return null;
          // A search opens whatever still has something in it, so results
          // are never left inside a folder the user closed yesterday.
          const open = searching || expanded[category] !== false;
          return (
            <div key={category} className="folder">
              <div
                className="folder-header"
                onClick={() => toggleFolder(category)}
              >
                <span className="folder-icon">{open ? '📂' : '📁'}</span>
                <span className="folder-name">{category.replace('_', ' ')}</span>
              </div>
              {open && (
                <div className="folder-items">
                  {/* The building tools are part of the department, not
                      of the search results - hidden while searching so a
                      query never returns a toggle it does not match. */}
                  {category === BUILDING_CATEGORY && !searching && renderBuildingTools()}
                  {category === SCADA_CATEGORY && !searching && <ScadaTools />}
                  {shown.map(def => (
                    <div
                      key={def.type}
                      className="library-item"
                      draggable
                      onDragStart={(e) => handleDragStart(e, def.type, category)}
                      title={`${def.label} (${def.type})`}
                    >
                      📄 {def.label}
                    </div>
                  ))}
                </div>
              )}
            </div>
          );
        })}

        {searching && !anyResult && (
          <div style={{ padding: 10, opacity: 0.8 }}>
            No symbols match "{query}".
          </div>
        )}
      </div>
    </div>
  );
};
