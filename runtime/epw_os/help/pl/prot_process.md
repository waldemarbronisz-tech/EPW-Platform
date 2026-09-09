# Zabezpieczenia procesowe

Minimalny, zbudowany od zera moduł: wybierz istniejący punkt
**Wejścia Analogowego**, ustaw **próg górny** i **dolny**, opcjonalną
**histerezę** i opcjonalną **zwłokę** — to cała konfiguracja. W
przeciwieństwie do Zabezpieczeń elektrycznych, ten moduł faktycznie
ewaluuje na żywo: w chwili, gdy wartość podpiętego punktu wychodzi
poza okno [dolny, górny], po uwzględnieniu histerezy i zwłoki,
zabezpieczenie pokazuje **PRZEKROCZONY**.

- **Histereza** — jak daleko *w głąb* okna odczyt musi wrócić, zanim
  Przekroczenie się wyczyści. Zapobiega drganiu, gdy odczyt siedzi
  tuż przy progu. Samo wyczyszczenie jest zawsze natychmiastowe, bez
  zwłoki.
- **Zwłoka** — jak długo odczyt musi pozostawać poza oknem, zanim
  Przekroczenie faktycznie się zatrzaśnie. Filtruje krótki skok albo
  zakłócenie; 0 = zatrzaskuje się w chwili przekroczenia okna.
- **Włączone** — zabezpieczenie można tymczasowo wyłączyć bez
  usuwania go; wyłączone zabezpieczenie nigdy nie pokazuje
  Przekroczenia, niezależnie od bieżącej wartości.

Tak jak każdy inny moduł alarmowo-nadzorczy w tym programie, ten
**nigdy nie steruje żadnym wyjściem**. Wystawia tylko tag sygnałowy
tylko-do-odczytu, `Process.<id>.Exceeded`, dla programu logiki, który
zareaguje tak, jak wymaga tego instalacja — włączy alarm, uruchomi
wentylator, cokolwiek pasuje. Sama reakcja należy w całości do tej
logiki.

Dodawanie, edycja lub usuwanie zabezpieczenia wymaga poziomu
**Inżyniera**; podgląd tabeli nie wymaga żadnego konkretnego poziomu.

Ta strona wcześniej nie istniała — przed nią nigdzie w programie nie
było działającej funkcji progów procesowych (patrz
[Zabezpieczenia elektryczne a procesowe](help://prot_what), dlaczego
dawna kategoria Environmental tej starej strony nie liczy się jako
poprzedniczka).
