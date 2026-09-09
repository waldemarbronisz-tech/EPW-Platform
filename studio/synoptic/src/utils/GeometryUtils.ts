import type { SynopticObject } from '../store';
import { getSymbolDefinition } from '../symbols/SymbolRegistry';
import type { ConnectionPoint } from '../symbols/SymbolRegistry';
import { getBoundaryPortFraction } from '../symbols/scada/BoundaryPointSymbol';
import type { BoundaryPortSide } from '../symbols/scada/BoundaryPointSymbol';

export const resolveConnectionPoint = (obj: SynopticObject, portId: string): ConnectionPoint | null => {
  const def = getSymbolDefinition(obj.type);
  if (!def) return null;

  // Normal port
  let port = def.connectionPoints?.find(p => p.id === portId);

  // Dynamic port (busbars, etc). Two id formats:
  //  - 'dyn_NN' (legacy): a single row through the vertical/horizontal
  //    center, inferred from aspect ratio - unchanged since this was
  //    introduced, still what the original electrical.busbar produces.
  //  - 'dyn_top_NN' / 'dyn_bot_NN': a row along the top or bottom edge -
  //    added for the SCADA busbar, which accepts connections on either
  //    side of its length, not just through the middle.
  if (!port && portId.startsWith('dyn_')) {
    if (!def.supportsDynamicPorts) return null;

    const edgeMatch = portId.match(/^dyn_(top|bot)_(\d+)$/);
    const centerMatch = portId.match(/^dyn_(\d+)$/);

    let posPercent: number;
    let yFraction: number | null = null; // null = infer from aspect ratio, like the legacy format always has

    if (edgeMatch) {
      posPercent = parseInt(edgeMatch[2], 10);
      yFraction = edgeMatch[1] === 'top' ? 0 : 1;
    } else if (centerMatch) {
      posPercent = parseInt(centerMatch[1], 10);
    } else {
      return null;
    }

    if (isNaN(posPercent) || posPercent < 0 || posPercent > 100) return null;
    const pos = posPercent / 100;

    // Prefer the object's own current width/height over the symbol
    // definition's static default - a resizable busbar's actual width
    // can differ from it, and using the default here would place ports
    // as if the bar were still its original size.
    const w = obj.width || def.defaultWidth || 80;
    const h = obj.height || def.defaultHeight || 80;

    if (yFraction !== null) {
      port = { id: portId, x: pos, y: yFraction, domain: 'electrical', medium: 'electrical_ac', direction: 'passive', multiplicity: 'multiple' };
    } else if (w >= h) {
      port = { id: portId, x: pos, y: 0.5, domain: 'electrical', medium: 'electrical_ac', direction: 'passive', multiplicity: 'multiple' };
    } else {
      port = { id: portId, x: 0.5, y: pos, domain: 'electrical', medium: 'electrical_ac', direction: 'passive', multiplicity: 'multiple' };
    }
  }

  // Boundary point (scada.boundary_point): exactly one port, whose side
  // is a per-instance property (boundaryPortSide) rather than something
  // fixed in the registry - so, like the dynamic ports above, it is
  // resolved here instead of listed in def.connectionPoints. Not part of
  // the dyn_ family above: it is a single fixed id, not a percentage
  // along a length.
  if (!port && portId === 'PORT' && obj.type === 'scada.boundary_point') {
    const side: BoundaryPortSide =
      obj.boundaryPortSide === 'BOTTOM' || obj.boundaryPortSide === 'LEFT' || obj.boundaryPortSide === 'RIGHT'
        ? obj.boundaryPortSide
        : 'TOP';
    const { x, y } = getBoundaryPortFraction(side);
    const isWater = obj.boundaryMedium === 'WATER';
    port = {
      id: portId,
      x,
      y,
      domain: isWater ? 'water' : 'electrical',
      medium: isWater ? 'water' : 'electrical_ac',
      direction: obj.boundaryDirection === 'SINK' ? 'in' : 'out',
      multiplicity: 'multiple'
    };
  }

  return port || null;
};

export const getAbsolutePortPosition = (obj: SynopticObject, port: ConnectionPoint) => {
  const w = obj.width * (obj.scaleX || 1);
  const h = obj.height * (obj.scaleY || 1);

  const cx = port.x * w - w / 2;
  const cy = port.y * h - h / 2;

  const rot = obj.rotation || 0;
  const radians = rot * (Math.PI / 180);

  const rx = cx * Math.cos(radians) - cy * Math.sin(radians);
  const ry = cx * Math.sin(radians) + cy * Math.cos(radians);

  return {
    x: obj.x + w / 2 + rx,
    y: obj.y + h / 2 + ry
  };
};

export const getPortWorldDirection = (obj: SynopticObject, port: ConnectionPoint) => {
  // Base local direction
  let dx = 0;
  let dy = 0;
  if (port.y === 0) dy = -1;
  else if (port.y === 1) dy = 1;
  else if (port.x === 0) dx = -1;
  else if (port.x === 1) dx = 1;

  if (dx === 0 && dy === 0) {
    if (port.x < 0.25) dx = -1;
    else if (port.x > 0.75) dx = 1;
    else if (port.y < 0.25) dy = -1;
    else if (port.y > 0.75) dy = 1;
  }

  // Rotate it
  const rot = obj.rotation || 0;
  const radians = rot * (Math.PI / 180);
  const worldDx = dx * Math.cos(radians) - dy * Math.sin(radians);
  const worldDy = dx * Math.sin(radians) + dy * Math.cos(radians);

  return {
    x: Math.abs(worldDx) > 0.5 ? Math.sign(worldDx) : 0,
    y: Math.abs(worldDy) > 0.5 ? Math.sign(worldDy) : 0
  };
};

export const calculateOrthogonalPath = (x1: number, y1: number, x2: number, y2: number, fromPortDir: {x:number, y:number}, toPortDir: {x:number, y:number}) => {
  const dx = Math.abs(x2 - x1);
  const dy = Math.abs(y2 - y1);

  if (dx < 5) return `M ${x1} ${y1} L ${x1} ${y2}`;
  if (dy < 5) return `M ${x1} ${y1} L ${x2} ${y1}`;

  if (fromPortDir.y !== 0 || toPortDir.y !== 0) {
     const midY = y1 + (y2 - y1) / 2;
     return `M ${x1} ${y1} L ${x1} ${midY} L ${x2} ${midY} L ${x2} ${y2}`;
  }
  if (fromPortDir.x !== 0 || toPortDir.x !== 0) {
     const midX = x1 + (x2 - x1) / 2;
     return `M ${x1} ${y1} L ${midX} ${y1} L ${midX} ${y2} L ${x2} ${y2}`;
  }

  if (dy > dx) {
    const midY = y1 + (y2 - y1) / 2;
    return `M ${x1} ${y1} L ${x1} ${midY} L ${x2} ${midY} L ${x2} ${y2}`;
  } else {
    const midX = x1 + (x2 - x1) / 2;
    return `M ${x1} ${y1} L ${midX} ${y1} L ${midX} ${y2} L ${x2} ${y2}`;
  }
};