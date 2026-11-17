# Aplicativo nativo experimental

O alvo `StormNative` integra ReXGlue e o código recompilado do título. É
separado do aplicativo UIKit de infraestrutura `StormRevolution`. Ainda não há
execução comprovada em iPhone físico nem validação de gameplay.

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
licenças e 37.255.824 bytes na seção de código recompilado. Esse IPA usa a
versão anterior do backend de memória e será atualizado antes da indicação
para teste no aparelho.
[Relatório do link](validation/native-iphone-link-2026-11-17.json).

## Memória no sandbox

O quinto adaptador substitui `shm_open` no branch iPhone por um arquivo esparso
criado no diretório temporário privado do processo e desvinculado antes de
retornar o descriptor. Mantém aliases `MAP_SHARED` sem depender de um nome
POSIX global ou entitlement de grupo. Não torna os bytes PowerPC executáveis.

O teste do helper real passou por 25 verificações no Linux/UBSan e no macOS:
dois aliases coerentes acima de 4 GiB, tamanho esparso, nome removido, descriptor
close-on-exec, restrição de escrita no descriptor somente leitura, validade dos
views depois de fechar o descriptor e rejeição de tamanhos inválidos. A
compilação para iPhone também passou; o link do SDK completo está em andamento.
Não houve execução desse backend em aparelho físico.

O reempacotamento mantém o executável comercial já vinculado apenas quando
todos os headers públicos do SDK são idênticos aos usados nessa compilação.
O novo pacote precisa conter o quinto adaptador; depois é inspecionado de novo.

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
