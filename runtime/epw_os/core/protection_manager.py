from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class ProtectionStage:
    name: str
    enabled: bool = True
    setting: float = 0.0
    hysteresis: Optional[float] = None
    delay_ms: int = 0
    action: str = "TRIP"  # Disabled, Information, Warning, Trip, Custom Logic
    
    # Live status
    status: str = "READY"
    pickups: int = 0
    trips: int = 0
    last_pickup: str = "N/A"
    last_trip: str = "N/A"
    operating_time: str = "0 ms"

@dataclass
class ProtectionFunction:
    id: str
    source: str
    category: str
    unit: str
    stages: List[ProtectionStage] = field(default_factory=list)

class ProtectionManager:
    def __init__(self):
        self.protections = {}
        self.init_defaults()
        
    def add_prot(self, cat, pid, source, unit, stages):
        self.protections[pid] = ProtectionFunction(
            id=pid,
            source=source,
            category=cat,
            unit=unit,
            stages=stages
        )

    def init_defaults(self):
        # Voltage
        self.add_prot("Voltage", "27 Under Voltage", "Voltage", "V", [
            ProtectionStage("Stage 1", setting=200.0, hysteresis=5.0, delay_ms=5000, action="Warning"),
            ProtectionStage("Stage 2", setting=180.0, hysteresis=5.0, delay_ms=500, action="Trip")
        ])
        self.add_prot("Voltage", "59 Over Voltage", "Voltage", "V", [
            ProtectionStage("Stage 1", setting=245.0, hysteresis=5.0, delay_ms=5000, action="Warning"),
            ProtectionStage("Stage 2", setting=255.0, hysteresis=5.0, delay_ms=100, action="Trip")
        ])
        self.add_prot("Voltage", "59N Neutral Overvoltage", "Voltage N", "V", [
            ProtectionStage("Stage 1", setting=20.0, hysteresis=2.0, delay_ms=1000, action="Trip")
        ])
        self.add_prot("Voltage", "47 Phase Sequence / Phase Loss", "Sequence", "", [
            ProtectionStage("Stage 1", setting=0.0, hysteresis=0.0, delay_ms=500, action="Trip")
        ])
        
        # Frequency
        self.add_prot("Frequency", "81U Under Frequency", "Frequency", "Hz", [
            ProtectionStage("Stage 1", setting=49.5, hysteresis=0.1, delay_ms=1000, action="Warning"),
            ProtectionStage("Stage 2", setting=48.5, hysteresis=0.1, delay_ms=200, action="Trip")
        ])
        self.add_prot("Frequency", "81O Over Frequency", "Frequency", "Hz", [
            ProtectionStage("Stage 1", setting=50.5, hysteresis=0.1, delay_ms=1000, action="Warning"),
            ProtectionStage("Stage 2", setting=51.5, hysteresis=0.1, delay_ms=200, action="Trip")
        ])

        # Current
        self.add_prot("Current", "50 Instantaneous Overcurrent", "Current", "A", [
            ProtectionStage("Stage 1", setting=80.0, hysteresis=5.0, delay_ms=100, action="Trip"),
            ProtectionStage("Stage 2", setting=120.0, hysteresis=5.0, delay_ms=0, action="Trip")
        ])
        self.add_prot("Current", "51 Time Overcurrent", "Current", "A", [
            ProtectionStage("Stage 1", setting=50.0, hysteresis=2.0, delay_ms=1000, action="Warning"),
            ProtectionStage("Stage 2", setting=60.0, hysteresis=2.0, delay_ms=500, action="Trip")
        ])
        self.add_prot("Current", "46 Negative Sequence Current", "Current Neg", "A", [
            ProtectionStage("Stage 1", setting=10.0, hysteresis=1.0, delay_ms=1000, action="Trip")
        ])
        self.add_prot("Current", "49 Thermal Overload", "Thermal", "%", [
            ProtectionStage("Stage 1", setting=90.0, hysteresis=5.0, delay_ms=5000, action="Warning"),
            ProtectionStage("Stage 2", setting=100.0, hysteresis=2.0, delay_ms=1000, action="Trip")
        ])
        self.add_prot("Current", "50N Earth Fault Instantaneous", "Current N", "A", [
            ProtectionStage("Stage 1", setting=20.0, hysteresis=1.0, delay_ms=0, action="Trip")
        ])
        self.add_prot("Current", "51N Earth Fault Time", "Current N", "A", [
            ProtectionStage("Stage 1", setting=10.0, hysteresis=1.0, delay_ms=1000, action="Trip")
        ])

        # Power/Supply
        self.add_prot("Power/Supply", "Control Voltage Loss", "Control V", "V", [
            ProtectionStage("Stage 1", setting=20.0, hysteresis=1.0, delay_ms=100, action="Trip")
        ])
        self.add_prot("Power/Supply", "Technical Supply Loss", "Tech V", "V", [
            ProtectionStage("Stage 1", setting=200.0, hysteresis=5.0, delay_ms=500, action="Warning")
        ])
        self.add_prot("Power/Supply", "UPS Supply Loss", "UPS V", "V", [
            ProtectionStage("Stage 1", setting=200.0, hysteresis=5.0, delay_ms=500, action="Warning")
        ])

        # Task (page-split): the old "Environmental"/"Communication"/
        # "System" categories that used to live here are REMOVED, not
        # relocated - they were pure facades. Every stage's "Actual
        # Value" column always showed a static "---" placeholder and
        # on_tag_changed() never mapped any of them to a real tag (see
        # page_protection.py's own removed comment to that effect) - no
        # stage here was EVER bound to a live reading or evaluated
        # against one. None of them fit either new "Zabezpieczenia"
        # page cleanly (Environmental's *shape* resembles a process
        # threshold, but as static templates with no real analog point
        # behind them they cannot simply be "moved" onto the new,
        # from-scratch Process Protections page, which only ever binds
        # to a REAL point from the Analog Inputs manager - see
        # process_protection_manager.py; Communication/System are
        # neither electrical nor process protections at all). Per this
        # project's own established rule (Environment/Lighting pages,
        # interlock_engine.py) a facade in the UI is a bug, not a
        # feature to carry forward - confirmed via a full-codebase
        # search that none of the 14 removed stage names appears
        # anywhere outside this file (no test, no other module, no
        # live tag). See SESSION_REPORT.md for the itemized list.
