"""The register blocks the controller reads beyond a card's I/O channels
- the executable form of the contracts in shared/docs:

  ADA01_REGISTER_MAP.md            PROT block: the protection stages
  EPM_REGISTER_MAP.md              POWER block: the supply
  CARD_DIAGNOSTIC_REGISTER_MAP.md  DIAG block: every card's own health

Rule Z3 of the register work: the controller READS what the device
decided and exposes it; nothing here compares a measurement with a
setting. The maps are the contract for the firmware that does not exist
yet; the emulation (tools/device_emulation.py) implements the same maps,
so the driver, the bits and the logic are written once and a real card
later is a swap at the end of the bus.

Every address is a Modbus register address (0-based, as in the PDU).
Input registers are read with FC4, the command registers written with
FC6. A card that answers a block's read with a Modbus exception (illegal
address - a firmware without that block) is not in error: the driver
marks the block unsupported for that card and retries it occasionally.
"""
from shared.logic.protection_stages import STAGE_IDS

FC_READ_INPUT_REGISTERS = 4

# --- PROT (ADA01) ------------------------------------------------------------------------
PROT_STATUS = 100            # status word (bits below)
PROT_FIRMWARE = 101          # major << 8 | minor
PROT_FIRMWARE_BUILD = 102
PROT_CHECKSUM_LO = 103       # CRC-16 of the settings, low word (shared/logic/protection_stages.settings_checksum)
PROT_CHECKSUM_HI = 104       # reserved for a wider checksum; 0 today
PROT_STAGE_BASE = 110        # one status word per stage, in STAGE_IDS order
PROT_STAGE_COUNT = len(STAGE_IDS)
PROT_BLOCK = (PROT_STATUS, PROT_STAGE_BASE + PROT_STAGE_COUNT - PROT_STATUS)   # (start, count): 100..131

PROT_BIT_READY, PROT_BIT_ACTIVE, PROT_BIT_BLOCKED, PROT_BIT_FAIL = 1 << 0, 1 << 1, 1 << 2, 1 << 3
PROT_BIT_ANY_START, PROT_BIT_ANY_TRIP, PROT_BIT_TEST_ACTIVE, PROT_BIT_TEST_OK = 1 << 4, 1 << 5, 1 << 6, 1 << 7
PROT_BIT_ANY_LATCHED = 1 << 8

STAGE_BIT_ENABLED, STAGE_BIT_START, STAGE_BIT_TRIP, STAGE_BIT_BLOCKED, STAGE_BIT_LATCHED = (
    1 << 0, 1 << 1, 1 << 2, 1 << 3, 1 << 4)

PROT_CMD = 200               # holding register: a command code, executed on write
PROT_CMD_RESET, PROT_CMD_RESET_LATCH, PROT_CMD_SELFTEST = 1, 2, 3
PROT_BLOCK_STAGE = 201       # holding register: stage index + 1 -> that stage blocked
PROT_UNBLOCK_STAGE = 202     # holding register: stage index + 1 -> that stage unblocked

# --- POWER (EPM) -------------------------------------------------------------------------
POWER_UL1, POWER_UL2, POWER_UL3 = 0, 1, 2      # V x 10
POWER_FREQ = 3                                 # Hz x 100
POWER_UN = 4                                   # neutral-earth V x 10
POWER_STATUS = 10                              # status word (bits below)
POWER_BLOCK = (0, 11)

POWER_BIT_MAINS_OK, POWER_BIT_L1_OK, POWER_BIT_L2_OK, POWER_BIT_L3_OK = 1 << 0, 1 << 1, 1 << 2, 1 << 3
POWER_BIT_NEUTRAL_OK, POWER_BIT_PHASE_SEQUENCE_OK = 1 << 4, 1 << 5
POWER_BIT_BACKUP_AVAILABLE, POWER_BIT_BACKUP_ACTIVE = 1 << 6, 1 << 7
POWER_BIT_DC_BUS_OK, POWER_BIT_AUX_POWER_OK, POWER_BIT_POWER_24V_OK = 1 << 8, 1 << 9, 1 << 10

# --- DIAG (every card) -------------------------------------------------------------------
DIAG_STATUS = 500            # status word (bits below)
DIAG_FIRMWARE = 501          # major << 8 | minor
DIAG_TEMPERATURE = 502       # degrees C x 10, signed
DIAG_SUPPLY = 503            # card supply V x 100
DIAG_ERRORS = 504            # error counter since power-up
DIAG_BLOCK = (DIAG_STATUS, 5)

DIAG_BIT_READY, DIAG_BIT_RUNNING, DIAG_BIT_FAULT, DIAG_BIT_WATCHDOG_OK = 1 << 0, 1 << 1, 1 << 2, 1 << 3
DIAG_BIT_POWER_OK, DIAG_BIT_CONFIG_OK, DIAG_BIT_MAINTENANCE, DIAG_BIT_SIMULATION = 1 << 4, 1 << 5, 1 << 6, 1 << 7
DIAG_BIT_IO_FAULT = 1 << 8

DIAG_CMD = 600               # holding register: 1 RESET (the card restarts), 2 RESYNC (re-reads its configuration)
DIAG_CMD_RESET, DIAG_CMD_RESYNC = 1, 2

# Which blocks a card model carries. "DIAG" for every card.
BLOCKS_BY_MODEL_PREFIX = {"ADA": ("PROT", "DIAG"), "EPM": ("POWER", "DIAG"), "ELA": ("DIAG",)}
BLOCK_RANGES = {"PROT": PROT_BLOCK, "POWER": POWER_BLOCK, "DIAG": DIAG_BLOCK}

# How many input registers an emulated unit needs to hold every block.
EMULATED_INPUT_REGISTERS = DIAG_STATUS + 5
EMULATED_HOLDING_REGISTERS = DIAG_CMD + 1


def blocks_for_model(model: str) -> tuple:
    text = (model or "").upper()
    for prefix, blocks in BLOCKS_BY_MODEL_PREFIX.items():
        if text.startswith(prefix):
            return blocks
    return ("DIAG",)


def signed16(value: int) -> int:
    value &= 0xFFFF
    return value - 0x10000 if value & 0x8000 else value
