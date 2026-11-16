# Boot: relógio atualizado e reservas guest32 — 2026-11-16

O jogo continua sem versão jogável. Não há execução comercial comprovada no
simulador/iPhone, renderer Xenos no aplicativo, gameplay ou FPS medido.

## Relógios e export de dados

`TimestampBundle` liga o export de dados xboxkrnl 0xAD (`KeTimeStampBundle`),
validando slot, palavra original e a revisão XEX/PE no probe. Somente o campo
BE32 de uptime em +16 é mapeado; os outros campos permanecem indisponíveis.
A região conhecida de 24 bytes precisa estar livre e alinhada.

O uptime é amostrado de uma fonte monotônica serializada em cada leitura, com
truncamento para milissegundos e wrap uint32 após 2^32 ms. O epoch do diagnóstico
é estabelecido antes de entrar no código guest. Não há thread de timer escrevendo
em AddressSpace em paralelo, nem valor constante de sucesso.

AddressSpace ganhou providers de leitura read-only. Validam-se todos os trechos
antes de invocar callbacks; leituras que atravessam providers usam um buffer de
snapshot para não alterar parcialmente o destino se um callback falhar. Providers
não podem mutar/remapear a AddressSpace. Isso não cria um backend MMIO genérico.

O emissor fixado usa `__rdtsc()` para `mftb`. O probe agora intercepta essas
chamadas **depois** de incluir o contexto gerado e fornece ticks guest a 50 MHz,
calculados com a mesma origem monotônica do uptime. A declaração intrínseca ARM
no cabeçalho não é modificada. Não se usa a frequência bruta do contador x86 ou
CNTVCT ARM como se fosse a frequência Xbox. Essa adaptação vale somente no
prefixo diagnóstico; o upstream não foi modificado.

## lwarx/stwcx de 32 bits

O fluxo real encontrou uma rotina com load-reserve, store-conditional e alterações
de flags MSR EE/RI. O caminho anterior indexava `base` diretamente e usava CAS por
igualdade, que não detecta ABA. Esse caminho não foi liberado no probe.

O novo backend serializado mantém tokens por binding/contexto e versões de
regiões de reserva de 128 bytes. Escritas ordinárias, cópias, map/unmap e o próprio
store-conditional invalidam tokens anteriores que cobrem o mesmo granule. Mesmo
escrever o mesmo valor ou mudar A->B->A faz uma reserva anterior falhar. Escritas
em outro granule não a invalidam. Store-conditional exige endereço correspondente,
alinhamento e permissão, e consome o token em toda tentativa.

Uma adaptação estrita dos dois padrões de fonte emitidos pelo XenonRecomp fixado
substitui os acessos raw por `PPC_LOAD_RESERVE_U32` e
`PPC_STORE_CONDITIONAL_U32`. As funções adaptadas têm hashes revisados na config
privada. Outras variantes, atomics de 64 bits e padrões desconhecidos continuam
rejeitados. Não se aplica uma troca genérica de CAS a código arbitrário.

Este é um modelo experimental guest32 com acesso serializado, não prova de
coerência SMP, barreiras ARM, interrupções, DMA, aliases físicos ou CPU mode Xbox.
Providers dinâmicos não aceitam reservas. As alterações de MSR observadas no
código não implementam um scheduler. A ABI inicial completa segue não qualificada.

## Execução privada e limites

Os checkpoints anteriores paravam no export de uptime e depois na rotina atômica.
O novo caminho passou por ambos e avançou para mais inicializadores da biblioteca
C e do título. O perfil VGA virtual experimental permanece explícito e necessário
para este experimento, sem alegação de suporte real de vídeo.

A tabela de inicializadores foi revisada a partir dos limites reais do laço guest:
597 entradas, 596 destinos distintos não nulos. Para reduzir ciclos de compilação,
564 wrappers curtos passaram nos gates lexicais e foram registrados em lote;
32 candidatos ficaram de fora. Um checkpoint em `private/probectors-634/`
registrou 634 funções selecionadas e 607 entradas contando repetições. Isso não
significa que todas as selecionadas foram executadas nem aprova a imagem inteira.

O prefixo permite até 1024 funções e **2 MiB de corpos selecionados**, conservando
os limites de inputs, guardas de callees e timeout. A seleção em lote ocupou
812499 bytes e mantém os mesmos gates de memória/código. Novos destinos e callees
precisam passar por esses gates. Toda geração, adaptação, config, binário e log
comercial continua em `private/`; nada disso foi enviado ao repositório público.

## Verificação

Linux/GCC14/UBSan: 13/13 CTest. Os novos testes cobrem leitura dinâmica, snapshot
sem escrita parcial, permissões, overflow e wrap de uptime; reservas com dois
contextos, ABA, mesmo valor, endereço diferente, remap e invalidação por granule.

A fixture PPC própria `tests/integration/xenon_checked_reservations.py` foi
convertida pelo XenonRecomp, adaptada e compilada/executada com Clang19/UBSan:
50 verificações de valores BE32, guest32, CR0 e ABA passaram. A integração anterior
de dispatch e memória escalar também passou: 102 verificações nos modos alias
ELF e wrapper portátil. Nenhum desses testes executa o jogo.

A CI AOT inclui a nova fixture e sua compilação como objeto iPhone ARM64, além
do módulo TimestampBundle. Os resultados Apple dessa alteração ainda precisam
ser confirmados. Os pools Intel e ARM já falharam em adquirir runner em runs
anteriores; o run 43910606674 registrou explicitamente restrição de capacidade
macOS ARM. Os workflows agora oferecem seleção manual de pool, com fallback
Intel e opções macos-15/macOS latest. Falta de runner não foi tratada como erro
funcional do aplicativo nem como aprovação Apple.

## Investigação de runtime alternativo

Foi avaliado o ReXGlue SDK 0.11.0, BSD-3-Clause, com runtime e GPU Vulkan/MoltenVK
para Windows/Linux/macOS. Não declara iOS suportado. O SDK foi baixado privadamente
e seu SHA-256 conferido contra o digest da release:
`e7d543ab8dde2c7839836a0417bfe84691c10f93357ec2c023fa98d3d315803b`.

O experimento privado produziu 256 arquivos, incluindo 126 fontes C++, cerca de
134 MiB. A primeira execução teve timeout 124 apesar de terminar a escrita nos
logs; uma consulta posterior à stamp terminou com status 0 e indicou outputs
atualizados. Isso não é aprovação de código, boot ou compatibilidade. Há traps
de limites de switch que precisam de revisão, e a compilação nativa do projeto
experimental ainda deve ser concluída. A base UIKit e as dependências do IPA
não foram substituídas pelo SDK.

## Referências

- [Xenia, campo de uptime em KeTimeStampBundle](https://github.com/xenia-project/xenia/blob/95a5c3ee250f80c3b9d139658649d9ffb6db3eec/src/xenia/kernel/xboxkrnl/xboxkrnl_module.cc#L219).
- [Xenia, clock guest a 50 MHz](https://github.com/xenia-project/xenia/blob/95a5c3ee250f80c3b9d139658649d9ffb6db3eec/src/xenia/emulator.cc#L149).
- [ReXGlue SDK](https://github.com/rexglue/rexglue-sdk), source revisado em `ebac1cf0d04bab0042a5dd6148b34ab3953e9c0d`, sem incorporá-lo ao aplicativo.

Xenia e ReXGlue usam BSD-3-Clause. Foram consultados contratos/organização;
nenhuma chave, código comercial ou loader externo foi adicionado ao runtime.
