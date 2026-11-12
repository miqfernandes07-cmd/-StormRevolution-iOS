# LFSU/STFSU: segundo patch experimental do XenonRecomp

`tools/recompilation/patches/0002-single-update.patch` implementa `lfsu` e `stfsu`
no emissor C++ MIT do XenonRecomp fixado em REFERENCES. Licença upstream em
`patches/LICENSE.XenonRecomp`; não foram copiados disassembler ou bytes comerciais.
O binário experimental deste marco contém os patches 0001 (EQV) e 0002.

## Semântica implementada e limites

O escopo é endereçamento guest de 32 bits, como a representação inicial do
upstream: EA = GPR[RA].u32 + deslocamento de 16 bits estendido, módulo 2^32.
A emissão usa uma constante unsigned para evitar overflow assinado no C++.
A atualização de RA escreve o EA zero-estendido nos 64 bits, após o acesso.
RA=0 é recusado explicitamente. GPR e FPR são bancos distintos.

LFSU lê os 32 bits big-endian, converte binary32 em double no FPR e depois
atualiza RA. STFSU converte o FPR double em binary32, armazena big-endian e
só então atualiza RA. O patch segue a política FPU/flush já usada em LFS/STFS
pelo upstream. Não implementa semântica completa FPSCR/exceções, modos de
arredondamento do Xbox, MMU, callbacks de hardware ou MMIO. A forma STFSU
seguida de EIEIO (sinalizador MMIO do upstream) é rejeitada, não tratada como RAM.
O comportamento de endereço em modo guest de 64 bits permanece sem validação.

## Testes reais do host

`tests/integration/xenon_single_update.py` cria ELF32 BE sintéticos e invoca o
recompilador experimental. O C++ gerado é compilado e executado com Clang 19.1.7,
UBSan e libubsan do host Linux x86_64. Os resultados são:

- 405 casos usando as macros de memória originais do contexto upstream.
- 495 casos com callbacks de memória verificados escritos para o teste; incluem
  90 acessos recusados por falha injetada, limites ou alinhamento. Confirmam que
  RA/FPR e memória ficam intactos quando o callback lança antes do acesso.
- Três formas inválidas rejeitadas durante geração: RA=0 nos dois opcodes e
  sequência MMIO. O baseline original falha no gate de geração das formas válidas.
- Offsets 0, +4, -4, +32764 e -32768; wrap de endereço, bits altos iniciais em RA,
  zeros com sinal, normais, subnormais, extremos, infinitos, NaN e ties-to-even.
  NaNs são comparados por classe; seus payloads e sNaNs não estão validados.
- 3264 vetores EQV novamente aprovados no mesmo binário, sem regressão observada.
- Suíte pública padrão: 3/3 grupos CTest, 62 testes Python, 1038 verificações runtime,
  33 PCM. A integração upstream é explícita e não faz parte da descoberta padrão.

Os callbacks de falha são instrumentação de teste, não implementação de exceções
Xbox. Os acessos normais usam endereços alinhados; os testes não qualificam acessos
reais desalinhados, iOS/ARM64 ou funções comerciais. Arredondamento foi testado
somente com FE_TONEAREST. [Relatório real](validation/single-update-native-2026-11-12.json).

```sh
python3 tests/integration/xenon_single_update.py \
  --upstream private/toolchain/XenonRecomp \
  --recompiler private/toolchain/experimental-single-update/XenonRecomp \
  --clang /caminho/clang++ --work build/single-update-test
```

Aplicar os patches em um checkout experimental separado e compilar conforme
upstream antes do teste. `--work` precisa ser novo e estar em build/. O argumento
opcional `--system-ubsan` serve para o Clang Linux isolado sem compiler-rt.
O primeiro link falhou porque resolver o symlink clang++ transformava o comando
em clang e omitia a biblioteca C++ necessária às exceções. Os scripts agora usam
caminho absoluto sem resolver esse symlink, preservando o modo do driver C++.

## Nova geração privada do título

O log passou de 1603 ocorrências/27 variantes, com EQV, para **973/25**:
250 LFSU e 380 STFSU deixaram de gerar diagnóstico. Permanecem 242 arquivos C++
comerciais privados, sem aprovação para build nativo do jogo. As contagens não
comprovam alcançabilidade de todas as palavras ou recuperação correta de funções.
Não foram alteradas tabelas de salto para ocultar falhas.

Configuração, fontes geradas, logs e proveniência do binário/patches ficam em
private/. A tentativa usou diretamente o binário experimental, não o manifesto
fixado do adaptador. Fonte e binário originais foram restaurados e seus hashes
conferidos. A promoção de uma série de patches ao adaptador requer proveniência
explícita, sem reduzir as verificações existentes.
