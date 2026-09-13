// feat/workspace: "Kompilacja" - what would stop this screen from being
// handed to a controller, listed where it can be acted on.
//
// The checks themselves are project/ScreenValidation.ts (pure, tested).
// This is the part that matters in use: every row that names an object
// SELECTS it on the canvas when clicked. A list of errors you cannot
// find is only half a list - "Oprawa: brak przypisania do obwodu" is
// useless on a plan with forty luminaires unless it also shows you
// which one.
//
// Severity is colour AND text, never colour alone.

import React, { useMemo } from 'react';
import { useStore } from '../store';
import { validateScreen } from '../project/ScreenValidation';
import type { IssueSeverity, ScreenIssue } from '../project/ScreenValidation';
import {
  COLOR_ALARM, COLOR_BEVEL_DARK, COLOR_BEVEL_LIGHT, COLOR_OUTLINE, COLOR_PANEL,
  COLOR_RUN, COLOR_VALUE_FIELD, FONT_SIZE_SMALL, FONT_UI, VENTILATION_ACTIVE,
} from '../theme/ScadaTheme';

const SEVERITY_LABEL: Record<IssueSeverity, string> = {
  ERROR: 'ERROR',
  WARNING: 'WARNING',
  INFO: 'INFO',
};

const SEVERITY_COLOR: Record<IssueSeverity, string> = {
  ERROR: COLOR_ALARM,
  WARNING: VENTILATION_ACTIVE,
  INFO: COLOR_BEVEL_DARK,
};

export const CompilationPanel: React.FC = () => {
  const objects = useStore(s => s.objects);
  const walls = useStore(s => s.walls);
  const circuits = useStore(s => s.circuits);
  const devices = useStore(s => s.devices);
  const selectObjects = useStore(s => s.selectObjects);
  const selectedIds = useStore(s => s.selectedIds);

  const validation = useMemo(
    () => validateScreen(objects, walls, circuits, devices),
    [objects, walls, circuits, devices]
  );

  const rows: ScreenIssue[] = validation.issues;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', fontFamily: FONT_UI, fontSize: FONT_SIZE_SMALL }}>
      <div
        style={{
          display: 'flex', alignItems: 'center', gap: 10, padding: '3px 8px',
          background: COLOR_PANEL, borderBottom: `1px solid ${COLOR_BEVEL_DARK}`,
        }}
      >
        <span
          style={{
            fontWeight: 'bold',
            color: validation.runnable ? COLOR_RUN : COLOR_ALARM,
          }}
        >
          {validation.runnable ? 'READY TO RUN' : 'BUILD CHECK FAILED'}
        </span>
        <span>Errors: <b>{validation.errors}</b></span>
        <span>Warnings: <b>{validation.warnings}</b></span>
        <span>Info: <b>{validation.infos}</b></span>
        <span style={{ flex: 1 }} />
        {rows.length > 0 && <span style={{ opacity: 0.75 }}>Click a row to select the device on the drawing</span>}
      </div>

      <div style={{ flex: 1, minHeight: 0, overflowY: 'auto', background: COLOR_VALUE_FIELD }}>
        {rows.length === 0 && (
          <div style={{ padding: 10, color: COLOR_RUN }}>
            No issues. Every device has a circuit and every circuit has an output.
          </div>
        )}

        {rows.map(issue => {
          const selected = !!issue.objectId && selectedIds.includes(issue.objectId);
          return (
            <div
              key={issue.code}
              onClick={() => { if (issue.objectId) selectObjects([issue.objectId]); }}
              title={issue.objectId ? 'Click to select this device on the drawing' : undefined}
              style={{
                display: 'flex',
                gap: 8,
                padding: '2px 8px',
                cursor: issue.objectId ? 'pointer' : 'default',
                background: selected ? COLOR_BEVEL_LIGHT : 'transparent',
                borderBottom: `1px solid ${COLOR_PANEL}`,
                color: COLOR_OUTLINE,
              }}
            >
              <span
                style={{
                  minWidth: 64,
                  fontWeight: 'bold',
                  color: SEVERITY_COLOR[issue.severity],
                }}
              >
                {SEVERITY_LABEL[issue.severity]}
              </span>
              <span>{issue.message}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
};
