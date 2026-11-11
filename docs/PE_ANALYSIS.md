# Análise de uma imagem PE32 reconstruída

`tools/xex_analysis/pe.py` lê cabeçalhos DOS/NT/COFF/PE32, tamanho/base da imagem,
entry point, diretórios de dados e seções executáveis. O formato dos cabeçalhos é
little-endian; código PPC e descritores de imports XEX continuam big-endian.
A implementação é independente e usa apenas a biblioteca padrão Python.

O chamador precisa declarar o layout:

- `--layout file`: RVA é convertido para `PointerToRawData` da seção. A parte BSS
  sem bytes armazenados é recusada; não se inventa conteúdo ao resolver imports.
- `--layout mapped`: o offset no buffer é o RVA e exige bytes para os headers e todas
  as seções declaradas. Se o buffer termina antes de `SizeOfImage`, mas após todas
  as seções, o relatório informa `PE_IMAGE_TAIL_UNAVAILABLE`. Leituras nessa cauda
  continuam recusadas; nenhum zero é fabricado. O buffer de imports deve ser
  capturado antes de qualquer patch dos descritores.

No caminho consultado de Xenia, `ReadImageBasicCompressed` escreve os blocos e
intervalos de zeros diretamente na memória a partir do load address, e o leitor
PE usa base + VirtualAddress para as seções. Por isso uma imagem reconstruída por
esse caminho tem layout mapped. Não concluir que todo arquivo chamado `.exe` tem
esse layout: registrar a proveniência da ferramenta que produziu cada arquivo.

```bash
python3 tools/xex_analysis/pe.py private/image.bin --layout mapped \
  --xex-report private/reports/xex.json --output private/reports/pe.json
python3 -m unittest discover -s tests -p test_pe.py -v
```

O parser valida assinaturas, limites de leitura, PE32, contagens, headers,
intervalos virtuais e físicos das seções, sobreposições e overflow do endereço
guest de 32 bits. O orçamento é 512 MiB de imagem, até 96 seções e até 32
entradas de diretório. Os diretórios são somente enumerados, sem resolução de
exports, relocations, TLS ou exceções. Não valida assinatura nem executa código.
PE32+ é recusado. Zero ou formatos não reconhecidos não são tratados como sucesso.

Quando recebe o relatório XEX, confere o load address e lê os endereços de registros
de imports na imagem. Conforme `SetupLibraryImports` do Xenia, cada slot BE32 tem
tipo no byte superior e ordinal nos 16 bits inferiores. Tipo 0 corresponde a slot
de valor; tipo 1 a thunk que pode ser associado ao slot anterior de mesmo ordinal.
Tipos desconhecidos e thunks não pareados geram diagnósticos. A contagem de slots
não é igual à contagem de serviços: um serviço pode usar slot e thunk. Os símbolos
e os serviços nativos permanecem sem resolução por este módulo.

Fonte de semântica consultada: [Xenia xex_module.cc, commit fixado](https://github.com/xenia-project/xenia/blob/95a5c3ee250f80c3b9d139658649d9ffb6db3eec/src/xenia/cpu/xex_module.cc),
licença BSD-3-Clause registrada em [REFERENCES.md](REFERENCES.md). Nenhum código
upstream, constante de chave ou byte comercial foi incorporado a este parser.

Os testes geram seus próprios arquivos PE e buffers mapeados, verificando os dois
layouts, seções executáveis, limites e todas as posições de truncamento da fixture,
registros de importação, endian, erros de esquema e proteção contra sobrescrita por
hardlinks. São 13 testes aprovados no Linux/Python 3.12 nesta implementação inicial.
O uso com a imagem do jogo deve ter seu resultado registrado separadamente pelo
pipeline privado; testes sintéticos não comprovam boot ou completude da análise.


A implementação de `XenonUtils/xex.cpp` do XenonRecomp fixado em REFERENCES faz
byteswap nos slots e substitui thunks de importação por NOP/retorno durante a carga.
Uma saída desse loader já transformada permite analisar cabeçalhos/seções, mas não
serve como imagem original dos descritores. Capturar antes dessa etapa ou registrar
os imports antes da mutação. Tipos desconhecidos no relatório não devem ser
convertidos em ordinais inventados: o estado fica `descriptor_analysis_incomplete`.
