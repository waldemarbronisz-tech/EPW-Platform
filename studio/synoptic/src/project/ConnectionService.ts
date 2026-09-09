import { resolveConnectionPoint } from '../utils/GeometryUtils';
import type { SynopticObject } from '../store';
import { getSymbolDefinition } from '../symbols/SymbolRegistry';
import { getMediaDefinition } from '../symbols/registry/MediaRegistry';

export interface ValidationResult {
  valid: boolean;
  code?: string;
  message?: string;
  inferredType?: string;
}

export class ConnectionService {
  static validateConnection(
    fromObj: SynopticObject,
    fromPortId: string,
    toObj: SynopticObject,
    toPortId: string,
    existingConnections: any[]
  ): ValidationResult {
    if (!fromObj || !toObj) return { valid: false, code: "MISSING_OBJECT", message: "Source or target object missing" };

    if (fromObj.id === toObj.id) return { valid: false, code: "SELF_CONNECTION", message: "Cannot connect an object to itself" };

    const fromPort = resolveConnectionPoint(fromObj, fromPortId);
    const toPort = resolveConnectionPoint(toObj, toPortId);

    if (!fromPort) return { valid: false, code: "MISSING_PORT", message: `Source port ${fromPortId} not found` };
    if (!toPort) return { valid: false, code: "MISSING_PORT", message: `Target port ${toPortId} not found` };

    // Dynamic port bounds checking
    const fromDef = getSymbolDefinition(fromObj.type);
    const toDef = getSymbolDefinition(toObj.type);

    if (fromPortId.startsWith('dyn_') && !fromDef?.supportsDynamicPorts) {
      return { valid: false, code: "DYN_UNSUPPORTED", message: "Source object does not support dynamic ports" };
    }
    if (toPortId.startsWith('dyn_') && !toDef?.supportsDynamicPorts) {
      return { valid: false, code: "DYN_UNSUPPORTED", message: "Target object does not support dynamic ports" };
    }

    // Media and Domain compatibility
    if (fromPort.domain !== toPort.domain) {
      return { valid: false, code: "DOMAIN_MISMATCH", message: `Cannot connect ${fromPort.domain} to ${toPort.domain}` };
    }

    if (fromPort.medium && !getMediaDefinition(fromPort.medium)) {
      return { valid: false, code: "UNKNOWN_MEDIUM", message: `Unknown medium: ${fromPort.medium}` };
    }
    if (toPort.medium && !getMediaDefinition(toPort.medium)) {
      return { valid: false, code: "UNKNOWN_MEDIUM", message: `Unknown medium: ${toPort.medium}` };
    }

    if (fromPort.medium && toPort.medium && fromPort.medium !== toPort.medium) {
      return { valid: false, code: "MEDIUM_MISMATCH", message: `Cannot connect ${fromPort.medium} to ${toPort.medium}` };
    }

    // Direction validation
    if (fromPort.direction === 'in' && toPort.direction === 'in') {
      return { valid: false, code: "DIRECTION_MISMATCH", message: "Cannot connect IN to IN" };
    }
    if (fromPort.direction === 'out' && toPort.direction === 'out') {
      return { valid: false, code: "DIRECTION_MISMATCH", message: "Cannot connect OUT to OUT" };
    }

    // Bug fix (usterka: "Source/Target port is already occupied" blocked
    // any real schematic - several circuits leave one feed, several
    // wires land on one node). A port now accepts any number of wires;
    // the multiplicity check that used to reject a second connection on
    // the same port here has been removed entirely. Every other rule
    // above and below (domain, medium, direction, self-connection,
    // duplicates) is unchanged.

    // Duplicate connections check
    const duplicate = existingConnections.find(c =>
      (c.fromId === fromObj.id && c.fromPort === fromPortId && c.toId === toObj.id && c.toPort === toPortId) ||
      (c.fromId === toObj.id && c.fromPort === toPortId && c.toId === fromObj.id && c.toPort === fromPortId)
    );
    if (duplicate) {
      return { valid: false, code: "DUPLICATE_CONNECTION", message: "Connection already exists" };
    }

    // Infer connection type
    let inferredType = 'electrical_ac';
    if (fromPort.medium) inferredType = fromPort.medium;
    else if (toPort.medium) inferredType = toPort.medium;
    else if (fromPort.domain === 'water') inferredType = 'water';
    else if (fromPort.domain === 'hvac') inferredType = 'hvac_air';
    else if (fromPort.domain === 'data' || fromPort.domain === 'control') inferredType = 'data'; // fallback

    return { valid: true, inferredType };
  }

  // tryCreateConnection (used to build a port-pair SynopticConnection
  // and addConnection() it) is gone - the node-based wiring model has no
  // ports to pair up, so there is nothing left for it to do. Wire
  // creation now happens directly in Canvas.tsx's freehand drawing tool,
  // which posts its own readable, UUID-free Messages entry when a wire
  // is finished (see describeObject usage there). validateConnection
  // above is kept: it is still a useful, independently-testable port-
  // compatibility check (domain/medium/direction/self-connection), even
  // though nothing in the live app feeds it real connections any more.
}
