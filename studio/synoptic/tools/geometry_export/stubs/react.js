// Minimal stand-in for 'react', so every symbol component file
// (studio/synoptic/src/symbols/**/*.tsx) can be executed as a PLAIN
// FUNCTION - outside any renderer - to read back the JSX tree it
// builds. Not a React reimplementation; it does exactly this:
//
// 1. createElement(type, props, ...children) returns a plain
//    {type, props, children} object - exactly what the JSX produced.
// 2. useState(initial) always returns [initial, noop] and useEffect/
//    useLayoutEffect never run their callback: every animated symbol is
//    frozen at its OWN declared initial pose (angle 0, blink on). What
//    animates, and how, is recorded separately as a directive by
//    export.mjs - the geometry file carries the base pose only.
// 3. useRef/useMemo/useCallback/memo/forwardRef are the trivial
//    versions a single synchronous call needs.
//
// Anything else a component might reach for throws by name (the Proxy
// below) - a real finding for the export log, never silently wrong.
function createElement(type, props, ...children) {
  const flat = children.flat(Infinity).filter((c) => c !== null && c !== undefined && c !== false && c !== true);
  const { children: propChildren, ...rest } = props || {};
  const all = flat.length ? flat : (propChildren === undefined ? [] : [propChildren].flat(Infinity).filter(Boolean));
  return { type, props: rest, children: all };
}
// export.mjs sets globalThis.__EPW_PERTURB_STATE for one extra pass per
// animated symbol: every numeric state comes back shifted, and the
// nodes whose `rotation` changed between the two passes are the ones
// the symbol's own animation loop rotates (a fan's blades, not its
// housing) - marked $animate_rotation in the export.
function useState(initial) {
  let value = typeof initial === 'function' ? initial() : initial;
  if (globalThis.__EPW_PERTURB_STATE && typeof value === 'number') value = value + 37;
  return [value, () => {}];
}
function useEffect() {}
function useLayoutEffect() {}
function useRef(initial) { return { current: initial === undefined ? null : initial }; }
function useMemo(factory) { return factory(); }
function useCallback(fn) { return fn; }
function memo(component) { return component; }
function forwardRef(component) { return (props) => component(props, null); }
function useContext() { return undefined; }
const Fragment = 'Fragment';
const React = { createElement, useState, useEffect, useLayoutEffect, useRef, useMemo, useCallback, memo, forwardRef, useContext, Fragment };
export default new Proxy(React, {
  get(target, prop) {
    if (prop in target) return target[prop];
    if (typeof prop === 'symbol' || prop === 'then' || prop === '__esModule') return undefined;
    throw new Error(`stubs/react.js: React.${String(prop)} is not implemented in the geometry exporter's React stand-in.`);
  },
});
export { createElement, useState, useEffect, useLayoutEffect, useRef, useMemo, useCallback, memo, forwardRef, useContext, Fragment };
