import type { StateCreator } from 'zustand';
import { effectiveSize, isOpeningFlipped, isOpeningType, objectCenter, seatOpeningInWall, topLeftForCenter } from '../project/WallOpenings';
import type { AppState } from './appState';

// Layout/arrangement operations over the current object selection
// (z-order, align, distribute, lock, rotate) - each one is a single
// set() over `objects` followed by one saveHistory() call, no state of
// its own.
export type LayoutSlice = Pick<AppState,
  | 'bringToFront' | 'sendToBack'
  | 'alignSelected' | 'distributeSelected'
  | 'lockSelected' | 'unlockSelected'
  | 'rotateSelected'
>;

export const createLayoutSlice: StateCreator<AppState, [], [], LayoutSlice> = (set, get) => ({
  bringToFront: () => {
    const { objects, selectedIds } = get();
    if (selectedIds.length === 0) return;

    const maxZ = Math.max(...objects.map(o => o.zIndex || 0), 0);
    const newObjects = objects.map(o => selectedIds.includes(o.id) ? { ...o, zIndex: maxZ + 1 } : o);

    set({ objects: newObjects, isDirty: true });
    get().saveHistory();
  },

  sendToBack: () => {
    const { objects, selectedIds } = get();
    if (selectedIds.length === 0) return;

    const minZ = Math.min(...objects.map(o => o.zIndex || 0), 0);
    const newObjects = objects.map(o => selectedIds.includes(o.id) ? { ...o, zIndex: minZ - 1 } : o);

    set({ objects: newObjects, isDirty: true });
    get().saveHistory();
  },

  alignSelected: (alignment) => {
    const { objects, selectedIds } = get();
    if (selectedIds.length < 2) return;

    const selected = objects.filter(obj => selectedIds.includes(obj.id));
    let target = 0;

    switch(alignment) {
      case 'left': target = Math.min(...selected.map(o => o.x)); break;
      case 'right': target = Math.max(...selected.map(o => o.x + o.width * o.scaleX)); break;
      case 'top': target = Math.min(...selected.map(o => o.y)); break;
      case 'bottom': target = Math.max(...selected.map(o => o.y + o.height * o.scaleY)); break;
      case 'center':
        target = selected.reduce((sum, o) => sum + o.x + (o.width * o.scaleX)/2, 0) / selected.length;
        break;
      case 'middle':
        target = selected.reduce((sum, o) => sum + o.y + (o.height * o.scaleY)/2, 0) / selected.length;
        break;
    }

    set({
      objects: objects.map(obj => {
        if (!selectedIds.includes(obj.id)) return obj;
        if (['left', 'center', 'right'].includes(alignment)) {
           const newX = alignment === 'center' ? target - (obj.width * obj.scaleX)/2 : alignment === 'right' ? target - obj.width * obj.scaleX : target;
           return { ...obj, x: newX };
        } else {
           const newY = alignment === 'middle' ? target - (obj.height * obj.scaleY)/2 : alignment === 'bottom' ? target - obj.height * obj.scaleY : target;
           return { ...obj, y: newY };
        }
      })
    });
    get().saveHistory();
  },

  distributeSelected: (axis) => {
    const { objects, selectedIds } = get();
    if (selectedIds.length < 3) return;

    const selected = objects.filter(obj => selectedIds.includes(obj.id));

    if (axis === 'horizontal') {
      selected.sort((a, b) => a.x - b.x);
      const min = selected[0].x;
      const max = selected[selected.length-1].x;
      const step = (max - min) / (selected.length - 1);

      set({
        objects: objects.map(obj => {
          const idx = selected.findIndex(s => s.id === obj.id);
          if (idx <= 0 || idx >= selected.length - 1) return obj;
          return { ...obj, x: min + idx * step };
        })
      });
    } else {
      selected.sort((a, b) => a.y - b.y);
      const min = selected[0].y;
      const max = selected[selected.length-1].y;
      const step = (max - min) / (selected.length - 1);

      set({
        objects: objects.map(obj => {
          const idx = selected.findIndex(s => s.id === obj.id);
          if (idx <= 0 || idx >= selected.length - 1) return obj;
          return { ...obj, y: min + idx * step };
        })
      });
    }
    get().saveHistory();
  },

  lockSelected: () => {
    const { selectedIds } = get();
    if (selectedIds.length === 0) return;
    set((state) => ({
      objects: state.objects.map(obj => selectedIds.includes(obj.id) ? { ...obj, locked: true } : obj)
    }));
    get().saveHistory();
  },

  unlockSelected: () => {
    const { selectedIds } = get();
    if (selectedIds.length === 0) return;
    set((state) => ({
      objects: state.objects.map(obj => selectedIds.includes(obj.id) ? { ...obj, locked: false } : obj)
    }));
    get().saveHistory();
  },

  rotateSelected: (direction: 'cw' | 'ccw') => {
    const { selectedIds, walls } = get();
    if (selectedIds.length === 0) return;
    set((state) => ({
      objects: state.objects.map(obj => {
        if (!selectedIds.includes(obj.id)) return obj;
        // ABOUT ITS CENTRE. Konva turns a group about its origin (the
        // top-left), so changing `rotation` alone swung a symbol around
        // its corner - a door rotated on its wall walked off the wall and
        // its doorway moved with the new centre (user, 2026-09-18). The
        // centre is kept and the origin moved to where that centre needs
        // it, exactly what topLeftForCenter is for.
        const center = objectCenter(obj);
        const { width, height } = effectiveSize(obj);
        const currentRotation = obj.rotation || 0;
        // An opening turns by flipping its hinge/swing side whichever way
        // is asked: on its wall that is the only meaningful turn, and
        // seatOpeningInWall keeps it on the wall in that orientation
        // (editor.opening_flipped, so a fresh door and a flipped one are
        // never confused by their angle alone).
        if (isOpeningType(obj.type)) {
          const flipped = { ...obj, editor: { ...(obj.editor || {}), opening_flipped: !isOpeningFlipped(obj) } };
          const seat = seatOpeningInWall(walls, flipped);
          if (seat) return { ...flipped, ...seat };
          const turned = currentRotation + 180;
          return { ...flipped, ...topLeftForCenter(center, width, height, turned), rotation: turned };
        }
        const newRotation = currentRotation + (direction === 'cw' ? 90 : -90);
        return { ...obj, ...topLeftForCenter(center, width, height, newRotation), rotation: newRotation };
      })
    }));
    get().saveHistory();
  }
});
