# Recompilação AOT: bring-up sintético

`tools/recompilation/ppc_aot.py` é um tradutor estático pequeno, escrito para testar
o caminho bytes PowerPC big-endian → C++ → código nativo do host. Não substitui o
XenonRecomp, não recompila o jogo e não executa instruções por interpretação/JIT.
O XenonRecomp continua sendo o candidato principal para o executável real.

Subconjunto aceito: `addi`, `addis`, `ori`, `add` sem OE/Rc, `or` sem Rc,
`b` relativo sem link apenas para alvos adiante dentro da função, e `blr` exato
como retorno ao chamador nativo. Os GPR são de 64 bits, a soma é módulo 2^64 e
imediatos negativos são estendidos antes da operação. RA=0 tem a semântica especial
somente nos opcodes que a definem. Flags CR/XER não são modificadas por esse
subconjunto. `blr` não simula a leitura do LR: o contrato desta prova é uma função
isolada com retorno ao host.

Cada palavra é validada, mesmo quando inacessível por um salto. Instruções ou
variantes desconhecidas geram diagnóstico JSON identificável com endereço e palavra.
Laços, chamadas, branches condicionais, memória, ponto flutuante, atomics, VMX/VMX128,
exceções e ABI completa não são suportados pelo tradutor. A função deve terminar
em `blr`; destinos externos e overflow de endereços são recusados.

```bash
python3 tools/recompilation/ppc_aot.py private/function.ppc private/function.cpp \
  --base 0x82000000 --report private/function.json
python3 -m unittest discover -s tests -p 'test_aot.py' -v
```

O teste cria palavras sintéticas, gera C++, compila com o compilador `CXX` (padrão
`c++`) e executa o binário nativo com UBSan. Compara resultados conhecidos de soma,
extensão de sinal, OR e branch. Não há decodificação de instruções no binário gerado.
Este teste executado em Linux x86_64 não comprova geração ARM64, comportamento do
executável comercial ou execução no iOS. Saídas derivadas de executáveis comerciais
devem permanecer em `private/` e jamais ser publicadas por CI.

O CLI limita a leitura a 1 MiB + 1 byte. Em caso de falha, uma saída anterior não
é removida: o código de saída precisa ser verificado e um arquivo antigo jamais
deve ser apresentado como resultado da tentativa atual.

## Adaptador XenonRecomp real

`xenon_pipeline.py` usa o CLI documentado no commit
`ddd128bcca99fe8bfbb99bea583c972351fa6ace`, sem shell nem downloads automáticos.
Requer Python 3.11+ (`tomllib` da biblioteca padrão). Por padrão somente valida e
imprime um plano; `--execute` invoca os binários locais. Os testes do adaptador
verificam montagem de argumentos, hashes e limites de caminhos; não executam
XenonRecomp na suíte pública. Separadamente, os binários upstream foram compilados
com Clang 19.1.7 e executados privadamente sobre o XEX validado: XenonAnalyse não
recuperou tabelas; XenonRecomp produziu 242 C++ e 1643 diagnósticos em 28 variantes.
A geração foi rejeitada e não houve compilação nativa desse código.

Depois de obter e compilar o checkout fixado e auditar as dependências, criar
localmente `private/toolchain.json`, com caminhos absolutos e SHA-256 dos artefatos:

```json
{
  "source_commit": "ddd128bcca99fe8bfbb99bea583c972351fa6ace",
  "source_checkout": "/caminho/XenonRecomp",
  "analyse": {"path": "/caminho/XenonAnalyse", "sha256": "SHA256_REAL_64_HEX"},
  "recomp": {"path": "/caminho/XenonRecomp", "sha256": "SHA256_REAL_64_HEX"},
  "context": {"path": "/caminho/XenonRecomp/XenonUtils/ppc_context.h", "sha256": "SHA256_REAL_64_HEX"}
}
```

O adaptador verifica HEAD, alterações em arquivos rastreados e os hashes dos três
arquivos. Isso detecta substituições em relação ao manifesto local, mas não atesta
que um binário foi construído daquele fonte nem audita os submódulos. Registrar a
proveniência e licenças da compilação continua necessário.

Antes de invocar upstream, a execução passa o XEX pelo analisador local e exige
correspondência de Title ID, Media ID, versão, elegibilidade NTSC-U, tamanho e SHA-1
com `config/game_reference.json`; também compara o SHA-256 com o plano. O plano
sozinho pode ser inspecionado com entradas sintéticas, mas elas não passam esse
controle de execução. Dados em uso devem permanecer estáveis durante a execução;
o diretório privado não é uma sandbox contra alterações concorrentes hostis.

```bash
# Plano de análise (acrescentar --execute --log private/analyse.log antes de analyse
# para executar; a saída e o log devem ser novos):
python3 tools/recompilation/xenon_pipeline.py --manifest private/toolchain.json \
  analyse private/default.xex private/switches.toml
```

Revisar as tabelas de salto, funções, imports e endereços no executável real.
Criar `private/storm.toml` com `[main] file_path`, `out_directory_path` e
`switch_table_file_path`, relativos ao diretório do TOML, e demais campos específicos
do título conforme upstream. Nenhum endereço de Sonic foi reutilizado. Todos os
caminhos de dados e saídas precisam resolver dentro de `private/`. Atualizações XEXP
são recusadas até existir validação da identidade do executável resultante.

```bash
# Substituir HASH_REVISADO pelo SHA-256 da configuração já revisada:
python3 tools/recompilation/xenon_pipeline.py --manifest private/toolchain.json \
  recompile private/storm.toml --reviewed-config-sha256 HASH_REVISADO
```

A mudança de um byte da configuração invalida o hash revisado. Na execução, o
adaptador grava stdout/stderr somente no log privado e recusa retorno não zero,
saída ausente ou mensagens de error/fatal/warning/unsupported/unimplemented,
not implemented ou unrecognized instruction. Esse filtro é
conservador e não prova cobertura: revisar também o C++ gerado por traps, instruções
omitidas e chamadas sem implementação antes de compilar. Saída sem avisos não é
prova de correção nem de boot. Nada desse fluxo invoca JIT no aplicativo.
