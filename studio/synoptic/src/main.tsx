import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import { ErrorBoundary } from './components/ErrorBoundary.tsx'
import { applyScadaCssVariables } from './theme/ScadaTheme'
import { useStore } from './store'

// Must run before the first paint, so the interface CSS (which reads these
// as var(--scada-*)) never has a chance to render with stale fallback
// colors.
applyScadaCssVariables()

// fix/audit-findings commit 2: main.py's native desktop launcher needs
// to know the store's own isDirty flag before letting its window
// actually close (so it can warn about unsaved changes), but reading
// it via pywebview's own evaluate_js from that close handler deadlocks
// in the installed pywebview version - window.events.closing always
// fires on the UI thread, and evaluate_js's WebView2 backend needs
// that same thread's message loop free to deliver its result, so it
// can never complete while the very handler calling it is what has
// that thread blocked (verified live before choosing this design -
// see main.py's own module docstring and raport.md). Pushing the
// value INTO Python instead, the moment it changes, needs no call
// across the bridge at close time at all - nothing to deadlock on.
// window.pywebview.api only exists inside the native window (main.py
// exposes set_dirty there via window.expose); in an ordinary browser
// tab window.pywebview is simply undefined and every call below is a
// silent no-op, exactly as intended.
type PywebviewBridge = { pywebview?: { api?: { set_dirty?: (value: boolean) => void } } };
function pushDirtyToNativeHost(isDirty: boolean): void {
  (window as unknown as PywebviewBridge).pywebview?.api?.set_dirty?.(isDirty);
}
// pywebview injects window.pywebview.api asynchronously after the page
// loads (it dispatches this event once ready) - an initial push once
// that happens covers the (unlikely, but possible on a reload) case
// where isDirty was already true before the bridge existed to hear
// about it; the subscription below covers every change after that,
// for the rest of the session.
window.addEventListener('pywebviewready', () => pushDirtyToNativeHost(useStore.getState().isDirty));
useStore.subscribe((state, prevState) => {
  if (state.isDirty !== prevState.isDirty) pushDirtyToNativeHost(state.isDirty);
});

// Read-only state bridge for the EPW Studio shell ("EPW Studio: jedna
// szata graficzna", Stage 2, Blocker B - approved for READ access only,
// nothing settable, no command dispatch added here). The shell's shared
// Undo/Redo/Save toolbar buttons reach Synoptic's own actions by
// clicking this page's (now shell-hidden) menu items directly - see
// studio/shell/synoptic_panel.py - but a button that's always clickable
// regardless of whether there's actually anything to undo/redo/save is
// exactly the "lying button" uściślenie 2.2 exists to rule out. The
// shell polls window.__synopticStudioState() before deciding whether to
// enable those three buttons. Every field is read fresh off the live
// store on each call - nothing cached, and there is no companion setter.
type SynopticStudioState = {
  canUndo: boolean;
  canRedo: boolean;
  isDirty: boolean;
  hasSelection: boolean;
};
type StudioStateBridge = { __synopticStudioState?: () => SynopticStudioState };
(window as unknown as StudioStateBridge).__synopticStudioState = (): SynopticStudioState => {
  const s = useStore.getState();
  return {
    canUndo: s.historyIndex > 0,
    canRedo: s.historyIndex < s.history.length - 1,
    isDirty: s.isDirty,
    hasSelection:
      s.selectedIds.length > 0 ||
      s.selectedConnectionIds.length > 0 ||
      s.selectedMeterIds.length > 0 ||
      s.selectedSignalPanelIds.length > 0 ||
      s.selectedFrameIds.length > 0 ||
      s.selectedGroupCommandIds.length > 0 ||
      s.selectedSetpointPanelIds.length > 0,
  };
};

// Task "Studio: wyostrzenie stylu" Problem 4.3 - a second, equally
// narrow read-only bridge function, same convention as the one above:
// Studio's own color picker (studio/shell/color_picker.py) needs the
// CURRENT canvasConfig.background to open already showing it (4.1's
// own "podgląd: obecny kolor obok nowego"), and there is still no
// general window.useStore exposure - reading it means one more single-
// purpose getter, not widening the existing one's stated scope.
type CanvasBackgroundBridge = { __synopticCanvasBackground?: () => string };
(window as unknown as CanvasBackgroundBridge).__synopticCanvasBackground = (): string =>
  useStore.getState().canvasConfig.background;

// The write half of the same feature - GRANICE's own pre-approved
// exception ("jeśli w Synoptiku wymaga to zmiany [...] MINIMALNEJ i
// opisanej, tak jak przy moście stanu") for exactly this: Studio's own
// color picker has no DOM element to click (trigger_menu_item()/
// trigger_toolbar_button() only work for parameterless actions) - one
// explicit setter, taking the one argument it needs, calling the real
// store action so isDirty/history behave exactly as any other project
// edit would.
type CanvasBackgroundSetter = { __synopticSetCanvasBackground?: (color: string) => void };
(window as unknown as CanvasBackgroundSetter).__synopticSetCanvasBackground = (color: string): void => {
  useStore.getState().setCanvasBackground(color);
};

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  </StrictMode>,
)
