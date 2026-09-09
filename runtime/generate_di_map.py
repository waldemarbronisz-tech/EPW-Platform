di_map = {
    1: "Q1 closed feedback",
    2: "KMG closed feedback",
    3: "KM1 closed feedback",
    4: "KM2 closed feedback",
    5: "Loss of technical power",
    6: "Loss of UPS / guaranteed supply",
    7: "Loss of measurement voltage",
    8: "Door open",
    9: "Lighting automation enabled",
    10: "Fire protection trip",
    11: "Alarm armed",
    12: "Intruder alarm",
    13: "24 VDC control voltage healthy",
    14: "Incoming Voltage Healthy",
    15: "Main Valve CLOSED feedback",
    16: "Main Valve OPEN feedback",
    17: "Drain Valve CLOSED feedback",
    18: "Drain Valve OPEN feedback",
    19: "Water Leak Detection"
}
for i in range(1, 65):
    if i not in di_map:
        di_map[i] = f"Reserved"

print(di_map)
