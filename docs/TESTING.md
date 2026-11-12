# Testes e evidências

Nenhum arquivo comercial é necessário para a suíte pública. Os testes Python
produzem bytes PPC/XEX sintéticos; os testes C++ usam memória e recursos próprios.
Não são uma simulação do jogo e não provam sua execução.

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Debug -DSTORM_SANITIZERS=ON
cmake --build build --parallel 2
ctest --test-dir build --output-on-failure --output-junit results.xml
python3 scripts/check_public_tree.py
```

`ctest` reúne `storm_runtime_tests`, `storm_audio_tests` e a descoberta de testes Python.
O teste AOT invoca o compilador host, gera um binário nativo e o executa com UBSan.
Não roda um interpretador PPC no lugar do resultado recompilado. GCC/Clang precisam
estar instalados; ausência do compilador é falha, não teste silenciosamente pulado.
`CXX` pode selecionar o compilador. CMake encaminha o compilador configurado.

| Área | Cobertura automática | Limite |
| --- | --- | --- |
| XEX2 | Identidade, versão, blocos básicos, páginas, imports, truncamentos, limites, mutações determinísticas e CLI | Sem decriptação, exports ou funções no parser público |
| PE32 | Layouts file/mapped, seções, RVA, limites e descritores BE de imports | Sem exports, recuperação de funções ou resolução de serviços |
| PPC AOT | GPR64, overflow modular, imediatos negativos, RA=0, OR, branch adiante, diagnósticos | Sem FPU, VMX128, CR/XER, atomics, chamadas indiretas ou loops |
| Vetor | Soma modular de lanes u32, XOR e ordem BE | Helpers portáveis, não conjunto VMX completo nem equivalência SIMD ARM |
| Memória | Loads/stores BE, limites, alinhamento, allocator | Buffer de teste; sem proteção virtual/MMU ou comportamento Xbox completo |
| Runtime | API C, falhas de lançamento, registro e falha de imports, relógio | Sem serviços reais xboxkrnl/XAM |
| Recursos | Leitura limitada, travessia e symlinks recusados | Arquivos locais de teste; sem formatos comerciais, streaming ou saves |
| Input | Normalização, snapshot e concorrência no host | Touch/GameController necessitam iOS e interação |
| Gráficos/app | Workflow de simulador chama self-test e aguarda completion Metal | Ainda não executado; não valida pixels nem shaders Xenos |

## Dependências do executável original

O XEX fornecido já permitiu confirmar identidade, reconstruir a imagem, ler os
imports e tentar geração C++ privada. A geração foi rejeitada por diagnósticos;
não houve compilação ou execução desse C++. Permanecem pendentes: cobertura
completa de instruções, funções e tabelas de salto validadas, testes de ABI e
serviços usados, shaders/texturas/EDRAM, XMA/vozes, arenas, saves e gameplay.
Relatórios comerciais e código derivado permanecem privados. Não enviar para CI
pública. A suíte de CI só inclui fixtures próprias e o app de infraestrutura.

## Dispositivo e desempenho

Para registrar `Executa no iPhone`, é preciso assinar, instalar e iniciar o app em
hardware, com log identificando build/dispositivo/OS. Isso não muda o jogo para
`Jogo inicializa`. Cada tela e fase de batalha precisa de evidência separada.

Benchmark futuro deve registrar: commit, perfil do XEX, iOS e modelo, cena/arena,
personagens, resolução, limite 30/60, duração, frames perdidos, percentis CPU/GPU,
memória, estado térmico e configurações. Repetir aquecido e em condições controladas.
Não há resultados de benchmark nesta iteração.

## Execução registrada em 2026-11-05

Linux x86_64, GCC 14.2.0, Python 3.12.14, CMake 3.31.6. Build Debug com
`-DSTORM_SANITIZERS=ON` e build Release aprovados. Execução integrada inicial Debug:
2/2 grupos CTest, 1038 verificações C++ e 29 testes Python (14 XEX, 8 AOT,
7 adaptador XenonRecomp). [Log real](validation/host-debug-2026-11-05.log).
As 1038 verificações incluem 1000 snapshots no teste concorrente; não são 1038
casos de serviço Xbox. Os testes do adaptador usam doubles apenas para inspeção
de manifesto/Git; não comprovam execução das ferramentas upstream.

Release foi testado antes da inclusão dos sete casos do adaptador: 2/2 grupos,
1038 verificações C++ e 22 testes Python. Os binários C++ não mudaram depois.
A leitura de Info.plist e YAML é verificação de formato, não compilação Xcode.
Nenhum teste ocorreu no simulador, iPhone, ARM64 ou GitHub Actions nesta sessão.

## Suíte ampliada após continuação

Mesmo ambiente Linux: Debug/UBSan e Release aprovados em **3/3 grupos CTest**.
Total: **47 testes Python** (15 XEX, 9 AOT, 7 adaptador e 16 inventário),
**1038 verificações do runtime** e **33 verificações PCM**. O teste de fila
transferiu 100.000 frames numéricos ordenados entre duas threads. Sem áudio
reproduzido e sem certificação de latência de callback. O inventário testa formato
raw explícito, branches/AA/LK e candidatos, sem execução comercial.
[Log atualizado](validation/host-expanded-2026-11-05.log).

Os testes novos de colisão de caminhos preservam a entrada, inclusive hardlinks.
A suíte inicial de 29 testes permanece registrada no log anterior como marco
histórico. A ampliação não altera nenhum estado de execução Apple ou do jogo.

## Análise do XEX real e PE — 2026-11-06

Linux x86_64, GCC 14.2.0, Python 3.12.14, CMake 3.31.6: **3/3 grupos CTest**
aprovados em Debug/UBSan, com **62 testes Python** (16 XEX, 13 PE, 9 AOT,
8 adaptador e 16 inventário), 1038 verificações de runtime e 33 de PCM.
O teste adicional do adaptador verifica rejeição de diagnóstico mesmo quando
uma ferramenta retorna exit code zero. O subprocesso desse teste é sintético;
a execução real de XenonRecomp é registrada separadamente em PROGRESS.

Os relatórios reais foram produzidos localmente sobre dados privados. A suíte
pública continua independente desses arquivos. O parser PE registrou a diferença
entre `SizeOfImage` e o buffer reconstruído sem fabricar a cauda ausente.
Nenhuma execução de código comercial, Apple ou ARM64 foi concluída neste marco.
[Log completo da suíte pública](validation/host-pe-2026-11-06.log).

## Portabilidade dos testes macOS — 2026-11-12

A CI Apple com Xcode 16.4/SDK 18.5 expôs três asserções que comparavam o alias
`/var/folders` ao caminho físico `/private/var/folders`. A fixture agora resolve
a raiz temporária, como o código de produção já fazia. Os oito testes do adaptador
passaram localmente também com TMPDIR apontando a um symlink. No run
[43161886428](https://github.com/miqfernandes07-cmd/-StormRevolution-iOS/actions/runs/43161886428),
os três grupos CTest passaram no macOS Intel, incluindo os 62 testes Python.
O link do app ARM64 revelou ausência de CoreGraphics; a dependência foi adicionada
explicitamente ao target CMake. O resultado da nova CI está em PROGRESS/IOS.
