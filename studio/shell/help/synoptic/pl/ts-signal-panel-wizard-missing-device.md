# Kreator panelu sygnalizacyjnego nie pokazuje oczekiwanego aparatu

OBJAW: oczekiwany aparat nie pojawia sie na liscie w kreatorze panelu sygnalizacyjnego.

PRZYCZYNA: ten kreator pokazuje wylacznie aparaty SIGNAL i SWITCHED ([7.2](help://synoptic/elem-signal-panel)) - MEASURED i MODULATED nigdy sie tu nie pojawiaja, bo nie maja pojecia stanu dwustanowego do zasygnalizowania diodą.

CO ZROBIC: sprawdz zachowanie tego aparatu w Liscie aparatow - jesli to MEASURED, nalezy do miernika ([7.1](help://synoptic/elem-meter)), nie do panelu sygnalizacyjnego.
