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
}
