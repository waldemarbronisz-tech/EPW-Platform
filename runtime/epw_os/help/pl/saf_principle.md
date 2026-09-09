# Zasada nadrzędna: "ekran informuje, sprzęt chroni"

To najważniejsza zasada, na której zbudowany jest cały EPW OS —
warto ją rozumieć, zanim zaufa się temu, co pokazuje ekran.

**EPW OS nie jest zabezpieczeniem instalacji i nigdy nie jest wymagany
do tego, żeby zabezpieczenie zadziałało.**

Program działa w Pythonie na komputerze (Orange Pi) — może się zawiesić,
stracić zasilanie albo mieć błąd. Prawdziwą ochronę instalacji realizują
niezależne od tego programu zabezpieczenia elektroenergetyczne i sprzętowy
tor bezpieczeństwa — one działają dalej, nawet jeśli EPW OS przestanie
działać w ogóle.

Rola EPW OS to:

- **pokazywać** stan instalacji i jej zabezpieczeń na ekranie,
- **rejestrować** zdarzenia i alarmy,
- **ułatwiać** ręczne sterowanie, z zachowaniem sensownych blokad.

Rola EPW OS to NIE:

- być jedynym mechanizmem, który powstrzyma awarię,
- decydować samodzielnie o wyłączeniu instalacji w reakcji na
  wykrytą usterkę.

Ta zasada ma bezpośrednie konsekwencje w kodzie programu — patrz
[Monitorowanie zdrowia systemu (safety_kernel)](help://saf_kernel), gdzie
opisano dokładnie, gdzie przebiega granica między "wykrywaniem" a
"reagowaniem".
