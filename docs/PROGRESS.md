# Progresso — atualização em 2026-11-12

## Marco: série experimental acumulada

Sete patches do emissor e integração explícita de proveniência no adaptador.
117198 casos/vetores nativos sintéticos aprovados no mesmo binário Linux x86_64,
Clang 19.1.7/UBSan. Suíte padrão: 71 testes Python + 1038 verificações runtime +
33 PCM, 3/3 CTest. Os testes usam dados próprios, não executam o título.

Geração privada pelo adaptador: de 973/25 para **45 ocorrências/3 variantes**,
mais **um aviso de RLDICL. sem comparação CR**. O adaptador rejeitou a saída.
Permanecem VPKSWSS128/VSCR, MACs suspeitas, fluxo indireto e os subsistemas do jogo.
Fonte/binário originais restaurados, hashes conferidos. O manifesto experimental
recusou corretamente o fonte restaurado. Sem função comercial compilada/executada.
[Implementação, comandos, provas e bloqueios](SERIES_SEVEN.md).

## Marco: LFSU/STFSU com atualização de endereço

Segundo patch experimental do emissor implementado: LFSU/STFSU em endereçamento
guest32, atualização de RA após acesso, RA=0/MMIO recusados. **900 casos nativos**
passaram com Clang/UBSan no Linux x86_64: 405 com macros upstream e 495 com
callbacks verificados. EQV passou novamente nos 3264 vetores no mesmo binário.
Nova geração privada: **973 ocorrências em 25 variantes**, contra 1603/27;
250 LFSU e 380 STFSU desapareceram. Saída continua incompleta, sem build nativo
ou execução comercial. O baseline original foi restaurado e seu hash conferido.
[Reprodução e limites](SINGLE_UPDATE_PATCH.md). Suíte pública: 3/3 CTest aprovados.

## Marco: correção experimental de EQV

Primeiro patch do emissor XenonRecomp implementado e testado: EQV sem record,
3264 vetores de C++ gerado executados com Clang/UBSan no Linux x86_64.
Nova geração privada reduziu os diagnósticos de **1643/28 para 1603/27**;
as 40 ocorrências EQV desapareceram. `eqv.` permanece rejeitada explicitamente.
A suíte pública passou novamente em 3/3 grupos CTest (62 testes Python,
1038 verificações runtime, 33 PCM). Nenhuma função comercial foi compilada ou
executada. Fonte e binário upstream originais foram restaurados e verificados.
Ver [patch, reprodução e limitações](EQV_PATCH.md).

A CI [43163104401](https://github.com/miqfernandes07-cmd/-StormRevolution-iOS/actions/runs/43163104401)
terminou globalmente com sucesso, incluindo build ARM64, IPA e smoke no simulador.
Ela valida a infraestrutura pública anterior a este patch offline; não testa o jogo.

## Estado atual comprovado

O executável fornecido pelo usuário está em `private/game/default.xex`, ignorado
pelo Git. Tamanho, SHA-1, Title ID e Media ID correspondem à referência publicada.
O primeiro uso real revelou um erro de interpretação da versão: raw `0x00000004`
foi inicialmente exibido como `4.0.0.0`. A leitura correta resulta em `0.0.0.4`;
o parser, o validador iOS e as regressões foram corrigidos. A identidade agora passa.

A imagem cifrada/comprimida foi reconstruída localmente. Os cabeçalhos PE e as
seções foram analisados antes de alterar os descritores de importação. A leitura
identificou 9 seções e 291 imports distintos por biblioteca/ordinal: 112 de XAM e
179 de xboxkrnl. São 569 registros, incluindo 278 thunks pareados, sem diagnósticos
de tipo desconhecido ou pareamento. Esses números não significam serviços nativos
implementados. Relatórios completos e imagens permanecem privados.

O PE declara 14.669.312 bytes, enquanto a imagem reconstruída e o tamanho XEX são
13.762.560. Todas as seções estão disponíveis; o parser registra explicitamente
`PE_IMAGE_TAIL_UNAVAILABLE` e recusa leituras na cauda ausente. Nenhum byte foi
fabricado para ocultar a diferença. Bases de carga XEX e PE coincidem.

XenonAnalyse foi executado sobre o arquivo real e recuperou zero tabelas de salto.
Isso exige investigação de fluxo indireto; não comprova ausência dessas tabelas.
XenonRecomp gerou 242 arquivos C++ privados. A auditoria encontrou 1.643 ocorrências
de 28 variantes rejeitadas ([mapa de lacunas](CPU_GAPS.md)), portanto a saída permanece incompleta e não foi
compilada como código nativo do jogo. Nenhuma instrução rejeitada foi declarada
suportada para produzir uma afirmação de sucesso.

No Linux, passaram **62 testes Python, 1.038 verificações do runtime e 33 da fila
PCM, em 3/3 grupos CTest**. Os testes usam fixtures sintéticas; as análises do XEX
real são evidências separadas. GCC e Clang também passaram na CI host no marco
registrado abaixo, antes das alterações atuais.

A CI macOS Intel passou nos testes host após corrigir caminhos temporários.
O primeiro link ARM64 revelou falta de CoreGraphics, corrigida no CMake.
O run [43162119044](https://github.com/miqfernandes07-cmd/-StormRevolution-iOS/actions/runs/43162119044)
compilou o aplicativo para iPhone ARM64 e simulador x86_64 e empacotou o primeiro
IPA não assinado de infraestrutura. Xcode 16.4/SDK iOS 18.5, deployment 17.0.
O app iniciou no simulador e o smoke test aprovou runtime e comando Metal.
O artefato foi baixado: Mach-O ARM64, sem assinatura embutida ou dados do jogo.
Todos esses passos passaram; o run terminou globalmente cancelled na finalização
após outro push. Evidências, hash e download em [IOS.md](IOS.md).
Ainda não há instalação no iPhone nem execução do jogo. Não há medição de FPS,
gameplay ou qualificação de iPhone 15 Pro/iOS 27.

O índice do ZIP de 7,43 GB foi inspecionado por ranges: 21 arquivos e 8 diretórios,
9,43 GB descompactados. Somente seu XEX foi extraído e validado por CRC32/tamanho/
SHA-1, idêntico à cópia anterior. A extração completa excede o espaço disponível.
Ver [ASSETS.md](ASSETS.md). Nenhum recurso comercial, imagem
reconstruída, chave ou código C++ derivado foi incluído no repositório público.

## Próxima implementação prioritária

1. Investigar as 28 variantes rejeitadas e a configuração de geração, com testes
   diferenciais para as correções necessárias antes de compilar funções do jogo.
2. Revisar limites de funções, chamadas indiretas e as tabelas de salto que a
   análise automática não recuperou; manter logs e saídas detalhadas privados.
3. Validar a infraestrutura no simulador e, após assinatura, em aparelho físico.
   Importação real, controles, interrupções e renderização precisam de testes.
4. Obter os recursos em armazenamento com capacidade suficiente e iniciar os
   contratos xboxkrnl/XAM, shaders Xenos/Metal e áudio conforme evidência do título.

Importar os arquivos e gerar C++ são etapas preparatórias. O primeiro boot depende
de código nativo compilado, imports implementados e renderização correspondente.

## Histórico preservado das iterações anteriores

Os registros a seguir descrevem o estado observado em cada marco anterior. As
limitações que mencionavam ausência do XEX, falta de remoto ou CI ainda em fila
foram superadas ou atualizadas no estado atual acima; os logs e links históricos
são preservados para rastreabilidade.

O projeto foi criado em `/workspace/StormRevolution-iOS` porque o workspace estava
vazio, sem checkout utilizável ou arquivos do jogo. Foi iniciado um repositório
Git local, sem remoto; nenhum histórico existente foi removido.

### Resultado comprovado

Compilação host Linux x86_64 com GCC 14.2.0, Python 3.12.14 e CMake 3.31.6.
Build Debug com UBSan e build Release aprovados. CTest passou nos três grupos
(runtime C++, fila PCM e ferramentas Python). Os testes sintéticos não executam o jogo.
Total naquele marco: 1038 verificações do runtime, 33 da fila PCM e 47 testes Python. Detalhes em
[TESTING.md](TESTING.md) e [log de validação atualizado](validation/host-expanded-2026-11-05.log).

Não houve build CI, produção/assinatura de IPA, instalação, inicialização do app
Apple ou execução comercial. O iPhone 15 Pro/iOS 27 continua sem qualificação.

### Implementação concluída nesta iteração

- Auditoria das seis referências públicas, com commits, licenças e arquivos
  examinados. XenonRecomp tem caminho ARM64, mas requer auditoria de atomics,
  memória e fluxo indireto. SpeedBreaker usa Vulkan/MoltenVK; não fornece backend
  Metal nativo pronto. Android não publica as fontes completas.
- Analisador XEX2 independente, JSON, SHA-1/SHA-256, tamanho, Title/Media ID,
  versão, região, páginas e bibliotecas importadas. Estruturas incompletas,
  sobrepostas e fora dos limites são recusadas. Não inclui chaves.
- Tradutor AOT sintético para pequeno subconjunto inteiro PPC, emitindo C++.
  Geração/compilação/execução nativa host comprovadas; diagnósticos por palavra/PC
  para instruções e variantes não suportadas. Não é o tradutor do Storm.
- Adaptador para XenonRecomp com commit fixado, hashes e validação de identidade/
  caminhos privados; sete testes passaram. Upstream não foi executado.
- Runtime C++17 com API C, memória big-endian verificada, alocação alinhada,
  helpers vetoriais, registro de imports, relógio, input normalizado e arquivos
  locais limitados. Falta de import ou imagem AOT não retorna sucesso falso.
- Fonte de app UIKit/Objective-C++, MetalKit/MSL de diagnóstico, importação via
  Arquivos, validação, controles e configurações. Estado Apple: implementado sem
  compilação/teste nesta sessão. Ver [IOS.md](IOS.md).
- CMake e workflows de host/macOS, com empacotamento previsto de IPA não assinado.
  Nenhum material comercial entra nos artefatos públicos definidos.

### Erros encontrados e corrigidos

O workspace não era um Git checkout. Criado um repositório próprio no subdiretório.
CMake ausente: instalado isoladamente sob `/tmp`, sem alterar dependências do app.
A primeira configuração CMake detectou o compilador, mas falhou porque o arquivo de
testes ainda estava em implementação paralela. Após sua conclusão, ambos os builds
passaram. A revisão do parser encontrou aceitação indevida de referência JSON vazia
e risco de copiar headers sobrepostos repetidamente; o esquema agora é obrigatório
e os intervalos são verificados antes da cópia. Testes cobrem essas correções.

### Bloqueios técnicos reais

1. Sem `default.xex`/recursos: não é possível afirmar viabilidade específica,
   recuperar funções ou gerar o Storm. Referência documental não substitui arquivo.
2. Sem Clang/SDK Apple/Xcode ou remoto configurado: código iOS e workflow ainda
   não foram compilados/executados. Sem certificado/perfil/UDID não há instalação.
3. Renderer Xenos/Metal, shaders, EDRAM, áudio XMA, serviços guest e mapas de
   funções completos ainda exigem implementação. Não são resolvidos por importar
   dados ou compilar a interface.
4. Atomics, denormais, VMX128, exceções, MMIO e tabelas indiretas precisam de testes
   diferenciais antes de confiar no resultado AOT ARM64 do título.

### Próxima implementação prioritária

Com uma cópia local: executar identidade, guardar relatório privado, reconstruir
imagem offline e gerar inventário de imports/funções pelo XenonRecomp fixado;
revisar tabelas de salto e ABI. Em paralelo, executar o workflow Apple para corrigir
problemas reais de SDK/simulador e começar testes Metal de textura/depth/resolve.
Só depois de vincular uma imagem AOT válida tentar o entry point comercial e
implementar serviços conforme os primeiros diagnósticos reais. Não há previsão
medida de FPS nem promessa de prazo para gameplay.

### Histórico local

- `489d6c3`: analisador XEX2, perfil de identidade, testes e auditoria pública.
- `bdff73b`: runtime, AOT sintético, adaptador XenonRecomp e CI host.
- `ff7d83e`: app iOS, controles, diagnóstico Metal e workflow IPA não assinado.

Os controles receberam correção na revisão estática: gestos de reposicionamento
ficam desabilitados durante uso normal; o scroll não cancela os toques iniciados
nos controles. Isso ainda exige verificação física. `OBJCXX_STANDARD=17` foi
explicitado. Bash, plist e YAML passaram em verificação de sintaxe no Linux.
Nenhum commit foi enviado a GitHub e nenhuma execução de CI foi solicitada, pois
este repositório local não tem remoto configurado.

### Marco adicional após continuação

Implementado inventário estático de regiões PPC raw, com referências diretas,
AA/LK, deslocamentos com sinal, candidatos a funções e diagnósticos por PC. Os
16 testes passaram; isso não recupera funções completas, jump tables nem imagem
XEX/PE. A cobertura do tradutor sintético aparece separada da classificação de
instruções e da cobertura desconhecida do XenonRecomp.

Implementada fila PCM `float` intercalado, limitada, com um produtor/consumidor,
sem alocação em read/write, contadores e preenchimento com silêncio no underrun.
33 verificações passaram, incluindo 100.000 frames concorrentes ordenados; não há
Core Audio/XMA nem reprodução real. Builds CMake Debug/UBSan e Release passaram
nos três grupos; suíte Python daquele marco tinha 47 testes.

A revisão adicional encontrou possibilidade de um CLI sobrescrever seu arquivo de
entrada. O teste reproduziu o problema; XEX, AOT e inventário agora recusam colisão
de caminhos, symlinks resolvidos e hardlinks. As regressões passaram, preservando
os bytes de entrada. O projeto Xcode também passou a gerar scheme explicitamente
para o comando de archive documentado. Compilação Apple continua não realizada.

Commits adicionais: `f540fe2` (scheme Xcode), `bfcde40` (proteção das entradas),
`c4078fc` (fila PCM) e `3b60788` (inventário PPC). Todos são locais.

### Integração GitHub e primeira execução de CI

Destino configurado: https://github.com/miqfernandes07-cmd/-StormRevolution-iOS .
Os 58 arquivos foram transferidos, mantendo o commit inicial remoto e a sequência
original de nove alterações. Cada commit remoto registra o SHA local de origem.
A árvore final foi conferida pelo hash Git `7313942db6b740a05897652601cfa2aed42caf9c`,
idêntico ao snapshot local. Nenhum arquivo de private/ ou recurso comercial foi enviado.

Primeira execução host: https://github.com/miqfernandes07-cmd/-StormRevolution-iOS/actions/runs/42083707473 .
GCC passou build/testes; Clang 18.1.3 em Ubuntu 24.04 falhou no link de
`__atomic_is_lock_free`. CMake agora testa o link e acrescenta libatomic somente
quando necessário em Linux. Essa biblioteca do toolchain GCC tem GPL com GCC Runtime
Library Exception; não é acrescentada ao IPA Apple. Build e três grupos CTest locais
passaram após a correção; resultado da nova CI ainda pendente neste registro.

Workflow iOS iniciado: https://github.com/miqfernandes07-cmd/-StormRevolution-iOS/actions/runs/42083707503 .
Nenhum resultado de build Apple, IPA, simulador ou dispositivo foi confirmado ainda.

### Resultado da correção na CI

Execução [42083949244](https://github.com/miqfernandes07-cmd/-StormRevolution-iOS/actions/runs/42083949244):
GCC e Clang concluíram build, os três grupos CTest e higiene dos arquivos com sucesso.
No Clang 18.1.3, a detecção encontrou a necessidade de libatomic e o teste de link
com essa biblioteca passou. A falha inicial está corrigida por evidência da CI.

Workflow iOS observado naquele marco: [42083949119](https://github.com/miqfernandes07-cmd/-StormRevolution-iOS/actions/runs/42083949119).
Estado observado no momento do registro: queued, aguardando runner macOS, sem
steps executados. A execução iOS anterior foi substituída automaticamente pelo
commit de correção via concurrency; não houve falha Apple nela. Ainda não há IPA
produzido, app Apple iniciado ou jogo executado.
