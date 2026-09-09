// feat/help-system commit 2 - the Help window itself, Windows 98 Help
// style (task: "pomoc ma wygladac jak Windows Help z tamtych lat"),
// consistent with this editor's own existing SCADA chrome rather than a
// literal Win98 skin: the same --sys-light/--sys-dark bevel technique
// already used throughout index.css (dropdown menus, the sunken toolbox
// well), just with the RAISED orientation (light top-left, dark
// bottom-right) the task asks for on the window's own outer frame.
//
// Non-modal by design: no backdrop, no stopPropagation wall - task:
// "okno nie blokuje pracy w edytorze, da sie je zostawic otwarte obok".
// Reused across repeated F1 presses (App.tsx keeps it mounted once
// opened) so Back/Forward history survives navigating away and back,
// the same reasoning EPW-OS's own HelpWindow gives for staying a single
// persistent instance.

import React, { useEffect, useRef, useState } from 'react';
import { Panel, PanelGroup, PanelResizeHandle } from 'react-resizable-panels';
import { useStore } from '../store';
import { HELP_TOC, findTopicMeta, findChapterOfTopic } from '../help/HelpToc';
import { getTopicBody, placeholderBody } from '../help/HelpContentRegistry';
import { searchHelp } from '../help/HelpSearch';
import type { HelpSearchResult } from '../help/HelpSearch';
import { resolveLocalized, HELP_LANGUAGES } from '../i18n/HelpLanguage';
import type { HelpLanguage } from '../i18n/HelpLanguage';
import type { HelpBlock } from '../help/HelpTypes';
import { HELP_GLOSSARY } from '../help/HelpGlossary';
import { FONT_SIZE_BASE, FONT_SIZE_SMALL, FONT_SIZE_TITLE, COLOR_ALARM, COLOR_LAMP_LIT } from '../theme/ScadaTheme';

const FALLBACK_NOTICE: Record<'pl' | 'en', string> = {
  pl: 'Ten rozdzial nie jest jeszcze przetlumaczony na wybrany jezyk. Pokazano tresc angielska.',
  en: 'This chapter has not been translated into the selected language yet. Showing the English text.',
};

function fallbackNoticeText(language: HelpLanguage): string {
  return language === 'pl' ? FALLBACK_NOTICE.pl : FALLBACK_NOTICE.en;
}

const LINK_RE = /\[\[([a-z0-9-]+)\|([^\]]+)\]\]/g;
const CODE_RE = /`([^`]+)`/g;

/** Splits one run of plain text on `code` spans only - used inside link labels and as the second pass over non-link segments. */
function renderCodeSpans(text: string, keyPrefix: string): React.ReactNode[] {
  const parts: React.ReactNode[] = [];
  let lastIndex = 0;
  let match: RegExpExecArray | null;
  let i = 0;
  CODE_RE.lastIndex = 0;
  while ((match = CODE_RE.exec(text))) {
    if (match.index > lastIndex) parts.push(text.slice(lastIndex, match.index));
    parts.push(<code key={`${keyPrefix}-c${i++}`} style={codeStyle}>{match[1]}</code>);
    lastIndex = match.index + match[0].length;
  }
  if (lastIndex < text.length) parts.push(text.slice(lastIndex));
  return parts;
}

/** Paragraph/list-item text with this help system's two inline markers - see HelpTypes.ts's own header for the tiny, non-Markdown syntax. */
function renderInline(text: string, onNavigate: (topicId: string) => void, keyPrefix: string): React.ReactNode[] {
  const parts: React.ReactNode[] = [];
  let lastIndex = 0;
  let match: RegExpExecArray | null;
  let i = 0;
  LINK_RE.lastIndex = 0;
  while ((match = LINK_RE.exec(text))) {
    if (match.index > lastIndex) parts.push(...renderCodeSpans(text.slice(lastIndex, match.index), `${keyPrefix}-pre${i}`));
    const topicId = match[1];
    const label = match[2];
    parts.push(
      <a key={`${keyPrefix}-l${i}`} href="#" onClick={(e) => { e.preventDefault(); onNavigate(topicId); }} style={linkStyle}>
        {label}
      </a>
    );
    i++;
    lastIndex = match.index + match[0].length;
  }
  if (lastIndex < text.length) parts.push(...renderCodeSpans(text.slice(lastIndex), `${keyPrefix}-post`));
  return parts;
}

function escapeRegExp(text: string): string {
  return text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

/** Search results list: task's own explicit "podswietlone trafienie" - the matched query text within a result's snippet, wrapped in the theme's own lamp-lit highlight color rather than a hand-picked one. */
function highlightMatch(snippet: string, query: string): React.ReactNode[] {
  const needle = query.trim();
  if (!needle) return [snippet];
  const re = new RegExp(`(${escapeRegExp(needle)})`, 'ig');
  const parts = snippet.split(re);
  return parts.map((part, i) =>
    part.toLowerCase() === needle.toLowerCase()
      ? <mark key={i} style={highlightStyle}>{part}</mark>
      : part
  );
}

const HelpBlockView: React.FC<{ block: HelpBlock; index: number; onNavigate: (topicId: string) => void }> = ({ block, index, onNavigate }) => {
  const key = `b${index}`;
  switch (block.kind) {
    case 'heading':
      return <h3 style={headingStyle}>{block.text}</h3>;
    case 'p':
      return <p style={paragraphStyle}>{renderInline(block.text, onNavigate, key)}</p>;
    case 'list': {
      const Tag = block.ordered ? 'ol' : 'ul';
      return (
        <Tag style={listStyle}>
          {block.items.map((item, i) => <li key={i}>{renderInline(item, onNavigate, `${key}-${i}`)}</li>)}
        </Tag>
      );
    }
    case 'table':
      return (
        <div style={{ overflowX: 'auto' }}>
          <table style={tableStyle}>
            <thead>
              <tr>{block.headers.map((h, i) => <th key={i} style={thStyle}>{h}</th>)}</tr>
            </thead>
            <tbody>
              {block.rows.map((row, ri) => (
                <tr key={ri}>{row.map((cell, ci) => <td key={ci} style={tdStyle}>{renderInline(cell, onNavigate, `${key}-${ri}-${ci}`)}</td>)}</tr>
              ))}
            </tbody>
          </table>
        </div>
      );
    case 'note':
      return <div style={noteStyle}>{renderInline(block.text, onNavigate, key)}</div>;
  }
};

export interface HelpWindowRequest {
  topicId: string;
  /** Bumped by App.tsx on every F1 press so a repeated request for the SAME topic id still re-navigates while the window is already open on it. */
  nonce: number;
}

export interface HelpWindowProps {
  request: HelpWindowRequest;
  onClose: () => void;
}

export const HelpWindow: React.FC<HelpWindowProps> = ({ request, onClose }) => {
  const helpLanguage = useStore(s => s.helpLanguage);
  const setHelpLanguage = useStore(s => s.setHelpLanguage);

  const [activeTopicId, setActiveTopicId] = useState(request.topicId);
  const [history, setHistory] = useState<string[]>([request.topicId]);
  const [historyIndex, setHistoryIndex] = useState(0);
  const [leftTab, setLeftTab] = useState<'contents' | 'search'>('contents');
  const [searchQuery, setSearchQuery] = useState('');
  const [expandedChapters, setExpandedChapters] = useState<Set<string>>(() => new Set(HELP_TOC.map(c => c.id)));
  const lastNonceRef = useRef(request.nonce);

  const navigateTo = (topicId: string, recordHistory = true) => {
    setActiveTopicId(topicId);
    if (recordHistory) {
      setHistory(prev => {
        const trimmed = prev.slice(0, historyIndex + 1);
        return [...trimmed, topicId];
      });
      setHistoryIndex(prev => prev + 1);
    }
  };

  // A fresh F1 press while the window is already open still navigates,
  // even to the topic already showing (nonce changes either way).
  useEffect(() => {
    if (request.nonce !== lastNonceRef.current) {
      lastNonceRef.current = request.nonce;
      navigateTo(request.topicId);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [request.nonce]);

  // Escape-closes-help is handled by App.tsx's own global F1 listener,
  // not a second window-level listener here - see that file's own
  // comment for why (an in-browser-only, never isolated quirk with a
  // listener registered from this lazily-mounted child specifically
  // for the Escape key).

  const goBack = () => {
    if (historyIndex > 0) {
      const next = historyIndex - 1;
      setHistoryIndex(next);
      setActiveTopicId(history[next]);
    }
  };
  const goForward = () => {
    if (historyIndex < history.length - 1) {
      const next = historyIndex + 1;
      setHistoryIndex(next);
      setActiveTopicId(history[next]);
    }
  };

  const toggleChapter = (chapterId: string) => {
    setExpandedChapters(prev => {
      const next = new Set(prev);
      if (next.has(chapterId)) next.delete(chapterId); else next.add(chapterId);
      return next;
    });
  };

  const meta = findTopicMeta(activeTopicId);
  const chapter = findChapterOfTopic(activeTopicId);
  const titleResolution = meta ? resolveLocalized(meta.title, helpLanguage) : null;
  const title = titleResolution?.value ?? activeTopicId;
  const bodyResolution = resolveLocalized(getTopicBody(activeTopicId), helpLanguage);
  const body = bodyResolution?.value ?? placeholderBody(activeTopicId);
  const showFallbackNotice = bodyResolution?.isFallback ?? false;

  const searchResults: HelpSearchResult[] = leftTab === 'search' ? searchHelp(searchQuery, helpLanguage) : [];

  return (
    <div style={windowStyle}>
      <div style={toolbarStyle}>
        <input
          value={searchQuery}
          onChange={(e) => { setSearchQuery(e.target.value); setLeftTab('search'); }}
          placeholder={helpLanguage === 'pl' ? 'Szukaj w pomocy...' : 'Search help...'}
          style={{ flex: 1, minWidth: '100px' }}
        />
        <button onClick={goBack} disabled={historyIndex <= 0}>{helpLanguage === 'pl' ? 'Wstecz' : 'Back'}</button>
        <button onClick={goForward} disabled={historyIndex >= history.length - 1}>{helpLanguage === 'pl' ? 'Dalej' : 'Forward'}</button>
        <select value={helpLanguage} onChange={(e) => setHelpLanguage(e.target.value as HelpLanguage)}>
          {HELP_LANGUAGES.map(l => <option key={l.code} value={l.code}>{l.nativeName}</option>)}
        </select>
        <button onClick={onClose} title="Esc">x</button>
      </div>

      <div style={{ flex: 1, minHeight: 0 }}>
        <PanelGroup direction="horizontal" autoSaveId="epw-help-layout">
          <Panel defaultSize={28} minSize={15} maxSize={60}>
            <div style={leftPanelStyle}>
              <div style={tabBarStyle}>
                <div style={leftTab === 'contents' ? tabActiveStyle : tabInactiveStyle} onClick={() => setLeftTab('contents')}>
                  {helpLanguage === 'pl' ? 'Spis tresci' : 'Contents'}
                </div>
                <div style={leftTab === 'search' ? tabActiveStyle : tabInactiveStyle} onClick={() => setLeftTab('search')}>
                  {helpLanguage === 'pl' ? 'Szukaj' : 'Search'}
                </div>
              </div>
              <div style={treeScrollStyle}>
                {leftTab === 'contents' ? (
                  HELP_TOC.map(c => {
                    const chapterTitle = resolveLocalized(c.title, helpLanguage)?.value ?? c.id;
                    const expanded = expandedChapters.has(c.id);
                    return (
                      <div key={c.id}>
                        <div style={chapterRowStyle} onClick={() => toggleChapter(c.id)}>
                          {expanded ? '▼' : '▶'} {chapterTitle}
                        </div>
                        {expanded && c.topics.map(t => {
                          const topicTitle = resolveLocalized(t.title, helpLanguage)?.value ?? t.id;
                          return (
                            <div
                              key={t.id}
                              style={t.id === activeTopicId ? topicRowActiveStyle : topicRowStyle}
                              onClick={() => navigateTo(t.id)}
                            >
                              {topicTitle}
                            </div>
                          );
                        })}
                      </div>
                    );
                  })
                ) : (
                  searchResults.length === 0 ? (
                    <div style={{ padding: '8px', fontSize: `${FONT_SIZE_SMALL}px`, fontStyle: 'italic' }}>
                      {helpLanguage === 'pl' ? 'Brak wynikow.' : 'No results.'}
                    </div>
                  ) : searchResults.map(r => (
                    <div key={r.topicId} style={topicRowStyle} onClick={() => navigateTo(r.topicId)}>
                      <div>{r.title}</div>
                      {r.snippet && <div style={snippetStyle}>{highlightMatch(r.snippet, searchQuery)}</div>}
                    </div>
                  ))
                )}
              </div>
            </div>
          </Panel>
          <PanelResizeHandle style={resizeHandleStyle} />
          <Panel defaultSize={72} minSize={30}>
            <div style={contentScrollStyle}>
              <div style={contentHeaderStyle}>
                {chapter && <div style={breadcrumbStyle}>{resolveLocalized(chapter.title, helpLanguage)?.value}</div>}
                <h2 style={titleStyle}>{title}</h2>
              </div>
              {showFallbackNotice && <div style={noteStyle}>{fallbackNoticeText(helpLanguage)}</div>}
              {body.map((block, i) => <HelpBlockView key={i} block={block} index={i} onNavigate={navigateTo} />)}
              {activeTopicId === 'glossary-all' && (
                <dl style={glossaryListStyle}>
                  {[...HELP_GLOSSARY]
                    .sort((a, b) => (resolveLocalized(a.term, helpLanguage)?.value ?? '').localeCompare(resolveLocalized(b.term, helpLanguage)?.value ?? ''))
                    .map((entry, i) => {
                      const term = resolveLocalized(entry.term, helpLanguage)?.value ?? '';
                      const definition = resolveLocalized(entry.definition, helpLanguage)?.value ?? '';
                      return (
                        <React.Fragment key={i}>
                          <dt style={glossaryTermStyle}>{term}</dt>
                          <dd style={glossaryDefStyle}>
                            {definition}{' '}
                            <a href="#" onClick={(e) => { e.preventDefault(); navigateTo(entry.topicId); }} style={linkStyle}>
                              {'→'}
                            </a>
                          </dd>
                        </React.Fragment>
                      );
                    })}
                </dl>
              )}
            </div>
          </Panel>
        </PanelGroup>
      </div>
    </div>
  );
};

const windowStyle: React.CSSProperties = {
  position: 'fixed', top: '8%', left: '18%', width: '64%', height: '76%',
  minWidth: '560px', minHeight: '360px',
  display: 'flex', flexDirection: 'column',
  background: 'var(--scada-panel)', color: 'var(--scada-outline)',
  fontFamily: 'var(--scada-font-ui)', fontSize: 'var(--scada-font-size-base)',
  // Raised bevel: light top-left, dark bottom-right, plus the same 1px
  // black outline every other panel in index.css already uses - see
  // this file's own header comment for the exact precedent (.dropdown's
  // border + box-shadow, .canvas-container's outline technique).
  border: '2px solid var(--sys-light)',
  borderRightColor: 'var(--sys-dark)',
  borderBottomColor: 'var(--sys-dark)',
  outline: '1px solid var(--scada-outline)',
  outlineOffset: '-2px',
  boxShadow: '2px 2px 6px rgba(0,0,0,0.4)',
  zIndex: 900,
} as React.CSSProperties;

const toolbarStyle: React.CSSProperties = {
  display: 'flex', gap: '6px', alignItems: 'center', padding: '4px 6px',
  borderBottom: '1px solid var(--sys-dark)', flexShrink: 0,
};

const leftPanelStyle: React.CSSProperties = { display: 'flex', flexDirection: 'column', height: '100%', borderRight: '1px solid var(--sys-dark)' };
const tabBarStyle: React.CSSProperties = { display: 'flex', borderBottom: '1px solid var(--sys-dark)', flexShrink: 0 };
const tabBaseStyle: React.CSSProperties = { padding: '4px 10px', cursor: 'pointer', fontSize: `${FONT_SIZE_SMALL}px` };
const tabActiveStyle: React.CSSProperties = { ...tabBaseStyle, background: 'var(--scada-value-field)', fontWeight: 'bold' };
const tabInactiveStyle: React.CSSProperties = { ...tabBaseStyle };
const treeScrollStyle: React.CSSProperties = { flex: 1, overflowY: 'auto', padding: '4px' };
const chapterRowStyle: React.CSSProperties = { fontWeight: 'bold', padding: '3px 2px', cursor: 'pointer', userSelect: 'none' };
const topicRowStyle: React.CSSProperties = { padding: '2px 2px 2px 16px', cursor: 'pointer', fontSize: `${FONT_SIZE_SMALL}px` };
const topicRowActiveStyle: React.CSSProperties = { ...topicRowStyle, background: 'var(--scada-outline)', color: 'var(--scada-white)' };
const snippetStyle: React.CSSProperties = { fontSize: `${FONT_SIZE_SMALL}px`, fontStyle: 'italic', paddingLeft: '4px', opacity: 0.85 };
const highlightStyle: React.CSSProperties = { background: COLOR_LAMP_LIT, color: 'var(--scada-outline)', fontStyle: 'normal' };

const resizeHandleStyle: React.CSSProperties = { width: '4px', background: 'var(--sys-dark)', cursor: 'col-resize' };

const contentScrollStyle: React.CSSProperties = { height: '100%', overflowY: 'auto', padding: '8px 14px', background: 'var(--scada-value-field)' };
const contentHeaderStyle: React.CSSProperties = { marginBottom: '8px' };
const breadcrumbStyle: React.CSSProperties = { fontSize: `${FONT_SIZE_SMALL}px`, opacity: 0.75 };
const titleStyle: React.CSSProperties = { fontSize: `${FONT_SIZE_TITLE}px`, fontWeight: 'bold', margin: '2px 0 8px' };
const headingStyle: React.CSSProperties = { fontSize: `${FONT_SIZE_BASE}px`, fontWeight: 'bold', margin: '12px 0 4px' };
const paragraphStyle: React.CSSProperties = { margin: '0 0 8px', lineHeight: 1.4 };
const listStyle: React.CSSProperties = { margin: '0 0 8px', paddingLeft: '22px', lineHeight: 1.4 };
const linkStyle: React.CSSProperties = { color: 'var(--scada-water)', textDecoration: 'underline', cursor: 'pointer' };
const codeStyle: React.CSSProperties = { fontFamily: 'var(--scada-font-value)', background: 'var(--scada-panel)', padding: '0 3px' };
const noteStyle: React.CSSProperties = {
  margin: '0 0 10px', padding: '6px 8px', border: '1px solid var(--sys-dark)',
  background: 'var(--scada-panel)', color: COLOR_ALARM, fontSize: `${FONT_SIZE_SMALL}px`,
};
const tableStyle: React.CSSProperties = { borderCollapse: 'collapse', margin: '0 0 10px', fontSize: `${FONT_SIZE_SMALL}px`, minWidth: '100%' };
const thStyle: React.CSSProperties = { textAlign: 'left', border: '1px solid var(--sys-dark)', padding: '3px 6px', background: 'var(--scada-panel)' };
const tdStyle: React.CSSProperties = { border: '1px solid var(--sys-dark)', padding: '3px 6px' };

const glossaryListStyle: React.CSSProperties = { margin: '4px 0 0' };
const glossaryTermStyle: React.CSSProperties = { fontWeight: 'bold', marginTop: '8px' };
const glossaryDefStyle: React.CSSProperties = { margin: '2px 0 0 0', lineHeight: 1.4 };
