# Filtrowanie fałszywych alarmów

Każdej linii dozorowej można nadać do czterech dodatkowych parametrów
(poziom Engineer, w tym samym oknie Konfiguruj linie co jej typ i stan
spoczynkowy), które sprawiają, że zwykła czujka zachowuje się jak
droższa, z wbudowanym filtrowaniem. Każdy z nich domyślnie jest
**wyłączony** — linia dodana przed wprowadzeniem tej funkcji albo taka,
której nigdy nie dotkniesz, działa dokładnie tak, jakby jej w ogóle nie
było.

**Minimalny czas naruszenia** — wejście musi być aktywne dłużej niż ten
czas, żeby w ogóle liczyło się jako naruszenie. Filtruje krótkie
zakłócenia i drgania styków: zadziałanie krótsze niż próg nigdy nie
trafia do tagu `Security.Line.<id>.Violated`, nigdy nie alarmuje i nie
liczy się do niczego poniżej. 0 = wyłączone.

**Liczba naruszeń / w oknie** — ile osobnych naruszeń w oknie czasowym
jest potrzebnych, żeby linia faktycznie zaalarmowała. Pojedyncze
naruszenie poniżej progu nic nie robi; osiągnięcie liczby w oknie
alarmuje natychmiast, a licznik zaczyna się od nowa. Jeśli kolejne
naruszenie nie nadejdzie przed upływem okna, licznik sam zeruje się do
0 — pojedyncze, dawne naruszenie nigdy nie doliczy się do znacznie
późniejszego. 1 naruszenie potrzebne = wyłączone (każde naruszenie
alarmuje samodzielnie, jak dotychczas).

**Blokada po** — po tylu alarmach z *tej samej linii* w jednym cyklu
uzbrojenia linia automatycznie się blokuje: przestaje alarmować w
ogóle, po cichu, aż do rozbrojenia strefy. Chroni przed jedną linią,
która utknęła w naruszeniu i alarmuje w kółko. Zablokowana linia
pokazuje "(zablokowana)" przy swoim stanie na stronie Podgląd,
a sam fakt zablokowania trafia do dziennika audytowego. Rozbrojenie
strefy zawsze czyści blokadę (i licznik alarmów) każdej jej linii, więc
kolejny cykl uzbrojenia zaczyna się od zera. 0 = wyłączone.

**Czas trwania alarmu** — gdy linia wywoła ALARM, to jest minimalny
czas, przez jaki ten stan jest utrzymywany. Po jego upływie, jeśli
linia nie jest już naruszona, strefa automatycznie wraca do UZBROJONA —
bez potrzeby ręcznego rozbrajania i uzbrajania dla czegoś, co samo się
już wyciszyło. Jeśli linia *nadal* jest naruszona w momencie upływu
czasu, strefa zostaje w ALARM (sprawdzane ponownie w chwili, gdy linia
faktycznie się wyciszy). 0 = wyłączone — strefa zostaje w ALARM, dopóki
ktoś jej nie rozbroi, tak jak każda linia bez tego ustawienia.

Nic z tego nie zmienia tego, co robi typ linii, jak działa uzbrajanie
ani co moduł robi z naruszeniem, gdy już zdecyduje się zaalarmować —
patrz [Typy linii](help://intr_line_types) i
[Uzbrajanie, rozbrajanie i czasy](help://intr_arming). Moduł nadal w
żaden sposób nie steruje żadnym wyjściem — patrz
[Sygnały dla logiki](help://intr_tags) po opis dwóch nowych tagów
(`MultiplicityCounting`, `Locked`), które te filtry publikują.
