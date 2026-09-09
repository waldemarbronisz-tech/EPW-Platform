import { ProjectManager } from './ProjectManager';
import { useStore } from '../store';

export class ProjectFileService {
  static async openFile() {
    try {
      if (window.showOpenFilePicker) {
        const [fileHandle] = await window.showOpenFilePicker({
          types: [{
            description: 'EPW Synoptic Files',
            accept: { 'application/json': ['.epwsyn'] }
          }],
          multiple: false
        });
        const file = await fileHandle.getFile();
        const text = await file.text();
        if (ProjectManager.loadProject(text, file.name)) {
          useStore.getState().setFileHandle(fileHandle);
        }
      } else {
        // Fallback for browsers without File System Access API
        const input = document.createElement('input');
        input.type = 'file';
        input.accept = '.epwsyn';
        input.onchange = () => {
          const file = input.files?.[0];
          if (!file) return;
          const reader = new FileReader();
          reader.onload = (re) => {
            ProjectManager.loadProject(re.target?.result as string, file.name);
          };
          reader.readAsText(file);
        };
        input.click();
      }
    } catch (err) {
      if (err instanceof Error && err.name !== 'AbortError') {
        useStore.getState().addMessage(`[ERROR] Failed to open file: ${err.message}`);
      }
    }
  }

  static async saveFile() {
    const state = useStore.getState();
    const data = ProjectManager.getProjectData();
    if (!data) return; // Validation aborted save

    if (state.fileHandle && window.showSaveFilePicker) {
      try {
        const writable = await state.fileHandle.createWritable();
        await writable.write(data);
        await writable.close();
        useStore.getState().setDirty(false);
        useStore.getState().addMessage(`[INFO] Project saved: ${state.fileName}`);
      } catch (err) {
        const message = err instanceof Error ? err.message : String(err);
        useStore.getState().addMessage(`[ERROR] Failed to save file: ${message}`);
      }
    } else {
      await this.saveFileAs();
    }
  }

  static async saveFileAs() {
    const state = useStore.getState();
    const data = ProjectManager.getProjectData();
    if (!data) return; // Validation aborted save
    const suggestedName = state.fileName || `${state.projectName}.epwsyn`;

    if (window.showSaveFilePicker) {
      try {
        const fileHandle = await window.showSaveFilePicker({
          suggestedName,
          types: [{
            description: 'EPW Synoptic Files',
            accept: { 'application/json': ['.epwsyn'] }
          }]
        });
        const writable = await fileHandle.createWritable();
        await writable.write(data);
        await writable.close();

        const file = await fileHandle.getFile();
        useStore.getState().setFileHandle(fileHandle);
        useStore.getState().setFileName(file.name);
        useStore.getState().setDirty(false);
        useStore.getState().addMessage(`[INFO] Project saved as: ${file.name}`);
      } catch (err) {
        if (err instanceof Error && err.name !== 'AbortError') {
          useStore.getState().addMessage(`[ERROR] Failed to save file as: ${err.message}`);
        }
      }
    } else {
      // Fallback: trigger a browser download. revokeObjectURL is deferred
      // to the next tick (rather than called synchronously right after
      // click()) because some browsers (older Safari in particular) start
      // the download asynchronously and an immediate revoke can race it,
      // silently cancelling the download.
      const blob = new Blob([data as string], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = suggestedName;
      a.click();
      setTimeout(() => URL.revokeObjectURL(url), 0);

      useStore.getState().setFileName(suggestedName);
      useStore.getState().setDirty(false);
      useStore.getState().addMessage(`[INFO] Project downloaded as: ${suggestedName}`);
    }
  }
}
