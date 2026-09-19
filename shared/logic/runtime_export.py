"""The EPW_RUNTIME_LOGIC contract itself - format marker, schema version,
the fields the checksum covers, and the checksum functions.

Both sides of the contract need exactly these: Logic Studio's
compiler/exporter.py WRITES the payload, EPW-OS's program loader
(shared/logic/program_loader.py) READS it back and refuses to run
anything whose checksum doesn't match. Keeping a second copy of the
field list or the canonical-serialization rules on the reading side is
precisely the kind of drift that makes a checksum useless - so there is
one implementation, here, and the exporter re-exports these names for
its own callers.
"""
import hashlib
import json

FORMAT_MARKER = "EPW_RUNTIME_LOGIC"

# Bump when the EPW_RUNTIME_LOGIC structure changes in a way a consumer
# (EPW-OS) needs to know about. See AUDIT_REPORT.md §2.2.
RUNTIME_SCHEMA_VERSION = 4

# The closed set of fields that make up the EPW_RUNTIME_LOGIC schema and are
# covered by the checksum. Compiler.compile() attaches a non-serializable
# "program" (CompiledProgram) key, and a "cycle_delayed_reads" list (feat/
# internal-bits §5/§8.1 - diagnostic data DERIVED from the fields already
# covered below, not independent data), on top of Exporter.export()'s
# return value for the ExecutionEngine's/EPW-OS's own use - those keys (and
# anything else outside this set) are deliberately ignored by both
# checksumming and verification, so handing verify_checksum() a compile()
# result instead of an export() result degrades to "checksum still valid"
# rather than a TypeError.
CHECKSUM_FIELDS = (
    "format", "schema_version", "source_version", "cycle_time_ms",
    "execution_order", "blocks", "generated_at", "generated_by",
    "project_name", "block_count", "contains_forced_io", "analog_points",
    "internal_bits", "system_catalog_version", "io_labels",
    "contains_disabled_blocks",
)


def compute_checksum(payload: dict) -> str:
    """SHA-256 over the canonical serialization of CHECKSUM_FIELDS only -
    computed before the "checksum" field itself is added."""
    subset = {k: payload[k] for k in CHECKSUM_FIELDS if k in payload}
    canonical = json.dumps(subset, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
    return hashlib.sha256(canonical.encode('utf-8')).hexdigest()


def verify_checksum(data: dict) -> bool:
    """Recomputes the SHA-256 checksum over CHECKSUM_FIELDS only and compares
    it against the "checksum" field. Returns False (never raises) if the
    checksum is missing, if any covered field was altered after export, or if
    the payload can't be serialized at all - a dict that also carries
    unrelated, non-serializable keys (e.g. a compile() result's "program")
    is handled the same as a clean export() result, since those keys are
    outside CHECKSUM_FIELDS and are simply ignored."""
    if "checksum" not in data:
        return False

    try:
        expected = compute_checksum(data)
    except TypeError:
        return False

    return expected == data["checksum"]
