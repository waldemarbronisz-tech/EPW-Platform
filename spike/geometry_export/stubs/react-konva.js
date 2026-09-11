// Minimal stand-in for 'react-konva'. The real package's Group/Rect/
// Circle/etc. are host components tied to react-konva's own reconciler
// (they only mean something once mounted onto a real Konva.Stage) -
// this spike never mounts anything. Since JSX compiles a tag like
// <Rect width={10}/> to createElement(Rect, {width: 10}), all that
// matters for a plain-object element tree is that `Rect` (etc.) is
// SOME stable, identifiable value - a plain string tag is enough, and
// keeps stubs/react.js's createElement() trivial (no per-type logic).
export const Group = 'Group';
export const Rect = 'Rect';
export const Circle = 'Circle';
export const Path = 'Path';
export const Line = 'Line';
export const Text = 'Text';
export const Arc = 'Arc';
export const Wedge = 'Wedge';
export const RegularPolygon = 'RegularPolygon';
export const Ring = 'Ring';
export const Star = 'Star';
export const Ellipse = 'Ellipse';
