# Áudio: fila PCM implementada

`runtime/audio/pcm_ring.h` e `.cpp` implementam uma fila limitada de PCM `float`
intercalado. Esse componente transporta amostras já decodificadas; não reproduz
áudio, não decodifica XMA e não representa uma implementação dos serviços de áudio
do Xbox 360. Nenhum arquivo comercial foi usado nos testes.

## Contrato

- Um produtor chama `write`; um consumidor chama `read`. Cada papel pertence a
  uma única thread de cada vez. Os contadores podem ser consultados por outra
  thread. Destruir a fila exige interromper e aguardar ambos os participantes.
- A construção valida taxa de 8.000 a 192.000 Hz, 1 a 8 canais e capacidade em
  frames potência de dois, de 1 a 1.048.576. Essas faixas são limites do componente,
  não uma promessa de suporte do hardware. Há no máximo 32 MiB de amostras.
- Cada chamada solicita no máximo a capacidade. O chamador fornece espaço para
  `frames × canais` floats e mantém o buffer válido até o retorno. Não há conversão
  de formato, resampling, clipping, mistura ou substituição de NaN.
- A escrita copia o prefixo que cabe e descarta os frames mais novos excedentes.
  Retorna a quantidade aceita e soma os descartados a `overflow_frames`.
- A leitura copia o prefixo disponível e preenche os frames faltantes com zeros.
  Retorna somente a quantidade de frames consumidos e soma os faltantes a
  `underrun_frames`. Frames de silêncio inseridos não avançam o índice de leitura.
- Ponteiro nulo com solicitação não vazia e solicitação acima da capacidade
  retornam erro sem alterar fila, saída ou contadores. Zero frames aceita nulo.
- Contadores saturam em `UINT64_MAX`; os dois valores são leituras independentes,
  não uma captura simultânea da posição de reprodução.

Os índices usam acquire/release: publicação pelo produtor acontece depois de
copiar amostras; devolução de slots pelo consumidor acontece depois de copiá-las
para a saída. Contadores de diagnóstico usam relaxed. A capacidade potência de
dois mantém o mapeamento de slots no rollover dos índices unsigned de 64 bits.
Não há reset concorrente, seek, descarte por outro consumidor ou acesso direto ao
armazenamento. Reinicializar exige parar as threads e construir outra fila.

`write` e `read` são `noexcept`, não alocam e não usam mutex. A implementação de
`std::atomic<uint64_t>` depende da plataforma; `atomics_are_lock_free()` permite
consultá-la. Isso não certifica prazos de callbacks, latência ou segurança para
tempo real. A integração Apple deverá medir esses aspectos no aparelho e manter
alocação, logs, filesystem e decodificação fora do callback.

## Verificação executada

Linux x86_64, GCC 14.2, C++17 e UBSan: testes de formato inválido, buffers, limites,
estéreo/mono/8 canais, wraparound, overflow, underrun e ordem de 100.000 frames em
duas threads. Os valores são contadores numéricos produzidos pelo próprio teste,
não áudio extraído do jogo. As verificações permanecem ativas em Release.

```bash
g++ -std=c++17 -Wall -Wextra -Wpedantic -Werror -pthread \
  -fsanitize=undefined -fno-sanitize-recover=all -Iruntime \
  runtime/audio/pcm_ring.cpp tests/test_audio.cpp -o /tmp/storm-audio-tests
/tmp/storm-audio-tests
```

Próxima etapa: conectar PCM de autoria própria a Core Audio/AVAudioEngine, tratar
interrupções e mudanças de rota, testar saída real, medir underruns e somente depois
investigar containers/XMA e sincronização do jogo. Fontes japonesas serão preservadas
quando identificadas na cópia local; não foram inspecionadas nesta iteração.
