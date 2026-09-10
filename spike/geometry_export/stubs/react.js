// Minimal stand-in for 'react', used only so the real symbol component
// files (studio/synoptic/src/symbols/**/*.tsx) can be executed as PLAIN
// FUNCTIONS, outside any real renderer, to read back the JSX tree they
// build. This is NOT a React reimplementation - it does exactly three
// things, deliberately:
//
// 1. createElement(type, props, ...children) returns a plain
//    {type, props} object - a real React element is normally opaque,
//    but its type/props are exactly what a JSX call produces, and
//    that's all a geometry-extraction walker needs to read.
// 2. useState(initial) always returns [initial, noop] - it NEVER
//    re-renders. This freezes every animated symbol (FanSymbol,
//    IndicatorLampSymbol, ...) at its OWN declared initial pose
//    (angle=0, blinkOn=true) - exactly the "geometry, not animation"
//    split this spike's task requires: the animation itself is
//    recorded separately as a hand-authored directive (see
//    extract.mjs), not derived from tracing timer behavior.
// 3. useEffect's callback is never invoked at all (no commit phase
//    exists here) - so no interval/rAF loop ever starts. This is what
//    makes (2) true: nothing ever calls the setter this stub hands back.
//
// Anything beyond createElement/useState/useEffect that a real
// component might import from 'react' would throw "not implemented"
// here rather than silently doing the wrong thing - see the Proxy
// below. None of the 4 target symbols in this spike needed anything
// else (confirmed - this file would throw immediately if they had).
function createElement(type, props, ...children) {
  const flatChildren = children.flat(Infinity).filter((c) => c !== null && c !== undefined && c !== false);
  return { type, props: props || {}, children: flatChildren };
}

function useState(initial) {
  const value = typeof initial === 'function' ? initial() : initial;
  const noopSetter = () => {};
  return [value, noopSetter];
}

function useEffect(_callback, _deps) {
  // Deliberately does nothing - see file header, point 3.
}

const React = { createElement, useState, useEffect, Fragment: 'Fragment' };

export default new Proxy(React, {
  get(target, prop) {
    if (prop in target) return target[prop];
    throw new Error(
      `stubs/react.js: '${String(prop)}' is not implemented in this spike's minimal React stand-in. ` +
      `This means the symbol under extraction uses a React API beyond createElement/useState/useEffect - ` +
      `a real finding for the spike report, not a bug to silently paper over.`
    );
  },
});
export { createElement, useState, useEffect };
export const Fragment = 'Fragment';
