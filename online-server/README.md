# CM Online — base inicial

Este diretório inicia a evolução do CM para multiplayer online sem alterar o APK Solo enquanto a base da América do Sul ainda está em QA.

## Regras já codificadas

- Sala com código curto.
- Um clube controlado por no máximo um treinador humano.
- Cada comando é associado ao treinador e ao clube que ele controla.
- O servidor rejeita comandos enviados para o clube de outro humano.
- O dia só avança quando todos os humanos conectados estiverem prontos e confirmarem CONTINUAR.
- Estado da sala possui `revision` monotônica para futura sincronização/recuperação.

## Limite desta primeira etapa

O servidor ainda é coordenador de sessão e permissões. A Match Engine e o save completo continuam locais no APK. Antes de liberar multiplayer público, a simulação precisa ser movida para uma autoridade de servidor ou para uma camada determinística validável; o cliente não deve ser a fonte de verdade de resultados, transferências ou calendário.

## Desenvolvimento

```bash
cd online-server
npm install
npm test
npm start
```

Health check: `GET /health`  
WebSocket: `/ws`
