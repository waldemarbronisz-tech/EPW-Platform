// feat/synoptic-library: the Object Library - a catalogue of the things
// you insert, and nothing else.
//
// The drawing tools (walls, rooms, frames, wires) used to live here, in
// between the valves; they now belong to the work modes on the toolbar.
// What is left, top to bottom:
//
//   Search         - by Polish name, English name or type. With some
//                    eighty entries, typing three letters beats any
//                    folder structure.
//   In this project - what is already on the screens, most used first:
//                    a project reuses its own handful of symbols.
//   Recently used  - the same list the Logic editor keeps.
//   Domains        - one criterion, the installation domain
//                    (project/LibraryDomains.ts).
//
// Symbols are dragged onto the canvas. The text box and the four screen
// panels can also simply be clicked - they land at the top-left of the
// view.

import React, { useMemo, useState } from 'react';
import { useStore } from '../store';
import { getLanguage, tr } from '../i18n/tr';
import {
  allLibraryEntries, entryMatches, groupLibrary, libraryEntry, projectSymbolUsage,
} from '../project/LibraryDomains';
import type { LibraryEntry, ScreenSymbols, WidgetType } from '../project/LibraryDomains';
import { insertWidget } from './insertWidget';
import { insertTextBox } from './insertTextBox';
import { TEXT_BOX_TYPE } from '../project/TextFormatting';

const IN_PROJECT_FOLDER = 'in-project';
const RECENT_FOLDER = 'recent';

export const Toolbox: React.FC = () => {
  const language = getLanguage();
  const entries = useMemo(() => allLibraryEntries(language), [language]);
  const recentSymbols = useStore(s => s.recentSymbols);
  const objects = useStore(s => s.objects);
  const meters = useStore(s => s.meters);
  const signalPanels = useStore(s => s.signalPanels);
  const groupCommands = useStore(s => s.groupCommands);
  const setpointPanels = useStore(s => s.setpointPanels);
  const screenContents = useStore(s => s.screenContents);
  const activeScreenId = useStore(s => s.activeScreenId);
  const [query, setQuery] = useState('');
  // Folders the user closed. Everything starts open; a search opens all.
  const [closed, setClosed] = useState<Record<string, boolean>>({});

  const searching = query.trim().length > 0;
  const groups = groupLibrary(entries, query, language);

  // The active screen lives in the store's own arrays; the stored copy of
  // it in screenContents may be stale, so it is skipped there.
  const usage = useMemo(() => {
    const screens: ScreenSymbols[] = [
      { objects, meters, signalPanels, groupCommands, setpointPanels },
      ...Object.entries(screenContents || {})
        .filter(([id]) => id !== activeScreenId)
        .map(([, content]) => content),
    ];
    return projectSymbolUsage(screens, language);
  }, [objects, meters, signalPanels, groupCommands, setpointPanels, screenContents, activeScreenId, language]);

  const inProject = usage
    .map(u => ({ entry: libraryEntry(u.type, language), count: u.count }))
    .filter((u): u is { entry: LibraryEntry; count: number } => u.entry !== null)
    .filter(u => !searching || entryMatches(u.entry, query));

  const recent = recentSymbols
    .map(type => libraryEntry(type, language))
    .filter((entry): entry is LibraryEntry => entry !== null)
    .filter(entry => !searching || entryMatches(entry, query));

  const toggle = (folder: string) => setClosed(prev => ({ ...prev, [folder]: !prev[folder] }));
  const isOpen = (folder: string) => searching || !closed[folder];

  const handleDragStart = (e: React.DragEvent, entry: LibraryEntry) => {
    e.dataTransfer.setData('application/reactflow', JSON.stringify({ type: entry.type, category: entry.category }));
    e.dataTransfer.effectAllowed = 'move';
  };

  const clickInserts = (entry: LibraryEntry) => entry.isWidget || entry.type === TEXT_BOX_TYPE;

  const handleClick = (entry: LibraryEntry) => {
    if (entry.isWidget) insertWidget(entry.type as WidgetType);
    else if (entry.type === TEXT_BOX_TYPE) insertTextBox();
  };

  const renderItem = (entry: LibraryEntry, keyPrefix: string, count?: number) => (
    <div
      key={`${keyPrefix}-${entry.type}`}
      className="library-item"
      draggable
      data-type={entry.type}
      onDragStart={e => handleDragStart(e, entry)}
      onClick={clickInserts(entry) ? () => handleClick(entry) : undefined}
      style={clickInserts(entry) ? { cursor: 'pointer' } : undefined}
      title={clickInserts(entry)
        ? tr('library.click_to_insert', { name: entry.name })
        : tr('library.item_title', { name: entry.name, type: entry.type })}
    >
      {entry.isWidget ? '▣' : '📄'} {entry.name}
      {count !== undefined && (
        <span className="library-count" title={tr('library.used_count', { count })}> ({count})</span>
      )}
    </div>
  );

  const renderFolder = (id: string, title: string, children: React.ReactNode) => (
    <div key={id} className="folder" data-folder={id}>
      <div className="folder-header" onClick={() => toggle(id)}>
        <span className="folder-icon">{isOpen(id) ? '📂' : '📁'}</span>
        <span className="folder-name">{title}</span>
      </div>
      {isOpen(id) && <div className="folder-items">{children}</div>}
    </div>
  );

  const nothingFound = searching && inProject.length === 0 && recent.length === 0 && groups.length === 0;

  return (
    <div className="toolbox">
      <div className="toolbox-header">{tr('library.title')}</div>

      <div style={{ padding: 4, display: 'flex', gap: 4 }}>
        <input
          type="search"
          value={query}
          onChange={e => setQuery(e.target.value)}
          placeholder={tr('library.search_placeholder')}
          title={tr('library.search_title')}
          aria-label={tr('library.search_title')}
          style={{ flex: 1, minWidth: 0 }}
        />
        {searching && (
          <button onClick={() => setQuery('')} title={tr('library.clear_search')} style={{ padding: '0 6px' }}>
            x
          </button>
        )}
      </div>

      <div className="toolbox-content">
        {/* Hidden when empty rather than shown as an empty folder. */}
        {inProject.length > 0 && renderFolder(
          IN_PROJECT_FOLDER,
          tr('library.in_project'),
          inProject.map(u => renderItem(u.entry, IN_PROJECT_FOLDER, u.count))
        )}

        {recent.length > 0 && renderFolder(
          RECENT_FOLDER,
          tr('library.recent'),
          recent.map(entry => renderItem(entry, RECENT_FOLDER))
        )}

        {groups.map(group => renderFolder(
          `domain-${group.domain}`,
          tr(`domain.${group.domain}`),
          group.entries.map(entry => renderItem(entry, group.domain))
        ))}

        {nothingFound && (
          <div style={{ padding: 10, opacity: 0.8 }}>
            {tr('library.no_results', { query })}
          </div>
        )}
      </div>
    </div>
  );
};
