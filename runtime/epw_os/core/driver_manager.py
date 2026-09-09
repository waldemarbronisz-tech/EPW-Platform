from typing import Dict, Optional, Any
from epw_os.core.events import EventBus
from epw_os.drivers.base_driver import BaseDriver
from epw_os.core.logging import log

class DriverManager:
    def __init__(self, event_bus: EventBus, training_mode=None):
        self.event_bus = event_bus
        self.drivers: Dict[str, BaseDriver] = {}
        self.is_running = False
        # Optional epw_os.core.training_mode.TrainingModeManager - see
        # route_command() below, the actual driver-layer cutoff point
        # (Task: tryb cwiczebny). None outside EPWCore (e.g. isolated
        # tests constructing a bare DriverManager) simply means route_command()
        # always behaves exactly as it did before this feature existed.
        self.training_mode = training_mode

        # Subscribe to driver updates
        self.event_bus.subscribe("driver_update", self._on_driver_update)

    def _on_driver_update(self, tag_name: str, value: Any, quality: str):
        self.event_bus.emit("driver_to_tag", tag_name, value, quality)

    def register_driver(self, driver_id: str, driver: BaseDriver):
        self.drivers[driver_id] = driver
        log.info(f"Driver registered: {driver_id}")

    def get_driver(self, driver_id: str) -> Optional[BaseDriver]:
        return self.drivers.get(driver_id)

    def route_command(self, driver_id: str, output_tag: str, value: Any) -> bool:
        """The driver layer's own boundary - the one and only place a
        command actually reaches a driver instance. This is deliberately
        where Training Mode cuts the connection (GRANICE: "odciecie ma
        nastepowac na granicy warstwy sterownikow, NIE przez omijanie
        sprawdzen uprawnien czy blokad") - CommandManager.request_command_ex()
        calls this exact method the same way whether Training Mode is
        active or not; everything upstream of it (safety_kernel,
        logic_engine, the access-level gate the GUI applies before ever
        calling into CommandManager) is completely unaware this check
        exists and runs unchanged.

        When active, the real driver is never looked up and
        driver.write_tag() is never called - the command genuinely does
        not reach it, not merely "reaches it but is told to do nothing"
        (SimulatorDriver.write_tag() itself is untouched by this feature,
        per GRANICE). Instead this emits the exact same "driver_update"
        event a real write_tag() would have emitted, so the rest of the
        pipeline - the TagManager bridge that makes the device "change
        state" on screen, and SimulatedPlant's own feedback simulation -
        runs exactly as it always does (Task: "sprzezenie zwrotne
        symulowane, zeby interfejs zachowywal sie realistycznie"), and
        the caller sees the same True it would see from a real
        successful write, regardless of whether any real driver is even
        registered or running."""
        if self.training_mode is not None and self.training_mode.active:
            log.info(f"[TRAINING MODE] Command suppressed at the driver boundary: "
                     f"{output_tag} = {value} (driver_id={driver_id}) - never reached a driver.")
            self.event_bus.emit("driver_update", output_tag, value, "GOOD")
            return True
        driver = self.get_driver(driver_id)
        if driver and driver.is_running:
            return driver.write_tag(output_tag, value)
        log.error(f"Cannot route command {output_tag} to {driver_id}: driver not running or not found")
        return False
        
    def all_required_running(self) -> bool:
        return all(driver.is_running for driver in self.drivers.values())

    def start_all(self):
        self.is_running = True
        for name, driver in self.drivers.items():
            driver.start()
            
    def stop_all(self):
        self.is_running = False
        for name, driver in self.drivers.items():
            driver.stop()
