# 4.8 Formularz aparatu i walidacja na zywo

Formularz aparatu waliduje NA ZYWO, przy kazdej zmianie pola, przez `validateDeviceRegistry` (jedyne miejsce, gdzie jakakolwiek regula jest faktycznie rozstrzygana) - kazdy blad pojawia sie natychmiast pod polem, ktorego dotyczy, a przycisk Zapisz pozostaje wygaszony, dopoki istnieje choc jeden blad.

Picker adresu kanalu wyszarza kazdy kanal juz zajety przez inny aparat, pokazujac jego identyfikator w nawiasie - dzieki temu kolizja kanalow jest praktycznie niemozliwa do przypadkowego wprowadzenia, mimo ze `CHANNEL_ADDRESS_COLLISION` formalnie nadal istnieje jako regula sprawdzana przy zapisie.

Pole Id jest edytowalne tylko przy tworzeniu nowego aparatu (rozwijana lista lokalizacji + wolny sufiks) i zablokowane przy edycji istniejacego - powod jest w [4.2](help://synoptic/dev-naming).
