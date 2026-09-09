# Polska terminologia EPW-OS — do przeglądu

**Do przeglądu przez:** Waldek  
**Wygenerowano:** 2026-08-27 (po dodaniu strony Analog Inputs do nawigacji)  
**Źródło:** `epw_os/i18n/locales/pl.json` porównane z `en.json`

Lista zawiera **wszystkie** napisy przetłumaczone dotąd na polski: pasek menu górny (z podmenu *File* i *Settings*), lewe menu nawigacyjne, pasek statusu oraz kluczowe elementy UI (popupy Language / Change PIN / dostęp / timeout, dialogi menu *File*). Treść samych stron (Digital Inputs, Analog Inputs, Control Outputs itd.) **nie jest jeszcze tłumaczona** — to kolejne etapy.

### Jak zgłaszać poprawki

Przy każdej pozycji jest **Klucz** (identyfikator w plikach JSON). Żeby zgłosić poprawkę, wystarczy podać: `klucz` → proponowany polski tekst. Nie ruszamy tu tłumaczeń — decyzja należy do Ciebie.

Oznaczenia w tekście:
- `{n}` — wstawiana liczba (np. liczba urządzeń offline)
- `{level}` — wstawiana nazwa poziomu dostępu (Użytkownik / Operator / Inżynier)
- ` / ` w kolumnie — w oryginale jest w tym miejscu złamanie linii

---

## Tytuł aplikacji / okna

| Klucz | Angielski (oryginał) | Polski (obecny) |
|---|---|---|
| `app.title` | EPW OS - Ela Power Watch | EPW OS - Ela Power Watch |

## Pasek menu górny (kolejność jak na pasku)

| Klucz | Angielski (oryginał) | Polski (obecny) |
|---|---|---|
| `menu.file` | File | Plik |
| `menu.view` | View | Widok |
| `menu.project` | Project | Projekt |
| `menu.devices` | Devices | Urządzenia |
| `menu.tools` | Tools | Narzędzia |
| `menu.settings` | Settings | Ustawienia |
| `menu.help` | Help | Pomoc |

## Menu File — pozycje podmenu (kolejność od góry)

| Klucz | Angielski (oryginał) | Polski (obecny) |
|---|---|---|
| `menu.file_new` | New Project | Nowy projekt |
| `menu.file_open` | Open Project... | Otwórz projekt... |
| `menu.file_save` | Save Project | Zapisz projekt |
| `menu.file_save_as` | Save Project As... | Zapisz projekt jako... |
| `menu.file_export` | Export Project (Backup)... | Eksportuj projekt (kopia zapasowa)... |
| `menu.file_import` | Import Project... | Importuj projekt... |
| `menu.file_exit` | Exit | Wyjście |

## Menu Settings — pozycje podmenu (otwierają okienka popup)

| Klucz | Angielski (oryginał) | Polski (obecny) |
|---|---|---|
| `menu.settings_language` | Language... | Język... |
| `menu.settings_change_pin` | Change PIN... | Zmień PIN... |

## Lewe menu nawigacyjne — przyciski (kolejność od góry)

| Klucz | Angielski (oryginał) | Polski (obecny) |
|---|---|---|
| `nav.main_view` | MAIN VIEW | WIDOK GŁÓWNY |
| `nav.power_quality` | POWER QUALITY | JAKOŚĆ ENERGII |
| `nav.digital_inputs` | DIGITAL INPUTS | WEJŚCIA CYFROWE |
| `nav.analog_inputs` | ANALOG INPUTS | WEJŚCIA ANALOGOWE |
| `nav.control_outputs` | CONTROL OUTPUTS | WYJŚCIA STERUJĄCE |
| `nav.protection_settings` | PROTECTION SETTINGS | NASTAWY ZABEZPIECZEŃ |
| `nav.events` | EVENTS | ZDARZENIA |
| `nav.system_topology` | SYSTEM TOPOLOGY | TOPOLOGIA SYSTEMU |
| `nav.engineer_mode` | ENGINEER MODE | TRYB INŻYNIERA |

## Pasek statusu (dół okna, od lewej)

| Klucz | Angielski (oryginał) | Polski (obecny) |
|---|---|---|
| `statusbar.user` | User | Użytkownik |
| `statusbar.db` | DB | Baza |
| `statusbar.fps` | FPS | FPS |
| `statusbar.latency` | Latency | Opóźnienie |
| `statusbar.scan` | Scan | Skan |
| `statusbar.simulation_mode` | SIMULATION MODE | TRYB SYMULACJI |
| `statusbar.live_mode` | LIVE MODE | TRYB RZECZYWISTY |

## Pasek górny (nad treścią)

| Klucz | Angielski (oryginał) | Polski (obecny) |
|---|---|---|
| `topbar.project` | Project | Projekt |
| `topbar.alarms` | Alarms | Alarmy |
| `topbar.access` | Access | Dostęp |
| `topbar.comm_ok` | COMM: OK | ŁĄCZNOŚĆ: OK |
| `topbar.comm_offline` | COMM: {n} OFFLINE | ŁĄCZNOŚĆ: {n} OFFLINE |

## Wybór poziomu dostępu (rozwijane menu w pasku górnym)

| Klucz | Angielski (oryginał) | Polski (obecny) |
|---|---|---|
| `access.menu_user` | User (view only) | Użytkownik (tylko podgląd) |
| `access.menu_operator` | Operator (control from Main View) | Operator (sterowanie z Widoku Głównego) |
| `access.menu_engineer` | Engineer (full access, incl. Force) | Inżynier (pełny dostęp, w tym Force) |
| `access.user` | User | Użytkownik |
| `access.operator` | Operator | Operator |
| `access.engineer` | Engineer | Inżynier |

## Popup: Język (Settings > Język...)

| Klucz | Angielski (oryginał) | Polski (obecny) |
|---|---|---|
| `settings.language_section` | LANGUAGE | JĘZYK |
| `settings.language_label` | Interface language: | Język interfejsu: |
| `settings.language_hint` | The interface language changes after EPW OS is restarted. | Język interfejsu zmienia się po ponownym uruchomieniu EPW OS. |
| `dialog.restart_needed` | The interface language will change after EPW OS is restarted. | Język interfejsu zmieni się po ponownym uruchomieniu EPW OS. |

## Popup: Zmiana PIN-u (Settings > Zmień PIN...)

| Klucz | Angielski (oryginał) | Polski (obecny) |
|---|---|---|
| `settings.pin_change_title` | Change PIN | Zmiana PIN-u |
| `settings.pin_header` | {level} PIN | PIN - {level} |
| `settings.pin_info` | Access control PINs are stored as SHA-256 hashes in epw_os/config/access.local.json (not committed to source control). Changing a PIN here requires entering the current PIN for that level, regardless of what access level this session is currently logged in at. | PIN-y kontroli dostępu są przechowywane jako skróty SHA-256 w epw_os/config/access.local.json (poza kontrolą wersji). Zmiana PIN-u wymaga podania bieżącego PIN-u dla danego poziomu, niezależnie od tego, na jakim poziomie dostępu zalogowana jest bieżąca sesja. |
| `settings.old_pin` | Old PIN: | Stary PIN: |
| `settings.new_pin` | New PIN: | Nowy PIN: |
| `settings.confirm_pin` | Confirm New PIN: | Potwierdź nowy PIN: |
| `settings.save` | Save | Zapisz |
| `settings.pin_updated` | PIN updated. | PIN zaktualizowany. |
| `settings.pin_old_wrong` | Old PIN is incorrect. | Stary PIN jest nieprawidłowy. |
| `settings.pin_not_numeric` | New PIN must be numeric. | Nowy PIN musi być liczbą. |
| `settings.pin_mismatch` | New PINs do not match. | Nowe PIN-y nie są zgodne. |
| `settings.pin_same` | New PIN must differ from the old one. | Nowy PIN musi różnić się od starego. |

## Popup: żądanie PIN-u (wejście w tryb Operator / Engineer)

| Klucz | Angielski (oryginał) | Polski (obecny) |
|---|---|---|
| `pin_prompt.title` | {level} ACCESS REQUIRED | WYMAGANY DOSTĘP: {level} |
| `pin_prompt.prompt` | Enter {level} PIN to continue: | Podaj PIN poziomu {level}, aby kontynuować: |
| `pin_prompt.unlock` | UNLOCK | ODBLOKUJ |
| `pin_prompt.cancel` | CANCEL | ANULUJ |
| `pin_prompt.incorrect` | Incorrect PIN. | Nieprawidłowy PIN. |

## Popup: koniec sesji (5 min bezczynności)

| Klucz | Angielski (oryginał) | Polski (obecny) |
|---|---|---|
| `timeout_popup.title` | SESSION TIMEOUT | KONIEC SESJI |
| `timeout_popup.message` | No activity detected for 5 minutes. /  / Access level returned to User. | Brak aktywności przez 5 minut. /  / Poziom dostępu przywrócony do Użytkownika. |
| `timeout_popup.ok` | OK | OK |

## Okna dialogowe menu File (potwierdzenia / komunikaty)

| Klucz | Angielski (oryginał) | Polski (obecny) |
|---|---|---|
| `dialog.unsaved_title` | Unsaved changes | Niezapisane zmiany |
| `dialog.unsaved_text` | The current project has unsaved changes. Save them before continuing? | Bieżący projekt ma niezapisane zmiany. Zapisać je przed kontynuacją? |
| `dialog.exit_title` | Exit EPW OS | Zamknij EPW OS |
| `dialog.exit_text` | Close EPW OS? | Zamknąć EPW OS? |
| `dialog.new_created` | New project created (not yet saved). | Utworzono nowy projekt (jeszcze niezapisany). |
| `dialog.saved` | Project saved. | Projekt zapisany. |
| `dialog.exported` | Project exported to a backup copy. | Projekt wyeksportowany do kopii zapasowej. |
| `dialog.imported` | Project imported. | Projekt zaimportowany. |
| `dialog.invalid_project` | The selected file is not a valid EPW OS project. | Wybrany plik nie jest prawidłowym projektem EPW OS. |
| `dialog.open_title` | Open Project | Otwórz projekt |
| `dialog.save_as_title` | Save Project As | Zapisz projekt jako |
| `dialog.export_title` | Export Project (Backup) | Eksportuj projekt (kopia zapasowa) |
| `dialog.import_title` | Import Project | Importuj projekt |
| `dialog.project_filter` | EPW OS Project (*.json) | Projekt EPW OS (*.json) |
| `dialog.info_title` | EPW OS | EPW OS |

---

**Razem: 83 napisów do przeglądu.**

> Nazwy własne języków w rozwijanej liście (English, Polski, Deutsch, Español, Українська, Français, Italiano) są w językach oryginalnych i celowo nietłumaczone.
