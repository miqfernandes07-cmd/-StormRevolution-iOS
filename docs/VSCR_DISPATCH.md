# VSCR, formatos D3D e ligação AOT — 2026-11-12

A série experimental possui 13 patches sobre XenonRecomp
`ddd128bcca99fe8bfbb99bea583c972351fa6ace`. Os hashes estão em
`config/xenon_experimental_series.json`; a aplicação sequencial em checkout
limpo reproduziu os hashes finais. Emissor e contexto MIT; licença upstream
acompanha os patches. Nada nesta entrega contém código gerado do título.

## Semântica implementada e testada

O patch 0010 acrescenta VSCR ao contexto: SAT sticky e NJ, MFVSCR/MTVSCR,
VPKSWSS128 e atualização de SAT nas operações saturadas já emitidas que foram
identificadas nesta revisão. VCTSXS/VCFPSXWS128 convertem bits IEEE binary32 para
inteiro signed32 com escala 0..31, truncamento e saturação independentes do modo
FP do host. NaN resulta em zero sem acrescentar SAT. Overflow e infinidade
saturam; INT32_MIN exato não acrescenta SAT. NJ controla denormais VMX; isso não
qualifica todas as instruções nem demonstra o modo CPU real do jogo.

O layout PPCContext mudou: todos os consumidores precisam ser recompilados com
o mesmo cabeçalho. Não misturar contextos de séries diferentes.

O patch 0011 decide entre alias ELF e wrapper fraco no momento da compilação do
código gerado, permitindo preparar no Linux e depois compilar para Mach-O.
Ambos os caminhos foram executados no host; a CI Apple é uma verificação separada.

O patch 0012 implementa VPKD3D128/VUPKD3D128 float16_2 e float16_4 com IEEE
binary16 e arredondamento de pack em direção a zero. Cobre subnormais, zeros com
sinal, infinitos, NaNs quiet, registros altos, alias de origem/destino e
máscaras/deslocamentos de inserção. Preserva palavras não escritas. Não implementa
renderização Metal nem todo o conjunto de formatos D3D.

O patch 0013 implementa BLRL: lê o LR antigo, mascara os dois bits inferiores,
grava o endereço de retorno e chama a função compilada por dispatch verificado.
O modo skip_lr é recusado para essa instrução. O teste observa o link PC durante
a chamada e a restauração posterior. BCTRL também foi exercitada com essa ponte.

## Runtime de chamadas nativas

`runtime/cpu/aot_dispatch.*` registra ponteiros de funções C++ realmente compiladas
por endereço guest e sela a tabela antes de usar. `AotBinding` vincula tabela,
contexto e memória a cada thread, com escopos aninhados. Erros de registro,
contexto, memória, thread não vinculada e destino ausente têm código e endereço.
A tabela/contexto/memória devem permanecer vivos durante as chamadas; a tabela
selada não pode ser modificada nem copiada. Não existe decoder ou JIT nesse caminho.

`xenon_bridge.h` deve ser incluído antes do contexto no alvo AOT privado. A
aritmética guest do alvo usa `-fwrapv -fno-strict-aliasing`; o runtime genérico
continua com seus checks e UBSan. Isso não torna seguros todos os acessos de
memória emitidos: o mapa virtual real e MMIO continuam pendentes.

## Evidências reproduzíveis

As 12 integrações `tests/integration/xenon_*.py` foram executadas no mesmo
binário da série 13, com Clang 19.1.7, Linux x86_64 e UBSan:
**780443 verificações/casos/vetores sintéticos aprovados**. Incluem 167951 VSCR,
386748 half e 66 de dispatch em dois modos de wrapper. Os testes half percorrem
todos os 65536 encodings binary16, bordas e dados pseudoaleatórios. São fixtures
próprias; nenhum jogo foi executado por eles.
[Relatório com hashes](validation/series-thirteen-native-2026-11-12.json).

Exemplo, após compilar a ferramenta com os 13 patches:

```sh
python3 tests/integration/xenon_half_formats.py \
  --upstream private/toolchain/XenonRecomp \
  --recompiler private/toolchain/experimental-thirteen/XenonRecomp \
  --clang /caminho/clang++ --work build/half-check
python3 tests/integration/xenon_dispatch_bridge.py \
  --upstream private/toolchain/XenonRecomp \
  --recompiler private/toolchain/experimental-thirteen/XenonRecomp \
  --clang /caminho/clang++ --work build/bridge-check
```

`--system-ubsan` é opcional para Linux sem compiler-rt instalado. Work precisa
ser novo e ficar em build/. A workflow `aot-tests.yml` usa apenas estas fixtures,
compila a ferramenta pública fixada e publica relatórios próprios, sem ferramenta,
executável comercial, dados do jogo ou código derivado. O job Apple também tenta
compilar objetos sintéticos ARM64 para iOS; um objeto não prova execução no aparelho.

## Geração privada e bloqueios

Os 42 VPKSWSS128 antes rejeitados foram tratados, e os oito traps encontrados
posteriormente (sete caminhos D3D half e um BLRL) desapareceram da geração.
Não houve liberação de boot. O gate de fonte revelou também chamadas omitidas
que o log upstream não reportava. A recuperação conservadora de 49 entradas
alternativas reduziu esses pontos de 321 para **79**, com todos os callsites
verificados contra as palavras de branch da imagem original. As entradas são
candidatas; convenção de chamada e fluxo indireto ainda exigem qualificação.

Há ainda **19909 palavras zero emitidas como `.long`**, incluindo funções de
padding inferidas pelo analisador. O gate as rejeita: zero não é NOP PowerPC.
É necessário restringir os intervalos àqueles realmente executáveis e investigar
se algum caminho alcança essas regiões. Não se apagam esses diagnósticos para
obter build aprovado. A auditoria lexical não prova semântica ou alcançabilidade.

A geração mais recente tem 14625 locais de chamada indireta. Não são 14625
funções resolvidas. Tabelas de salto, imports xboxkrnl/XAM, memória/MMIO, shaders
Xenos/EDRAM, recursos e áudio ainda impedem um port viável. O botão iOS continua
retornando `RUNTIME_AOT_IMAGE_MISSING`; não foi ligado a uma imagem incompleta.

As **242 unidades C++ comerciais privadas passaram em `clang++ -fsyntax-only`**
no Linux x86_64. Isso verifica sintaxe/tipos, sem produzir objetos, fazer link ou
executar funções. O gate de qualificação continua reprovado pelos pontos acima.
[Relatório agregado, sem código comercial](validation/title-syntax-2026-11-12.json).
