# CM Android

Repositório de build Android do projeto CM, baseado no OpenFoot Manager (GPLv3).

## Como funciona

O GitHub Actions:
1. baixa a revisão original do OpenFoot Manager usada na adaptação;
2. aplica o patch mobile/PT-BR do CM;
3. instala Rust + Android SDK/NDK;
4. gera um APK Android de teste;
5. publica o APK como artefato do workflow.

Base upstream: openfootmanager/openfootmanager  
Revisão fixada: `8f6659f5022edcb80529661b0d4d416430c9b6b9`

A adaptação continua sob GPLv3.

Build Android automático configurado.
