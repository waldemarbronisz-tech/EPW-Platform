"""Project menu > Properties... (Task: fill in the previously-empty
Project menu). Project-level metadata (name/description/location/
author) the operator maintains, plus a read-only summary computed live
from the current state - not stored anywhere itself, just calculated
from tag_manager/project_manager each time this dialog opens.

View: every access level. Edit: Engineer only - both the visual gate
(fields become read-only, Save disabled otherwise) and the real,
execution-time gate (_try_save() re-checks access_manager independently
of what the fields looked like when this dialog was constructed - the
5-minute auto-logout timer keeps running while a modal dialog is open,
so access really can lapse mid-session here).
"""
from datetime import datetime

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QLabel,
                             QLineEdit, QDialogButtonBox)

from epw_os.core.access_manager import AccessLevel
from epw_os.gui.theme_manager import error_text_style
from epw_os.i18n import tr


def _format_timestamp(iso_str):
    """None/empty -> None (caller shows the "never set" placeholder); an
    unparsable string is shown as-is rather than hidden, so a corrupt
    value is at least visible instead of silently disappearing."""
    if not iso_str:
        return None
    try:
        return datetime.fromisoformat(iso_str).strftime("%Y-%m-%d %H:%M")
    except (ValueError, TypeError):
        return iso_str


class ProjectPropertiesDialog(QDialog):
    def __init__(self, project_manager, tag_manager, access_manager, audit_logger=None, parent=None):
        super().__init__(parent)
        self.project_manager = project_manager
        self.tag_manager = tag_manager
        self.access_manager = access_manager
        self.audit_logger = audit_logger

        self.setObjectName("IndustrialDialog")
        self.setWindowTitle(tr("project_properties.title"))
        self.setModal(True)
        self.setMinimumWidth(420)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)

        header = QLabel(tr("project_properties.title"))
        header.setObjectName("SectionHeader")
        layout.addWidget(header)

        form = QFormLayout()
        layout.addLayout(form)

        # Operator-entered content (task: NEVER translate the VALUES here,
        # only the field labels via tr() below).
        meta = project_manager.get_metadata()
        self.edit_name = QLineEdit(meta["name"])
        form.addRow(tr("project_properties.lbl_name"), self.edit_name)
        self.edit_description = QLineEdit(meta["description"])
        form.addRow(tr("project_properties.lbl_description"), self.edit_description)
        self.edit_location = QLineEdit(meta["location"])
        form.addRow(tr("project_properties.lbl_location"), self.edit_location)
        self.edit_author = QLineEdit(meta["author"])
        form.addRow(tr("project_properties.lbl_author"), self.edit_author)

        never = tr("project_properties.never")
        self.lbl_created = QLabel(_format_timestamp(meta["created"]) or never)
        form.addRow(tr("project_properties.lbl_created"), self.lbl_created)
        self.lbl_modified = QLabel(_format_timestamp(meta["modified"]) or never)
        form.addRow(tr("project_properties.lbl_modified"), self.lbl_modified)

        summary_header = QLabel(tr("project_properties.summary_header"))
        summary_header.setObjectName("SectionHeader")
        layout.addWidget(summary_header)

        summary_form = QFormLayout()
        layout.addLayout(summary_form)

        analog_count = len(tag_manager.get_analog_points()) if tag_manager is not None else 0
        summary_form.addRow(tr("project_properties.lbl_analog_points"), QLabel(str(analog_count)))

        # "opisanych" (described) - channels with a NON-EMPTY custom
        # description ever saved, not just "has some description at all"
        # (every DI/DO always has at least the generic auto-generated
        # default, which would make this count trivially equal the
        # total channel count and say nothing useful).
        di_described = sum(1 for v in project_manager.get_tag_descriptions().values() if v and v.strip())
        summary_form.addRow(tr("project_properties.lbl_di_described"), QLabel(str(di_described)))

        do_described = sum(1 for v in project_manager.get_output_descriptions().values() if v and v.strip())
        summary_form.addRow(tr("project_properties.lbl_do_described"), QLabel(str(do_described)))

        logic_file = project_manager.get_logic_file()
        logic_text = logic_file if logic_file else tr("project_properties.logic_not_configured")
        summary_form.addRow(tr("project_properties.lbl_logic_project"), QLabel(logic_text))

        path_label = QLabel(getattr(project_manager, "project_file", "") or "")
        path_label.setWordWrap(True)
        summary_form.addRow(tr("project_properties.lbl_project_path"), path_label)

        self.lbl_error = QLabel("")
        self.lbl_error.setStyleSheet(error_text_style())
        self.lbl_error.setWordWrap(True)
        layout.addWidget(self.lbl_error)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        self.btn_save = buttons.button(QDialogButtonBox.StandardButton.Save)
        buttons.accepted.connect(self._try_save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._apply_edit_permission()

    def _apply_edit_permission(self):
        can_edit = self.access_manager is not None and self.access_manager.has_access(AccessLevel.ENGINEER)
        for edit in (self.edit_name, self.edit_description, self.edit_location, self.edit_author):
            edit.setReadOnly(not can_edit)
        self.btn_save.setEnabled(can_edit)

    def _try_save(self):
        # Execution-time re-check (same pattern as every other Engineer-
        # only save path in this app - Digital Inputs/Control Outputs/
        # Analog Inputs description edits, Protection settings): the
        # Save button being enabled at all already implies Engineer
        # access AT THE TIME this dialog was built, but access can lapse
        # while it's still open (5-minute auto-logout keeps running under
        # a modal .exec() loop) - so this is re-checked here regardless
        # of the button's current state, not just trusted.
        if self.access_manager is None or not self.access_manager.has_access(AccessLevel.ENGINEER):
            main_window = self.parent()
            if main_window is not None and hasattr(main_window, "deny_access"):
                main_window.deny_access(AccessLevel.ENGINEER, "Edit Project Properties")
            self._apply_edit_permission()
            return

        name = self.edit_name.text()
        description = self.edit_description.text()
        location = self.edit_location.text()
        author = self.edit_author.text()
        self.project_manager.set_metadata(name=name, description=description, location=location, author=author)
        self.project_manager.touch_metadata_modified()
        self.project_manager.save_project()
        if self.audit_logger is not None:
            actor = self.access_manager.level if self.access_manager is not None else ""
            # Deliberately untranslated, plain diagnostic text (task:
            # metadata content is operator data, never translated - and
            # matches this codebase's existing convention for audit/alarm
            # detail strings, e.g. SafetyKernel's own audit records).
            self.audit_logger.record(
                "PROJECT_METADATA_CHANGE", actor,
                f"Project properties updated (name: '{name}')", success=True,
            )
        self.accept()
