# Aplicação iOS: infraestrutura nativa

Status: **Compila para iPhone ARM64 e executa a infraestrutura no simulador x86_64**. O run
[43162119044](https://github.com/miqfernandes07-cmd/-StormRevolution-iOS/actions/runs/43162119044)
usou macOS Intel, Xcode 16.4 (16F6), AppleClang 17 e SDK 18.5, com deployment
17.0. O IPA de infraestrutura foi empacotado sem assinatura. O smoke test
aprovou autoteste do runtime e conclusão de comando Metal; `game_executed=false`. Instalação em
hardware e execução do jogo continuam pendentes. O ambiente local é Linux;
os builds Apple foram realizados exclusivamente no GitHub Actions.

O bundle UIKit/Objective-C++ liga diretamente a `storm_runtime`. O botão de iniciar
chama `storm_runtime_start` após a identidade do XEX ser validada. A versão atual
do runtime recusa iniciar por ausência da imagem AOT; não existe fallback para JIT,
streaming ou emulador. A interface deixa isso explícito.

## Implementação

- Importação de **pasta extraída** pelo aplicativo Arquivos, com acesso security-scoped,
  coordenação de leitura e cópia assíncrona para Application Support/Game. Symlinks
  são recusados. A cópia usa staging e substitui o conteúdo anterior somente após
  validar `default.xex`; é necessário espaço para a nova cópia além da anterior.
- SHA-1 calculado incrementalmente, tamanho de referência 11.776.000 bytes, magic
  XEX2, Title ID `4E4D0868`, Media ID `29E320A9`, versão raw `00000004` (0.0.0.4) e máscara de região
  incluindo NTSC-U. Isso verifica a revisão documentada, não a integridade dos demais
  recursos nem a possibilidade de boot. Headers maiores que 1 MiB não são aceitos
  pelo validador simplificado do app. O analisador host continua sendo a ferramenta
  de engenharia reversa completa desta iteração.
- Metal: biblioteca MSL compilada durante o build, fila, pipeline, três frames em
  voo e um triângulo diagnóstico. **Não renderiza o jogo, não traduz Xenos, não
  implementa texturas, depth/stencil, blending ou EDRAM.** O teste de simulador verifica
  conclusão de command buffer; não compara pixels.
- Perfis 30/60 Hz e escala .5–1.0 afetam somente o diagnóstico. Resolução adaptativa
  usa tempo GPU dos command buffers com ajuste limitado a cada 60 frames. Não há
  benchmark do jogo, garantia de FPS, cache de shaders do jogo ou otimização medida.
- GameController recebe controles com extended gamepad (incluindo dispositivos Xbox
  e PlayStation compatíveis com iOS), D-pad, sticks, botões e gatilhos analógicos.
  Touchscreen: analógico esquerdo, A/B/X/Y, LB/RB/LT/RT, Start/Back. Posição,
  transparência e escala são persistidas em UserDefaults. Feedback tátil usa UIKit.
  Mapeamento usa bits XInput; ações específicas de chakra, substituição, jutsu,
  despertar e apoio ainda precisam ser verificadas com o jogo real.
- Pausa de Metal, limpeza de input e parada do runtime quando o app perde atividade;
  redução do alvo de renderização sob pressão de memória ou temperatura.
- Áudio/XMA ainda não implementados. A interface informa essa limitação, sem
  oferecer controles de volume sem efeito.

## Compilação em Mac

Requer macOS, Xcode com SDK iOS, Command Line Tools selecionadas, CMake >= 3.20
e Python >= 3.11. A licença de CMake é BSD-3-Clause; Xcode/SDK são ferramentas
Apple externas e não são redistribuídos. O deployment target inicial é iOS 17.0,
compatível em princípio com iPhone 15 Pro. **iOS 27 não foi validado**, e o SDK
efetivamente usado deve ser consultado nos logs `xcodebuild -version/-showsdks`.

```sh
cmake -S . -B build-ios -G Xcode -DCMAKE_SYSTEM_NAME=iOS \
  -DCMAKE_OSX_SYSROOT=iphoneos -DCMAKE_OSX_ARCHITECTURES=arm64 \
  -DCMAKE_OSX_DEPLOYMENT_TARGET=17.0
cmake --build build-ios --config Release --target StormRevolution \
  -- CODE_SIGNING_ALLOWED=NO CODE_SIGNING_REQUIRED=NO
```

Se o Xcode instalado exigir download separado do compilador Metal, instale seu
componente Metal Toolchain pelo Xcode antes de compilar. Não confundir falta desse
componente com falha do runtime.

O workflow `.github/workflows/build-ios.yml` roda testes host, constrói ARM64,
empacota `Payload/StormRevolution.app` como `StormRevolution-UNSIGNED.ipa`, compila
para a arquitetura do host do simulador e executa o smoke test. Publica apenas
esse IPA de infraestrutura, hashes e logs. Nenhuma pasta private/ ou dados do
jogo é incluída. O IPA **exige assinatura posterior antes da instalação**.

O smoke test inicia o app com `--smoke-test`, espera `Documents/smoke-result.json`
e exige sucesso no autoteste do runtime e na conclusão de um command buffer
Metal. Falta de GPU/Metal no simulador é falha explícita, sem sucesso simulado.

## Assinatura e dispositivo

Para assinatura convencional são necessários certificado Apple Development com
chave privada, provisioning profile que inclua o bundle ID e o UDID do iPhone,
Team ID, e iPhone com modo de desenvolvedor habilitado quando exigido pelo iOS.
As regras de validade dependem do tipo de conta Apple. Uma ferramenta de sideload
compatível pode assinar o IPA não assinado usando as credenciais do usuário.
Credenciais nunca devem ser comitadas ou impressas em logs.

Para gerar um archive assinado no Mac, use o projeto CMake gerado e forneça
as opções de assinatura ao Xcode, substituindo os identificadores locais:

```sh
xcodebuild -project build-ios/StormRevolutionIOS.xcodeproj \
  -scheme StormRevolution -configuration Release -sdk iphoneos \
  -destination 'generic/platform=iOS' -archivePath build-ios/Storm.xcarchive \
  CODE_SIGNING_ALLOWED=YES CODE_SIGNING_REQUIRED=YES \
  DEVELOPMENT_TEAM=SEU_TEAM_ID CODE_SIGN_STYLE=Manual \
  CODE_SIGN_IDENTITY='Apple Development' \
  PROVISIONING_PROFILE_SPECIFIER='SEU_PROFILE' archive
```

Depois exporte com `xcodebuild -exportArchive` e um ExportOptions.plist apropriado
à conta/distribuição e versão do Xcode. Assinatura/exportação não foram executadas
nesta iteração. A CI não recebe certificados por padrão. Certificado/profile, teste
físico e inspeção Instruments são dependências exatas para os próximos marcos Apple.

Compilar, produzir IPA, assinar, instalar, iniciar a infraestrutura e executar o
jogo são seis verificações independentes. Nenhuma aprovação do smoke test equivale
a boot ou gameplay de Naruto Storm Revolution.

## Artefato e evidência — 2026-11-12

[Baixar artefato da CI](https://github.com/miqfernandes07-cmd/-StormRevolution-iOS/actions/runs/43162119044/artifacts/13918423298)
(disponibilidade original até 2026-11-19). Inclui `StormRevolution-UNSIGNED.ipa`
e logs. O ZIP foi baixado e inspecionado no Linux: IPA contém somente o executável
Mach-O ARM64, Info.plist, PkgInfo e default.metallib. Não há recursos do jogo,
perfil de provisionamento ou comando Mach-O de assinatura embutida.

SHA-256 do IPA: `264e0994fc01c74fc9be45eef445c6a7ca25467909b369026681a035c97bd1a2`.

[JSON real do smoke test](validation/ios-2026-11-12-simulator-smoke.json),
[toolchain](validation/ios-2026-11-12-xcode-version.txt) e
[testes host Apple](validation/ios-2026-11-12-host-tests.txt).
O teste não compara pixels, não exercita importação/controles e não executa o jogo.

Todos os passos de build, empacotamento, smoke e upload desse run passaram.
O estado global terminou `cancelled` durante a finalização, após um novo push
que separou o upload do IPA dos testes e limitou o smoke a dez minutos.
Esse novo workflow está no run 43163104401; não se atribui a ele o resultado
já medido no run anterior. Assinatura, instalação e teste em iPhone não ocorreram.
