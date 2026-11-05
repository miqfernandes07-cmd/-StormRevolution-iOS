# Áudio — buffering PCM implementado

A camada de saída iOS deve consumir PCM por Core Audio/AVAudioEngine; o formato
XMA do Xbox requer decodificação separada. Sem corpus local não foram identificados
containers, canais, loops, callbacks nem idiomas. Nenhum stub retorna sucesso de
reprodução. Não há dependência FFmpeg incorporada; avaliar configuração e obrigações
LGPL antes de integrar.

`pcm_ring.h/.cpp`: fila SPSC limitada de PCM float intercalado, sem alocações nos
caminhos de escrita/leitura, contadores de overflow/underrun e silêncio na falta
de frames. Testes de host e contrato estão em `tests/test_audio.cpp` e
[`docs/AUDIO.md`](../../docs/AUDIO.md). Esse buffering não produz som nem comprova
decodificação XMA. Próxima integração: saída/interrupção em dispositivo Apple com
áudio próprio.
