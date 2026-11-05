# Compatibilidade — 2026-11-05

Alvo: iPhone 15 Pro / A17 Pro / ARM64 / iOS 27. Não há aparelho, SDK Apple ou XEX
comercial disponível nesta sessão. Nenhum FPS, compatibilidade iOS 27 ou boot foi
medido. `Validado` será usado somente com escopo e evidência explícitos.

| Componente | Estado objetivo | Evidência / limite |
| --- | --- | --- |
| XEX2 metadados e identidade | Teste automatizado aprovado | 14 testes Python sintéticos em Linux x86_64 |
| Validador aplicado ao XEX comercial | Implementado sem teste com arquivo real | Referência documental; arquivo ausente |
| Decriptação/descompressão/PE/exports | Não implementado | Sem chaves nem extração de imagem |
| Descoberta de funções e tabelas de salto | Não implementado | Necessita imagem e análise específica |
| PPC AOT sintético | Teste automatizado aprovado | 8 testes Python, C++ gerado executado com GCC/UBSan no host |
| Adaptador CLI XenonRecomp | Teste automatizado aprovado | 7 testes de contratos/caminhos/identidade; ferramenta upstream não executada |
| Recompilação XenonRecomp do Storm | Não implementado | Candidato auditado; sem configuração real de funções e sem geração do jogo |
| Runtime C++, memória, vetor, imports, input e arquivos | Teste automatizado aprovado | Build CMake Debug/UBSan e Release, 1038 verificações em Linux x86_64 |
| VMX128, FPU e atomics guest | Não implementado | Helpers de vetor não equivalem a ISA completa |
| Serviços xboxkrnl/XAM do jogo | Não implementado | Resolver existe, contratos do título não |
| Metal de diagnóstico | Implementado sem teste | Fonte MSL/MetalKit; não é renderer Xenos |
| Shaders Xenos/EDRAM/texturas do jogo | Não implementado | Nenhum caminho gráfico do título implementado |
| XMA, áudio/voz/vídeo | Não implementado | Sem decodificador/saída PCM integrada |
| Touch/GameController no iOS | Implementado sem teste | Necessita build Apple e controles/aparelho |
| Aplicativo/importação iOS | Implementado sem teste | Fonte e workflow; sem resultado Xcode |
| Build/IPA em CI | Implementado sem teste | Workflow não executado nesta sessão |

## Estados de entrega independentes

| Etapa | Resultado comprovado |
| --- | --- |
| Compilação local | CMake Debug/UBSan e Release aprovados, biblioteca e testes x86_64; AOT sintético executado |
| Compilação em CI | Não realizada |
| IPA produzido | Não |
| IPA instalado | Não |
| Aplicativo iniciado no simulador | Não |
| Aplicativo iniciado no iPhone | Não |
| Jogo efetivamente executado | Não |

## Etapas do jogo

| Etapa | Estado |
| --- | --- |
| Introdução | Não implementado |
| Menu principal | Não implementado |
| Seleção de personagens | Não implementado |
| Carregamento de arena | Não implementado |
| Batalha | Não implementado |
| Finalização | Não implementado |
| Salvamento/carregamento | Não implementado |

30 FPS é alvo funcional futuro; 60 FPS é alvo de otimização. Escala/limite do
diagnóstico Metal não são resultados do jogo. Nenhuma etapa é `Gameplay funcional`,
`Jogável com limitações` ou `Validado` para o título.
