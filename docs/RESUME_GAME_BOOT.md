# Retomada direta do boot comercial

Versão atual publicada: **0.7.0 / build 9**, [download privado](https://github.com/miqfernandes07-cmd/StormRevolution-iPhone-Private/releases/tag/native-iphone-run-44189383485).

Os novos logs do build 8 identificaram 73–75% do intervalo medido em esperas
nas cópias de resolve, com nenhuma chamada de memexport. As duas sessões
estavam em estado térmico elevado; a resolução menor não eliminou a lentidão.
A otimização anterior de memexport não foi usada nessas sessões.

O novo perfil **Desempenho**, em Ajustes → Perfil gráfico, desativa as cópias
de resolve para CPU e mantém o renderizador clássico do Seguro e memexport
síncrono. Selecione-o e feche/reabra o aplicativo. É experimental: efeitos que
leem essas cópias podem apresentar artefatos; nesse caso, volte a Seguro.
Use 1×, 30 FPS e FXAA desligado, com o aparelho frio, para comparar a mesma luta.
Ainda não há ganho de FPS medido no aparelho para o build 9.

A tela inicial oferece **Modo trapaça**, ligado por padrão, para personagens,
variações e coleções presentes nos arquivos importados. Usa um perfil separado:
a primeira ativação copia o progresso normal; desligar antes de Jogar retorna
ao save original. Cada perfil mantém seu progresso. Não fornece DLC ausente
nem completa automaticamente todas as missões. [Comportamento dos saves e limites](UNLOCK_PROFILES.md).

Compilação nativa 44189383485 e publicação 44190341006 aprovadas. O IPA tem
22.800.674 bytes e SHA-256
`99460421c87b32cf25da0254460071ff5ff5e7c2401a88f4a5ccae58e2f33327`.
A auditoria independente confirma ARM64/iOS, os hooks de desbloqueio ligados,
o novo frontend e os conteúdos carregáveis dos 17 frameworks iguais ao SDK
verificado do run 44164692810. O teste UIKit passou em 273 verificações, incluindo
isolamento de saves; as máscaras passaram em 326.896 verificações com métodos
originais e memória sintética. Esses testes não executam gameplay física.
Preserva idiomas, ícone, controles, memória ampliada, Modo Jogo e créditos
MiquéiasF07. **Atualize pelo AltStore sem apagar o aplicativo.**

[Diagnóstico de desempenho e limitações](GPU_READBACK_PERFORMANCE.md).
[Testes UIKit e máscaras](validation/native-controls-unlock-v9-2026-11-17.json).
[Auditoria do IPA](validation/native-iphone-ipa-v9-2026-11-17.json).

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
