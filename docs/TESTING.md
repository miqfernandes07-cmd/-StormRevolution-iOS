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

`ctest` reúne o executável `storm_runtime_tests` e a descoberta de testes Python.
O teste AOT invoca o compilador host, gera um binário nativo e o executa com UBSan.
Não roda um interpretador PPC no lugar do resultado recompilado. GCC/Clang precisam
estar instalados; ausência do compilador é falha, não teste silenciosamente pulado.
`CXX` pode selecionar o compilador. CMake encaminha o compilador configurado.

| Área | Cobertura automática | Limite |
| --- | --- | --- |
| XEX2 | Identidade, versão, páginas, imports, truncamentos, limites, mutações determinísticas e CLI | Fixtures não são executáveis PE completos; sem XEX real, decriptação, exports ou funções |
| PPC AOT | GPR64, overflow modular, imediatos negativos, RA=0, OR, branch adiante, diagnósticos | Sem FPU, VMX128, CR/XER, atomics, chamadas indiretas ou loops |
| Vetor | Soma modular de lanes u32, XOR e ordem BE | Helpers portáveis, não conjunto VMX completo nem equivalência SIMD ARM |
| Memória | Loads/stores BE, limites, alinhamento, allocator | Buffer de teste; sem proteção virtual/MMU ou comportamento Xbox completo |
| Runtime | API C, falhas de lançamento, registro e falha de imports, relógio | Sem serviços reais xboxkrnl/XAM |
| Recursos | Leitura limitada, travessia e symlinks recusados | Arquivos locais de teste; sem formatos comerciais, streaming ou saves |
| Input | Normalização, snapshot e concorrência no host | Touch/GameController necessitam iOS e interação |
| Gráficos/app | Workflow de simulador chama self-test e aguarda completion Metal | Ainda não executado; não valida pixels nem shaders Xenos |

## Dependências do executável original

Permanecem bloqueados: confirmar identidade/edição; contar imports/opcodes; recuperar
funções e tabelas de salto; reconstruir imagem; gerar C++ do Storm; testes de ABI e
serviços usados; shaders/texturas/EDRAM; XMA/vozes; carregar arenas; saves e gameplay.
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
`-DSTORM_SANITIZERS=ON` e build Release aprovados. Execução integrada final Debug:
2/2 grupos CTest, 1038 verificações C++ e 29 testes Python (14 XEX, 8 AOT,
7 adaptador XenonRecomp). [Log real](validation/host-debug-2026-11-05.log).
As 1038 verificações incluem 1000 snapshots no teste concorrente; não são 1038
casos de serviço Xbox. Os testes do adaptador usam doubles apenas para inspeção
de manifesto/Git; não comprovam execução das ferramentas upstream.

Release foi testado antes da inclusão dos sete casos do adaptador: 2/2 grupos,
1038 verificações C++ e 22 testes Python. Os binários C++ não mudaram depois.
A leitura de Info.plist e YAML é verificação de formato, não compilação Xcode.
Nenhum teste ocorreu no simulador, iPhone, ARM64 ou GitHub Actions nesta sessão.
