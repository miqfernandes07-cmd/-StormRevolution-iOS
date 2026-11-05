# Compilação e distribuição

## Windows/WSL e Linux

Use WSL com GCC/Clang C++17, CMake >=3.20 e Python >=3.11. O projeto não depende
de bibliotecas externas de runtime nesta iteração. CMake (BSD-3-Clause), Ninja
(Apache-2.0) e compiladores são ferramentas de build, não incluídos no IPA.

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Debug -DSTORM_SANITIZERS=ON
cmake --build build --parallel 2
ctest --test-dir build --output-on-failure
python3 scripts/check_public_tree.py
```

No ambiente desta sessão CMake 3.31.6 foi instalado isoladamente em
`/tmp/storm-build-tools` via pip; o executável efetivo é
`/tmp/storm-build-tools/cmake/data/bin/cmake` (e `ctest` no mesmo diretório).
Esses caminhos são temporários, não requisitos para seu PC. GCC 14.2.0 e Python
3.12.14 já estavam disponíveis. Nenhum compilador Apple está presente no Linux.

## Preparação privada do jogo

```bash
mkdir -p private/game private/reports
# Copie aqui sua extração legítima, mantendo a árvore de recursos original.
python3 tools/xex_analysis/xex.py private/game/default.xex \
  --reference config/game_reference.json --output private/reports/xex.json
```

Uma correspondência de identidade não prova boot. Arquivos cifrados/comprimidos
recebem relatório de metadados e limitação explícita. Preparar o XenonRecomp fora
do app conforme [REFERENCES](REFERENCES.md), auditando dependências e mantendo
saídas do executável comercial sob `private/`. Não há mapa de funções pronto.

## iOS e GitHub Actions

A CI `build-ios.yml` configura CMake com gerador Xcode, compila ARM64 para dispositivo,
prepara um IPA **não assinado** sem dados do jogo e executa diagnóstico no simulador.
Consulte [IOS.md](IOS.md) para comandos, saída exata e limites do smoke test.
`tests.yml` cobre GCC e Clang em Ubuntu. O remoto agora é `miqfernandes07-cmd/-StormRevolution-iOS`. A execução host
[42083949244](https://github.com/miqfernandes07-cmd/-StormRevolution-iOS/actions/runs/42083949244)
passou com GCC e Clang. O workflow iOS
[42083949119](https://github.com/miqfernandes07-cmd/-StormRevolution-iOS/actions/runs/42083949119)
foi iniciado e aguarda runner macOS; ainda sem build Apple ou IPA confirmado.

Abra o projeto gerado em um Mac com Xcode e SDK suportando o deployment escolhido.
iOS 27 é alvo solicitado e não SDK detectado nesta sessão. A seleção de Xcode do
runner e o resultado da CI precisam ser registrados antes de afirmar compatibilidade.
O app usa APIs disponíveis desde iOS 17; isso permite testar infraestrutura antes
de qualificar um sistema mais recente.

Para instalação, um IPA sem assinatura precisa ser assinado por ferramenta
compatível e perfil válido para o bundle/device. Assinatura de desenvolvimento
via Xcode requer Apple Development certificate com chave privada, Team ID,
provisioning profile e registro do UDID, conforme tipo de conta. Não publicar
certificados, perfis, chaves ou credenciais. A primeira iteração não configura
segredos nem realiza assinatura. Não presume entitlements especiais concedidos
por qualquer método de sideload.

Estados independentes: build host → build CI iOS → IPA → assinatura/instalação →
app iniciado → jogo iniciado → gameplay. Falhar numa etapa não pode ser ocultado
pelo sucesso de outra. Se o app executar apenas seu diagnóstico Metal, registrar
somente inicialização da infraestrutura.
