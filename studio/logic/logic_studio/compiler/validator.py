def _block_owning_pin(pin_uuid, blocks):
    """feat/wire-labels §2.5: the block that owns the pin named
    `pin_uuid` (input or output, either direction) — used to name the
    block a free-end wire is still attached to. Distinct from
    `_direct_source_block()` below, which looks up a specific input's
    SOURCE by INDEX, not an arbitrary pin by its own uuid."""
    for block in blocks:
        for pin in block.inputs + block.outputs:
            if pin.uuid == pin_uuid:
                return block
    return None


def _direct_source_block(block, input_index, blocks):
    """fix/safety-block-semantics §4: see compiler/core.py's identical
    helper for the full rationale — duplicated here rather than imported
    across the module boundary."""
    if input_index >= len(block.inputs):
        return None
    connections = block.inputs[input_index].connections
    if not connections:
        return None
    source_pin_uuid = connections[0]
    for candidate in blocks:
        for pin in candidate.outputs:
            if pin.uuid == source_pin_uuid:
                return candidate
    return None


class Validator:
    def __init__(self, project):
        self.project = project

    def _block_ref(self, block) -> str:
        """feat/io-labels-and-ids §4.3/§3.3: every compiler/validator
        message identifies a block by its short_id — short, unique, and
        speakable over the phone, unlike the raw UUID or the possibly-
        shared display_name several untitled gates of the same type carry
        identically. For an I/O block with an assigned Address that also
        has a descriptive label (DeviceModel.get_io_label()), the address
        and label are appended in parens: "i3 (ELA01.DI01 — Wyłącznik Q1
        zamknięty)" — the single most useful extra context a message about
        an I/O block can carry."""
        from logic_studio.core.device_model import DeviceModel
        ref = getattr(block, 'short_id', '') or block.display_name  # defensive: a block never added to a project has no short_id yet
        properties = getattr(block, 'properties', None)
        addr = properties.get("Address", "") if isinstance(properties, dict) else ""
        if addr:
            label = DeviceModel.get_io_label(self.project, addr)
            if label:
                return f"{ref} ({addr} — {label})"
        return ref

    def _missing_card_suffix(self, addr: str) -> str:
        """Task "jedno źródło listy kart" 1.2: a block address invalid
        because its CARD no longer exists (removed in Studio, or never
        bridged in - the far more common case than a plain typo) must
        NAME that card in the message, not just say "invalid address" -
        the whole point of a compile error over a silently-dropped block
        is that the engineer can go fix the actual cause. Returns "" for
        a malformed address (nothing to name) or one whose card DOES
        exist but whose channel number is simply out of range - that
        case is already self-explanatory from the surrounding message."""
        from logic_studio.core.addressing import parse_address, InvalidAddressError
        from logic_studio.core.device_model import DeviceModel

        try:
            card, kind, _channel = parse_address(addr)
        except InvalidAddressError:
            return ""
        known = DeviceModel.get_ela_devices(self.project) if kind == "DI" else DeviceModel.get_ada_devices(self.project)
        if card in known:
            return ""
        return f" Card '{card}' does not exist in the project."

    def run(self, errors: list, warnings: list):
        import math
        from logic_studio.core.device_model import DeviceModel

        blocks = self.project.blocks

        if not blocks:
            warnings.append("Project contains no logic blocks.")
            # Falls through to §5 below rather than returning — the
            # internal-signal registry (bad names, unused entries) is
            # worth validating independent of whether any block exists
            # yet, e.g. right after defining signals in Project Settings.

        for block in blocks:
            # 1. Ask block to self-validate
            block_errors = block.validate()
            for err in block_errors:
                errors.append(f"[{self._block_ref(block)}] {err}")

            # 2. Pin Level Validation
            # feat/editor-modes-and-geometry §2.4: a disabled ("zaślepione")
            # input is excluded from validation the same way it's excluded
            # from evaluate() (base.py's _active_inputs()) — no "unconnected"
            # warning for it. Instead: an active-input-count check runs once
            # per block below (only for block types that opt in at all —
            # multi-input logic gates), covering the "too few active inputs"
            # and "every input disabled" cases §2.4 requires.
            has_inputs = False
            active_input_count = 0
            for pin in block.inputs:
                has_inputs = True
                if pin.disabled:
                    if not getattr(block, 'allows_disabled_inputs', False):
                        # Defensive: this state should be unreachable through
                        # the UI (PortItem only offers the toggle when the
                        # block opted in) but a hand-edited/older file could
                        # still carry it — never silently accept it.
                        errors.append(
                            f"[{self._block_ref(block)}] Input '{pin.name}' is stubbed, "
                            "but this block type does not allow stubbed inputs."
                        )
                    continue
                active_input_count += 1
                if not pin.connections:
                    warnings.append(f"[{self._block_ref(block)}] Input '{pin.name}' is unconnected.")

            if has_inputs and getattr(block, 'allows_disabled_inputs', False):
                if active_input_count == 0:
                    errors.append(
                        f"[{self._block_ref(block)}] All inputs of the block are stubbed — "
                        "the block has no active input."
                    )
                elif active_input_count == 1:
                    warnings.append(
                        f"Gate {self._block_ref(block)} has only 1 active input — "
                        "it works like a repeater."
                    )

            # fix/safety-block-semantics §6: a new category of rule, not the
            # same as "Input is unconnected" above — not every unconnected
            # OUTPUT is a problem (most are genuinely optional), but a pin
            # marked safety_relevant carries information about whether the
            # logic built on it can be trusted at all, so leaving it
            # unconnected means nothing downstream is even looking. Never
            # an error: an engineer may deliberately decide the quality
            # check isn't needed for a given signal.
            for pin in block.outputs:
                if pin.safety_relevant and not pin.connections:
                    warnings.append(
                        f"[{self._block_ref(block)}] Output '{pin.name}', which reports measurement trustworthiness, "
                        "is not used anywhere. The logic will run without signal quality checking."
                    )

            # 3. Explicit IO Address Validation
            # Task "jedno źródło listy kart" 1.2: an address whose CARD no
            # longer exists in the project (removed in Studio, or never
            # bridged in) must fail loudly, NAMING the missing card - never
            # silently dropped or rewritten. _missing_card_suffix() below
            # is what actually names it in the message.
            if block.type_id == "input.di":
                addr = block.properties.get("Address", "")
                if addr not in DeviceModel.get_ela_addresses(self.project):
                    errors.append(
                        f"[{self._block_ref(block)}] Invalid DI Address: '{addr}'. "
                        f"Must be valid DI01 to DI32 on a defined ELA device."
                        f"{self._missing_card_suffix(addr)}"
                    )
            elif block.type_id == "output.do":
                addr = block.properties.get("Address", "")
                if addr not in DeviceModel.get_ada_addresses(self.project):
                    errors.append(
                        f"[{self._block_ref(block)}] Invalid DO Address: '{addr}'. "
                        f"Must be valid DO01 to DO32 on a defined ADA device."
                        f"{self._missing_card_suffix(addr)}"
                    )
            elif block.type_id == "input.ai":
                # Analog points are project-defined, not fixed hardware channels
                # (AUDIT_REPORT.md §1) — the address must name a point with
                # direction="input" in project.settings["analog_points"].
                addr = block.properties.get("Address", "")
                if addr not in DeviceModel.get_analog_input_addresses(self.project):
                    errors.append(f"[{self._block_ref(block)}] Invalid AI Address: '{addr}'. Must match an analog point with direction=input.")
            elif block.type_id == "output.ao":
                addr = block.properties.get("Address", "")
                if addr not in DeviceModel.get_analog_output_addresses(self.project):
                    errors.append(f"[{self._block_ref(block)}] Invalid AO Address: '{addr}'. Must match an analog point with direction=output.")
            elif block.type_id == "system.signal":
                # §3.4 migration note: an old/unrecognized signal id is a
                # WARNING (the block runs safe — False/0.0 — not a hard
                # compile failure), so a project doesn't stop compiling the
                # moment the catalog gains/loses a signal.
                sig_id = block.properties.get("Sygnał", "")
                if sig_id:
                    from shared.logic import system_signals
                    if system_signals.get_signal(sig_id, self.project) is None:
                        warnings.append(f"[{self._block_ref(block)}] Unrecognised system signal: '{sig_id}' (not in the catalog).")
            elif block.type_id == "const.real":
                # feat/const-property-validation: ConstantBase.evaluate()
                # (blocks/constants.py) only catches ValueError around
                # float()/int() — a property holding None/a list/a dict
                # (possible from a hand-edited or corrupted .epwlogic file;
                # the property panel's own QDoubleSpinBox/QSpinBox can never
                # produce one) raises TypeError instead, uncaught, crashing
                # the engine mid-scan rather than falling back to the safe
                # default. Caught here as a compile ERROR instead — the same
                # "type checked live in the UI, but ALSO enforced at compile
                # time" belt-and-suspenders already applied to DI/DO/AI/AO
                # addresses above.
                raw = block.properties.get("Value", 0.0)
                try:
                    value = float(raw)
                except (TypeError, ValueError):
                    errors.append(f"[{self._block_ref(block)}] The REAL constant value is not a valid number: {raw!r}.")
                else:
                    if not math.isfinite(value):
                        errors.append(f"[{self._block_ref(block)}] The REAL constant value must be a finite number (not NaN/Inf): {raw!r}.")
            elif block.type_id == "const.int":
                raw = block.properties.get("Value", 0)
                try:
                    int(raw)
                except (TypeError, ValueError):
                    errors.append(f"[{self._block_ref(block)}] The INT constant value is not a valid integer: {raw!r}.")
            elif block.type_id == "analog.quality":
                # §4.2: "Z punktu analogowego" only makes sense wired
                # directly to an input.ai block — that's the only place a
                # min/max range for this block to inherit even exists.
                if block.properties.get("Range Source", "Własny") == "Z punktu analogowego":
                    source = _direct_source_block(block, 0, blocks)
                    if source is None or source.type_id != "input.ai":
                        errors.append(
                            f"[{self._block_ref(block)}] Range Source = From analog point requires "
                            "input In to come directly from an AI block."
                        )
                # fix/safety-block-semantics §1.4: Stuck Tolerance=0 means
                # bit-exact equality, which a real measurement chain's own
                # ADC noise essentially never produces — the check would
                # compile clean and pass every unit test, then silently
                # never fire in the field. Warn, don't error: a purely
                # digital/simulated signal source genuinely IS bit-exact.
                stuck_scans = int(block.properties.get("Stuck Scans", 0) or 0)
                tolerance = float(block.properties.get("Stuck Tolerance", 0.0) or 0.0)
                if stuck_scans > 0 and tolerance == 0.0:
                    warnings.append(
                        f"[{self._block_ref(block)}] Stuck-signal detection with a tolerance of 0 will not work "
                        "on a real measurement chain (last-bit converter noise). "
                        "Set Stuck Tolerance."
                    )
                # §2.4: one-shot notice right after a v8->v9 schema
                # migration converted this block's old per-scan "Max Rate"
                # into the new per-second property. Lives in
                # simulation_state, same mechanism as _legacy_force_state
                # (core/project.py). NOTE: `block` here is an ISOLATED
                # CLONE (core/macros.py's expand_project() clones every
                # top-level block for compile-time isolation — see
                # base.py's clone()), so deleting the key HERE only clears
                # the clone's own copy; Compiler.compile() clears the same
                # key on the live project's own blocks right after this
                # runs, which is what actually makes it fire once.
                migration = block.simulation_state.get("_max_rate_migration_notice")
                if migration:
                    old_rate, new_rate = migration["old"], migration["new"]
                    warnings.append(
                        f"[{self._block_ref(block)}] Max Rate was converted during project migration: "
                        f"{old_rate:g}/scan -> {new_rate:g}/s (same physical rate of change, new unit)."
                    )
            elif block.type_id == "const.time":
                raw = block.properties.get("Time (ms)", 1000)
                try:
                    value = int(raw)
                except (TypeError, ValueError):
                    errors.append(f"[{self._block_ref(block)}] The TIME constant is not a valid integer (ms): {raw!r}.")
                else:
                    if value < 0:
                        errors.append(f"[{self._block_ref(block)}] The TIME constant cannot be negative: {value} ms.")

        # 4. Duplicate Output Detection
        output_addresses = {}
        analog_output_addresses = {}
        analog_input_addresses = {}
        for block in blocks:
            if block.type_id == "output.do":
                addr = block.properties.get("Address", "")
                if addr in output_addresses:
                    errors.append(f"Multiple outputs assigned to address: {addr} ({output_addresses[addr]} and {self._block_ref(block)})")
                else:
                    output_addresses[addr] = self._block_ref(block)
            elif block.type_id == "output.ao":
                addr = block.properties.get("Address", "")
                if addr in analog_output_addresses:
                    errors.append(f"Multiple analog outputs assigned to address: {addr} ({analog_output_addresses[addr]} and {self._block_ref(block)})")
                else:
                    analog_output_addresses[addr] = self._block_ref(block)
            elif block.type_id == "input.ai":
                # Several blocks reading the same analog measurement is legal
                # (e.g. one for logic, one for a display) — warn, don't fail.
                addr = block.properties.get("Address", "")
                if addr in analog_input_addresses:
                    warnings.append(f"Multiple AI blocks read address: {addr} ({analog_input_addresses[addr]} and {self._block_ref(block)})")
                else:
                    analog_input_addresses[addr] = self._block_ref(block)

        # 5. Internal signal registry (feat/internal-bits §4).
        from shared.logic.internal_bits import validate_internal_bits_registry, internal_bit_id
        errors.extend(validate_internal_bits_registry(self.project.settings.get("internal_bits", [])))

        BOOL_SIGNAL_TYPE_IDS = ("virtual.input", "virtual.output")
        REAL_SIGNAL_TYPE_IDS = ("internal.reg_in", "internal.reg_out")
        WRITER_TYPE_IDS = ("virtual.output", "internal.reg_out")

        from shared.logic import system_signals

        writers = {}  # name.lower() -> [display_name, ...]
        readers = {}  # name.lower() -> [display_name, ...]
        # Catalog signals are counted separately: they have no registry
        # entry to hang the other warnings off, but "two blocks writing
        # the same command" is every bit as wrong for them.
        system_writers = {}
        referenced_lower_names = set()

        for block in blocks:
            if block.type_id not in BOOL_SIGNAL_TYPE_IDS and block.type_id not in REAL_SIGNAL_TYPE_IDS:
                continue
            name = block.properties.get("Bit", "")
            if not name:
                continue  # unconfigured — the "???" canvas warning already covers this

            expected_type = "REAL" if block.type_id in REAL_SIGNAL_TYPE_IDS else "BOOL"

            # feat/signal-register §1.1: a "Bit" may name EITHER a project
            # registry entry or a signal of the fixed platform catalog.
            # The catalog is consulted first and wins - its ids are a
            # contract shared by every project, and a marker must not be
            # able to shadow one (the collision itself is reported below,
            # under the registry's own checks).
            catalog_entry = system_signals.get_signal(name, self.project)
            if catalog_entry is not None:
                if catalog_entry.get("type") != expected_type:
                    errors.append(f"[{self._block_ref(block)}] System signal '{name}' is of type {catalog_entry.get('type')}, but this block needs {expected_type}.")
                    continue
                # §2.4's rule, now enforced for the bit blocks too: only a
                # source == "logic" signal may be written. The picker does
                # not offer the others, but a hand-edited file or a project
                # from a newer catalog can still get here.
                if block.type_id in WRITER_TYPE_IDS and catalog_entry.get("source") != "logic":
                    errors.append(
                        f"[{self._block_ref(block)}] System signal '{name}' is written by the runtime "
                        f"(source == '{catalog_entry.get('source')}') and cannot be written from the logic."
                    )
                    continue
                # The symmetric rule on the READ side (owner's correction).
                # A request is not a state: REQ.SEC.ARM_ALL is what the
                # logic SAYS, and nothing maintains a value for it to be
                # read back from - a schematic built on reading one waits
                # for a bit that only moves when that same program writes
                # it. Tested by `source`, not by the name.
                if block.type_id not in WRITER_TYPE_IDS and catalog_entry.get("source") != "runtime":
                    errors.append(
                        f"[{self._block_ref(block)}] System signal '{name}' is a request the logic "
                        f"issues (source == '{catalog_entry.get('source')}'), not a state the "
                        f"controller maintains - it cannot be read."
                    )
                    continue
                # A catalog signal has no registry entry, so none of the
                # registry bookkeeping below (single-writer, read-but-never-
                # written, defined-but-unused) applies to it - except the
                # single-writer rule, which is just as real for a command.
                if block.type_id in WRITER_TYPE_IDS:
                    # Grouped case-insensitively like the registry's own
                    # rule, but the message quotes the CATALOG's spelling -
                    # a lower-cased id is not a name anybody can search for.
                    key = name.lower()
                    system_writers.setdefault(key, (catalog_entry["id"], []))[1].append(self._block_ref(block))
                continue

            # feat/signal-register §3.1: a RETIRED name gets its own
            # message. Falling through to "exists in neither place" would
            # be true and useless - the engineer would go looking for a
            # signal that was renamed, not deleted.
            from shared.logic.signal_renames import new_name as _renamed_to
            replacement = _renamed_to(name)
            if replacement:
                errors.append(
                    f"[{self._block_ref(block)}] Signal '{name}' no longer exists - "
                    f"it is now called '{replacement}'. Nothing was converted automatically: "
                    f"point the block at the new name."
                )
                continue

            entry = DeviceModel.get_internal_bit(self.project, name)
            # §4.4: signal in neither address space -> ERROR. Exactly the
            # point of replacing free-text "Tag" with a registry: a typo is
            # now a compile error instead of silently creating a new signal.
            if entry is None:
                errors.append(f"[{self._block_ref(block)}] Signal '{name}' exists neither in the project registry (Project settings -> Internal signals) nor in the system signal catalog.")
                continue

            # §4.5: a BOOL block (virtual.*) pointing at a REAL entry, or vice versa -> ERROR.
            if entry.get("type") != expected_type:
                errors.append(f"[{self._block_ref(block)}] Signal '{name}' is of type {entry.get('type')}, but this block needs {expected_type}.")
                continue

            lname = name.lower()
            referenced_lower_names.add(lname)
            if block.type_id in WRITER_TYPE_IDS:
                writers.setdefault(lname, []).append(self._block_ref(block))
            else:
                readers.setdefault(lname, []).append(self._block_ref(block))

        # §4.1: more than one writer for the same signal -> ERROR, exactly
        # like output.do above — must name every writing block.
        for entry in self.project.settings.get("internal_bits", []):
            lname = entry.get("name", "").lower()
            writer_names = writers.get(lname, [])
            if len(writer_names) > 1:
                errors.append(
                    f"Internal signal '{internal_bit_id(entry)}' has more than one writing block: "
                    + ", ".join(writer_names) + "."
                )

        for signal_id, writer_names in system_writers.values():
            if len(writer_names) > 1:
                errors.append(
                    f"System signal '{signal_id}' has more than one writing block: "
                    + ", ".join(writer_names) + "."
                )

        # feat/signal-register §1.1: a registry entry whose NAME is also a
        # catalog id can never be reached - resolution gives the catalog
        # priority, so the marker silently stops being the thing the
        # engineer thinks they are editing. An error, not a warning: there
        # is no reading of this that was intended.
        for entry in self.project.settings.get("internal_bits", []):
            entry_name = entry.get("name", "")
            if entry_name and system_signals.get_signal(entry_name, self.project) is not None:
                errors.append(
                    f"Internal signal '{entry_name}' has the same name as a system signal from the "
                    f"platform catalog. Rename it - a block using this name reads the system signal."
                )

        # §4.2: read but never written -> WARNING (can be legitimate while
        # a schematic is still being built).
        registry_by_lname = {e.get("name", "").lower(): e for e in self.project.settings.get("internal_bits", [])}
        for lname, reader_names in readers.items():
            if lname not in writers:
                entry = registry_by_lname.get(lname)
                sig_label = internal_bit_id(entry) if entry else lname
                warnings.append(f"Internal signal '{sig_label}' is read but not written by any block: " + ", ".join(reader_names) + ".")

        # §4.3: registered but unused by any block -> WARNING (housekeeping aid).
        for entry in self.project.settings.get("internal_bits", []):
            lname = entry.get("name", "").lower()
            if lname not in referenced_lower_names:
                warnings.append(f"Defined internal signal '{entry.get('name', '')}' is not used by any block.")

        # 6. I/O label registry (feat/io-labels-and-ids §1.2): a label whose
        # address no longer names a real ELA/ADA channel or project analog
        # point -> WARNING, not an error — the address may simply have
        # disappeared after a reconfiguration (a deleted analog point, a
        # DeviceModel change), and the label itself is otherwise harmless.
        valid_addresses = set(DeviceModel.all_addresses(self.project))
        for address in DeviceModel.get_labelled_addresses(self.project):
            if address not in valid_addresses:
                warnings.append(
                    f"A label is defined for address '{address}', which does not exist in the project."
                )

        # 7. Macro parameters (fix/safety-and-macro-params §C4) — validated
        # against `self.project.settings["macro_definitions"]` (the
        # registry ITSELF, present here regardless of whether
        # expand_project() found any live instance to substitute onto for
        # THIS compile — same "validate the registry, not just what's
        # currently wired up" spirit as §5's internal-signal-registry
        # checks above), once per definition, independent of how many
        # instances (if any) exist right now. A "value out of range for
        # the bound property" rule (e.g. a negative TIME) needs no code
        # here at all: substitution (core/macros.py's own §C3.1, run
        # BEFORE this Validator ever sees the expanded graph) has already
        # overwritten the target block's property with the instance's own
        # value by the time this runs, so whatever range check that block
        # TYPE already has for that property (const.time's own "nie może
        # być ujemny", say) fires on the substituted value exactly as it
        # would on one typed in directly — no macro-aware duplicate rule
        # needed, or wanted, for that one bullet.
        from logic_studio.core import macros as macros_module
        macro_definitions = self.project.settings.get(macros_module.SETTINGS_KEY, {})
        for def_id, definition in macro_definitions.items():
            def_name = definition.get("name") or def_id
            ref = f"makroblok '{def_name}'"
            blocks_by_uuid = {b.get("uuid"): b for b in definition.get("blocks", [])}
            params_by_name = {p.get("name"): p for p in definition.get("parameters", [])}

            bound_param_names = set()
            property_targets = {}  # (block_uuid, property_name) -> [display_name, ...]

            for binding in definition.get("parameter_bindings", []):
                param_name = binding.get("parameter")
                block_uuid = binding.get("block_uuid")
                property_name = binding.get("property_name")
                param = params_by_name.get(param_name)

                if param is None:
                    errors.append(f"[{ref}] A parameter binding points to a parameter that does not exist: '{param_name}'.")
                    continue
                block_data = blocks_by_uuid.get(block_uuid)
                if block_data is None or property_name not in block_data.get("properties", {}):
                    errors.append(
                        f"[{ref}] Parameter binding '{param.get('display_name', param_name)}' points to "
                        "an internal block or property that does not exist."
                    )
                    continue

                bound_param_names.add(param_name)
                current_value = block_data["properties"][property_name]
                if not macros_module.value_matches_param_type(current_value, param.get("type", "STRING")):
                    errors.append(
                        f"[{ref}] Parameter '{param.get('display_name', param_name)}' (type {param.get('type')}) "
                        f"does not match the type of property '{property_name}'."
                    )
                property_targets.setdefault((block_uuid, property_name), []).append(param.get("display_name", param_name))

            # §C4: defined but never bound to anything -> WARNING (an
            # engineer may still be wiring up a brand-new macro).
            for param in definition.get("parameters", []):
                if param.get("name") not in bound_param_names:
                    warnings.append(
                        f"[{ref}] Parameter '{param.get('display_name', param.get('name'))}' "
                        "is not bound to any property."
                    )

            # §C4: two parameters aimed at the same (block, property) ->
            # WARNING, not an error — legal but misleading (whichever
            # binding core/macros.py's own substitution loop iterates last
            # silently wins).
            for (block_uuid, property_name), names in property_targets.items():
                if len(names) > 1:
                    warnings.append(
                        f"[{ref}] More than one parameter is bound to the same property "
                        f"'{property_name}': {', '.join(names)} — the last substitution wins."
                    )

        # 8. System-signal WRITE direction (feat/security-signals §2.3) — the
        # first category of system signals with source == "logic"
        # (SEC.CMD_* today). system.signal (read) already has its own,
        # deliberately lenient WARNING for an unrecognized id (§3.4
        # migration compat, case 3 above) — system.signal_out is a brand
        # new block type with no such back-compat concern, so an unknown
        # id there is a hard ERROR instead.
        from shared.logic import system_signals

        sys_writers = {}  # signal_id -> [block_ref, ...]
        sys_referenced = set()  # any signal_id read OR written by a block

        for block in blocks:
            if block.type_id == "system.signal":
                sig_id = block.properties.get("Sygnał", "")
                if sig_id:
                    sys_referenced.add(sig_id)
                    # The same read-direction rule as the bit blocks above.
                    # An UNRECOGNISED id here stays a lenient warning (case
                    # 3's migration compat), but an id that IS in the
                    # catalogue and belongs to the logic is a real mistake,
                    # not an old file.
                    entry = system_signals.get_signal(sig_id, self.project)
                    if entry is not None and entry.get("source") != "runtime":
                        errors.append(
                            f"[{self._block_ref(block)}] Signal '{sig_id}' is a request the logic "
                            f"issues (source == '{entry.get('source')}'), not a state the "
                            f"controller maintains - it cannot be read."
                        )
            elif block.type_id == "system.signal_out":
                sig_id = block.properties.get("Sygnał", "")
                if not sig_id:
                    continue  # unconfigured — no separate "???" warning for this block yet
                sys_referenced.add(sig_id)
                entry = system_signals.get_signal(sig_id, self.project)
                if entry is None:
                    errors.append(f"[{self._block_ref(block)}] Unrecognised system signal: '{sig_id}' (not in the catalog).")
                    continue
                if entry.get("source") == "runtime":
                    errors.append(
                        f"[{self._block_ref(block)}] Signal '{sig_id}' is produced by the device "
                        "and cannot be written by the logic."
                    )
                    continue
                sys_writers.setdefault(sig_id, []).append(self._block_ref(block))

        # §2.3: more than one writer for the same "logic"-sourced signal ->
        # ERROR, exactly like the internal-signal registry's own rule above.
        for sig_id, writer_refs in sys_writers.items():
            if len(writer_refs) > 1:
                errors.append(
                    f"System signal '{sig_id}' has more than one writing block: "
                    + ", ".join(writer_refs) + "."
                )

        # §2.3: a "logic"-sourced catalog signal nobody reads OR writes ->
        # WARNING (housekeeping aid, same spirit as §4.3's unused-internal-
        # signal rule) — every SEC.CMD_* entry is a fixed catalog
        # signal, never itself "undefined", so there's no ERROR case
        # analogous to internal bits' missing-registry-entry rule here.
        for sig in system_signals.get_all_signals(self.project):
            if sig.get("source") == "logic" and sig["id"] not in sys_referenced:
                warnings.append(f"System signal '{sig['id']}' (command) is not used by any block.")

        # 9. Access-level gate on a block writing a safety_relevant system
        # signal (feat/security-signals §3.3) — WARNING only, never an error:
        # an engineer may deliberately decide "Brak" is fine for a given
        # deployment, but leaving it unset without a second thought on a
        # signal like REQ.SEC.DISARM_ALL is exactly the "logic bug disarms
        # the object" hazard this property exists to catch early. §3.2:
        # Logic Studio itself never ENFORCES the gate — only warns that
        # it's missing — EPW-OS is what actually checks it at runtime.
        for block in blocks:
            if block.type_id != "system.signal_out":
                continue
            sig_id = block.properties.get("Sygnał", "")
            if not sig_id:
                continue
            entry = system_signals.get_signal(sig_id, self.project)
            if entry is None or not entry.get("safety_relevant"):
                continue
            level = block.properties.get("Minimalny poziom dostępu", "Brak")
            if level == "Brak":
                warnings.append(
                    f"[{self._block_ref(block)}] The block drives the critical signal '{sig_id}' "
                    "without a required access level."
                )
        # feat/wire-labels §2.5: a free end with no label is a normal
        # PENDING state while a wire is being drawn or a label is about
        # to be typed in — a warning, not an error, naming whichever
        # block the wire is still actually attached to. fix/wire-labels-
        # and-project-integrity §A2 (confirmed, not a leftover): kept
        # exactly as a warning even now that labels merge nodes
        # (compiler/label_merge.py) — a free-end wire with no label
        # carries no signal and breaks nothing else either; it's an
        # UNFINISHED DRAWING, not faulty logic, so it stays a warning,
        # never an error, regardless of how far label-merging itself
        # grows. An unlabeled free end names no node to validate yet, so
        # there is nothing for label_merge.py to check here; this is the
        # only free-end/label check that stays independent of it. Every
        # STRONGER check (a labeled node with no source, more than one,
        # or no receiver) now lives in compiler/label_merge.py instead,
        # run right after this stage in compiler/core.py. A label of
        # only whitespace counts as no label at all here — same
        # reasoning group_labeled_pins() already applies via its own
        # .strip() before grouping.
        for wire in getattr(self.project, 'wires', []):
            if (wire.label or "").strip() or not wire.has_free_end():
                continue
            attached_pin = wire.source_pin if wire.source_pin is not None else wire.dest_pin
            attached_block = _block_owning_pin(attached_pin, blocks) if attached_pin else None
            ref = self._block_ref(attached_block) if attached_block else "?"
            warnings.append(f"[{ref}] Unfinished wire (free end without a label).")
