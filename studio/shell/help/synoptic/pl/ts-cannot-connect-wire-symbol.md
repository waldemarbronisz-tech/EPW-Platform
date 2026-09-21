# Nie da sie przylaczyc przewodu do symbolu

OBJAW: przewod konczy sie obok symbolu, ale nie wyglada na polaczony (nie ma kropki wezlowej, siec nie obejmuje symbolu).

PRZYCZYNA: polaczenie powstaje wylacznie z DOKLADNEGO dotkniecia punktu siatki zacisku ([5.1](help://synoptic/sch-node-model)) - jesli koniec przewodu ladowal o piksel obok, geometrycznie nie stykaja sie w ogole, mimo ze wizualnie wygladaja blisko.

CO ZROBIC: upewnij sie, ze przyciaganie do siatki jest wlaczone (View > Snap to Grid), oddal/przybliz widok, zeby dokladnie trafic w widoczny znacznik zacisku (pojawia sie przy najechaniu na symbol), i zakoncz tam rysowanie przewodu.
