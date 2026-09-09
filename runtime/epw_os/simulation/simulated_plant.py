import threading

class SimulatedPlant:
    def __init__(self, event_bus, mappings=None):
        self.event_bus = event_bus
        self.mappings = mappings or {}
        self.event_bus.subscribe("driver_update", self._on_driver_update)

    def _on_driver_update(self, tag_name, value, quality):
        mapping = self.mappings.get(tag_name)
        if mapping is None:
            return

        if value != mapping.get("trigger_value", True):
            return

        delay = mapping.get("delay_ms", 0)
        
        def publish():
            self.event_bus.emit(
                "driver_update",
                mapping["feedback_tag"],
                mapping.get("feedback_value", True),
                "GOOD"
            )
            
        if delay > 0:
            timer = threading.Timer(delay / 1000.0, publish)
            timer.start()
        else:
            publish()
