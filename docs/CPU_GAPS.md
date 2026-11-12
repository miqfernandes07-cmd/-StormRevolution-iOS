# Diagnósticos da geração exploratória

O XenonRecomp fixado em REFERENCES foi executado privadamente sobre o XEX
validado, com otimizações de registradores desativadas. O log contém 1643
ocorrências de `Unrecognized instruction`, agrupadas em 28 variantes. A saída
C++ foi rejeitada pelo adaptador, mesmo com retorno zero da ferramenta.

| Grupo | Variantes e ocorrências | Total |
| --- | --- | ---: |
| Memória com atualização, D-form | lfsu 250; stfsu 380; lhau 9; sthu 277; lhzu 64; stfdu 8; lfdu 4 | 992 |
| Memória com atualização, indexada | lwzux 2; lbzux 4; lfsux 47; sthux 1; lhzux 41; stfsux 4; ldux 28; stdux 28 | 155 |
| Branch condicional/CTR | bdzf 323; bdnzt 2 | 325 |
| Inteiro/CR/XER | addc 24; subfze 27; subfze. 2; addme 26; eqv 40 | 119 |
| Vetor | lvehx 4; vpkswss128 42; vandc 1 | 47 |
| Memória byte-reversed | lhbrx 2 | 2 |
| Mnemonics MAC reportados | maclhwu 1; macchwu 2 | 3 |

Esses números descrevem o log de uma tentativa. Não comprovam que cada palavra
seja uma instrução alcançável: dados embutidos, limites de funções incorretos ou
configuração incompleta podem causar falsos candidatos. Em particular, investigar
os mnemonics MAC e o grande grupo de branches antes de adicionar emissores.
XenonAnalyse não recuperou tabelas de salto; nenhuma foi inventada para avançar.

Prioridade de implementação:

1. Cruzar cada ocorrência com seção executável, limites de função, chamadas e
   fluxo alcançável. Os endereços, palavras e C++ derivados permanecem privados.
2. Para loads/stores com atualização, conferir cálculo do endereço, sinal,
   endianness, restrições de RA e ordem de atualização do registrador. FPU exige
   ainda preservação de bits, arredondamento e conversões float/double.
3. Validar CTR, BO/BI, condição CR, fallthrough e destino dos branches; não
   substituir desvios desconhecidos por no-op ou sucesso.
4. Cobrir carry/XER e variante record, saturação/ordem de lanes VMX128 e loads
   byte-reversed com vetores independentes de borda e testes diferenciais.
5. Regerar com a configuração revisada, exigir ausência de diagnósticos e revisar
   traps/defaults, chamadas indiretas e semântica ARM64 antes do build nativo.

No baseline deste relatório, nenhuma dessas 28 variantes tinha correção local. Os testes AOT
sintéticos públicos atuais cobrem um subconjunto separado; não provam correção
das funções comerciais nem execução ARM64 do jogo.

## Atualização: primeiro patch experimental

EQV sem record foi implementada no emissor e validada em 3264 vetores nativos
sintéticos. A nova tentativa privada eliminou as 40 ocorrências EQV: restam
1603 diagnósticos em 27 variantes. A tabela acima preserva o baseline original.
EQV. e as demais variantes permanecem pendentes. Ver [EQV_PATCH.md](EQV_PATCH.md).
