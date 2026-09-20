// The photometry of ONE fitting - what it emits, how widely, and how
// high it hangs.
//
// Owner, 2026-09-20: "chce moc definiowac parametry opraw zeby
// sprawdzac rozklad oswietlenia".
//
// project/Illuminance.ts holds one defensible figure per KIND of
// fitting, which is enough to sketch a room and nothing like enough to
// check one: the fitting being installed comes off a manufacturer's
// page, and 3200 lm against the catalogue's 1200 is the difference
// between a design that passes and one that does not. These three
// fields are that page, typed in.
//
// BLANK MEANS THE CATALOGUE. Each box shows the type's own figure as
// its placeholder and stays empty until somebody overrides it, so the
// panel always answers "is this fitting special?" without a second
// control to read. Clearing a box goes back to the catalogue; that is
// what the Reset button does to all three at once.
//
// Nothing is clamped as you type - Illuminance.photometryFor holds the
// stored figure to PHOTOMETRY_LIMITS when it reads it, which is the
// place that must never produce an infinity. Clamping in the box as
// well would rewrite what somebody was halfway through typing.

import React, { useEffect, useState } from 'react';
import { useStore } from '../store';
import type { SynopticObject } from '../store';
import { PHOTOMETRY, hasCustomPhotometry } from '../project/Illuminance';
import { tr } from '../i18n/tr';
import { FONT_SIZE_SMALL } from '../theme/ScadaTheme';

/** The three overridable figures, by their key in the editor bag. */
type PhotometryKey = 'lighting_flux' | 'lighting_exponent' | 'lighting_height';

const formatNumber = (value: number, digits = 2) => value.toFixed(digits).replace('.', ',');

/**
 * One figure. Empty = inherit, so `value` is the OVERRIDE and
 * `catalogue` is only ever the placeholder.
 *
 * Not type="number", for the same reason MetreField is not: a number
 * input rejects "1,85" outright and the box goes blank as you type.
 */
const FigureField: React.FC<{
  name: PhotometryKey;
  label: string;
  unit: string;
  digits: number;
  value: number | undefined;
  catalogue: number;
  onCommit: (value: number | undefined) => void;
}> = ({ name, label, unit, digits, value, catalogue, onCommit }) => {
  const shown = typeof value === 'number' && Number.isFinite(value) ? formatNumber(value, digits) : '';
  const [draft, setDraft] = useState<string | null>(null);
  useEffect(() => { setDraft(null); }, [value]);

  const commit = () => {
    if (draft === null) return;
    const text = draft.trim();
    setDraft(null);
    // An emptied box is not a zero - it is "whatever the catalogue says".
    if (text === '') {
      if (value !== undefined) onCommit(undefined);
      return;
    }
    const parsed = Number(text.replace(',', '.'));
    if (Number.isFinite(parsed) && parsed !== value) onCommit(parsed);
  };

  return (
    <div className="property-row">
      <label>{label}</label>
      <input
        type="text"
        inputMode="decimal"
        name={name}
        value={draft ?? shown}
        placeholder={formatNumber(catalogue, digits)}
        onChange={e => setDraft(e.target.value)}
        onKeyDown={e => { if (e.key === 'Enter') commit(); e.stopPropagation(); }}
        onBlur={commit}
      />
      <span className="property-unit">{unit}</span>
    </div>
  );
};

export const LuminaireInspector: React.FC<{ obj: SynopticObject }> = ({ obj }) => {
  const catalogue = PHOTOMETRY[obj.type];
  if (!catalogue) return null;

  const set = (key: PhotometryKey, value: number | undefined) => {
    const store = useStore.getState();
    const editor = { ...(obj.editor || {}) };
    if (value === undefined) {
      delete editor[key];
    } else {
      editor[key] = value;
    }
    store.updateObject(obj.id, { editor });
    store.saveHistory();
  };

  const reset = () => {
    const store = useStore.getState();
    const editor = { ...(obj.editor || {}) };
    delete editor.lighting_flux;
    delete editor.lighting_exponent;
    delete editor.lighting_height;
    store.updateObject(obj.id, { editor });
    store.saveHistory();
  };

  const custom = hasCustomPhotometry(obj);

  return (
    <div className="property-group">
      <div className="property-group-title">{tr('lighting.title')}</div>

      <FigureField
        name="lighting_flux"
        label={tr('lighting.flux')}
        unit="lm"
        digits={0}
        value={obj.editor?.lighting_flux}
        catalogue={catalogue.flux}
        onCommit={v => set('lighting_flux', v)}
      />
      <FigureField
        name="lighting_exponent"
        label={tr('lighting.spread')}
        unit=""
        digits={1}
        value={obj.editor?.lighting_exponent}
        catalogue={catalogue.exponent}
        onCommit={v => set('lighting_exponent', v)}
      />
      <FigureField
        name="lighting_height"
        label={tr('lighting.height')}
        unit="m"
        digits={2}
        value={obj.editor?.lighting_height}
        catalogue={catalogue.mountingHeight}
        onCommit={v => set('lighting_height', v)}
      />

      {/* What the numbers mean, once, where they are typed: an exponent
          is not a figure anybody carries in their head, and the height
          is measured from the WORKING PLANE rather than the floor -
          getting that wrong by 0.85 m is a third of the illuminance. */}
      <div className="property-row" style={{ opacity: 0.75, fontSize: FONT_SIZE_SMALL }}>
        {tr('lighting.hint')}
      </div>

      {custom && (
        <div className="property-row">
          <button data-cmd="lighting_reset" onClick={reset} style={{ fontSize: FONT_SIZE_SMALL }}>
            {tr('lighting.reset')}
          </button>
        </div>
      )}
    </div>
  );
};
