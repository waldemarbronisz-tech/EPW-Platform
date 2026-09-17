# Ekran osadzony w projekcie (Synoptyka)

**Widok główny → Synoptyka** pokazuje na żywo ekran narysowany w
Studio (Schemat synoptyczny) i zapisany w pliku projektu (`projekt.epw`,
sekcja `screens`). Każdy symbol z przypisanym aparatem (**Aparat** w
edytorze) podąża za stykiem potwierdzenia tego aparatu: wyłącznik lub
stycznik rysuje się jako ZAŁĄCZONY/WYŁĄCZONY, lampka ŚWIECI/NIE ŚWIECI,
wentylator PRACUJE/STOI, zawór OTWARTY/ZAMKNIĘTY; wyświetlacz pomiaru
pokazuje wartość analogową z jednostką; mierniki i panele sygnalizacji
czytają te same aparaty. Symbol, którego potwierdzenia brakuje albo
nie da się go odczytać, rysowany jest w wyglądzie FAULT, jeśli symbol
taki ma.

**Sterowanie:** kliknięcie aparatu SWITCHED pyta o potwierdzenie i
wysyła polecenie, którego wymaga stan (ZAŁĄCZ gdy wyłączony, WYŁĄCZ gdy
załączony) — te same uprawnienia Operatora i ta sama droga polecenia co
na schemacie jednokreskowym. Gdy stan aparatu nie jest jeszcze znany,
polecenie nie jest proponowane.

**Gdy nic nie jest rysowane:** strona mówi dlaczego — projekt nie ma
ekranu, osadzony ekran został odrzucony albo na tym sterowniku brakuje
pliku biblioteki symboli (`shared/symbols/geometry.json`, eksportowanego
z Edytora Synoptyki; symbole rysowane są wtedy jako proste ramki).

**Przewody** mają kolor według sieci, do której należą, jak w edytorze:
sieć zasilana z punktu granicznego ŹRÓDŁO albo z wyjścia aparatu, którego
potwierdzenie mówi „załączony", jest pod napięciem (czerwona dla
elektryki, niebieska dla wody, bursztynowa dla wentylacji); reszta jest
szara. Typ symbolu, którego obecna biblioteka edytora już nie ma,
pokazywany jest jako purpurowa przerywana ramka.
