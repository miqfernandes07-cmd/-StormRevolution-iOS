# Memória e diagnóstico nativo do entrypoint — 2026-11-12

O diagnóstico privado **compilou e ligou 11 funções AOT reais do executável e
entrou em oito delas no Linux x86_64**. Não é inicialização do jogo: usa registradores
zerados, SP de diagnóstico numa região de 64 KiB e LR sentinela. A ABI inicial
Xbox, threads/TLS e o modo CPU ainda não estão qualificados. Nenhuma função
comercial foi enviada à CI, ao IPA ou ao repositório público.

## Componentes funcionais

`AddressSpace` mantém regiões esparsas de bytes próprios em endereços guest32,
com leitura/escrita big-endian, permissões, verificação de overflow e acessos
que cruzam regiões adjacentes. Uma cópia verifica todos os trechos antes de
alterar o destino; falhas não causam escrita parcial. Regiões são zeradas ao
mapear e não há reserva física automática de 4 GiB. Concorrência e atomics Xbox
não são implementadas por esses métodos: o chamador deve sincronizar acessos.

`xenon_checked_memory.h` conecta os acessos **escalares** emitidos pelo XenonRecomp
à região vinculada à thread/contexto. MMIO produz diagnóstico explícito.
VMX e atomics que indexam diretamente `base` ainda exigem um backend próprio;
o diagnóstico recusa funções selecionadas com esses caminhos detectáveis.
Isso não é um mapa físico Xbox completo nem prova ausência de todos os acessos
não modelados em código arbitrário.

`XexHeader` lê a tabela de cabeçalhos opcionais: chave de tamanho 0 retorna valor,
tamanho 1 retorna endereço do valor e os demais retornam endereço do bloco.
Chaves ausentes retornam zero. Estruturas inválidas produzem diagnóstico.
Essa leitura estrutural não substitui validação de identidade/assinatura.

`ExecutableModule` mapeia o cabeçalho original como read-only, a variável
XexExecutableModuleHandle e os campos de descriptor implementados. Somente esses
campos são mapeados: leituras de campos não implementados falham. O binding do
slot exige o ordinal 0x193 de dados e a palavra original esperada. O probe também
confere biblioteca, tipo de registro, ausência de thunk e imagem original antes
de relocá-lo numa cópia privada de memória. Não muda o XEX nem a imagem no disco.

`VirtualMemory` implementa o subconjunto observado de NtAllocateVirtualMemory:
reserva, commit, recommit com proteção preservada, commit parcial por páginas,
alocação fixa e automática, top-down, páginas 4/64 KiB, proteção read-only/RW,
zeragem inicial e release da reserva inteira. MEM_HEAP é tratado como hint,
coerente com a referência consultada. Reserva não torna bytes acessíveis; commit
fornece os bytes. O limite inicial de backing é 512 MiB, sem compromisso de que
isso atenda ao título. O alocador procura faixas livres e evita sobreposição.

Entradas inválidas retornam NTSTATUS nos casos modelados. Modos/proteções ainda
não implementados produzem diagnóstico identificável. Reset, decommit, mudança
de proteção via recommit, páginas 16 MiB, devkit, aliases físicos e MMIO continuam
pendentes. O adaptador de ponteiros guest verifica ambas as saídas antes de
alocar/liberar e só escreve os resultados quando a operação tem sucesso.
Os pools precisam pertencer ao kernel e as chamadas devem ser serializadas.

## Resultado do diagnóstico real

A primeira tentativa parou no ordinal de dados ainda não ligado. Após implementar
o descriptor e a leitura do cabeçalho, o fluxo alcançou a inicialização do heap.
A primeira chamada reservou **1 MiB**, flags `0x60002000`, proteção RW, sem backing.
A chamada seguinte fez commit de **64 KiB**, que ficaram acessíveis e zerados.
O próximo bloqueio foi **KeGetCurrentProcessType**, recusado explicitamente.
Não houve retorno fictício de sucesso para esse serviço ou para outros ausentes.
[Relatório agregado sem código comercial](validation/entry-prefix-2026-11-12.json).

O probe inclui a imagem inteira como dados RW para esse experimento, uma pilha
controlada e somente os helpers selecionados. As outras 19 dependências diretas
possuem guards que interrompem com o nome, sem implementar comportamento falso.
A saída global continua reprovada por 79 chamadas omitidas e 19909 palavras
não decodificadas; esse experimento limitado não autoriza a imagem inteira.
Não há tela, menus, Xenos/Metal do jogo, áudio ou gameplay comprovados.

## Reprodução privada

`tools/recompilation/prefix_probe.py` tem modo de plano por padrão. A execução
exige config privada com digest revisado, identidade comercial correta, imagem
reconstruída com hash, manifesto da toolchain, nomes/hashes das funções escolhidas,
hashes dos três cabeçalhos gerados, símbolo de entrypoint e layouts de diagnóstico.
A associação do entrypoint e do import de dados é verificada contra o XEX/PE.
Os fontes selecionados e o contexto precisam corresponder aos hashes revisados.
O preâmbulo que o CLI upstream acrescenta ao contexto é conferido byte a byte.

O arquivo local de configuração já preparado nesta sessão é
`private/entry-prefix-reviewed.json`. Ele contém metadados específicos do título
e permanece privado. Work precisa ser novo:

```sh
python3 tools/recompilation/prefix_probe.py \
  --config private/entry-prefix-reviewed.json \
  --reviewed-config-sha256 DIGEST_DA_CONFIG_REVISADA \
  --clang /caminho/clang++ --work private/novo-prefix-probe --execute
```

O comando compila com `-fwrapv -fno-strict-aliasing` e UBSan, executa com timeout,
e grava fonte derivado, binário, logs e relatório **somente em private/**.
`--system-ubsan` é opcional no Linux sem compiler-rt. Um `PREFIX_STOP` esperado
significa que o diagnóstico detectou um bloqueio, nunca que o jogo inicializou.

## Verificação

GCC e Clang 19.1.7 com UBSan passaram nos sete grupos CTest: **98 testes Python,
1038 checks runtime, 33 PCM, 21 dispatch, 2088 memória esparsa, 44 de módulo e
1083 de memória virtual**. A ponte com C++ PPC sintético gerado passou em
102 checks nativos em dois modos de wrapper, incluindo permissões e MMIO.
A suíte cobre rollback, bordas guest32, reserva sem backing, recommit sem perda
de dados, pointers de saída, proteção e reutilização após release.

A CI anterior a estes componentes passou para Linux/macOS e compilou objetos
AOT sintéticos Mach-O ARM64: [run 43212214238](https://github.com/miqfernandes07-cmd/-StormRevolution-iOS/actions/runs/43212214238).
O [run iOS 43212214281](https://github.com/miqfernandes07-cmd/-StormRevolution-iOS/actions/runs/43212214281)
produziu novo IPA de infraestrutura não assinado e passou no smoke runtime/Metal
no simulador, Xcode 16.4/SDK 18.5. Os componentes deste marco precisam de sua
própria execução em CI; não se atribuem a eles os resultados do commit anterior.


## Serviços adicionais de processo — marco posterior

ProcessState mapeia somente PIB+0x2f RW, inicial USER=1. Getter lê o byte real;
setter valida0..2 e grava o mesmo byte. Região0x60 inteira precisa estar livre
na criação; campos desconhecidos ficam sem mapeamento. Não há PIB/KTHREAD/TLS
completo. Chamadas precisam ser serializadas pelo proprietário da AddressSpace.

Inicialização de critical section preserva bytes2..3 e8..15; escreve tipo,
spin, signal, lock_count=-1, recursion/owner=0. Preflight impede escrita parcial.
O wrap uint32 no arredondamento de spin segue a referência Xenia, sem prova em
hardware Xbox. Enter/TryEnter/Leave continuam ausentes, sem sucesso fictício.

Probe passa a exigir process_block na config privada e digest novamente revisado.
Os quatro wrappers foram executados com contexto sintético; não há nova execução
comercial. Consulte RESUME_GAME_BOOT.md para os artefatos privados ausentes.
