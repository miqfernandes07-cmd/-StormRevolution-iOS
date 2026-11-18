# Controles por ações e comparação de desempenho

A versão 0.5.0 acrescenta uma interface própria de ações para celular,
inspirada no tipo de controle solicitado pelo proprietário. Ela usa o mesmo
gamepad virtual Xbox 360 já ligado ao Revolution. O código, os shaders e os
assets do primeiro STORM enviado como referência continuam privados e não
foram incorporados ao aplicativo.

A versão atual 0.6.0 / build 7 mantém esses controles e acrescenta
[idiomas da interface, acesso pelo Arquivos e memória ampliada](APP_LANGUAGES_AND_FILES.md).
O relatório do build 6 confirmou Seguro ativo e média de 14,12 FPS em amostras
que misturam menus e jogo; não é um benchmark controlado. O ganho de FPS do
build 7 ainda precisa ser medido no aparelho.

## Entrada manual

Em Ajustes → Botões, **Celular** seleciona os nomes de ações e a disposição
móvel. PlayStation e Xbox preservam suas opções e posições anteriores.

| Ação | Entrada padrão Xbox 360 |
| --- | --- |
| Pulo / confirmação nos menus | A |
| Ataque / cancelamento nos menus | B |
| Kunai | X |
| Chakra | Y |
| Aliado 1 / Aliado 2 | LB / RB |
| Substituição / Guarda | LT / RT |
| Pausa | Start |
| Botão adicional de voltar/selecionar | Back/Select |

O analógico esquerdo move o personagem; o direito controla a câmera quando
o jogo permite. Duplo toque continua enviando L3/R3. Os direcionais permanecem
disponíveis para itens e navegação. Em Organizar, botões e analógicos podem
ser movidos, incluindo os três atalhos novos.

As posições das ações usam `touchPositionsActionsV1`. Os controles móveis com
símbolos usam `touchPositionsMobileV3`; o clássico mantém
`touchPositionsXbox360V2`. Restaurar uma disposição preserva as outras.

## Atalhos

| Atalho | Sequência enviada |
| --- | --- |
| Jutsu | Y → soltar → B → soltar |
| Supremo | Y → soltar → Y → soltar → B → soltar |
| Dash | Y → soltar → A → soltar |

Os comandos dependem de chakra, estado do personagem, tipo de combate e
bindings do próprio jogo. A interface não garante a execução de uma técnica
quando o jogo não a permite. Bindings alterados dentro do jogo podem exigir
voltar ao esquema original.

Os intervalos usam aproximadamente dois quadros de apresentação, limitados a
80–350 ms, com valor inicial de 180 ms. A frequência vem do contador do SDK;
ela não garante a frequência de leitura dos controles pelo código guest.
O toque no atalho inicia a sequência, que continua depois de soltar o dedo.
Toques nos botões normais, cancelamento de toque, reset, organização, ajustes
e saída do app invalidam os passos pendentes. O estado de um botão mantido
manualmente ou por controle externo continua independente dos bits do atalho.

O teste de simulador verifica a ordem e a liberação dos bits, cancelamento e
limites do layout. A execução dos golpes exige confirmação na luta real.

## Perfis gráficos

O arquivo do aparelho confirmou build 5, Seguro, 720p, 1×, FXAA desligado,
zero avisos de memória e 1875 MiB disponíveis. O proprietário informou
aproximadamente 11 FPS; os arquivos anteriores não medem CPU/GPU separadamente.

| Configuração | Seguro | Rápido | Padrão |
| --- | --- | --- | --- |
| Render target solicitado | host | host | host |
| Dynamic rendering | não | não | sim |
| Resolve direto do host | não | não | sim |
| Leitura de resolves | full | fast | none |
| Memexport habilitado | sim | sim | sim |
| Memexport em buffers alternados | não | sim | não |
| Orçamento do título com Memória ampliada desligada | 512 MiB | 512 MiB | 480 MiB |

No build 7, Memória ampliada vem ligada e seleciona o valor documentado `0`
(sem teto de orçamento do runtime) nos três perfis, mantendo os endereços
físicos esperados pelo jogo e os limites de RAM impostos pelo iOS.

Rápido é experimental e usa os caminhos de leitura em buffers alternados
existentes no SDK. Eles podem apresentar resultados anteriores ou artefatos;
Seguro restaura as leituras completas da versão que o usuário conseguiu jogar.
Nenhum perfil solicita FSI. A atualização preserva a seleção do usuário e
inicializa a nova opção de leitura rápida desabilitada.

Para comparação, testar os mesmos personagens e arena por aproximadamente
60 segundos com Seguro e Rápido, mantendo inicialmente os demais ajustes
iguais. Depois, testar 480p / 1× / FXAA desligado para reduzir a carga visual.
Perfil, resolução, escala e FXAA exigem fechar e reabrir o app. O limite de FPS
define o teto; a taxa entregue depende do tempo de processamento.

## Dados registrados

`native-session.json` inclui até 60 amostras, aproximadamente a cada dois
segundos, com FPS, tempo de quadro e número de quadros do SDK, estado térmico,
modo de pouca energia e estado da sobreposição nativa. O resumo exclui a
sobreposição de ajustes, mas pode incluir menus e pausas do próprio jogo.
As amostras não são uma medição separada de CPU, GPU ou tempo gasto em fences.

`runtimeRequested` mostra as preferências atuais; `runtimeConfigured` lê os
valores registrados no SDK. Uma alteração pendente de reinício pode aparecer
somente no primeiro. Esses valores não expõem todos os fallbacks do backend.
O relatório é atualizado periodicamente a cada dez segundos e imediatamente
em eventos relevantes ou no compartilhamento. Nenhum save ou arquivo de
conteúdo do jogo é incluído no compartilhamento.
