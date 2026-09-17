// Every react-konva primitive becomes its own name as a plain string
// element type - the exporter's tree walker switches on that name.
// Anything not listed here would surface as an unknown primitive in the
// output (recorded, never dropped), so this list is complete on purpose
// for what the symbol library uses today: see export.mjs's PRIMITIVES.
export const Group = 'Group';
export const Rect = 'Rect';
export const Circle = 'Circle';
export const Ellipse = 'Ellipse';
export const Path = 'Path';
export const Line = 'Line';
export const Text = 'Text';
export const Arc = 'Arc';
export const Wedge = 'Wedge';
export const RegularPolygon = 'RegularPolygon';
export const Ring = 'Ring';
export const Star = 'Star';
export const Shape = 'Shape';
export const Image = 'Image';
export const Label = 'Label';
export const Tag = 'Tag';
export const Layer = 'Layer';
export const Stage = 'Stage';
