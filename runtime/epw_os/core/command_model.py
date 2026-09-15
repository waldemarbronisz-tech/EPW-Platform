from dataclasses import dataclass
from typing import Any, Optional

@dataclass(frozen=True)
class CommandDefinition:
    command_id: str
    target: str
    action: str
    driver_id: str
    output_tag: str
    output_value: Any
    pulse_ms: Optional[int] = None
    feedback_tag: Optional[str] = None
    feedback_value: Any = None
    timeout_ms: int = 1500
    # Task "wyłącznik jednocewkowy bistabilny" (single-coil impulse relay:
    # the SAME +24 V pulse both closes and opens). Such a coil must only
    # be pulsed when the apparatus is NOT already in the requested state -
    # pulsing an already-closed relay would open it. When True,
    # CommandManager checks `feedback_tag` first and resolves the command
    # as SUCCESS without touching the output if it already equals
    # `feedback_value`. See apparatus.apparatus_command_definitions().
    skip_when_feedback_matches: bool = False
    # Two maintained coils (a three-position valve: separate OPEN/CLOSE
    # coils held energized) - the OTHER coil is released (written False)
    # before this command's own output is energized, so both are never
    # on at once.
    also_reset_tag: Optional[str] = None

@dataclass
class CommandRecord:
    id: str
    definition: CommandDefinition
    state: str
    requested_at: float
    dispatched_at: Optional[float] = None
    completed_at: Optional[float] = None
    user: str = ""
    source: str = ""
    reason: str = ""
