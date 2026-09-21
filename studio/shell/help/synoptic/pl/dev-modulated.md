# 4.7 MODULATED - sterowalne plynnie

MODULATED to urzadzenie sterowalne plynnie: zawor modulujacy, falownik. Pola: setpointOutput (adres kanalu AO - wartosc zadana wysylana do sprzetu), opcjonalny feedbackInput (adres kanalu AI - rzeczywista pozycja/predkosc, jesli sprzet ja raportuje), unit, rangeMin/rangeMax, startupValue i safeValue (obie musza miescic sie w zakresie rangeMin..rangeMax).

startupValue i safeValue to, tak jak safeState aparatu SWITCHED ([4.4](help://synoptic/dev-switched)), wartosci nalezace do KONFIGURACJI SPRZETU, nie do logiki ekranu - opisuja, jaka wartosc aparat ma przyjac przy starcie i w stanie bezpiecznym.
