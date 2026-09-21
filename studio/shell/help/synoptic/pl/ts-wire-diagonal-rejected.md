# Przewod nie chce isc po skosie

OBJAW: przy rysowaniu przewodu ruch myszy po skosie nie daje odcinka po skosie, tylko dwa odcinki pod katem prostym.

PRZYCZYNA: to nie usterka - kazdy odcinek przewodu MUSI byc poziomy albo pionowy (`appendWirePoint` w `WireDrawing.ts`); ruch po skosie jest automatycznie dzielony na poziomy odcinek, a potem pionowy, w jeden naroznik.

CO ZROBIC: to zamierzone zachowanie - jesli potrzebny inny ksztalt naroznika, kliknij posrednie punkty, zeby samemu ustawic, gdzie przewod skreca.
