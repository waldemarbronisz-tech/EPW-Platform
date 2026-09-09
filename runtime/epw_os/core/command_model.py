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
