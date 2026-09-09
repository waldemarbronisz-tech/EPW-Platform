from PySide6.QtCore import QObject, Signal
from datetime import datetime
from epw_os.core.logging import log

class UILogger(QObject):
    # Timestamp, Priority, Group, Object, Event, User, Mode, Result
    log_event = Signal(str, str, str, str, str, str, str, str)

    def log(self, priority, group, obj, event, user, mode, result):
        t_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.log_event.emit(t_timestamp, priority, group, obj, event, user, mode, result)

ui_logger = UILogger()
