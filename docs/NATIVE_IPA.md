# Aplicativo nativo experimental

Versão atual publicada: **0.6.1 / build 8**, [download privado](https://github.com/miqfernandes07-cmd/StormRevolution-iPhone-Private/releases/tag/native-iphone-run-44165837354).
O renderizador agora reaproveita o buffer de leitura síncrona de memexport,
em vez de criar, mapear, desmapear e destruir uma alocação por leitura. A espera
pelos dados da submissão atual e a invalidação da memória permanecem. Novos logs
`Native GPU timing` medem os tempos inclusivos de desenhos/leituras e as esperas.

O proprietário relata até 18 FPS nos menus e jogabilidade travada no build
anterior. O log enviado não mede CPU/GPU nem identifica o perfil ativo.
O ganho do build 8 ainda precisa ser medido no iPhone. Use Seguro, 1×, 30 FPS,
FXAA desligado, reabra o aplicativo e exporte logs + native-session.json após
comparar a mesma arena e personagens. Rápido continua experimental.

O build do runtime 44164692810, o refresh 44165837354 e a publicação 44165928216
passaram. O pacote tem 22.795.253 bytes e SHA-256
`157a57b769403c90f883fc1c058c40109891e202149f2d02f75ead9f5366cb86`.
Todos os 924 headers públicos são idênticos ao SDK anterior. Só o binário do
renderizador Vulkan e Info.plist mudaram; os outros 79 itens, incluindo o
executável principal, ícones e demais frameworks, são idênticos ao build 7.
Preserva idiomas, controles, memória ampliada, Modo Jogo, importação e saves.
Não apague o app para atualizar.

[Detalhes da otimização e limitações](GPU_READBACK_PERFORMANCE.md).
[Testes do caminho de leitura](validation/pooled-readback-2026-11-17.json).
[Auditoria do IPA](validation/native-iphone-ipa-v8-2026-11-17.json).

O alvo `StormNative` integra ReXGlue e o código recompilado do título. É
separado do aplicativo UIKit de infraestrutura `StormRevolution`. O proprietário
executou o build 2 em um iPhone 15 Pro: abriu o jogo, selecionou personagens e
chegou a uma luta. Há crashes no carregamento e casos de tela preta; uma sessão
de gameplay estável ainda não foi validada.

O SDK aberto com 17 frameworks iPhone ARM64 passou pelo link de um fixture e
pela compilação do frontend no run público
[44003543615](https://github.com/miqfernandes07-cmd/-StormRevolution-iOS/actions/runs/44003543615).
A compilação privada seguinte aprovou todos os fontes do título para iPhone;
o primeiro link completo apontou CoreGraphics ausente, depois incluído no alvo.
O run privado 44007706307 aprovou a compilação e o link completos. O arquivo
IPA não foi concluído nesse run porque o script confundiu uma pasta provisória
do Xcode com o aplicativo final. A seleção da pasta e a inclusão dos frameworks foram corrigidas. O run
privado 44018437659 passou pelo build e archive completos. A auditoria estática
confirmou ARM64/iOS, 17 frameworks com dependências presentes, rpath do bundle,
licenças e 37.255.824 bytes na seção de código recompilado. O build 2 foi
reempacotado com o novo backend de memória no run privado 44022730725 e
publicado privadamente no run 44022871358. Seus 17 hashes de frameworks
correspondem ao SDK verificado; o executável comercial permaneceu idêntico.
[Auditoria do IPA atual](validation/native-iphone-ipa-v2-2026-11-17.json).
[Relatório do link](validation/native-iphone-link-2026-11-17.json).

O build 3 / 0.4.0 foi compilado e publicado no run privado 44029386428
(publicação 44030836808). Contém os ajustes descritos abaixo e diagnóstico
privado do alocador/cópia. O IPA de 20.186.253 bytes passou pela auditoria na CI
e por conferência independente do checksum, identidade do bundle, frameworks
iOS e ligação dos dois hooks aos originais.
[Auditoria do build 3](validation/native-iphone-ipa-v3-2026-11-17.json).
O teste físico posterior encontrou artefatos desde a abertura e nos menus com
o perfil Compatível. O diagnóstico solicitava FSI; o caminho efetivamente
selecionado pode sofrer fallback interno e não está exposto pelo SDK. Os logs
005/006 e a captura não comprovam a origem exata da corrupção. Esses arquivos
não contêm outro SIGBUS ou falha de alocação, o que também não comprova que os
crashes da luta foram corrigidos. O teste UIKit do
[run 44030440277](https://github.com/miqfernandes07-cmd/-StormRevolution-iOS/actions/runs/44030440277)
passou por 116 verificações programáticas sem executar o jogo.

## Memória no sandbox

O quinto adaptador substitui `shm_open` no branch iPhone por um arquivo esparso
criado no diretório temporário privado do processo e desvinculado antes de
retornar o descriptor. Mantém aliases `MAP_SHARED` sem depender de um nome
POSIX global ou entitlement de grupo. Não torna os bytes PowerPC executáveis.

O teste do helper real passou por 25 verificações no Linux/UBSan e no macOS:
dois aliases coerentes acima de 4 GiB, tamanho esparso, nome removido, descriptor
close-on-exec, restrição de escrita no descriptor somente leitura, validade dos
views depois de fechar o descriptor e rejeição de tamanhos inválidos. A
compilação e o link do SDK completo para iPhone passaram no
[run 44020335898](https://github.com/miqfernandes07-cmd/-StormRevolution-iOS/actions/runs/44020335898).
Os logs enviados pelo proprietário confirmam execução desse backend em aparelho
físico. A proteção da página zero permanece ativa.

O reempacotamento mantém o executável comercial já vinculado apenas quando
todos os headers públicos do SDK são idênticos aos usados nessa compilação.
O pacote contém o quinto adaptador e passou de novo pela inspeção do
executável, dos frameworks, das dependências, das licenças e do SHA-256.
A publicação privada oferece o IPA não assinado para teste no aparelho.

## Ajustes após o teste físico

O frontend mantém o bundle ID e os dados importados. Inclui botões
PlayStation/Xbox, disposição para celular/clássica, edição de posições, tamanho,
opacidade, vibração opcional, controle externo e crédito para MiquéiasF07.
A engrenagem abre os ajustes e permite compartilhar os logs. Abrir os ajustes
bloqueia o controle virtual, mas a pausa deve ser acionada com OPTIONS no jogo.

O perfil Seguro da versão 0.4.1 solicita render targets host e render passes
tradicionais, espera os shaders, mantém readback e usa a cópia completa de
resolves. O perfil Padrão também solicita host, com dynamic rendering. Nenhum
dos dois solicita FSI. A conversão de primitivas volta à seleção automática do
driver. No build 7, Memória ampliada remove o teto de orçamento do runtime; desativá-la restaura 512 MiB no perfil Seguro.
Essas medidas precisam de confirmação física; não são uma correção comprovada
do backend gráfico. Tela preenchida pode alterar a
proporção; Original preserva a proporção do jogo. Mudanças no renderizador,
resolução, escala e FXAA exigem reabrir o aplicativo.

A versão 0.4.1 apresenta uma tela inicial UIKit própria: destaque para Jogar,
estado da biblioteca/importação, cartão de controles e gráficos e crédito para
MiquéiasF07. O teste de simulador usa a mesma classe que o aplicativo nativo.
Na primeira abertura após a atualização, a revisão do renderizador agenda a
remoção de `Caches/Native`; o jogo importado, os saves e as posições dos
controles mantêm seus diretórios e preferências. Se a remoção falhar, fica
pendente para a próxima abertura.

O ícone próprio usa uma shuriken com energia laranja e azul. A arte original
fica em `ios/Native/Icon/StormIcon.png`; o script de preparação gera um PNG RGB
opaco de 1024×1024 para o asset catalog. O compilador de assets da Apple gera
os tamanhos usados pelo iPhone e os metadados `CFBundleIcons`. A integração
também está no CMake do alvo nativo para os próximos builds.

A nova tela inicial, os controles, os dois perfis sem FSI e a migração do cache
passaram por 127 verificações programáticas no
[run 44057533788](https://github.com/miqfernandes07-cmd/-StormRevolution-iOS/actions/runs/44057533788).
A captura real da tela inicial foi inspecionada. O estado de biblioteca dessa
captura é sintético; não há execução do jogo no simulador.
[Relatório](validation/native-home-2026-11-17.json).

O build nativo completo 44057527412 passou. O run 44060974749 adicionou o ícone
usando `actool`, declarou `CFBundleIcons` e manteve o executável e todos os
frameworks idênticos, byte a byte. O IPA 0.4.1 / build 5 foi publicado no run
44061631559 e passou pela auditoria independente de ARM64/iOS, dependências,
checksum, identidade, classe da nova tela e recursos do ícone.
[Auditoria do pacote com ícone](validation/native-iphone-ipa-v5-2026-11-17.json).
O comportamento gráfico e o gameplay dessa versão ainda não foram confirmados
em aparelho físico.

Os dois crashes foram localizados na cópia de recursos, com destino inválido.
Uma instrumentação privada registra falhas do alocador e os argumentos antes
da cópia, sem ignorar erros nem alterar os retornos. Os logs também contêm
limitações do caminho gráfico de render targets host. Essas observações não
comprovam que o novo perfil resolveu os crashes ou a tela preta.

O workflow `Native controls and settings` testa os controles UIKit e a
persistência dos ajustes com eventos programáticos no simulador, sem executar
o jogo. O gameplay e os toques físicos dependem de validação no aparelho.

## Build privado

Requer macOS, Xcode 26/AppleClang 17, CMake com gerador Xcode, o pacote aberto
de runtime descompactado e os fontes comerciais gerados da cópia do usuário.
Não enviar esses fontes ou os arquivos do jogo à CI pública.

```bash
cmake -S . -B build-native-ios -G Xcode \
  -DCMAKE_SYSTEM_NAME=iOS -DCMAKE_OSX_SYSROOT=iphoneos \
  -DCMAKE_OSX_ARCHITECTURES=arm64 -DCMAKE_OSX_DEPLOYMENT_TARGET=17.0 \
  -DSTORM_BUILD_NATIVE=ON \
  -DSTORM_REX_IOS_SDK="$PWD/private/rexglue/iphone-sdk/runtime" \
  -DSTORM_NATIVE_GENERATED="$PWD/private/rexglue/project/generated/default" \
  -DCMAKE_XCODE_ATTRIBUTE_CODE_SIGNING_ALLOWED=NO
cmake --build build-native-ios --config Release --target StormNative --parallel 3
```

O pacote exige a revisão SDK fixada e `REX_PHYSICAL_OFFSET_IN_CODE=1`, a ABI
para as páginas ARM64 de 16 KiB. Os frameworks são copiados para o bundle,
incluindo MoltenVK dinâmico para iOS. O frontend seleciona UIKit no SDL,
mantém saves/caches/logs em diretórios graváveis e alimenta um gamepad virtual
com os controles de toque e GameController existentes.

O proprietário criou o repositório privado
`miqfernandes07-cmd/StormRevolution-iPhone-Private`. Seus workflows compilam o
título, verificam os Mach-O e arquivam um IPA sem conteúdo do jogo. A publicação
privada depende de build aprovado e verificação de hash/conteúdo do pacote.

## Instalação e execução

O IPA precisa de assinatura para instalar. No AltStore Classic, a importação
fica em My Apps → +, e a assinatura usa o AltServer configurado em computador.
A compilação não fornece certificado nem conta Apple.

Depois de instalar, abrir Storm Native e importar o ZIP completo da cópia
suportada. A extração precisa de espaço para 9,43 GB de conteúdo além do ZIP.
O programa valida a identidade antes de solicitar a execução real do título.
Um build aprovado ou uma importação concluída não comprova gameplay.

Logs do runtime ficam em Documents/Logs, acessíveis pelo app Arquivos. Em caso
de fechamento do processo, o relatório de análise do próprio iOS também pode
ser necessário para identificar a falha no aparelho.
