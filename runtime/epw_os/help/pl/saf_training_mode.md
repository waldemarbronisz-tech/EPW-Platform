# Tryb ćwiczebny

**Settings > Tryb ćwiczebny** — przełącznik widoczny i dostępny tylko na
poziomie **Engineer**. Gdy jest zaznaczony, cały program działa
zupełnie normalnie, ale żaden rozkaz nie dociera faktycznie do
sterownika, więc nic na prawdziwym sprzęcie nie może się przełączyć.
Służy do nauki obsługi i pokazywania systemu bez ryzyka, że coś
faktycznie zadziała.

## Po co to jest

Dziś jedynym, co stoi między operatorem a prawdziwym sprzętem, jest to,
że sterowniki są symulowane. Po podłączeniu prawdziwego sterownika ten
przypadkowy bezpiecznik znika. Tryb ćwiczebny to dokładnie to samo
zabezpieczenie, tylko jawne i niezależne od tego, jaki sterownik jest
skonfigurowany — działa identycznie, niezależnie od tego, czy za nim
stoi `SIM_DRIVER`, czy prawdziwy sterownik.

## Co się naprawdę zmienia

Nic w sposobie podejmowania decyzji o rozkazie. Rozkaz nadal przechodzi
przez całą normalną ścieżkę — sprawdzenie poziomu dostępu, blokady,
CommandManager, własne sprawdzenia bezpieczeństwa platformy — bez
żadnych skrótów i bez żadnych wyjątków. Nadal jest widoczny w rejestrze
zdarzeń dokładnie tak samo, jak każdy inny rozkaz.

Jedyna różnica pojawia się w samym ostatnim kroku: zamiast dotrzeć do
warstwy sterowników, rozkaz jest po cichu zatrzymywany dokładnie na jej
granicy. Sprzężenie zwrotne nadal jest symulowane w sposób realistyczny,
więc aparat nadal widocznie "zmienia stan" na ekranie — interfejs
zachowuje się tak, jakby rozkaz naprawdę przeszedł. Czego nigdy nie ma,
to jakiegokolwiek faktycznego zapisu na sprzęt.

## Co pozostaje bez zmian

Uprawnienia i blokady działają identycznie niezależnie od tego, czy Tryb
ćwiczebny jest włączony, czy wyłączony. Rozkaz zablokowany przez
blokadę, zbyt niski poziom dostępu albo własne sprawdzenia bezpieczeństwa
platformy jest blokowany w Trybie ćwiczebnym dokładnie tak samo, jak w
trybie normalnym — Tryb ćwiczebny niczego nie zmienia w tym, co jest
*dozwolone*, tylko w tym, czy dozwolony rozkaz fizycznie dociera do
sprzętu.

## Wskaźnik — niemożliwy do przeoczenia

Gdy Tryb ćwiczebny jest aktywny, pasek statusu pokazuje wyraźnie
kolorowaną etykietę ostrzegawczą, a cały główny obszar roboczy zyskuje
kolorową ramkę. Oba pojawiają się razem właśnie po to, żeby ten tryb
nigdy nie umknął uwadze — nikt nie powinien sądzić, że steruje
prawdziwym urządzeniem, gdy w rzeczywistości działa Tryb ćwiczebny.

## Włączanie i wyłączanie

Każde włączenie i wyłączenie Trybu ćwiczebnego jest zapisywane w
[Dzienniku audytowym](help://ea_audit_log) — kto i kiedy to zmienił.

Tryb ćwiczebny **nigdy nie jest zapamiętywany między uruchomieniami
programu**. Program zawsze startuje w trybie normalnym; włączenie Trybu
ćwiczebnego trzeba powtórzyć świadomie w każdej sesji.
