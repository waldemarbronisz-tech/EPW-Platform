# 3.1 Lokalizacje

Lokalizacja to KROTKI PRZEDROSTEK identyfikatora aparatu, nie jego nazwa. Przyklady poprawnych kodow: `KOT` (kotlownia), `BRAMA`, `MAG` (magazyn), `OGROD`. Kod musi skladac sie wylacznie z wielkich liter A-Z i cyfr 0-9 (regula `LOCATION_INVALID_CODE` w `DeviceValidation.ts`) - male litery sa odrzucane.

Lokalizacja aparatu jest WYLICZANA z przedrostka jego identyfikatora (czesc przed pierwszym podkresleniem), a NIE przechowywana jako osobne pole na aparacie. Z tego wynika konkretna, praktyczna konsekwencja: przeniesienie aparatu do innej lokalizacji nie jest "edycja" - identyfikator jest niezmienny po utworzeniu ([4.2](help://synoptic/dev-naming)), wiec jedynym sposobem jest USUNIECIE aparatu i UTWORZENIE go od nowa pod nowym identyfikatorem, z tymi samymi wartosciami pol.

Rejestr lokalizacji otwiera sie z menu Aparaty > Rejestry projektu..., zakladka Lokalizacje. Dodawanie wymaga kodu i opisu; edycja pozwala zmienic tylko opis - kod, raz nadany, jest tak samo niezmienny jak identyfikator aparatu, z tego samego powodu (jest juz czescia identyfikatorow istniejacych aparatow).
