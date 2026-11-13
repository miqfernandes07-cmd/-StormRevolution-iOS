# Teste do aplicativo com AltStore Classic

A versão 0.2.1 prepara arquivos ZIP e oferece controles e diagnóstico. **Não executa
o jogo**: a imagem AOT completa ainda não foi aprovada nem ligada ao aplicativo.
O ZIP não é convertido em código ARM64 no iPhone; essa preparação continua offline.
Projeto iOS desenvolvido por Miquéias.

[Baixar IPA 0.2.1 com correção de rolamento — artefato ZIP](https://github.com/miqfernandes07-cmd/-StormRevolution-iOS/actions/runs/43451112622/artifacts/14051071083)
Disponível originalmente até 20/11/2026; o GitHub pode exigir login.
[Capturas reais e logs do simulador](https://github.com/miqfernandes07-cmd/-StormRevolution-iOS/actions/runs/43446293033/artifacts/14049575402).
O controle “Gamepad” detectado nessas capturas é uma entrada fornecida pelo ambiente
do simulador; não comprova conexão Bluetooth/USB de um controle físico.

## Instalação

1. No Windows, instale/configure AltServer e AltStore **Classic** conforme o
   [guia oficial](https://faq.altstore.io/altstore-classic/how-to-install-altstore-windows).
   AltStore PAL não é o fluxo de sideload usado por este guia.
2. Baixe o artefato `storm-ios-infrastructure-unsigned` na execução iOS indicada
   em PROGRESS. Descompacte o ZIP **do artefato** para obter
   `StormRevolution-UNSIGNED.ipa`. Esse arquivo é o aplicativo, não o jogo.
3. Salve o IPA no aplicativo Arquivos do iPhone. Com AltServer acessível pelo
   iPhone, abra AltStore Classic → My Apps → **+** e selecione o IPA.
   AltStore realiza a assinatura com a sua conta. Não envie senha ou certificado
   ao repositório ou ao chat.
4. Se solicitado pelo iOS, ative o Modo de Desenvolvedor e conclua as instruções
   de confiança da conta. Renove a assinatura pelo AltStore antes do vencimento
   mostrado por ele. A compatibilidade do seu iOS com AltStore deve ser conferida
   no guia; **iOS 27 não foi testado por este projeto**.

Atualize usando o mesmo AltStore/conta, sem apagar o aplicativo antes, para
preservar a importação existente. A versão 0.2.1 permite iniciar o arrasto sobre
botões e mostra o indicador vertical. Confirme o rolamento físico nas três abas.

## Importação e controles

Abra Biblioteca → Selecionar arquivo ZIP e escolha a cópia extraída de Xbox 360
compactada em ZIP. ISO, APK, ZIP com senha/múltiplos volumes e métodos diferentes
de Store/Deflate não são aceitos. Esta versão exige caminhos ASCII e uma única
entrada `default.xex`, sem distinção de maiúsculas. Pastas externas ao diretório
que contém esse executável não são instaladas como recursos do jogo.

O app lê ZIP/ZIP64 em blocos, verifica CRC/tamanhos, procura o executável inclusive
sob uma pasta envolvente e valida tamanho, hash e metadados. Após aprovação,
normaliza o nome para `default.xex` e instala a árvore relativa ao executável.
A cópia de origem permanece intacta. Erro ou cancelamento antes do commit mantém
os dados anteriores. Extrações abandonadas são limpas na próxima importação.

Mantenha o app aberto. Para a cópia informada de 9,43 GB descompactados, reserve
esse espaço **mais 256 MiB livres**. O ZIP já armazenado no aparelho e uma eventual
instalação anterior também ocupam espaço. Um provedor de arquivos/iCloud pode
precisar baixar o ZIP para o aparelho antes de disponibilizar sua leitura.

Em Controles, use o layout Xbox 360: A verde, B vermelho, X azul, Y amarelo,
LB/RB, LT/RT, Start/Back, D-pad, dois analógicos e cliques LS/RS. Tamanho, opacidade
e posições são configuráveis. O painel mostra os valores recebidos.
Emparelhe um controle compatível em Ajustes → Bluetooth do iPhone, ou conecte por
USB quando suportado. O app reconhece controles com perfil extended gamepad do
GameController. **Layout Xbox 360 não implica compatibilidade física com o
controle Xbox 360 original.** Xbox One/Series e PlayStation dependem do modelo e
do suporte fornecido pelo iOS; não houve teste físico nesta iteração.

Teste também Ajustes → Diagnóstico Metal. O triângulo é identificado como teste
visual da infraestrutura, não como jogo. Compartilhar diagnóstico abre a folha
nativa de compartilhamento apenas por ação do usuário.

## Resultado que precisamos registrar no aparelho

- O app instala e abre sem encerrar?
- Seleção, progresso, cancelamento e erros do ZIP aparecem corretamente?
- Após importar a cópia correta, o app informa arquivos preparados e AOT pendente?
- Botões, dois sticks e gatilhos mudam o painel de entrada e liberam ao soltar?
- Conectar/desconectar o controle atualiza o status sem entradas presas?
- O diagnóstico Metal aparece? Há travamentos ao alternar de app ou girar a tela?

Registre modelo do iPhone, versão exata do iOS, modelo do controle e o erro/log
observado. Abertura do aplicativo e importação bem-sucedida não comprovam gameplay.
