# Storm Revolution — pesquisa de port nativo para iOS

Projeto de port AOT PowerPC → C++ → ARM64 de Naruto Shippuden:
Ultimate Ninja Storm Revolution, versão Xbox 360. **O jogo abre no iPhone 15 Pro,
mas o gameplay ainda apresenta crashes, tela preta e regressões gráficas.**
Em 2026-11-16, um experimento privado com ReXGlue compilou o título completo
no Linux e exibiu abertura, título, diálogos de salvamento e menu de modos.
START, A e seleção responderam; um save foi gravado no Linux.
O alvo iPhone `StormNative` já gerou um IPA ARM64 com os 17 frameworks
embutidos e dependências conferidas. O proprietário executou o build 2 no
iPhone 15 Pro, selecionou personagens e chegou a uma luta; forneceu captura e
três logs. O teste do build 3 encontrou artefatos desde a abertura e os menus.
O proprietário confirmou gameplay no build 5, mas informou aproximadamente
11 FPS em Seguro / 720p / 1×. A versão 0.5.0 / build 6 acrescenta controles
por ações para celular, atalhos de Jutsu/Supremo/Dash, um perfil Rápido
experimental e amostras de desempenho. Mantém o perfil Seguro, ícone ninja,
tela inicial e crédito para MiquéiasF07. O IPA foi compilado e auditado;
o ganho de FPS e os golpes pelos atalhos ainda exigem teste físico.
[Build nativo](docs/NATIVE_IPA.md).
[Estado atual e limites](docs/REXGLUE_BOOT_2026_11_16.md).

A CI pública também produz um aplicativo de infraestrutura separado. Ele não
contém o título. O aplicativo nativo e o código recompilado permanecem privados.
Os controles, atalhos, perfis e ajustes passaram por 224 verificações no
simulador; isso não valida gameplay nem toques no aparelho.
[Ações móveis e comparação dos perfis](docs/MOBILE_CONTROLS.md).

O código original deste repositório é MIT. Não inclui jogo, código comercial
recompilado, chaves, APKs ou assets. Forneça localmente os arquivos da sua cópia
em `private/game/`; esse diretório é ignorado pelo Git.

Histórico do runtime próprio e da análise anterior à integração ReXGlue:
analisador de metadados XEX2 com validação de identidade, tradutor
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
O runtime já possui dispatch AOT e memória escalar verificados. Um diagnóstico
privado executou oito funções reais de entrada e avançou até a reserva/commit
inicial do heap; parou no próximo serviço ausente. A ABI inicial não está
validada e o jogo não inicializa. [Evidências](docs/KERNEL_BRINGUP.md).
Essas limitações descrevem o caminho anterior, separado do alvo nativo ReXGlue.

Estado em 2026-11-13: 98 testes Python e oito suítes C++ passaram em
9/9 grupos CTest no Linux/UBSan, incluindo ZIP64 e mapeamento Xbox 360.
A versão 0.2.0 traz biblioteca ZIP, nova interface e crédito ao Miquéias;
[guia de teste com AltStore](docs/IPA_TESTE.md). GCC e Clang já passaram na CI host em um
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

Requisitos host: C++17, CMake >=3.20, Python >=3.11, zlib de desenvolvimento
(`zlib1g-dev` no Debian/Ubuntu) e ferramenta de build.
WSL/Linux cobre análise e testes; iOS exige macOS/Xcode. O deployment mínimo
do app é iOS 17; há execução comprovada no iPhone 15 Pro, sem estabilidade de
gameplay validada. A versão exata de iOS deve ser confirmada pelos diagnósticos.

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

Prioridade seguinte: testar o novo perfil gráfico no aparelho e diagnosticar o
destino inválido na cópia de recursos durante o carregamento da luta. Não
desabilitar a proteção da página zero nem ignorar cópias ou alocações com erro.
O ZIP de 7,43 GB contém 21 arquivos e 8 diretórios. Os 9,43 GB foram extraídos
privadamente com CRC conferido, usando filesystem e tmpfs separados.
Ver [inventário de recursos](docs/ASSETS.md). O executável e as saídas derivadas
permanecem em `private/`.
