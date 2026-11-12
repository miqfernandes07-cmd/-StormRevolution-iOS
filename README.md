# Storm Revolution — pesquisa de port nativo para iOS

Projeto de port AOT PowerPC → C++ → ARM64 de Naruto Shippuden:
Ultimate Ninja Storm Revolution, versão Xbox 360. **O jogo ainda não executa.**
A CI produziu um IPA não assinado de infraestrutura; não há instalação no iPhone
ou medição de FPS.

O código original deste repositório é MIT. Não inclui jogo, código comercial
recompilado, chaves, APKs ou assets. Forneça localmente os arquivos da sua cópia
em `private/game/`; esse diretório é ignorado pelo Git.

Implementado: analisador de metadados XEX2 com validação de identidade, tradutor
AOT de um subconjunto PPC sintético, inventário de branches/candidatos a funções,
memória big-endian, fila PCM e serviços básicos C++,
app UIKit/Objective-C++ com diagnóstico Metal e workflows de host/macOS.
O XEX fornecido passou na validação de identidade; sua imagem foi reconstruída
localmente e foram lidos 291 imports distintos por biblioteca/ordinal. O
XenonAnalyse executou e recuperou zero tabelas de salto, o que exige investigação.
O XenonRecomp gerou 242 arquivos C++ privados. A série experimental de 13 patches
passou em **780443** verificações sintéticas nativas no host, mas a geração do
jogo continua bloqueada por 79 chamadas sem destino e 19909 palavras zero
não decodificadas. [Implementação e evidências](docs/VSCR_DISPATCH.md).
O runtime já possui dispatch AOT verificado; o app ainda não tem uma imagem
do jogo recompilada e qualificada para executar.

Estado em 2026-11-12: 62 testes Python, 1.038 verificações do runtime e 33 de PCM
passaram em 3/3 grupos CTest no Linux. GCC e Clang já passaram na CI host em um
marco anterior. A CI macOS agora compilou o app para iPhone ARM64 e simulador
x86_64, gerando o IPA não assinado. O aplicativo iniciou no simulador e passou
no autoteste do runtime e na conclusão de um comando Metal. Ver [integração iOS](docs/IOS.md) para evidências.
Não há JIT nem emulador completo no runtime.

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Debug -DSTORM_SANITIZERS=ON
cmake --build build --parallel 2
ctest --test-dir build --output-on-failure
python3 tools/xex_analysis/xex.py private/game/default.xex \
  --reference config/game_reference.json --output private/reports/xex.json
```

Requisitos host: C++17, CMake >=3.20, Python >=3.11 e ferramenta de build.
WSL/Linux cobre análise e testes; iOS exige macOS/Xcode. O deployment mínimo
do app é iOS 17; iOS 27 e iPhone 15 Pro são alvos solicitados, ainda sem validação.

- [Progresso e evidências](docs/PROGRESS.md)
- [Compatibilidade por componente e etapa](docs/COMPATIBILITY.md)
- [Arquitetura](docs/ARCHITECTURE.md)
- [Build local, CI e assinatura](docs/BUILD.md)
- [Testes e suas limitações](docs/TESTING.md)
- [Auditoria das seis referências e licenças](docs/REFERENCES.md)
- [Engenharia reversa](docs/REVERSE_ENGINEERING.md)
- [Analisador XEX](docs/XEX_ANALYZER.md) e [imagem PE/imports](docs/PE_ANALYSIS.md)
- [AOT sintético](docs/AOT.md) e [inventário PPC](docs/PPC_ANALYSIS.md)
- [Fila PCM](docs/AUDIO.md) e [integração iOS](docs/IOS.md)

Prioridade seguinte: corrigir as variantes rejeitadas, investigar o fluxo indireto
e as tabelas de salto e validar funções geradas antes da compilação nativa do jogo.
Também faltam serviços xboxkrnl/XAM, gráficos Xenos/Metal, áudio e os recursos.
O ZIP de 7,43 GB foi inspecionado parcialmente: 21 arquivos e 8 diretórios,
9,43 GB extraídos. Seu XEX foi validado isoladamente; recursos completos ainda
não foram extraídos. Ver [inventário de recursos](docs/ASSETS.md). O executável e as saídas derivadas
permanecem em `private/`.
