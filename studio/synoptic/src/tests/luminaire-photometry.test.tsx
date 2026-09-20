/** @vitest-environment jsdom */
// Turning a fitting, and giving it figures of its own.
//
// Owner, 2026-09-20:
//   2) "obracam oprawę i zmienia się widmo świetlne"
//   3) "chcę móc definiować parametry opraw żeby sprawdzać rozkład oświetlenia"
//
// (2) was a real defect and the screenshot showed it plainly: a batten
// turned upright, and the pool of light stayed where the batten used to
// be, offset a metre to the side. collectSources took the centre as
// (x + w/2, y + h/2) while Konva turns an object about its TOP-LEFT, so
// the physics and the picture disagreed about where the lamp was. The
// tests below pin the agreement rather than the old arithmetic: after
// any rotation the brightest point is under the fitting's DRAWN centre.
//
// (3) is new: the catalogue in Illuminance.ts holds one figure per kind
// of fitting, and a real design needs the figure off the manufacturer's
// page. An override wins; a blank box means the catalogue; and neither
// can push the model somewhere it stops meaning anything.

import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { render, screen, cleanup, fireEvent, act } from '@testing-library/react';
import {
  PHOTOMETRY, PHOTOMETRY_LIMITS, collectSources, hasCustomPhotometry,
  illuminanceAt, photometryFor,
} from '../project/Illuminance';
import { objectCenter } from '../project/WallOpenings';
import { useStore } from '../store';
import type { SynopticObject } from '../store';
import { LuminaireInspector } from '../components/LuminaireInspector';
import { LightingPanel } from '../components/LightingPanel';
import { setLanguage } from '../i18n/tr';
import { cm, m, PIXELS_PER_METRE } from '../theme/Scale';

const fitting = (over: Partial<SynopticObject> = {}): SynopticObject => ({
  id: 'l1', type: 'building.luminaire_fluorescent', category: 'BUILDING',
  x: m(2), y: m(2), rotation: 0, scaleX: 1, scaleY: 1,
  visible: true, locked: false, layer: 0,
  tag: '', description: '', color: '', fill: '', border: '', text: '', font: '', fontSize: 12,
  tooltip: '', width: cm(120), height: cm(17), customProperties: {},
  editor: { preview_state: 'ON' },
  ...over,
});

/** The metre coordinates of where the fitting is actually DRAWN. */
const drawnCentre = (obj: SynopticObject) => {
  const c = objectCenter(obj);
  return { x: c.x / PIXELS_PER_METRE, y: c.y / PIXELS_PER_METRE };
};

describe('a fitting that has been turned', () => {
  it('lights the place it is drawn, not the place it started', () => {
    // The defect, stated as the user saw it. Turning about the centre
    // moves x/y and leaves width/height alone, so the naive
    // (x + w/2, y + h/2) lands somewhere the fitting no longer is.
    const upright = fitting({ rotation: 90, x: m(2) + cm(17), y: m(2) });
    const centre = drawnCentre(upright);

    const sources = collectSources([upright]);
    const meanX = sources.reduce((s, p) => s + p.x, 0) / sources.length;
    const meanY = sources.reduce((s, p) => s + p.y, 0) / sources.length;

    expect(meanX).toBeCloseTo(centre.x, 6);
    expect(meanY).toBeCloseTo(centre.y, 6);
  });

  it('is brightest directly beneath itself at every angle', () => {
    for (const rotation of [0, 45, 90, 180, 270, -90]) {
      const obj = fitting({ rotation });
      const centre = drawnCentre(obj);
      const sources = collectSources([obj]);

      const beneath = illuminanceAt(sources, centre.x, centre.y);
      // A metre away in each direction must be dimmer than under it.
      for (const [dx, dy] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) {
        expect(illuminanceAt(sources, centre.x + dx, centre.y + dy)).toBeLessThan(beneath);
      }
    }
  });

  it('turns a batten\'s band of light with the batten', () => {
    // Lying down, the samples spread along x; stood up, along y. Before
    // this the axis was read off the unrotated box, so a batten hung
    // lengthways lit a band across itself.
    const lying = collectSources([fitting({ rotation: 0 })]);
    const standing = collectSources([fitting({ rotation: 90 })]);

    const spread = (points: { x: number; y: number }[], axis: 'x' | 'y') =>
      Math.max(...points.map(p => p[axis])) - Math.min(...points.map(p => p[axis]));

    // The samples sit at the CENTRES of the seven segments the batten is
    // cut into, not at its ends, so the outermost pair spans one segment
    // less than its 1.2 m - half a segment is left at each end, which is
    // what stops the flux piling up on the tips.
    const sampled = 1.2 * (6 / 7);

    expect(spread(lying, 'x')).toBeCloseTo(sampled, 3);
    expect(spread(lying, 'y')).toBeCloseTo(0, 6);

    expect(spread(standing, 'y')).toBeCloseTo(sampled, 3);
    expect(spread(standing, 'x')).toBeCloseTo(0, 6);
  });

  it('gives the same total light whichever way it faces', () => {
    // Rotation moves light about; it does not create or destroy any.
    const total = (rotation: number) =>
      collectSources([fitting({ rotation })]).reduce((s, p) => s + p.intensity, 0);

    expect(total(90)).toBeCloseTo(total(0), 6);
    expect(total(37)).toBeCloseTo(total(0), 6);
  });
});

describe('a fitting\'s own figures', () => {
  it('uses the catalogue until told otherwise', () => {
    const plain = fitting({ type: 'building.luminaire', editor: { preview_state: 'ON' } });
    expect(photometryFor(plain)).toMatchObject(PHOTOMETRY['building.luminaire']);
    expect(hasCustomPhotometry(plain)).toBe(false);
  });

  it('takes the flux off the manufacturer\'s page when one is given', () => {
    const real = fitting({
      type: 'building.luminaire',
      editor: { preview_state: 'ON', lighting_flux: 3600 },
    });
    expect(photometryFor(real)!.flux).toBe(3600);
    // ...and everything not overridden still comes from the catalogue.
    expect(photometryFor(real)!.exponent).toBe(PHOTOMETRY['building.luminaire'].exponent);
    expect(hasCustomPhotometry(real)).toBe(true);
  });

  it('brightens the room in proportion to the flux', () => {
    // The model is linear in flux, so three times the lumens is three
    // times the lux - the check that the override actually reaches the
    // calculation rather than merely being stored.
    const base = PHOTOMETRY['building.luminaire'].flux;
    const one = collectSources([fitting({ type: 'building.luminaire', width: cm(30), height: cm(30) })]);
    const three = collectSources([fitting({
      type: 'building.luminaire', width: cm(30), height: cm(30),
      editor: { preview_state: 'ON', lighting_flux: base * 3 },
    })]);
    const at = (s: ReturnType<typeof collectSources>) => illuminanceAt(s, 2.5, 2.5);
    expect(at(three)).toBeCloseTo(at(one) * 3, 4);
  });

  it('refuses a figure that would make the model meaningless', () => {
    // A mounting height of zero puts the source ON the working plane,
    // where the inverse-square law divides by nothing - one typo would
    // otherwise turn the whole grid into infinity.
    const zeroHeight = fitting({ editor: { preview_state: 'ON', lighting_height: 0 } });
    expect(photometryFor(zeroHeight)!.mountingHeight).toBe(PHOTOMETRY_LIMITS.mountingHeight.min);

    const absurdFlux = fitting({ editor: { preview_state: 'ON', lighting_flux: 1e12 } });
    expect(photometryFor(absurdFlux)!.flux).toBe(PHOTOMETRY_LIMITS.flux.max);

    const sources = collectSources([zeroHeight, absurdFlux]);
    expect(sources.every(s => Number.isFinite(s.intensity) && Number.isFinite(s.height))).toBe(true);
    expect(Number.isFinite(illuminanceAt(sources, 2, 2))).toBe(true);
  });

  it('ignores rubbish in the stored value rather than propagating it', () => {
    const broken = fitting({
      editor: { preview_state: 'ON', lighting_exponent: Number.NaN, lighting_flux: undefined },
    });
    expect(photometryFor(broken)!.exponent).toBe(PHOTOMETRY['building.luminaire_fluorescent'].exponent);
    expect(photometryFor(broken)!.flux).toBe(PHOTOMETRY['building.luminaire_fluorescent'].flux);
  });

  it('is not offered for something that does not emit light', () => {
    expect(photometryFor(fitting({ type: 'building.socket_outlet' }))).toBeNull();
  });
});

describe('the luminaire panel', () => {
  beforeEach(() => {
    setLanguage('en');
    useStore.setState({ objects: [fitting()], selectedIds: ['l1'] });
  });
  afterEach(cleanup);

  const field = (name: string) => document.querySelector(`input[name="${name}"]`) as HTMLInputElement;
  const current = () => useStore.getState().objects[0];

  it('shows the catalogue figure as a placeholder, and leaves the box empty', () => {
    render(<LuminaireInspector obj={current()} />);
    expect(field('lighting_flux').value).toBe('');
    expect(field('lighting_flux').placeholder).toBe('4800');
    expect(field('lighting_height').placeholder).toBe('1,85');
  });

  it('stores what is typed, with a comma for the decimal point', () => {
    // The figure is shown Polish-style, so it has to be accepted that
    // way too - a number input would simply refuse "2,40".
    render(<LuminaireInspector obj={current()} />);
    act(() => {
      fireEvent.change(field('lighting_height'), { target: { value: '2,40' } });
      fireEvent.blur(field('lighting_height'));
    });
    expect(current().editor?.lighting_height).toBe(2.4);
  });

  it('treats an emptied box as "use the catalogue", not as zero', () => {
    useStore.setState({ objects: [fitting({ editor: { preview_state: 'ON', lighting_flux: 3600 } })] });
    render(<LuminaireInspector obj={current()} />);
    act(() => {
      fireEvent.change(field('lighting_flux'), { target: { value: '' } });
      fireEvent.blur(field('lighting_flux'));
    });
    expect(current().editor?.lighting_flux).toBeUndefined();
    expect(photometryFor(current())!.flux).toBe(PHOTOMETRY['building.luminaire_fluorescent'].flux);
  });

  it('offers the way back to the catalogue only once something was changed', () => {
    const { rerender } = render(<LuminaireInspector obj={current()} />);
    expect(screen.queryByText('Back to catalogue')).toBeNull();

    act(() => {
      fireEvent.change(field('lighting_flux'), { target: { value: '3600' } });
      fireEvent.blur(field('lighting_flux'));
    });
    rerender(<LuminaireInspector obj={current()} />);
    expect(screen.getByText('Back to catalogue')).toBeTruthy();

    act(() => { fireEvent.click(screen.getByText('Back to catalogue')); });
    expect(hasCustomPhotometry(current())).toBe(false);
  });

  it('keeps every other editor setting while it writes its own', () => {
    // The editor bag is shared - clobbering it here would switch the
    // fitting off, which is exactly what a naive spread would do.
    render(<LuminaireInspector obj={current()} />);
    act(() => {
      fireEvent.change(field('lighting_flux'), { target: { value: '3600' } });
      fireEvent.blur(field('lighting_flux'));
    });
    expect(current().editor?.preview_state).toBe('ON');
  });
});

describe('the Lighting panel in Polish', () => {
  // It was written straight into English while everything around it
  // switched - a Polish session read half a panel in each language.
  afterEach(() => { cleanup(); setLanguage('en'); });

  it('names the target rooms and the caveat in the chosen language', () => {
    setLanguage('pl');
    useStore.setState({ objects: [], walls: [] });
    render(<LightingPanel />);

    expect(screen.getByText('Mapa natężenia na rysunku')).toBeTruthy();
    expect(screen.getByText(/Tylko składowa bezpośrednia/)).toBeTruthy();
    expect(screen.getByText('Biuro, praca przy monitorze - 500 lx')).toBeTruthy();
    // The lux figures are the standard's, so they stay put.
    expect(screen.getByText('Korytarz - 100 lx')).toBeTruthy();
  });

  it('says so in English when English is chosen', () => {
    setLanguage('en');
    useStore.setState({ objects: [], walls: [] });
    render(<LightingPanel />);

    expect(screen.getByText('Illuminance map on the drawing')).toBeTruthy();
    expect(screen.getByText('Office, screen work - 500 lx')).toBeTruthy();
  });
});
