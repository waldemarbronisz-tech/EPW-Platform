from PySide6.QtWidgets import QTableWidgetItem

class EventTableItem(QTableWidgetItem):
    def __init__(self, text, col_type):
        super().__init__(text)
        self.col_type = col_type

    def __lt__(self, other):
        if not isinstance(other, EventTableItem):
            return super().__lt__(other)
            
        t1 = self.text()
        t2 = other.text()

        if self.col_type == "Priority":
            order = {"TRIP": 5, "FAULT": 4, "ALARM": 3, "WARNING": 2, "INFO": 1}
            return order.get(t1.upper(), 0) < order.get(t2.upper(), 0)
            
        if self.col_type == "Group":
            order = {"PROTECTION": 5, "OPERATION": 4, "AUTOMATION": 3, "ENVIRONMENT": 2, "SYSTEM": 1}
            return order.get(t1.upper(), 0) < order.get(t2.upper(), 0)
            
        # Default alphabetical or timestamp string sort
        return t1 < t2
