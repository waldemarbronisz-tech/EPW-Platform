# Schemat synoptyczny

Main View to strona startowa programu — schemat jednokreskowy instalacji
przykładowej, z lewej strony ekranu.

Układ (od góry): Zasilanie wejściowe → **Q1** (wyłącznik, DO01) →
**KMG** (stycznik generatora, DO02) → szyna zbiorcza → dwa odejścia:
**KM1** (stycznik, DO03) zasilający "DOM" i **KM2** (stycznik, DO04)
zasilający "WARSZTAT".

Każdy aparat rysowany jest w kolorze pokazującym jego aktualny stan
(otwarty/zamknięty) i reaguje na kliknięcie — patrz
[Sterowanie aparatami i wymagane uprawnienia](help://mv_control).
Nazwy "DOM"/"WARSZTAT" oraz opisy aparatów pochodzą z tych samych
opisów, które ustawia się w Control Outputs — zmiana opisu tam pojawi
się tutaj po ponownym otwarciu programu.

## Przyciski

Ekran może mieć **przyciski** (symbol „Przycisk” w edytorze). Przycisk
nie steruje aparatem — pisze jeden **bit wewnętrzny WE** logiki
(np. `M.START`), a logika czyta go blokiem „Wejście bitowe”. Nasadka
przycisku pokazuje wartość bitu: zielona = TRUE. Tryb ustawia projektant:
**przełączanie** (każde kliknięcie odwraca bit) albo **impuls** (TRUE,
po zadanym czasie FALSE). Zapis podlega tym samym zasadom co na stronie
[Bity wewnętrzne](help://dio_internal_bits): poziom dostępu z rejestru
bitu, wpis w dzienniku audytowym, bit wymuszony ze Studia nie daje się
przełączyć — odmowa pokazuje powód.
