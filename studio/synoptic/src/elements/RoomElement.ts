// The room record (ZADANIA p. 6): what the room enclosed by a chain of
// walls is called and which project location it belongs to - ONE record
// per room, referenced by every wall of the room through
// WallElement.roomId. Geometry stays on the walls (a room is what they
// close - project/RoomFloors.ts); nothing here draws. Its own array in
// the store, in every history snapshot and in each screen's content,
// like the other project-level elements. See project/Rooms.ts for the
// rules that keep records and walls together.
export interface RoomElement {
  id: string;
  name: string;       // 'Kotlownia' - shown on the floor, '' = unnamed
  location: string;   // a project location code ('KOT'), '' = none
}
