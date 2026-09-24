// feat/synoptic-library: the Object Library, divided by ONE criterion -
// the installation domain a thing belongs to.
//
// The registry's own categories mixed two orders: WHERE (Electrical,
// Water, SITE, HVAC) and WHAT KIND (SCADA, Automation, Instrumentation,
// Measurements, Graphics). A pressure sensor on a pipe was Water or
// Instrumentation, and there is no right answer - so people looked in
// three places. Here every symbol sits where it is LOOKED FOR: the
// pressure sensor with the water, the temperature sensor with the
// heating. No group is smaller than four.
//
// The operator's screen is a domain of its own - the control system: the
// indicator diode, the meter, the boundary point, the four screen panels,
// and the text box and label frame that describe the screen. On their own
// the two descriptions would be a folder of two.
//
// The registry's `category` is left exactly as it is: it is written into
// every placed object and read elsewhere. The library simply stops using
// it for its folders. Symbols hidden from the library stay hidden; they
// still get a domain (from their category) should an old project use one.
//
// Everything here is pure; Toolbox.tsx renders it.

import { getSymbolDefinition, SYMBOL_REGISTRY } from '../symbols/SymbolRegistry';
import type { SymbolDefinition } from '../symbols/SymbolRegistry';
import { symbolName, symbolNamesInAllLanguages, tr } from '../i18n/tr';
import type { Language } from '../i18n/tr';
import { matchesAnyName } from './RecentSymbols';

export type LibraryDomain = 'BUILDING' | 'LIGHTING' | 'ELECTRICAL' | 'WATER' | 'HVAC' | 'AUTOMATION';

/** Folder order, top to bottom: the room first, then the installations that go into it, then the control system. */
export const LIBRARY_DOMAIN_ORDER: LibraryDomain[] = ['BUILDING', 'LIGHTING', 'ELECTRICAL', 'WATER', 'HVAC', 'AUTOMATION'];

/** Every symbol the library shows, and its domain. */
export const SYMBOL_DOMAIN: Record<string, LibraryDomain> = {
  // Building & site - the structure and what stands in or around it.
  'building.door': 'BUILDING',
  'building.window': 'BUILDING',
  'building.gate': 'BUILDING',
  'building.table': 'BUILDING',
  'building.chair': 'BUILDING',
  'building.shelf': 'BUILDING',
  'site.house': 'BUILDING',
  'site.warehouse': 'BUILDING',
  'site.sliding_gate': 'BUILDING',
  'site.grass': 'BUILDING',
  'site.concrete_road': 'BUILDING',

  // Lighting - indoor and outdoor alike.
  'building.luminaire': 'LIGHTING',
  'building.luminaire_pendant': 'LIGHTING',
  'building.luminaire_wall': 'LIGHTING',
  'building.luminaire_fluorescent': 'LIGHTING',
  'building.luminaire_halogen': 'LIGHTING',
  'site.lamp_post_double': 'LIGHTING',
  'site.lamp_post_single': 'LIGHTING',
  'site.halogen': 'LIGHTING',
  'site.garden_light': 'LIGHTING',

  // Electrical - switchgear, outlets, earthing and signalling.
  'electrical.circuit_breaker': 'ELECTRICAL',
  'electrical.disconnect_switch': 'ELECTRICAL',
  'electrical.selector_switch': 'ELECTRICAL',
  'electrical.indicator_lamp': 'ELECTRICAL',
  'electrical.motor': 'ELECTRICAL',
  'electrical.earth': 'ELECTRICAL',
  'building.socket_outlet': 'ELECTRICAL',
  'site.cable_junction': 'ELECTRICAL',
  'site.alarm_beacon': 'ELECTRICAL',
  'site.alarm_horn': 'ELECTRICAL',

  // Water & drainage - including the sensors that sit on the pipes.
  'water.pump': 'WATER',
  'water.tank': 'WATER',
  'water.ball_valve': 'WATER',
  'water.solenoid_valve': 'WATER',
  'water.drain_valve': 'WATER',
  'water.drain': 'WATER',
  'site.sewage_plant': 'WATER',
  'site.water_manhole': 'WATER',
  'site.garden_sprinkler': 'WATER',
  'site.rainwater_tank2': 'WATER',
  'site.water_selector_valve_switched': 'WATER',
  'site.water_selector_valve_3pos': 'WATER',
  'site.check_valve': 'WATER',
  'site.water_filter': 'WATER',
  'site.hydrofor': 'WATER',
  'site.flow_meter': 'WATER',
  'site.water_meter': 'WATER',
  'site.pressure_switch': 'WATER',
  'site.sprinkler_head': 'WATER',
  'site.drip_line': 'WATER',
  'instrumentation.pressure_sensor': 'WATER',
  'instrumentation.level_sensor': 'WATER',
  'instrumentation.leak_sensor': 'WATER',
  'site.rain_sensor': 'WATER',

  // Heating & ventilation - with the room-climate sensors.
  'hvac.fan': 'HVAC',
  'hvac.heater': 'HVAC',
  'instrumentation.temperature_sensor': 'HVAC',
  'instrumentation.humidity_sensor': 'HVAC',

  // Control & the SCADA screen - indicators, readouts and descriptions.
  'scada.indicator_diode': 'AUTOMATION',
  'scada.push_button': 'AUTOMATION',
  'scada.meter': 'AUTOMATION',
  'scada.boundary_point': 'AUTOMATION',
  'scada.text_box': 'AUTOMATION',
  'scada.label_frame': 'AUTOMATION',
};

/** The screen panels that are not symbols but are inserted like them: their own element arrays, bound to devices. */
export const WIDGET_TYPES = ['widget.meter', 'widget.signal_panel', 'widget.group_command', 'widget.setpoint_panel'] as const;
export type WidgetType = typeof WIDGET_TYPES[number];

/** The translation key of a panel: "widget.meter" -> "widget.meter" under the widget table, looked up without splitting its own dot. */
function widgetKey(type: string): string {
  return `widget.${type.slice("widget.".length)}`;
}

export function isWidgetType(type: string): type is WidgetType {
  return (WIDGET_TYPES as readonly string[]).includes(type);
}

/** For a symbol hidden from the library that still turns up in an old project: the domain its registry category points to. */
const CATEGORY_FALLBACK: Record<string, LibraryDomain> = {
  Electrical: 'ELECTRICAL',
  Water: 'WATER',
  HVAC: 'HVAC',
  Instrumentation: 'AUTOMATION',
  Measurements: 'AUTOMATION',
  Automation: 'AUTOMATION',
  SCADA: 'AUTOMATION',
  Graphics: 'AUTOMATION',
  SITE: 'BUILDING',
  BUILDING: 'BUILDING',
};

export function domainOfType(type: string): LibraryDomain | null {
  if (isWidgetType(type)) return 'AUTOMATION';
  if (SYMBOL_DOMAIN[type]) return SYMBOL_DOMAIN[type];
  const def = getSymbolDefinition(type);
  return def ? (CATEGORY_FALLBACK[def.category] ?? null) : null;
}

export interface LibraryEntry {
  type: string;
  /** The name in the requested language. */
  name: string;
  domain: LibraryDomain;
  /** The registry category a dropped object is created with (empty for a widget). */
  category: string;
  isWidget: boolean;
}

/** One entry for a type, in `language`; null for a type the library does not know. */
export function libraryEntry(type: string, language?: Language): LibraryEntry | null {
  const domain = domainOfType(type);
  if (!domain) return null;
  if (isWidgetType(type)) {
    return { type, name: tr(widgetKey(type), undefined, language), domain, category: '', isWidget: true };
  }
  const def = getSymbolDefinition(type);
  if (!def) return null;
  return { type, name: symbolName(type, def.label, language), domain, category: def.category, isWidget: false };
}

/** Everything the library offers: every symbol not hidden from it, and the four panels. */
export function allLibraryEntries(language?: Language): LibraryEntry[] {
  const symbols = Object.values(SYMBOL_REGISTRY)
    .filter((def: SymbolDefinition) => !def.hiddenFromLibrary)
    .map(def => libraryEntry(def.type, language))
    .filter((entry): entry is LibraryEntry => entry !== null);
  const widgets = WIDGET_TYPES.map(type => libraryEntry(type, language)).filter((entry): entry is LibraryEntry => entry !== null);
  return [...symbols, ...widgets];
}

/** Whether a library entry matches a search: its Polish name, its English name, its registry label, or its type. */
export function entryMatches(entry: LibraryEntry, query: string): boolean {
  const def = getSymbolDefinition(entry.type);
  const names = [entry.name, ...symbolNamesInAllLanguages(entry.type), def?.label ?? ''];
  if (entry.isWidget) {
    names.push(tr(widgetKey(entry.type), undefined, 'en'), tr(widgetKey(entry.type), undefined, 'pl'));
  }
  return matchesAnyName(names, entry.type, query);
}

export interface LibraryGroup {
  domain: LibraryDomain;
  entries: LibraryEntry[];
}

/** The folders, in order, each sorted by name; while searching, only what matches, and no empty folder. */
export function groupLibrary(entries: LibraryEntry[], query = '', language?: Language): LibraryGroup[] {
  const searching = query.trim().length > 0;
  const collator = new Intl.Collator(language ?? 'en', { sensitivity: 'base' });
  return LIBRARY_DOMAIN_ORDER
    .map(domain => ({
      domain,
      entries: entries
        .filter(entry => entry.domain === domain)
        .filter(entry => !searching || entryMatches(entry, query))
        .sort((a, b) => collator.compare(a.name, b.name)),
    }))
    .filter(group => group.entries.length > 0);
}

/** What a project's screens are made of, for counting. */
export interface ScreenSymbols {
  objects: { type: string }[];
  meters?: unknown[];
  signalPanels?: unknown[];
  groupCommands?: unknown[];
  setpointPanels?: unknown[];
}

export interface ProjectUsage {
  type: string;
  count: number;
}

/**
 * The symbols already placed on the project's screens - the active one
 * and every stored one - counted, most used first, then by name. The four
 * screen panels are counted like symbols.
 */
export function projectSymbolUsage(screens: ScreenSymbols[], language?: Language): ProjectUsage[] {
  const counts = new Map<string, number>();
  const add = (type: string, n = 1) => {
    if (n <= 0 || !libraryEntry(type)) return;
    counts.set(type, (counts.get(type) ?? 0) + n);
  };
  for (const screen of screens) {
    for (const obj of screen.objects) add(obj.type);
    add('widget.meter', screen.meters?.length ?? 0);
    add('widget.signal_panel', screen.signalPanels?.length ?? 0);
    add('widget.group_command', screen.groupCommands?.length ?? 0);
    add('widget.setpoint_panel', screen.setpointPanels?.length ?? 0);
  }
  const collator = new Intl.Collator(language ?? 'en', { sensitivity: 'base' });
  return [...counts.entries()]
    .map(([type, count]) => ({ type, count }))
    .sort((a, b) => b.count - a.count
      || collator.compare(libraryEntry(a.type, language)!.name, libraryEntry(b.type, language)!.name));
}
