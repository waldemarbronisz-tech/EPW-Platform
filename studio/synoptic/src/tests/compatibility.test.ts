import { describe, it, expect, vi } from 'vitest';
import { ConnectionService } from '../project/ConnectionService';
import * as GeometryUtils from '../utils/GeometryUtils';
import type { SynopticObject } from '../store';

describe('Connection Compatibility Validator', () => {
  const mockWaterObj = { id: 'w1', type: 'water.pump' } as SynopticObject;
  const mockWaterObj2 = { id: 'w2', type: 'water.pump' } as SynopticObject;
  const mockElecObj = { id: 'e1', type: 'electrical.circuit_breaker' } as SynopticObject;
  const mockElecObj2 = { id: 'e2', type: 'electrical.circuit_breaker' } as SynopticObject;

  it('rejects cross-domain connections (water to electrical)', () => {
    const res = ConnectionService.validateConnection(mockWaterObj, 'IN', mockElecObj, 'IN', []);
    expect(res.valid).toBe(false);
    expect(res.code).toBe('DOMAIN_MISMATCH');
  });

  it('accepts valid intra-domain passive connections (electrical to electrical)', () => {
    const res = ConnectionService.validateConnection(mockElecObj, 'IN', mockElecObj2, 'OUT', []);
    expect(res.valid).toBe(true);
  });

  it('rejects IN -> IN direction mismatch', () => {
    const res = ConnectionService.validateConnection(mockWaterObj, 'IN', mockWaterObj2, 'IN', []);
    expect(res.valid).toBe(false);
    expect(res.code).toBe('DIRECTION_MISMATCH');
  });

  it('rejects OUT -> OUT direction mismatch', () => {
    const res = ConnectionService.validateConnection(mockWaterObj, 'OUT', mockWaterObj2, 'OUT', []);
    expect(res.valid).toBe(false);
    expect(res.code).toBe('DIRECTION_MISMATCH');
  });

  it('rejects self connections', () => {
    const res = ConnectionService.validateConnection(mockWaterObj, 'IN', mockWaterObj, 'OUT', []);
    expect(res.valid).toBe(false);
    expect(res.code).toBe('SELF_CONNECTION');
  });

  it('rejects connection if mediums do not match (e.g., ethernet and rs485)', () => {
    const fromObj = { id: 'obj1', type: 'automation.plc', x: 0, y: 0 } as any;
    const toObj = { id: 'obj2', type: 'automation.ada', x: 0, y: 0 } as any;
    
    // We are mocking this to pass standard bounds, the test relies on explicit validation code
    const spy = vi.spyOn(GeometryUtils, 'resolveConnectionPoint').mockImplementation((_obj: any, portId: string) => {
        if (portId === 'ETH') return { id: portId, x: 0, y: 0, domain: 'data', medium: 'ethernet', direction: 'passive' };
        if (portId === 'RS485') return { id: portId, x: 0, y: 0, domain: 'data', medium: 'rs485', direction: 'passive' };
        return { id: portId, x: 0, y: 0, domain: 'electrical', direction: 'passive' };
    });
    
    const res = ConnectionService.validateConnection(fromObj, 'ETH', toObj, 'RS485', []);
    expect(res.valid).toBe(false);
    expect(res.code).toBe('MEDIUM_MISMATCH');
    spy.mockRestore();
  });

  it('rejects unknown or invalid mediums', () => {
    const fromObj = { id: 'obj1', type: 'electrical.motor', x: 0, y: 0 } as any;
    const toObj = { id: 'obj2', type: 'electrical.motor', x: 0, y: 0 } as any;
    // mock unknown medium
    const spy = vi.spyOn(GeometryUtils, 'resolveConnectionPoint').mockImplementation((_obj: any, portId: string) => {
        return { id: portId, x: 0, y: 0, domain: 'electrical', medium: 'magical_unknown_power', direction: 'passive' };
    });
    
    const res = ConnectionService.validateConnection(fromObj, 'IN', toObj, 'IN', []);
    expect(res.valid).toBe(false);
    expect(res.code).toBe('UNKNOWN_MEDIUM');
    spy.mockRestore();
  });
});
