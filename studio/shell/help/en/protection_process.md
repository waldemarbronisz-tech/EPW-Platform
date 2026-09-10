# Process Protection

Unlike Electrical, this is a dynamic, user-created list — add a
protection, pick an analog point (from the Point Registry), and set
its **upper/lower threshold**, **hysteresis**, and **delay**.

The "En." checkbox in the table is the activity switch. The selected
row shows its full configuration on the right. Unlike Electrical, these
thresholds are **evaluated live in runtime**
(process_protection_manager.py), not just downloaded to hardware.
