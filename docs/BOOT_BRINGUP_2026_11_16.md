# Retomada do diagnóstico — 2026-11-16

## Atualização: locks e consulta de privilégios

O diagnóstico agora passa por `RtlEnterCriticalSection` e `RtlLeaveCriticalSection`
e para em `XGetAVPack` (XAM, ordinal 0x3CB). A execução final registrou 24 entradas
em funções, com chamadas repetidas, sobre 19 funções AOT selecionadas. Não houve
abertura do jogo, renderização, novo IPA nem build Apple.

`CriticalSections` usa identidade guest explícita e memória BE; suporta aquisição
sem contenção, recursão, TryEnter e liberação pelo proprietário. Acesso à memória
deve ser serializado pelo chamador. Enter com outro proprietário, estados inválidos,
waiters que exigiriam scheduler e overflow de recursão param antes de mutações.
Essa classe não é um mutex do host, KTHREAD, TLS ou scheduler Xbox. No probe,
`diagnostic_thread` é um token guest alinhado, revisado na configuração privada;
nenhum campo de KTHREAD ou registrador r13 é fabricado.

`XexCheckExecutablePrivilege` consulta o bit real do campo XEX `0x30000`.
Campo ausente retorna false; índices fora de 0..31 são diagnosticados antes do
shift. O wrapper retorna BOOL normalizado e exige módulo vinculado.

Fontes semânticas BSD-3-Clause:

- [Locks em xboxkrnl_rtl.cc](https://github.com/xenia-project/xenia/blob/95a5c3ee250f80c3b9d139658649d9ffb6db3eec/src/xenia/kernel/xboxkrnl/xboxkrnl_rtl.cc#L421).
- [Privilégios em xboxkrnl_modules.cc](https://github.com/xenia-project/xenia/blob/95a5c3ee250f80c3b9d139658649d9ffb6db3eec/src/xenia/kernel/xboxkrnl/xboxkrnl_modules.cc#L22).

A referência [XGetAVPack](https://github.com/xenia-project/xenia/blob/95a5c3ee250f80c3b9d139658649d9ffb6db3eec/src/xenia/kernel/xam/xam_info.cc#L193)
retorna 6, mas marca isso como stub e deixa vários valores sem especificação.
Esse retorno não foi copiado como serviço qualificado. O próximo trabalho é
modelar e revisar o contrato de ambiente de vídeo; a consulta não substitui o
backend Xenos/Metal, shaders, buffers e apresentação do título.

Verificação: GCC14/UBSan, 10/10 CTest; módulo de processo/locks, 3388 checks;
módulo XEX, 110 checks. Os wrappers reais de Enter/TryEnter/Leave foram compilados
com contexto sintético e verificaram preservação de r3 nos métodos void, resultado
BOOL em TryEnter e efeitos BE32 em ownership/recursão. Os testes incluem duas
identidades guest intercaladas, campos desconhecidos preservados, proteção de
memória, ausência de escrita parcial, overflow, não proprietário e contenção.
Diagnóstico comercial separado: Clang19.1.7/UBSan, `private/probepriv-19/`.
Config atual: `private/entry-prefix-qualified.json`. Todos os artefatos do título
continuam privados; não houve push ao GitHub.

O relatório abaixo registra o marco anterior desta sessão.


O jogo ainda não abre. Nenhum novo IPA, tela, menu, gameplay ou FPS foi produzido.

## Resultado reproduzido nesta sessão

O executável foi recuperado isoladamente do ZIP fornecido, via HTTP Range.
Foram transferidos 11.840.946 bytes; ZIP CRC32 e identidade XEX passaram.
SHA-256 do XEX: `b9fd8ac231a96560db2b54340880f2c3d7e8d4cd4cfa1153112077f2fa8af777`.
A imagem original antes da mutação de imports foi reconstruída com a ferramenta
privada baseada no loader fixado, 13.762.560 bytes, SHA-256
`98aee7eeca1e79ed2f1c54bca894c5aa0624ed21fb20de3af8b16b3587933275`.

XenonRecomp/XenonAnalyse foram reconstruídos no commit fixado com os 13 patches,
conferindo hashes de fontes. Clang 19.1.7. A análise novamente recuperou zero
tabelas de salto. Isso não comprova ausência de tabelas.

A configuração inicial desta sessão omitia os helpers GPR/LR. Sequências completas
foram localizadas e verificadas na seção executável. A nova ferramenta pública
`tools/ppc_analysis/abi_helpers.py` registra apenas candidatos exatos e únicos,
sem aprovar execução ou modificar a imagem/configuração. Não inclui bytes do jogo.
Os endereços descobertos foram incorporados somente na configuração privada.

A auditoria lexical da geração desta sessão passou de 12.574 chamadas estáticas
sem destino para 321 após configurar os dois helpers GPR/LR. Ambas as saídas têm
19.909 palavras não decodificadas. Os números iniciais desta sessão não substituem
os 79 registros do marco histórico, que usava outra configuração. Ambas geraram
241 arquivos C++; a imagem completa permanece reprovada para execução.

## Novo export de dados

Implementado `HardwareInfo` em `runtime/kernel/process_state.*`, com flags BE32 e
contagem de CPUs lógicas no byte +4. A região de 16 bytes precisa estar livre, mas
somente os cinco bytes conhecidos são mapeados, read-only. Campos desconhecidos
continuam indisponíveis. O binding exige slot alinhado, palavra original e ordinal
0x156; o probe também confere biblioteca e registro de dados sem thunk no XEX/PE.

O perfil explícito do diagnóstico usa flags 0x20 e seis CPUs lógicas, seguindo a
referência de Xenia; não representa detecção de hardware iOS nem um scheduler.
Fonte semântica: [Xenia xboxkrnl_module.cc, linhas 136–153](https://github.com/xenia-project/xenia/blob/95a5c3ee250f80c3b9d139658649d9ffb6db3eec/src/xenia/kernel/xboxkrnl/xboxkrnl_module.cc#L136),
BSD-3-Clause. Não há código desse loader nem chaves no novo componente.

## Execução privada e limite

O probe foi recompilado com UBSan e executou o trecho AOT real selecionado:
reserva de 1 MiB, commit de 64 KiB, leitura de tipo de processo USER=1,
inicialização do heap e leitura do export de hardware. O diagnóstico final
registrou 22 entradas (incluindo chamadas repetidas), em 18 funções selecionadas.
Parou explicitamente em `RtlEnterCriticalSection`, sem retornar sucesso fictício.
A inicialização de critical section foi alcançada no fluxo, mas os locks completos,
KTHREAD/TLS, scheduler e ABI de entrada continuam pendentes. Registradores iniciais
zerados e pilha sintética não equivalem ao ambiente Xbox.

Todos os fontes derivados, configs, binários e logs estão em `private/`, ignorado
pelo Git. O arquivo revisado é `private/entry-prefix-qualified.json`; relatórios
finais estão em `private/probeh-18/`. Conferir existência e hashes antes de retomar.
Se o workspace for substituído, esses arquivos podem desaparecer.

## Verificação e próximos passos

GCC14/UBSan: 10/10 grupos CTest passaram após a alteração, incluindo os três novos
testes Python do localizador de helpers e casos de hardware BE32, campos ausentes,
proteção, colisões, layouts/CPUs inválidos, imports incorretos e slots read-only.
Não houve build Apple nesta sessão.

1. Implementar ownership/recursão de locks com identidade de thread explícita e
   diagnosticar contenção sem um scheduler; validar contratos antes de ligar imports.
2. Reexecutar o probe, mantendo a configuração e os hashes atualizados.
3. Resolver chamadas omitidas, palavras não decodificadas e fluxo indireto antes de
   aprovar uma imagem completa.
4. Implementar backend Xenos/Metal, shaders e serviços/recursos necessários ao título.

Comandos úteis:

```sh
python3 tools/ppc_analysis/abi_helpers.py private/image-pristine.bin \
  --layout mapped --output private/reports/abi-helpers-novo.json
cmake --build build --parallel 2
ctest --test-dir build --output-on-failure
```
