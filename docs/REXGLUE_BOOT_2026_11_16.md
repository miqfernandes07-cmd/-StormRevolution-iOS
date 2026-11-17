# Boot privado com ReXGlue — 2026-11-16

Ainda não há versão jogável no iPhone. O aplicativo UIKit não incorpora o
ReXGlue nem o código comercial recompilado. O novo experimento privado Linux
compilou e vinculou o título completo e exibiu gráficos reais de inicialização:
indicador de carregamento, logotipos, vídeo de abertura, tela de título e diálogos
de salvamento. O START respondeu. Ainda não se comprovou carregamento do menu
de modos, combate ou desempenho jogável. As capturas correspondem à cópia
fornecida pelo usuário.

## Runtime alternativo e recursos

Usou-se a release ReXGlue 0.11.0, commit
`a3e1d82678ca20d68d4837a8e9ee4652ff073745`, e o pacote Linux AMD64 oficial com
SHA-256 `e7d543ab8dde2c7839836a0417bfe84691c10f93357ec2c023fa98d3d315803b`.
O source de main consultado anteriormente, `ebac1cf...`, não é a revisão da
release executada. A referência está em `config/rexglue_reference.json`.

A geração privada produziu 256 arquivos, incluindo 126 fontes C++, cerca de
134 MiB. A primeira geração foi interrompida por timeout apesar de terminar a
escrita nos logs; uma consulta posterior à stamp terminou com status 0. A
compilação e o link nativos seguintes terminaram com status 0. Isso não qualifica
todas as instruções ou caminhos comerciais; o output contém traps de limites de
switch. Nenhuma função foi substituída por retorno de sucesso para obter as telas.

Os 21 arquivos do ZIP fornecido foram materializados privadamente, somando
9.433.995.676 bytes. O XEX foi verificado anteriormente; os outros 20 arquivos
tiveram CRC32 conferido ao concluir a descompressão. Não se armazenou o ZIP
inteiro. Como o filesystem local é menor que o conjunto extraído, parte dos
containers foi colocada no tmpfs e ligada ao GameRoot por symlinks.

Os testes iniciais sem todos os recursos tinham falhas de abertura de CPK e
shaders. Um teste posterior sofreu SIGBUS ao disputar o tmpfs com a memória
compartilhada do runtime. Foram removidos somente mappings de processos já
encerrados e movidos dois containers para o filesystem. O teste seguinte passou
desse ponto. Isso foi uma restrição do ambiente Linux, não uma correção no jogo
nem evidência sobre memória disponível no iPhone.

O driver foi Vulkan por software, llvmpipe, numa janela Xvfb 1280×720. O áudio
usou um dispositivo virtual. Não há teste de áudio audível, GPU Apple ou FPS.
Os testes usaram inicialmente `-O0 -g0`; a recompilação `-O1 -g0` também terminou
com link bem-sucedido. Não se deduz desempenho dessa opção de compilador.
O run de cinco minutos com todos os recursos foi encerrado pelo timeout após
as telas iniciais, sem comprovação de gameplay. Avisos de falha de pacotes GPU
durante o encerramento não foram confundidos com a causa da inicialização.
O run otimizado foi estendido manualmente até cerca de 23 minutos e terminou
por timeout, após título/diálogos de save. Não foi chamado de teste de gameplay.
Um novo run usa o modo de vídeo 640×480 e limite de apresentação de 30 Hz;
esse limite configurado não é um FPS medido.

## Correção do importador iOS

O run [43918785875](https://github.com/miqfernandes07-cmd/-StormRevolution-iOS/actions/runs/43918785875)
compilou o app ARM64 para iPhone e o app x86_64 para simulador, com Xcode 16.4.
No simulador passaram o autoteste do runtime e a conclusão do comando Metal.
O teste sintético de importação encerrou o app por EXC_BAD_ACCESS na main queue.
O relatório identificou o bloco criado dentro do callback C++ de extração.

Esse bloco podia capturar a closure temporária da lambda e executar depois de
ela ser destruída. `ReportExtractionProgress` agora cria o bloco fora da lambda,
retendo os valores e o callback que serão entregues à main queue. A lambda
captura explicitamente o cancelamento e o callback por valor. A regressão é
verificada pelo mesmo teste real do importador no simulador, sem dados do jogo.
A correção passou no
[run 43980867932](https://github.com/miqfernandes07-cmd/-StormRevolution-iOS/actions/runs/43980867932):
build iPhone ARM64, build simulador e smoke completo. O relatório real do
importador registrou três verificações aprovadas: XEX inválido, traversal e
cancelamento, preservando a instalação anterior. O ZIP comercial completo
não foi importado no simulador. O Linux passou 13/13 CTest.

A qualificação sintética anterior
[43922468155](https://github.com/miqfernandes07-cmd/-StormRevolution-iOS/actions/runs/43922468155)
passou no Linux e no macOS, incluindo compilação dos bridges próprios de memória,
dispatch e reservas como objetos iPhone ARM64. Não executou o título no iPhone.

## Próxima fronteira: iPhone

O ReXGlue declara Windows/Linux/macOS, não iOS. Os binários Linux ou macOS não
podem ser incluídos no IPA como runtime iPhone. A versão usada exige Clang 20
ou AppleClang 17/Xcode 26 e C++23. O build UIKit atual usa C++17 e Xcode 16.4.

Há dependências concretas a conferir: fibers com ucontext, memória virtual e
aliases, tratamento de sinais, ciclo de vida UIKit, extração do CAMetalLayer de
uma janela SDL UIKit, MoltenVK para iOS e empacotamento/assinatura das bibliotecas.
O caminho SDL atual trata a janela Apple como Cocoa; passar pelo branch `APPLE`
no CMake não comprova suporte a iOS.

O workflow `rexglue-ios-probe.yml` compila fontes POSIX selecionadas e **sem
modificações** para `arm64-apple-ios17.0`, usando o Xcode mais novo instalado,
e depois repete a compilação com uma adaptação fixada por hashes. A baseline
permanece registrada como falha esperada; erros na versão adaptada falham o job.
Mesmo um resultado verde não
qualifica o SDK inteiro: não faz link, não executa no dispositivo e não contém
o título. Seu objetivo é obter os primeiros bloqueios reais da adaptação.

Em Xcode 26.3/SDK iPhoneOS 26.2, relógio, fibers e threading compilaram sem
alteração. Os dois fontes de consulta de memória falharam por usar
`mach/mach_vm.h`/`mach_vm_region`, indisponíveis no SDK iPhone. A adaptação usa
`vm_region_64` e os tipos `vm_address_t`/`vm_size_t` no branch iPhone, mantendo
o caminho macOS. Os cinco fontes adaptados compilaram no
[run 43983141070](https://github.com/miqfernandes07-cmd/-StormRevolution-iOS/actions/runs/43983141070).
[Relatório agregado](validation/rexglue-ios-sources-2026-11-17.json).

O workflow `rexglue-ios-base.yml` amplia a verificação para configurar o SDK e
compilar/linkar `rexbase` inteiro para iPhone. A configuração já passou e os
fontes compilaram; o primeiro link encontrou `GetPerfSettings` ausente porque
seu provider tinha sido desativado. A opção necessária foi restabelecida e o
build está sendo repetido. Ainda não há biblioteca base com link aprovado.
Os pacotes Vulkan/macOS servem à descoberta de headers na configuração; não
são bibliotecas iPhone e não entram no alvo base. Um resultado válido precisa
mostrar a plataforma iOS no Mach-O, não apenas arquitetura ARM64.

## Retomar neste workspace

Todos os recursos, C++ comercial, binários, configs e logs do título permanecem
sob `private/`. Podem desaparecer numa troca de ambiente. Nunca enviá-los ao Git,
à CI pública ou a artefatos públicos. Capturas privadas representam execução
real; não são imagens geradas nem provas de jogabilidade no iPhone.

- Projeto: `private/rexglue/project/StormProbe_manifest.toml`.
- SDK: `private/rexglue/sdk/linux-amd64/`.
- Binário: `private/rexglue/project/out/build/linux-probe/StormProbe`.
- Recursos: `private/game/`; conferir também os destinos dos symlinks no tmpfs.
- Extração: `private/reports/materialized-assets.json` e logs `materialize-*`.
- Boot: `private/reports/rexglue-all-assets-run.log` e `private/screens/`.
- Build otimizado: `private/reports/rexglue-o1-build-resume.log`.

No ambiente atual foram usados Clang 20.1.8 e headers GCC13, para compatibilidade
com a libstdc++ do SDK. A CI pública usa somente código próprio e fontes abertas.
Licença do SDK: BSD-3-Clause; consulte o LICENSE na revisão referenciada.
