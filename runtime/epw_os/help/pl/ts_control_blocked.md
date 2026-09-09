# Sterowanie zablokowane

Gdy okno sterowania aparatem (Main View) albo przycisk Force (Control
Outputs) pokazuje, że komenda jest niedozwolona, przyczyna jest zawsze
jedna z poniższych — program pokazuje ją wprost w oknie:

1. **EMERGENCY STOP aktywny** — zatrzymanie awaryjne blokuje wszystkie
   komendy, do czasu jego skasowania.
2. **Docelowe urządzenie w stanie COMM_FAILURE** — patrz
   [Urządzenie pokazuje OFFLINE](help://ts_device_offline).
3. **System w stanie niezdrowym** — monitor stanu zdrowia
   (safety_kernel) wykrył problem z urządzeniem lub systemem. Patrz
   [Monitorowanie zdrowia systemu](help://saf_kernel) — komendy wracają
   samoczynnie, gdy stan zdrowia wraca do normy (zatrzask alarmu i tak
   trzeba osobno potwierdzić na stronie Alarmy).
4. **Reguła logiki sterowania** — jeśli w projekcie wczytano program
   logiki, jego reguły interlockowe mogą blokować konkretną komendę.
   Brak wczytanego programu logiki **nie jest** traktowany jako awaria —
   to normalny stan, sterowanie ręczne wtedy działa.

To NIE jest kwestia poziomu dostępu — nawet Engineer nie obejdzie
żadnego z tych warunków. Jeśli powód blokady nie pasuje do żadnego z
powyższych, to znaczy, że warto to zgłosić jako coś, czego ta strona
pomocy jeszcze nie opisuje.
