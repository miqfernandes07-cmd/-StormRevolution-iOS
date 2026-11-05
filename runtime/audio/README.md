# Áudio — não implementado

A camada de saída iOS deve consumir PCM por Core Audio/AVAudioEngine; o formato
XMA do Xbox requer decodificação separada. Sem corpus local não foram identificados
containers, canais, loops, callbacks nem idiomas. Nenhum stub retorna sucesso de
reprodução. Não há dependência FFmpeg incorporada; avaliar configuração e obrigações
LGPL antes de integrar. Próximo teste independente: fila PCM limitada e tratamento
de underrun, seguido de saída/interrupção em dispositivo Apple com áudio próprio.
