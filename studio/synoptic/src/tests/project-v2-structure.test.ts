import { describe, it, expect } from 'vitest';
import { validateProjectV2 } from '../project/ProjectV2Validation';

/**
 * Minimal valid EPW Project v2: one location, one DI card, one DO card,
 * one SWITCHED device, one main screen. Each test mutates its own fresh
 * copy - loosely typed (any) so tests can deliberately introduce shape
 * violations (wrong types, missing fields) without fighting TypeScript.
 */
function makeMinimalProject(): any {
  return {
    format: 'EPW_PROJECT',
    schema_version: 2,
    project: {
      name: 'Test Project',
      description: '',
      created_at: '2026-01-01T00:00:00.000Z',
      modified_at: '2026-01-01T00:00:00.000Z'
    },
    controller: { id: 'PLC1', name: 'Main PLC', hardware: 'EPW Core' },
    symbolLibrary: 'default',
    devices: {
      locations: [{ code: 'KOT', description: 'Kotlownia' }],
      cards: [
        { id: 'ELA1', model: 'ELA01', channelKind: 'DI', channelCount: 64 },
        { id: 'ADA1', model: 'ADA01', channelKind: 'DO', channelCount: 60 }
      ],
      devices: [
        {
          id: 'KOT_KMG1',
          designation: '-K1',
          name: 'Stycznik grzalki',
          behavior: 'SWITCHED',
          kind: 'contactor',
          publishToHa: false,
          feedback: { mode: 'DUAL', diClosed: 'ELA1.DI.1', diOpen: 'ELA1.DI.2' },
          command: { outputCount: 2, style: 'PULSE', doClose: 'ADA1.DO.1', doOpen: 'ADA1.DO.2', pulseMs: 500 },
          supervision: { confirmTimeoutMs: 2000, discrepancyAlarm: true },
          safeState: { onStartup: 'NO_CHANGE', onLinkLoss: 'NO_CHANGE' },
          switchCounter: false
        }
      ]
    },
    screens: [
      {
        id: 'MAIN',
        name: 'Main View',
        isMain: true,
        canvas: { width: 1920, height: 1080, background: '#ffffff', gridSize: 20 },
        backdrop: [],
        items: [],
        connections: [],
        navigation: []
      }
    ]
  };
}

describe('Project v2 structure (validateProjectV2)', () => {
  it('1. a minimal valid v2 project has zero errors', () => {
    const result = validateProjectV2(makeMinimalProject());
    expect(result.valid).toBe(true);
    expect(result.issues).toEqual([]);
  });

  it('2. a format other than EPW_PROJECT is an error', () => {
    const project = makeMinimalProject();
    project.format = 'SOMETHING_ELSE';
    expect(validateProjectV2(project).valid).toBe(false);
  });

  it('3. schema_version 1 is an error', () => {
    const project = makeMinimalProject();
    project.schema_version = 1;
    expect(validateProjectV2(project).valid).toBe(false);
  });

  it('4. an empty project.name is an error', () => {
    const project = makeMinimalProject();
    project.project.name = '';
    expect(validateProjectV2(project).valid).toBe(false);
  });

  it('5. controller.id with a lowercase letter is an error', () => {
    const project = makeMinimalProject();
    project.controller.id = 'plc1';
    expect(validateProjectV2(project).valid).toBe(false);
  });

  it('6. controller.id with a hyphen is an error', () => {
    const project = makeMinimalProject();
    project.controller.id = 'PLC-1';
    expect(validateProjectV2(project).valid).toBe(false);
  });

  it('7. zero screens with isMain true is an error', () => {
    const project = makeMinimalProject();
    project.screens[0].isMain = false;
    expect(validateProjectV2(project).valid).toBe(false);
  });

  it('8. two screens with isMain true is an error', () => {
    const project = makeMinimalProject();
    project.screens.push({ ...project.screens[0], id: 'SECOND' });
    expect(validateProjectV2(project).valid).toBe(false);
  });

  it('9. two screens with the same id is an error', () => {
    const project = makeMinimalProject();
    project.screens.push({ ...project.screens[0], isMain: false });
    expect(validateProjectV2(project).valid).toBe(false);
  });

  it('10. an empty screen name is an error', () => {
    const project = makeMinimalProject();
    project.screens[0].name = '';
    expect(validateProjectV2(project).valid).toBe(false);
  });

  it('11. canvas.width of zero is an error', () => {
    const project = makeMinimalProject();
    project.screens[0].canvas.width = 0;
    expect(validateProjectV2(project).valid).toBe(false);
  });

  it('12. canvas.gridSize of zero is an error', () => {
    const project = makeMinimalProject();
    project.screens[0].canvas.gridSize = 0;
    expect(validateProjectV2(project).valid).toBe(false);
  });

  it('13. a screen with group set to text is valid', () => {
    const project = makeMinimalProject();
    project.screens[0].group = 'Elektryka';
    expect(validateProjectV2(project).valid).toBe(true);
  });

  it('14. a screen without a group field is valid', () => {
    const project = makeMinimalProject();
    delete project.screens[0].group;
    expect(validateProjectV2(project).valid).toBe(true);
  });

  it('15. a screen with group set to an empty string is an error', () => {
    const project = makeMinimalProject();
    project.screens[0].group = '';
    expect(validateProjectV2(project).valid).toBe(false);
  });

  it('16. a project with 12 screens has zero errors (no limit on screen count)', () => {
    const project = makeMinimalProject();
    for (let i = 0; i < 11; i++) {
      project.screens.push({
        id: `SCREEN_${i}`,
        name: `Screen ${i}`,
        isMain: false,
        canvas: { width: 1920, height: 1080, background: '#ffffff', gridSize: 20 },
        backdrop: [],
        items: [],
        connections: [],
        navigation: []
      });
    }
    expect(project.screens.length).toBe(12);
    const result = validateProjectV2(project);
    expect(result.valid).toBe(true);
    expect(result.issues).toEqual([]);
  });

  it('17. a WALL with identical from and to points is an error', () => {
    const project = makeMinimalProject();
    project.screens[0].backdrop.push({ id: 'W1', type: 'WALL', from: { x: 0, y: 0 }, to: { x: 0, y: 0 } });
    expect(validateProjectV2(project).valid).toBe(false);
  });

  it('18. a ROOM with 2 points is an error', () => {
    const project = makeMinimalProject();
    project.screens[0].backdrop.push({ id: 'R1', type: 'ROOM', points: [{ x: 0, y: 0 }, { x: 10, y: 0 }], name: 'Room' });
    expect(validateProjectV2(project).valid).toBe(false);
  });

  it('19. a ROOM with 3 points is valid', () => {
    const project = makeMinimalProject();
    project.screens[0].backdrop.push({ id: 'R1', type: 'ROOM', points: [{ x: 0, y: 0 }, { x: 10, y: 0 }, { x: 10, y: 10 }], name: 'Room' });
    expect(validateProjectV2(project).valid).toBe(true);
  });

  it('20. a TEXT with empty text is an error', () => {
    const project = makeMinimalProject();
    project.screens[0].backdrop.push({ id: 'T1', type: 'TEXT', x: 0, y: 0, text: '', fontSize: 12 });
    expect(validateProjectV2(project).valid).toBe(false);
  });

  it('21. a FRAME with width zero is an error', () => {
    const project = makeMinimalProject();
    project.screens[0].backdrop.push({ id: 'F1', type: 'FRAME', x: 0, y: 0, width: 0, height: 10 });
    expect(validateProjectV2(project).valid).toBe(false);
  });

  it('22. two backdrop elements with the same id on one screen is an error', () => {
    const project = makeMinimalProject();
    project.screens[0].backdrop.push({ id: 'X1', type: 'TEXT', x: 0, y: 0, text: 'A', fontSize: 12 });
    project.screens[0].backdrop.push({ id: 'X1', type: 'TEXT', x: 10, y: 10, text: 'B', fontSize: 12 });
    expect(validateProjectV2(project).valid).toBe(false);
  });

  it('23. a backdrop element with type BALLOON is an error', () => {
    const project = makeMinimalProject();
    project.screens[0].backdrop.push({ id: 'B1', type: 'BALLOON', x: 0, y: 0 });
    expect(validateProjectV2(project).valid).toBe(false);
  });
});

describe('Project v2 shape validation (validateProjectV2 against untrusted input)', () => {
  it('24. project === null is an error, not a crash', () => {
    expect(() => validateProjectV2(null)).not.toThrow();
    expect(validateProjectV2(null).valid).toBe(false);
  });

  it('25. project.screens === null is an error, not a crash', () => {
    const project = makeMinimalProject();
    project.screens = null;
    expect(() => validateProjectV2(project)).not.toThrow();
    expect(validateProjectV2(project).valid).toBe(false);
  });

  it('26. project.screens as an object instead of an array is an error, not a crash', () => {
    const project = makeMinimalProject();
    project.screens = { foo: 'bar' };
    expect(() => validateProjectV2(project)).not.toThrow();
    expect(validateProjectV2(project).valid).toBe(false);
  });

  it('27. a null screen inside the screens array is an error, not a crash', () => {
    const project = makeMinimalProject();
    project.screens.push(null);
    expect(() => validateProjectV2(project)).not.toThrow();
    expect(validateProjectV2(project).valid).toBe(false);
  });

  it('28. screen.items === undefined is an error, not a crash', () => {
    const project = makeMinimalProject();
    delete project.screens[0].items;
    expect(() => validateProjectV2(project)).not.toThrow();
    expect(validateProjectV2(project).valid).toBe(false);
  });

  it('29. isMain as the string "true" is an error', () => {
    const project = makeMinimalProject();
    project.screens[0].isMain = 'true';
    expect(validateProjectV2(project).valid).toBe(false);
  });

  it('30. canvas.width === NaN is an error', () => {
    const project = makeMinimalProject();
    project.screens[0].canvas.width = NaN;
    expect(validateProjectV2(project).valid).toBe(false);
  });

  it('31. project === an array is an error, not a crash', () => {
    expect(() => validateProjectV2([])).not.toThrow();
    expect(validateProjectV2([]).valid).toBe(false);
  });
});
