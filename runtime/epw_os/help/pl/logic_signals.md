# Co widzi program logiki

Poza zwykłymi adresami punktów tego projektu (`ELA1.DI.1`, `ADA1.DO.3`
oraz punkty analogowe z ich wartościami inżynierskimi) program może
czytać i pisać to, co poniżej.

## Bity wewnętrzne i retencyjne

Bity `M.` to własny brudnopis programu. Bity `MR.` / `MWR.` są tym
samym, tyle że **przeżywają restart**: ich wartości leżą we własnym
pliku stanu sterownika i wracają przy ponownym starcie — ale tylko dla
tych identyfikatorów, które bieżący program nadal deklaruje jako
retencyjne. Wartość po programie, który już ich nie zna, nie jest
wskrzeszana.

## Sygnały systemowe (`SYS.*`)

Stan samego sterownika jako sygnały: czy komunikacja jest sprawna, jaki
jest poziom dostępu, czy działa tryb szkoleniowy, czy zegar jest
zsynchronizowany, a do tego generatory impulsów i migania — do
odmierzania czasu bez budowania łańcucha przekaźników czasowych.

## Sygnały alarmówki (`SSWIN.*`)

Cała alarmówka jako sygnały, których może użyć schemat.

**Odczyty:** `ARMED` (wszystkie strefy uzbrojone, w pełni),
`ARMED_PARTIAL` (część stref albo dozór nocny), `DISARMED`,
`READY_TO_ARM`, `EXIT_DELAY`, `ENTRY_DELAY`, `DELAY_REMAINING`,
`ALARM_ACTIVE`, `ALARM_LATCHED`, `ALARM_MEMORY`, `TAMPER`, `FAULT`,
`LAST_TRIGGER`, `ACTIVE_COUNT` oraz sygnalizator: `SIREN_ACTIVE`,
`SIREN_TIME_LEFT`, `STROBE_ACTIVE`, `PANIC` — patrz
[Sygnalizator](help://intr_sounder).

**Komendy:** `CMD_ARM`, `CMD_ARM_PARTIAL` (noc), `CMD_DISARM`,
`CMD_RESET`, `CMD_SILENCE`. Działają na **wszystkie strefy** — komendy
z katalogu nie mają strefy do wskazania — i wykonują się na **zboczu
narastającym**, więc blok trzymający sygnał w jedynce nie powtarza
komendy co skan.

Komenda sprawdza też poziom dostępu, który deklaruje **sam blok**. Logic
Studio to wyłącznie zapisuje; egzekwuje ten sterownik.

## Dlaczego nie ma tu syreny

Bo to nie jest sygnał, który ten sterownik prowadzi — to sygnał, który
Ty podpinasz. `SSWIN.SIREN_ACTIVE` mówi, że sygnalizator ma dźwięczeć;
na które wyjście to trafi i przez jakie blokady, jest linią Twojego
schematu. Patrz [Sygnalizator](help://intr_sounder).
