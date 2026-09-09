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

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  </StrictMode>,
)
