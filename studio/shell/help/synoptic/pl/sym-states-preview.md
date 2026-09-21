# 6.3 Stany symbolu i podglad w edytorze

Kazdy typ symbolu deklaruje w rejestrze wlasna liste dopuszczalnych stanow (`allowedStates`) i stan domyslny. Przyklad: dioda sygnalizacyjna ma ON/OFF/QUALITY, miernik (SCADA, statyczny symbol - patrz [7.1](help://synoptic/elem-meter)) nie ma zadnego stanu wlasnego.

Poniewaz edytor nie ma zywych danych, aktualnie WYSWIETLANY stan pochodzi z pola `editor.preview_state` na obiekcie - to reczne ustawienie w Properties, sluzace wylacznie do zobaczenia, jak symbol wyglada w danym stanie podczas projektowania, nigdy odczyt z prawdziwego sprzetu.
