# Rotate/record e colisão de decodificação Xenon — 2026-11-12

Os patches 0008 e 0009 ampliam a série experimental do emissor XenonRecomp,
sem dados comerciais. Ambos modificam somente o emissor MIT; a licença upstream
acompanha a série. Nenhum código do disassembler GPL foi copiado ou distribuído.

## RLDICL e CR0

RLDICL, CLRLDI e ROTLDI agora emitem comparação CR0 quando Rc está ativo.
A comparação usa o resultado baixo signed32 e copia XER.SO, coerente com a política
guest32 da série. Foram conferidos `InstrEmit_rldiclx` em `ppc_emit_alu.cc` e
`PPCHIRBuilder::UpdateCR` em `ppc_hir_builder.cc` do Xenia fixado em REFERENCES:
UpdateCR trunca para INT32 antes de comparar com zero. Isso é referência de
implementação; não valida o modo real das threads do título no hardware.

A máscara do alias CLRLDI usa ComputeMask em vez de uma expressão que poderia
solicitar shift por 64 no host. A referência de teste constrói rotate/mask bit a bit,
sem usar o builtin da implementação. São 143 pares de shift/mask: todos os 64
valores de shift e de mask são exercitados, mais combinações de borda. Com Rc,
alias de destino, bordas, pseudoaleatórios e SO, são **82368 casos nativos** em
572 funções sintéticas. CR sem record, XER, origem e outros registradores são
verificados. O binário upstream original falha no gate desse teste.

## As ocorrências MAC eram colisões VMX128

A análise privada dos três registros inicialmente reportados como MAC encontrou
encodings VX128_5 de VSLDOI128, cercados por operações vetoriais. O decoder genérico
pode selecionar antes um mnemonic BookE/PPC405 (MACLHWU/MACCHWU), inadequado à
interpretação Xenon desse encoding. Não se implementaram operações MAC para ocultar
essa falha e não se classificaram essas palavras como dados descartáveis.

O patch 0009 reconhece somente esses dois IDs em encoding VX128_5 compatível,
recupera os campos divididos VD/VA/VB/SH e reentra no emissor VSLDOI128 existente.
A descrição do opcode é obtida pelo decoder usando uma instrução canônica própria
e seu ID é conferido; falha nessa conferência continua retornando diagnóstico.
O primeiro candidato canônico também colidia com BookE; o teste recusou a geração,
e o candidato foi substituído por um encoding que é confirmado como VSLDOI128.
Não há relaxamento do filtro de diagnósticos.

Os campos foram conferidos na estrutura VX128_5 de `ppc_instr.h` e na tabela
`ppc_opcode_table_gen.cc` do Xenia BSD-3-Clause fixado. São fatos de layout; não
foi incorporado HIR/JIT nem código de extração do disassembler GPL.
O teste gera 24 encodings próprios que reproduzem essa classe de colisão, com
registros vetoriais altos, dois deslocamentos e operandos distintos. Compara todos
os bytes contra concatenação/seleção escalar: **26112 vetores nativos aprovados**.
Não é uma substituição geral do decoder, nem qualificação de todos os encodings
VMX128 ou de outras instruções BookE. O baseline original falha nesse gate.

## Reprodução e evidência

```sh
python3 tests/integration/xenon_rotate_record.py \
  --upstream private/toolchain/XenonRecomp \
  --recompiler private/toolchain/experimental-vsldoi/XenonRecomp \
  --clang /caminho/clang++ --work build/rotate-test
python3 tests/integration/xenon_vsldoi_decode.py \
  --upstream private/toolchain/XenonRecomp \
  --recompiler private/toolchain/experimental-vsldoi/XenonRecomp \
  --clang /caminho/clang++ --work build/vsldoi-test
```

Requer checkout experimental compilado com os nove patches em ordem. Work deve
ser novo e ficar em build/. `--system-ubsan` é opcional no Linux sem compiler-rt.
Todas as nove integrações foram repetidas sobre o mesmo binário Clang 19.1.7,
Linux x86_64 com UBSan: **225678 casos/vetores aprovados**.
[Relatório conjunto com hashes](validation/series-nine-native-2026-11-12.json).
A suíte padrão também passou em 3/3 CTest, com 71 testes Python. Nenhum desses
resultados foi executado em ARM64, no iPhone ou usando funções comerciais.

A série revisada `storm-guest32-experimental-2026-11-12-r2` registra os hashes dos
nove patches e do fonte final. O adaptador aceitou essa proveniência e executou a
geração do título, mas recusou o resultado por **42 VPKSWSS128** ainda sem suporte.
O log novo tem zero avisos de CR ausente e zero mensagens de decode impossível.
Código/configurações/relatórios detalhados do jogo continuam privados.

O contexto ainda não modela VSCR/SAT, necessário à saturação. Há outras operações
já emitidas pelo upstream que também precisam preservar SAT, incluindo conversão
vetorial float→int usada no título. Acrescentar somente um pack sem esse estado
não tornaria o CPU correto. A próxima integração precisa abordar o contexto e a
série de operações saturadas, além da validação do modo guest.

Não houve build nativo de função comercial, boot ou gameplay. Serviços Xbox,
Xenos/Metal, áudio e recursos completos permanecem pendentes; o IPA existente
continua sendo somente infraestrutura.
