// Minimal ambient types for the File System Access API (showOpenFilePicker /
// showSaveFilePicker). Not yet part of TypeScript's DOM lib (Chromium-only
// API), and ProjectFileService.ts feature-detects it at runtime with
// `'showOpenFilePicker' in window` before ever touching these - only the
// members that file actually calls are declared here, on purpose, rather
// than pulling in a full third-party @types package for an API this app
// only ever uses through that one narrow surface.

interface FileSystemFileHandle {
  getFile(): Promise<File>;
  createWritable(): Promise<FileSystemWritableFileStream>;
}

interface FileSystemWritableFileStream {
  write(data: string | BufferSource | Blob): Promise<void>;
  close(): Promise<void>;
}

interface FilePickerAcceptType {
  description?: string;
  accept: Record<string, string | string[]>;
}

interface OpenFilePickerOptions {
  types?: FilePickerAcceptType[];
  multiple?: boolean;
}

interface SaveFilePickerOptions {
  suggestedName?: string;
  types?: FilePickerAcceptType[];
}

interface Window {
  showOpenFilePicker?(options?: OpenFilePickerOptions): Promise<FileSystemFileHandle[]>;
  showSaveFilePicker?(options?: SaveFilePickerOptions): Promise<FileSystemFileHandle>;
  // Bug fix ("ten pasek nie działa" - Save/Open did nothing, forever,
  // when driven from Studio's shared toolbar): studio/shell/
  // synoptic_panel.py's _STUDIO_SKIN_JS sets this true the moment the
  // page loads inside Studio's embedded QWebEngineView. Qt WebEngine's
  // Chromium exposes showOpenFilePicker/showSaveFilePicker as real
  // functions (`typeof` says "function") but never actually implements
  // the native picker dialog behind them - calling either one there
  // returns a Promise that neither resolves nor rejects, ever, which
  // is indistinguishable from "the button does nothing" to whoever
  // clicked it. A real browser (Synoptic run standalone, outside
  // Studio, via studio/synoptic/main.py) has no such gap, so this flag
  // - not just `window.showOpenFilePicker` truthiness - is what
  // ProjectFileService.ts gates on before trusting either API.
  __EPW_STUDIO_EMBED__?: boolean;
}
