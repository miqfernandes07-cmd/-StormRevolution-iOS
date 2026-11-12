# Compatibilidade — 2026-11-12

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
| Geração XenonRecomp do Storm | Implementado sem compilação nativa aprovada | Baseline 1643/28; EQV+LFSU/STFSU reduziram a 973/25; 242 C++ privados, ainda incompletos |
| Runtime C++, memória, vetor, imports, input e arquivos | Teste automatizado aprovado | 1.038 verificações em Linux x86_64; ainda sem contratos suficientes para executar o título |
| VMX128, FPU e atomics guest completos | Não implementado | Helpers e testes limitados não equivalem à ISA completa; variantes rejeitadas e sincronização exigem revisão |
| Serviços xboxkrnl/XAM do jogo | Não implementado | Imports identificados; o resolver genérico não implementa os contratos do título |
| Metal de diagnóstico | Executa no simulador | Comando Metal concluído no smoke test; sem comparação de pixels ou tradução Xenos |
| Shaders Xenos/EDRAM/texturas do jogo | Não implementado | Nenhum caminho gráfico do título validado |
| Fila de frames PCM | Teste automatizado aprovado | 33 verificações, incluindo transferência SPSC de 100.000 frames no host |
| XMA, reprodução de áudio/voz/vídeo | Não implementado | Sem decodificador/saída Apple integrada |
| Touch/GameController no iOS | Compila | Código compilado em CI; entrada física/touch ainda sem teste interativo |
| Aplicativo/importação iOS | Compila | App ARM64/simulador compilado; importação real pelo aplicativo Arquivos ainda sem teste |
| Build/IPA iOS em CI | Compila | App ARM64 e simulador x86_64 compilados; IPA de infraestrutura não assinado gerado no run 43162119044, Xcode 16.4/SDK 18.5 |

A imagem reconstruída tem 13.762.560 bytes, igual ao tamanho declarado pelo XEX;
o PE declara 14.669.312. Todas as seções estão presentes. O relatório mantém o
diagnóstico `PE_IMAGE_TAIL_UNAVAILABLE`; a cauda não disponível não foi preenchida
artificialmente. Isso exige atenção em qualquer futuro acesso fora das seções.

## Estados de entrega independentes

| Etapa | Resultado comprovado |
| --- | --- |
| Compilação local | Runtime e testes host aprovados; AOT sintético executado. Código gerado do jogo ainda não compilado |
| Testes locais atuais | 62 testes Python + 1.038 verificações do runtime + 33 de PCM; 3/3 grupos CTest aprovados em Linux |
| Compilação em CI host | GCC/Clang Linux e AppleClang/macOS Intel aprovados |
| Compilação em CI iOS | Aprovada para app de infraestrutura ARM64 e simulador x86_64 |
| IPA produzido | Sim, infraestrutura sem jogo e sem assinatura; exige assinatura posterior |
| IPA instalado | Não |
| Aplicativo iniciado no simulador | Sim; autoteste runtime e conclusão de comando Metal aprovados, sem execução do jogo |
| Aplicativo iniciado no iPhone | Não |
| Jogo efetivamente executado | Não |

## Recursos e etapas do jogo

O índice do ZIP de 7,43 GB foi lido parcialmente: 21 arquivos e 8 diretórios,
9,43 GB descompactados. Seu XEX foi extraído e validado isoladamente; os demais
recursos ainda não foram extraídos ou validados. Ver [ASSETS.md](ASSETS.md). O XEX sozinho
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

## EQV experimental

Patch offline do emissor: EQV sem record passou em 3264 vetores sintéticos de
C++ gerado executado no Linux x86_64 com UBSan. EQV. continua rejeitada. Não é
validação ARM64 nem execução de função comercial. Ver [EQV_PATCH.md](EQV_PATCH.md).
A CI 43163104401 terminou globalmente com sucesso para a infraestrutura iOS;
o patch offline não está ligado ao aplicativo.

## LFSU/STFSU experimental

Emissão guest32 passou em 900 casos sintéticos nativos com UBSan no Linux:
405 com memória upstream e 495 com callbacks de teste verificados. RA=0/MMIO
rejeitados; arredondamento somente nearest. Sem validação ARM64 ou exceções Xbox.
Ver [SINGLE_UPDATE_PATCH.md](SINGLE_UPDATE_PATCH.md). Nenhuma função comercial executada.
