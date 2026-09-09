import { Panel, PanelGroup, PanelResizeHandle } from 'react-resizable-panels';
import { MenuBar } from './components/MenuBar';
import { Toolbar } from './components/Toolbar';
import { Toolbox } from './components/Toolbox';
import { Canvas } from './components/Canvas';
import { PropertyInspector } from './components/PropertyInspector';
import { MessagesPanel } from './components/MessagesPanel';
import { StatusBar } from './components/StatusBar';
import { useStore } from './store';
import { validateDeviceBindings } from './project/DeviceBindingValidation';
import { syncObjectDesignationsAfterDeviceSave, formatDeviceSavedMessage, createAndAssignDevice, assignExistingDeviceById } from './project/DeviceFormSync';
import { getContextualHelpTopic } from './help/HelpContextResolver';
import { Suspense, lazy, useEffect, useRef, useState } from 'react';

// Internal-audit fix: a full-screen preview only ever mounted from the
// menu bar's "Style Preview" action - lazy so its code isn't part of the
// bundle every session pays for on first load.
const ScadaStylePreview = lazy(() =>
  import('./components/ScadaStylePreview').then(m => ({ default: m.ScadaStylePreview }))
);

// feat/device-list-ui commit 1: same lazy-on-first-open convention as
// ScadaStylePreview above.
const DeviceRegistriesDialog = lazy(() =>
  import('./components/DeviceRegistriesDialog').then(m => ({ default: m.DeviceRegistriesDialog }))
);

// feat/device-list-ui commit 2: same lazy convention.
const DeviceListDialog = lazy(() =>
  import('./components/DeviceListDialog').then(m => ({ default: m.DeviceListDialog }))
);

// feat/help-system commit 2: same lazy convention - opened often (F1),
// but its own content/tree data has no reason to load before it is
// actually asked for.
const HelpWindow = lazy(() =>
  import('./components/HelpWindow').then(m => ({ default: m.HelpWindow }))
);

// feat/device-form-from-canvas: same lazy convention as the three
// dialogs above - the SAME component DeviceListDialog.tsx has always
// used for Dodaj/Edytuj/Duplikuj, rendered here too so every other
// place an aparat is visible (a symbol's own double-click, Properties,
// a meter/signal-panel row, a wizard row) can open it without needing
// Lista aparatow to be open at all - see store/deviceFormSlice.ts.
const DeviceFormDialog = lazy(() =>
  import('./components/DeviceFormDialog').then(m => ({ default: m.DeviceFormDialog }))
);

function App() {
  const { projectName, fileName, isDirty, objects, devices, deviceFormRequest, deviceCreateOrAssignRequest } = useStore();
  const [showScadaPreview, setShowScadaPreview] = useState(false);
  const [showDeviceRegistries, setShowDeviceRegistries] = useState(false);
  const [showDeviceList, setShowDeviceList] = useState(false);
  const [showHelp, setShowHelp] = useState(false);
  const [helpRequest, setHelpRequest] = useState({ topicId: 'intro-what', nonce: 0 });

  const openHelp = (topicId: string) => {
    setHelpRequest(prev => ({ topicId, nonce: prev.nonce + 1 }));
    setShowHelp(true);
  };

  // feat/help-system commit 2: F1 opens (or re-navigates, if already
  // open) the Help window on the topic getContextualHelpTopic - the
  // ONE place that decision is made - resolves from whatever is
  // currently selected. Global, not gated behind isTypingInField() the
  // way Canvas.tsx's own shortcuts are: F1 requesting help while
  // focused in a text field is still exactly what the user wants.
  //
  // Escape-closes-help is handled HERE too, deliberately NOT as a
  // second window-level listener inside HelpWindow.tsx itself -
  // empirically (in the real browser, not just unit tests) a listener
  // registered from inside that lazily-mounted child never fired for
  // Escape specifically, for a reason that never resolved to a single
  // isolatable cause across an afternoon of direct in-browser
  // debugging (every other key worked; capture AND bubble diagnostic
  // listeners registered on window both before and after it, on the
  // same target and phase, both still fired - see this task's own
  // completion report). Reusing this ALREADY-empirically-reliable F1
  // listener sidesteps the mystery entirely. setShowHelp(false) when
  // help is already closed is a harmless no-op, so this never needs
  // `showHelp` in its own dependency array.
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'F1') {
        e.preventDefault();
        const s = useStore.getState();
        openHelp(getContextualHelpTopic(s));
      } else if (e.key === 'Escape') {
        setShowHelp(false);
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, []);

  // feat/device-list-ui commit 5: a symbol's Aparat can go dangling
  // (the device it pointed at got deleted from the registry elsewhere -
  // Rejestry projektu, or Lista aparatow) without the symbol itself ever
  // being touched. Reported to Messages once per object per time it
  // BECOMES dangling, not on every render - alreadyReportedRef tracks
  // which object ids already have a standing message so fixing then
  // re-breaking the same symbol reports it again, but simply re-opening
  // a menu does not spam the panel.
  const reportedDanglingRef = useRef<Set<string>>(new Set());
  useEffect(() => {
    const issues = validateDeviceBindings(objects, devices);
    const currentIds = new Set(issues.map(i => i.objectId));
    for (const issue of issues) {
      if (!reportedDanglingRef.current.has(issue.objectId)) {
        useStore.getState().addMessage(`[WARNING] ${issue.message}`);
      }
    }
    reportedDanglingRef.current = currentIds;
  }, [objects, devices]);

  useEffect(() => {
    const titleName = fileName || `${projectName}.epwsyn`;
    const dirtyMark = isDirty ? ' *' : '';
    document.title = `EPW Synoptic Editor — ${titleName}${dirtyMark}`;
  }, [projectName, fileName, isDirty]);

  // Internal-audit fix: isDirty was already tracked in the store (for the
  // title-bar "*" above) but nothing warned before closing the tab/window,
  // so an unsaved schematic could be lost with no prompt at all. Standard
  // native confirmation dialog - browsers ignore any custom message text,
  // but still show their own generic "changes you made may not be saved".
  useEffect(() => {
    if (!isDirty) return;
    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      e.preventDefault();
      e.returnValue = '';
    };
    window.addEventListener('beforeunload', handleBeforeUnload);
    return () => window.removeEventListener('beforeunload', handleBeforeUnload);
  }, [isDirty]);

  return (
    <div className="app-container">
      <MenuBar
        onOpenScadaPreview={() => setShowScadaPreview(true)}
        onOpenDeviceRegistries={() => setShowDeviceRegistries(true)}
        onOpenDeviceList={() => setShowDeviceList(true)}
        onOpenHelp={() => openHelp(getContextualHelpTopic(useStore.getState()))}
      />
      {showHelp && (
        <Suspense fallback={null}>
          <HelpWindow request={helpRequest} onClose={() => setShowHelp(false)} />
        </Suspense>
      )}
      {showScadaPreview && (
        <Suspense fallback={null}>
          <ScadaStylePreview onClose={() => setShowScadaPreview(false)} />
        </Suspense>
      )}
      {showDeviceRegistries && (
        <Suspense fallback={null}>
          <DeviceRegistriesDialog onClose={() => setShowDeviceRegistries(false)} />
        </Suspense>
      )}
      {showDeviceList && (
        <Suspense fallback={null}>
          <DeviceListDialog onClose={() => setShowDeviceList(false)} />
        </Suspense>
      )}
      {deviceFormRequest && (() => {
        // The device could in principle have been deleted from the
        // registry while this request was pending (e.g. from another
        // still-open Lista aparatow) - render nothing rather than an
        // empty form; deviceFormRequest itself is left as-is (the same
        // "problem, not a crash" treatment this project always gives a
        // dangling reference, harmless here since nothing is showing).
        const device = devices.find(d => d.id === deviceFormRequest.deviceId);
        if (!device) return null;
        return (
          <Suspense fallback={null}>
            <DeviceFormDialog
              mode="edit"
              initialDevice={device}
              sourceContext={deviceFormRequest.sourceContext}
              onSave={(saved) => {
                const store = useStore.getState();
                // Keep every symbol bound to this device whose own
                // designation still exactly matches the device's OLD one
                // (never customized away from it) in sync with the new
                // value - see DeviceFormSync.ts's own header for why this
                // is the same rule PropertyInspector.tsx's Aparat dropdown
                // already applies on first assignment, not a new one.
                const objectUpdates = syncObjectDesignationsAfterDeviceSave(store.objects, device.designation, saved);
                store.updateDevice(saved.id, saved);
                if (objectUpdates.length > 0) {
                  store.updateObjects(objectUpdates);
                  store.saveHistory();
                }
                // 3d: designation + name, never a raw id/UUID.
                store.addMessage(formatDeviceSavedMessage(saved));
                store.closeDeviceForm();
              }}
              onCancel={() => useStore.getState().closeDeviceForm()}
            />
          </Suspense>
        );
      })()}
      {deviceCreateOrAssignRequest && (
        <Suspense fallback={null}>
          <DeviceFormDialog
            mode="add"
            sourceContext={deviceCreateOrAssignRequest.sourceContext}
            creationContext={{
              symbolType: deviceCreateOrAssignRequest.symbolType,
              // fix/inline-device-creation commit 3c: PRZYPISZ ISTNIEJACY -
              // DeviceFormSync.ts's own assignExistingDeviceById, so it
              // is testable without mounting Canvas.tsx.
              onAssignExisting: (deviceId) => {
                const store = useStore.getState();
                assignExistingDeviceById(store, deviceCreateOrAssignRequest.symbolId, deviceId);
                store.closeDeviceCreateOrAssignForm();
              },
            }}
            onSave={(saved) => {
              // fix/inline-device-creation commit 3c: UTWORZ NOWY -
              // DeviceFormSync.ts's own createAndAssignDevice, same
              // reasoning as onAssignExisting above.
              const store = useStore.getState();
              createAndAssignDevice(store, deviceCreateOrAssignRequest.symbolId, saved);
              store.closeDeviceCreateOrAssignForm();
            }}
            onCancel={() => useStore.getState().closeDeviceCreateOrAssignForm()}
          />
        </Suspense>
      )}
      <Toolbar />

      <div className="main-workspace">
        <PanelGroup direction="horizontal" autoSaveId="epw-layout-main">
          <Panel defaultSize={20} minSize={10} className="panel-container">
            <Toolbox />
          </Panel>

          <PanelResizeHandle className="resize-handle-vertical" />

          <Panel defaultSize={60} minSize={30} className="panel-container">
            <PanelGroup direction="vertical" autoSaveId="epw-layout-center">
              <Panel defaultSize={80} minSize={30} className="panel-container">
                <Canvas />
              </Panel>

              <PanelResizeHandle className="resize-handle-horizontal" />

              <Panel defaultSize={20} minSize={10} className="panel-container">
                <MessagesPanel />
              </Panel>
            </PanelGroup>
          </Panel>

          <PanelResizeHandle className="resize-handle-vertical" />

          <Panel defaultSize={20} minSize={10} className="panel-container">
            <PropertyInspector />
          </Panel>
        </PanelGroup>
      </div>

      <StatusBar />
    </div>
  );
}

export default App;
