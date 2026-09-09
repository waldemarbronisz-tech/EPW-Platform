import { Component } from 'react';
import type { ErrorInfo, ReactNode } from 'react';

// Internal-audit fix: previously no component in the tree ever caught a
// render-time exception, so any uncaught error (a malformed .epwsyn object,
// a Konva quirk, a bad symbol definition) took the whole app down to a
// blank white screen with no way back to the work in progress. This is the
// single top-level boundary that catches that instead. It deliberately
// stays a class component - getDerivedStateFromError/componentDidCatch
// have no hook equivalent in React yet.
//
// It does NOT attempt to auto-recover the crashed subtree (the error may
// have come from Canvas.tsx itself, so silently re-rendering it risks an
// infinite crash loop) - it shows what happened and lets the user reload,
// same as any other unrecoverable app-level fault would be handled.

interface ErrorBoundaryProps {
  children: ReactNode;
}

interface ErrorBoundaryState {
  error: Error | null;
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = { error: null };

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    // eslint-disable-next-line no-console
    console.error('EPW Synoptic Editor crashed:', error, info.componentStack);
  }

  render(): ReactNode {
    if (this.state.error) {
      return (
        <div className="error-boundary">
          <h1>EPW Synoptic Editor hit an unexpected error</h1>
          <p>
            The editor could not continue rendering. Your last saved file on
            disk is unaffected; any unsaved changes made since your last save
            may be lost if you reload.
          </p>
          <pre>{this.state.error.message}</pre>
          <button type="button" onClick={() => window.location.reload()}>
            Reload the editor
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
