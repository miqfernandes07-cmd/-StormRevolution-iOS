# Storm Revolution — pesquisa de port nativo para iOS

Infraestrutura inicial de um port AOT PowerPC → C++ → ARM64 de Naruto Shippuden:
Ultimate Ninja Storm Revolution, versão Xbox 360. **O jogo ainda não executa.**
Não há IPA produzido, teste em iPhone ou medição de FPS nesta iteração.

O código original deste repositório é MIT. Não inclui jogo, código comercial
recompilado, chaves, APKs ou assets. Forneça localmente os arquivos da sua cópia
em `private/game/`; esse diretório é ignorado pelo Git.

Implementado: analisador de metadados XEX2 com validação de identidade, tradutor
AOT de um subconjunto PPC sintético, inventário de branches/candidatos a funções,
memória big-endian, fila PCM e serviços básicos C++,
app UIKit/Objective-C++ com diagnóstico Metal e workflows de host/macOS.
XenonRecomp é o candidato para o executável completo; o tradutor sintético é
somente um teste independente. Não há JIT nem emulador completo no runtime.

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
- [Analisador XEX](docs/XEX_ANALYZER.md)
- [AOT sintético](docs/AOT.md) e [inventário PPC](docs/PPC_ANALYSIS.md)
- [Fila PCM](docs/AUDIO.md) e [integração iOS](docs/IOS.md)

Prioridade seguinte: validar o XEX real, recuperar imagem/funções/imports e
configurar o XenonRecomp para esse executável. O primeiro frame do título depende
também de implementação Xenos/Metal; um triângulo de diagnóstico não é esse frame.
