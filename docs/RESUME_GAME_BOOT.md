# Retomada direta do boot comercial

Versão atual publicada: **0.6.0 / build 7**, [download privado](https://github.com/miqfernandes07-cmd/StormRevolution-iPhone-Private/releases/tag/native-iphone-run-44082240260).
O build nativo 44079853215, a configuração final 44082240260 e a publicação
44082291246 passaram. O IPA tem 22.794.234 bytes e SHA-256
`6a49c23f688eef6e7075d8f6237e3b43947ba6b5606e8acef50cc61660d290c6`.

A interface oferece português, inglês, espanhol, francês, alemão, italiano e
japonês sem alterar o idioma do jogo. A instalação migra para Documents/Game,
visível no Arquivos, por uma renomeação atômica sem duplicar os arquivos.
Memória ampliada remove o teto de alocação do runtime e amplia o cache;
o iOS mantém seus limites. O pacote declara as chaves atual e antiga do Modo
Jogo. A configuração final altera só Info.plist; outros 80 itens do pacote
permanecem idênticos ao build ligado, inclusive executável, frameworks e ícone.

Há um contorno específico para o abort na notificação opcional de renomear
threads. Uma segunda falha por recurso nulo continua em investigação, com
novos logs. Os dados enviados eram do perfil Seguro e registravam média de
14,12 FPS; não há medição física de ganho ou confirmação de estabilidade do
build 7. Não atribuir o crash ao Rápido com base nesses dados.

Validação: [255 checks UIKit](validation/native-app-ui-build7-2026-11-17.json),
15 casos do wrapper real com contexto sintético, frontend ARM64, link completo
e [auditoria do IPA](validation/native-iphone-ipa-v7-2026-11-17.json).
[Idiomas, Arquivos e memória](APP_LANGUAGES_AND_FILES.md).
[Controles e perfis](MOBILE_CONTROLS.md).

O estado operacional detalhado está em `private/NATIVE_IPA_STATE.json`. Não solicitar novo login nem uma nova importação quando a instalação já existe. Os arquivos e executáveis comerciais continuam privados.

Atualização após o teste do build 3: o proprietário relatou corrupção da imagem
desde a abertura e os menus, enviando captura, logs 005/006 e native-session.
Versão de iOS informada pelo diagnóstico: 27.2; o perfil solicitava FSI. O
build nativo 4 / 0.4.1 passou no run privado 44057527412 com dois perfis host,
opção Seguro com render passes clássicos, migração de cache e nova tela inicial.
O build 5 adicionou o ícone no run privado 44060974749, mantendo executável e
frameworks idênticos. O IPA foi publicado e auditado; falta novo teste físico.
O estado operacional atualizado permanece em `private/NATIVE_IPA_STATE.json`.

O IPA nativo experimental build 3 / 0.4.0 está publicado e auditado:
`native-iphone-run-44029386428`. O proprietário executou o build 2 em iPhone
15 Pro, selecionou personagens e chegou à luta, mas relatou crashes e tela preta
e enviou três logs. O build 3 inclui controles PlayStation/celular, ajustes,
perfil Compatível e diagnóstico de alocação/cópia. Falta testar essa atualização
no aparelho, preservando a instalação e seus dados. Não repetir a
geração/extração comercial ou substituir o executável por um diagnóstico.
Estado operacional: `private/NATIVE_IPA_STATE.json`; guia: [IPA nativo](NATIVE_IPA.md).

Histórico anterior ao teste físico: [boot privado completo com ReXGlue](REXGLUE_BOOT_2026_11_16.md).
O protótipo Linux chegou ao menu de modos e criou um save real; ainda não há
combate comprovado ou execução do runtime ReXGlue no aplicativo iOS.
A integração atual está em `ios/Native/`; o build privado preparado está em
`private/iphone-build/`. O proprietário criou e liberou
`miqfernandes07-cmd/StormRevolution-iPhone-Private`; a compilação privada está
em andamento. Não enviar o título à CI pública. Os recursos completos
foram extraídos privadamente. O importador iOS recebeu uma correção de lifetime
do callback de progresso após crash comprovado no simulador.

Atualização de 2026-11-16: [relógios e reservas guest32](BOOT_CLOCK_RESERVATIONS_2026_11_16.md).
O diagnóstico passou pelo export KeTimeStampBundle e por lwarx/stwcx de 32 bits.
Agora explora inicializadores do título, mantendo campos/variantes ausentes com
falha explícita. O jogo continua sem abrir. O perfil VGA é experimental.
Config: `private/entry-prefix-qualified.json`; checkpoints: `private/probectors-*/`.
A compilação privada alternativa está em `private/rexglue/`, sem integração iOS.
Conferir existência e hashes desses arquivos antes de retomar. O estado abaixo é
histórico.

Prioridade: execução do título. Não refazer interface, importação ou layout de
controles para tentar resolver a ausência de gameplay. O IPA 0.2.1 é infraestrutura.

## Estado salvo

- Última execução comercial comprovada: diagnóstico privado de 11 funções AOT
  compiladas/ligadas, oito entradas observadas, reserva de 1 MiB e commit de
  64 KiB; parou em `KeGetCurrentProcessType`. Não é boot Xbox qualificado.
- Agora implementados get/set do byte PIB+0x2f, inicial USER=1, e inicialização
  dos campos conhecidos de critical section, incluindo spin count. Adaptadores
  reais do probe compilados e executados com contexto sintético e UBSan.
- Esses novos handlers **ainda não foram reexecutados sobre o título**. Enter,
  TryEnter, Leave, scheduler/KTHREAD/TLS e a ABI inicial permanecem pendentes.
- `private/game/default.xex` foi recuperado novamente do arquivo fornecido,
  isoladamente por HTTP Range. 11.776.000 bytes, CRC32 e SHA-1 conferidos:
  c9c1cf1fc4d7a535542edb1aae19751d4ed7e090.
- Hash SHA-256: b9fd8ac231a96560db2b54340880f2c3d7e8d4cd4cfa1153112077f2fa8af777.
  Nunca enviar esse arquivo ou C++ comercial para Git/CI pública.

## Próxima implementação

1. Reconstruir a toolchain privada XenonRecomp no commit e série de 13 patches
   registrados em `config/xenon_experimental_series.json`. Os comandos públicos de
   build/revisão estão em `.github/workflows/aot-tests.yml`. O compilador usado
   antes era Clang19.1.7; o novo workspace só possui GCC14 e não retém a toolchain.
2. Recriar a imagem original antes de patches de import, configuração e saída
   privadas. Os antigos `image-pristine.bin`, `generated-thirteen` e config do
   diagnóstico foram perdidos na recriação do ambiente; não fingir que existem.
   Consultar KERNEL_BRINGUP/VSCR_DISPATCH para hashes e evidências históricas.
3. Config do probe agora exige `process_block`: endereço PIB guest32 alinhado,
   com 0x60 bytes livres de conflitos. Somente o byte conhecido será mapeado.
   Rever layout e hashes antes de executar; não reaproveitar digest anterior.
4. Selecionar/qualificar novamente as funções do prefixo real e executar
   `tools/recompilation/prefix_probe.py` com config revisada, toolchain verificada
   e UBSan. Guardar logs comerciais somente em `private/`. Corrigir o próximo
   contrato observado, mantendo dependências ausentes com diagnóstico explícito.
5. Resolver as 79 chamadas omitidas/19909 palavras zero do inventário anterior,
   revisar funções/branches/modo CPU e só então qualificar a imagem completa.
6. Implementar a tradução gráfica Xenos/Metal e os serviços realmente chamados;
   o renderer atual só desenha um triângulo diagnóstico. XMA/áudio do título e
   gameplay também não estão integrados. Código ARM64 sozinho não resolve isso.

## Validação atual

Linux x86_64/GCC14.2/UBSan: 10/10 CTest, 99 Python, 1069 verificações do novo
módulo. Incluem preservação de campos desconhecidos, falhas sem escrita parcial,
conflitos do PIB, tipos inválidos, arredondamento/wrap de spin e ABI dos wrappers.
Rodar `cmake --build build --parallel 2` e
`ctest --test-dir build --output-on-failure`. CI deste marco registrada à parte;
nenhum resultado antigo deve ser atribuído a estes novos handlers.

O usuário não precisa fornecer uma “imagem AOT” pronta. O projeto deve produzi-la
com sua cópia do jogo. Arquivos privados continuam fora do Git e podem desaparecer
quando o ambiente é substituído; os relatórios públicos não são backups do jogo.
