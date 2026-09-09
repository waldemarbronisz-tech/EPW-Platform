# Skąd się biorą alarmy

Strona Alarmy pokazuje wszystkie alarmy podniesione przez program.
Obecnie realne (nie testowe) źródła alarmów to:

- **Awaria komunikacji z urządzeniem** — gdy dowolne z czterech
  monitorowanych urządzeń (patrz [Panel statusu urządzeń](help://mv_device_status))
  przejdzie w stan COMM_FAILURE.
- **EMERGENCY STOP** — gdy tag zatrzymania awaryjnego jest aktywny.
- **Awaria stanu zdrowia systemu** — gdy monitor stanu zdrowia
  (safety_kernel) wykryje niezdrowe urządzenie albo cały system jako
  niezdrowy. Szczegóły w rozdziale
  [Monitorowanie zdrowia systemu](help://saf_kernel).

Alarm znika z listy aktywnych, gdy jego przyczyna ustąpi — ale, jeśli
nie został wcześniej potwierdzony, zostaje w stanie wymagającym
kwitowania. Patrz [Różnica między alarmem aktywnym a niepotwierdzonym](help://alm_states).
