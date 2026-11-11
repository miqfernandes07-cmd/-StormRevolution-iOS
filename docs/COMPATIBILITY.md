# Compatibilidade — 2026-11-11

Alvo: iPhone 15 Pro / A17 Pro / ARM64 / iOS 27. O XEX fornecido pelo usuário está
presente somente no diretório privado e sua identidade foi validada. Não há aparelho
ou SDK Apple local. Nenhum FPS, compatibilidade iOS 27 ou boot foi medido.

| Componente | Estado objetivo | Evidência / limite |
| --- | --- | --- |
| XEX2 metadados e identidade | Teste automatizado aprovado | Parser e testes de regressão no host; versão corrigida para major nos bits superiores e QFE nos inferiores |
| Identidade do XEX fornecido | Validado | Tamanho, SHA-1, Title ID, Media ID e versão correspondem à referência; raw `0x00000004` corresponde a `0.0.0.4` |
| Reconstrução offline e leitura PE | Validado para o arquivo fornecido | Imagem privada reconstruída antes de alterar imports; 9 seções lidas e bases XEX/PE coincidem; assinatura não verificada |
| Imports XEX na imagem original reconstruída | Validado para leitura dos descritores | 569 registros; 291 pares biblioteca/ordinal distintos; 278 thunks pareados, sem tipo desconhecido ou erro de pareamento; serviços nativos não resolvidos |
| Exports | Não implementado | Diretórios PE enumerados; exports ainda não resolvidos |
| Inventário PPC de região raw | Teste automatizado aprovado | Branches e candidatos a funções; não prova limites de funções |
| Recuperação validada das tabelas de salto do Storm | Não implementado | XenonAnalyse executado; zero tabelas recuperadas, sem conclusão de que o jogo não as use |
| Validação completa de funções e fluxo indireto | Não implementado | Configuração e saída preliminares exigem revisão específica do executável |
| PPC AOT sintético | Teste automatizado aprovado | C++ gerado de instruções sintéticas executado com GCC/UBSan no host |
| Adaptador CLI XenonRecomp | Teste automatizado aprovado | Contratos, caminhos e identidade testados; ferramentas upstream também executadas privadamente sobre o XEX |
| Geração XenonRecomp do Storm | Implementado sem compilação nativa aprovada | 242 arquivos C++ privados; 1.643 ocorrências de 28 variantes rejeitadas; auditoria impede tratar a saída como pronta |
| Runtime C++, memória, vetor, imports, input e arquivos | Teste automatizado aprovado | 1.038 verificações em Linux x86_64; ainda sem contratos suficientes para executar o título |
| VMX128, FPU e atomics guest completos | Não implementado | Helpers e testes limitados não equivalem à ISA completa; variantes rejeitadas e sincronização exigem revisão |
| Serviços xboxkrnl/XAM do jogo | Não implementado | Imports identificados; o resolver genérico não implementa os contratos do título |
| Metal de diagnóstico | Implementado sem teste Apple | Fonte MSL/MetalKit; não é renderer Xenos |
| Shaders Xenos/EDRAM/texturas do jogo | Não implementado | Nenhum caminho gráfico do título validado |
| Fila de frames PCM | Teste automatizado aprovado | 33 verificações, incluindo transferência SPSC de 100.000 frames no host |
| XMA, reprodução de áudio/voz/vídeo | Não implementado | Sem decodificador/saída Apple integrada |
| Touch/GameController no iOS | Implementado sem teste Apple | Necessita build Apple e controles/aparelho |
| Aplicativo/importação iOS | Implementado sem teste Apple | Validador de versão corrigido para raw `0x00000004`; sem resultado Xcode |
| Build/IPA iOS em CI | Implementado sem teste Apple | Duas tentativas anteriores encerradas sem runner e sem etapas executadas; troca para `macos-15-intel` pendente de nova execução |

A imagem reconstruída tem 13.762.560 bytes, igual ao tamanho declarado pelo XEX;
o PE declara 14.669.312. Todas as seções estão presentes. O relatório mantém o
diagnóstico `PE_IMAGE_TAIL_UNAVAILABLE`; a cauda não disponível não foi preenchida
artificialmente. Isso exige atenção em qualquer futuro acesso fora das seções.

## Estados de entrega independentes

| Etapa | Resultado comprovado |
| --- | --- |
| Compilação local | Runtime e testes host aprovados; AOT sintético executado. Código gerado do jogo ainda não compilado |
| Testes locais atuais | 62 testes Python + 1.038 verificações do runtime + 33 de PCM; 3/3 grupos CTest aprovados em Linux |
| Compilação em CI host | GCC e Clang aprovados no marco anterior do GitHub Actions |
| Compilação em CI iOS | Não realizada; tentativas anteriores sem runner |
| IPA produzido | Não |
| IPA instalado | Não |
| Aplicativo iniciado no simulador | Não |
| Aplicativo iniciado no iPhone | Não |
| Jogo efetivamente executado | Não |

## Recursos e etapas do jogo

O ZIP de recursos disponibilizado no Drive tem aproximadamente 7,43 GB, acima do
espaço livre disponível neste ambiente. Não foi baixado ou validado. O XEX sozinho
não fornece os modelos, texturas, áudio, arenas e demais dados necessários ao jogo.

| Etapa | Estado |
| --- | --- |
| Introdução | Não implementado |
| Menu principal | Não implementado |
| Seleção de personagens | Não implementado |
| Carregamento de arena | Não implementado |
| Batalha | Não implementado |
| Finalização | Não implementado |
| Salvamento/carregamento | Não implementado |

30 FPS é alvo funcional futuro; 60 FPS é alvo de otimização. Nenhuma etapa é
`Gameplay funcional`, `Jogável com limitações` ou `Validado` para execução do título.
