# Série experimental de sete patches — 2026-11-12

Esta série amplia o emissor XenonRecomp fixado em REFERENCES. Não é código do
jogo e não inclui bytes, endereços ou C++ comerciais. Todos os patches do emissor
seguem MIT, com a licença upstream junto deles. Os binários completos das ferramentas
host têm dependências GPL/LGPL; não foram redistribuídos nem ligados ao aplicativo.

## Código implementado

| Patch | Comportamento |
| --- | --- |
| 0001 | EQV sem record, já documentada em EQV_PATCH |
| 0002 | LFSU/STFSU, já documentadas em SINGLE_UPDATE_PATCH |
| 0003 | LHZU, LHAU, STHU, LWZUX, LBZUX, STHUX, LHZUX, LDUX, STDUX, LFDU, STFDU, LFSUX, STFSUX e LHBRX |
| 0004 | BDZF/BDNZT e correção de BDNZF: seleção real de BI nos oito campos CR, em vez da suposição eq |
| 0005 | ADDC, SUBFZE, ADDME e variantes record, sem OE, segundo política guest32 CA/CR0 |
| 0006 | VANDC padrão usando o caminho SIMDe já existente para VANDC128 |
| 0007 | LVEHX no caminho Xenon de leitura vetorial completa, como a referência Xenia |

O patch 0003 calcula EA antes de alterar operandos, escreve RA somente após o
acesso e recusa RA=0 ou RA=destino nos loads GPR com update. Stores permitem
RA=origem e usam o valor antigo. RB=destino ou RB=RA são testados. São testadas
extensão de sinal de halfword, truncamento de stores e byte-reverse. MMIO continua
rejeitado nas novas formas. Endereços e atualização de RA seguem a política guest32,
com EA zero-estendido, não um modelo completo de MMU/exceções do Xbox.

O patch 0004 cobre saltos relativos dentro da função, fallthrough e laços. Destinos
externos, AA e LK são recusados pelo novo caminho. O contador decrementa em 64 bits
e é testado pelos 32 inferiores, política explícita compatível com o modelo upstream.
Não há afirmação de validação do modo efetivo de todas as threads do título.

O patch 0005 calcula carry de 32 bits e atualiza CR0 pelo resultado baixo assinado,
como os emissores ADDE/ADDIC do upstream. Resultados GPR usam aritmética unsigned
modular de 64 bits para evitar UB C++. SO/OV são preservados; variantes OE continuam
rejeitadas. Essa política é experimental, não validação completa de MSR/XER.

A referência nova consultada foi
[Xenia ppc_emit_altivec.cc](https://github.com/xenia-project/xenia/blob/95a5c3ee250f80c3b9d139658649d9ffb6db3eec/src/xenia/cpu/ppc/ppc_emit_altivec.cc),
BSD-3-Clause: LVEHX é tratado como LVX, carregando o bloco de 16 bytes alinhado e
invertendo a representação vetorial. A implementação reutiliza o caminho LVX do
emissor MIT, sem copiar HIR ou código do emulador. O teste confere cada byte.

## Provas executadas

Todas as integrações foram repetidas no **mesmo binário experimental**, identificado
pelo SHA-256 dos relatórios. Clang 19.1.7 + UBSan/libubsan, Linux x86_64; ELF/PPC,
memória, valores e referências de teste são próprios.

| Integração | Casos/vetores aprovados |
| --- | ---: |
| EQV | 3264 |
| LFSU/STFSU | 900 |
| 14 formas adicionais de memória | 3402 |
| Branches CTR/CR | 3456 |
| Carry/record | 78336 |
| VANDC | 3264 |
| Xenon LVEHX | 24576 |
| Total | 117198 |

Os relatórios `docs/validation/series-seven-*-2026-11-12.json` contêm os hashes e
escopos individuais. Testes cobrem aliases, bordas, referências bit a bit, offsets,
wrap, diferentes CR/CA/SO e falhas de callbacks. Callbacks verificados são
instrumentação, não exceções Xbox. Arredondamento FPU é somente nearest; NaNs
são comparados por classe nos caminhos com conversão, sem qualificar payloads/sNaNs.
O teste de carry usa soma serial por bits como referência independente.

Suíte pública padrão: **71 testes Python**, 1038 verificações runtime e 33 PCM,
em **3/3 CTest**. [Log](validation/host-series-seven-2026-11-12.log).
Nenhuma integração experimental ocorreu em ARM64, simulador ou iPhone.

Reprodução, após compilar um checkout experimental com a série em ordem:

```sh
python3 tests/integration/xenon_memory_forms.py \
  --upstream private/toolchain/XenonRecomp \
  --recompiler private/toolchain/experimental-lvehx/XenonRecomp \
  --clang /caminho/clang++ --work build/memory-forms-test
```

Os outros scripts `xenon_ctr_branch.py`, `xenon_carry.py`, `xenon_vandc.py` e
`xenon_lvehx.py` recebem os mesmos argumentos; usar diretório novo em build/ para
cada teste. `--system-ubsan` é opcional para Clang Linux sem compiler-rt.
A fixture ELF compartilhada foi corrigida para não sobrepor a tabela de strings
a .text quando os testes de branches cresceram além de 4 KiB. Inicialmente, essa
sobreposição provocou erros de decodificação; a correção preservou os testes pequenos.

## Integração com o adaptador

`config/xenon_experimental_series.json` registra ID, hashes dos sete patches,
hash do fonte final e do contexto esperado, com `game_execution_approved=false`.
O manifesto privado pode selecionar explicitamente `source_patch_series` e
`source_patch_series_sha256`. Sem esses campos, o adaptador continua exigindo
checkout limpo no commit fixado. Não aceita nomes extras de arquivos modificados,
fonte/contexto/patches alterados ou symlinks que escapem dos diretórios esperados.
Os hashes do manifesto local não atestam por si só que um binário foi construído
confiavelmente: os logs de build/proveniência continuam necessários.

A série foi aceita pelo adaptador sobre o checkout exato e a execução do título foi
**corretamente rejeitada** após a geração por diagnósticos. O plano registra a série
e mantém game_execution_approved=false. Fonte e binário originais foram restaurados;
o manifesto experimental então recusou o fonte não modificado. Nada reduz o gate
de identidade XEX ou o hash de configuração revisada.

O filtro de logs também passou a rejeitar `Unable to decode instruction` e o aviso
de RC sem comparação, mesmo com exit code zero. Testes públicos verificam esses
casos e a rejeição de adulterações na série experimental.

## Estado real e bloqueios

A geração privada mantém 242 C++ e agora registra **45 ocorrências em três variantes**:
42 VPKSWSS128, uma MACLHWU e duas MACCHWU. Há ainda **um aviso separado de RLDICL.
sem comparação CR**. A nova verificação impede aceitar esse aviso como sucesso.
Não houve build ou execução nativa de funções comerciais.

VPKSWSS128 precisa de saturação signed32→signed16, ordem de lanes e estado
sticky VSCR/SAT. Xenia emite explicitamente StoreSAT; o contexto upstream fixado
não modela VSCR/SAT, e outras operações saturadas também precisam de auditoria.
Não foi adicionado um pack que ignorasse esse estado. As ocorrências MAC precisam
ser cruzadas com limites e alcançabilidade: a existência de um mnemonic no
biblioteca de disassembly não prova que seja código Xenon executável.
RLDICL. exige teste de rotate/mask e record no modo correto antes de corrigir.

Continuam pendentes funções/indirect calls/tabelas de salto completas, contratos
XAM/xboxkrnl, renderer Xenos/Metal, shaders/EDRAM, áudio XMA e recursos extraídos.
O ZIP requer 9,43 GB extraídos, além da capacidade atual; ver ASSETS. O IPA
anterior é só infraestrutura. Não há jogo inicializado, gameplay ou FPS medido.
