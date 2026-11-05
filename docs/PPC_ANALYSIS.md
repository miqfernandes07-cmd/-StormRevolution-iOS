# Inventário estático PPC de uma região explícita

`tools/ppc_analysis/inventory.py` analisa até 1 MiB de palavras big-endian de uma
região de código já extraída. **Não recebe `default.xex` diretamente**, não decifra,
não descompacta e não identifica se bytes arbitrários são código ou dados. O
operador precisa fornecer o endereço guest da região e, opcionalmente, sua entrada.
O CLI exige `--raw-ppc` para deixar esse contrato explícito; cabeçalhos XEX1/XEX2
são recusados. A extração PE/XEX permanece pendente.

```bash
python3 tools/ppc_analysis/inventory.py --raw-ppc private/region.ppc \
  --base 0x82000000 --entry 0x82000000 --output private/reports/ppc.json
python3 -m unittest discover -s tests -p test_ppc_analysis.py -v
```

Os números acima são apenas exemplo de sintaxe, não endereços identificados do
Storm. Mantenha bytes comerciais e relatórios derivados em `private/`. Uma saída
JSON nunca pode substituir a entrada; o CLI recusa o mesmo caminho resolvido ou hardlink para a entrada.

## O que o relatório contém

- SHA-256, intervalo guest, entrada, número de palavras e histograma.
- Formatos reconhecidos: `addi`, `addis`, `ori`, `add` sem OE/Rc, `or` sem Rc,
  desvios diretos `b`/`bc` e encodings exatos de `blr`, `bctr` e `bctrl`.
- Referências diretas calculadas exclusivamente dos operandos de branch. Não
  transforma constantes, loads ou valores que parecem ponteiros em referências.
- Campos AA/LK, deslocamento com sinal, alvo dentro/fora da região e wrap relativo.
- BO/BI de `bc`, sem avaliar CR/CTR, predicado ou legalidade de todas as combinações
  BO. O relatório usa arestas possíveis conservadoras, inclusive fallthrough mesmo
  quando uma combinação BO corresponderia a branch incondicional.
- Arestas de fluxo local, possível continuidade de chamadas e registros de alvos
  indiretos não resolvidos. Não realiza análise de alcançabilidade.
- **Candidatos a funções**, provenientes somente da entrada selecionada e dos alvos
  de branches diretos com LK. Não há tamanho, limite ou função comprovada. Um branch
  com link pode ser usado para obter o PC, e um `blr` pode não retornar de uma função;
  o relatório não presume esses usos. Candidatos externos são marcados fora da região.
- Diagnósticos por PC/palavra para opcode ou variante desconhecida, inclusive dados
  que estiverem misturados ao código. Palavras inacessíveis também são inventariadas.

O cálculo de `b` usa sign extension de 26 bits; `bc`, de 16 bits. AA seleciona
endereço absoluto com sinal, enquanto o caso relativo soma ao PC da instrução.
Os alvos usam módulo 2³², explicitamente como modelo do endereço guest desta
ferramenta; o resultado de wrap relativo é informado. O intervalo de entrada não
pode cruzar o limite de 32 bits. Isso não implementa semântica completa de PPC64.

## Cobertura separada da recompilação

Reconhecer um formato não significa conseguir recompilá-lo. O campo
`synthetic_aot_check` chama diretamente o tradutor sintético existente e registra
se ele aceita a região inteira, ou o primeiro diagnóstico. Por exemplo, `bc`,
chamadas, branches para trás e indiretos podem ser reconhecidos no inventário,
mas são recusados pelo tradutor sintético. Esse check gera texto apenas para
avaliar o contrato; **não compila nem executa** o resultado. Não mede cobertura
do XenonRecomp, nem prova validade de uma função ou compatibilidade do jogo.

Estados explícitos `not_implemented` incluem recuperação de limites de funções,
tabelas de salto, alvos indiretos e decodificação XEX/PE. A separação código/dados
vem do chamador e não foi verificada. Não é um disassembler completo nem um CFG
completo. Novos opcodes só devem receber uma classificação após testes de encoding.

Saídas do CLI: `0` = inventário concluído sem formatos desconhecidos; `2` =
inventário concluído com diagnósticos de palavras desconhecidas; `1` = entrada,
intervalo, container ou I/O inválido. Um retorno 0 não indica que a recompilação é
possível. Em falha de entrada, uma saída anterior permanece; conferir sempre o
código de saída para não confundi-la com resultado novo.

## Evidência desta iteração

16 testes aprovados em Linux x86_64/Python 3.12.14, usando somente palavras criadas
pelos testes. Cobrem sign extension negativa/mínima, AA/LK, wrap de endereço,
candidatos internos/externos, opcodes/variantes desconhecidos, entrada malformada,
limites, determinismo e códigos do CLI. A semântica de endereçamento recebeu revisão
independente. Nenhum código do Storm foi inventariado ou executado.
