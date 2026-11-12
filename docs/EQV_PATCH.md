# Primeira correção experimental do emissor XenonRecomp

`tools/recompilation/patches/0001-eqv-nonrecord.patch` adiciona a instrução lógica
PowerPC `eqv` ao emissor C++ do commit upstream
`ddd128bcca99fe8bfbb99bea583c972351fa6ace`. Calcula XNOR dos 64 bits dos GPR,
respeitando o destino RA e os operandos RS/RB. O C++ avalia o lado direito antes
da atribuição, inclusive quando o destino reutiliza um dos operandos.
A variante record `eqv.` é recusada explicitamente; sua política CR0 ainda precisa
de auditoria. Não houve mudança no tradutor sintético `ppc_aot.py`.

O patch é destinado ao emissor MIT; a licença upstream acompanha o patch em
`patches/LICENSE.XenonRecomp`. Nenhum código do disassembler GPL foi copiado.
Os binários host completos ainda têm dependências GPL/LGPL próprias, conforme
REFERENCES. Nenhuma ferramenta ou código comercial gerado é distribuído aqui.

## Evidência executada no host

O teste `tests/integration/xenon_eqv.py` cria ELF32 big-endian próprios com palavras
PPC codificadas independentemente. O XenonRecomp experimental gera C++ dessas
funções; Clang compila e o binário nativo é executado com UBSan. São 3264 vetores:
combinações de valores de borda e pseudoaleatórios determinísticos, três formas
de destino/aliasing, referência independente por comparação bit a bit e verificação
de que CR0, carry e SO não mudam. Também se exige rejeição das três funções `eqv.`.
O upstream original diagnosticou as três funções EQV antes da correção.

Resultado: Linux x86_64, Clang 19.1.7, 3264 vetores aprovados, sem diagnóstico UBSan.
[Relatório com hashes](validation/eqv-native-2026-11-12.json).
Nenhum teste ARM64 ou execução de função comercial ocorreu nesse experimento.

O script é uma integração explícita e não faz parte da suíte pública padrão:
requer checkout auditado com SIMDe, ferramenta recompilada e Clang >=18. Não
instala dependências nem baixa qualquer arquivo. Aplicar o patch em checkout
experimental separado, compilar conforme upstream e executar:

```sh
python3 tests/integration/xenon_eqv.py \
  --upstream private/toolchain/XenonRecomp \
  --recompiler private/toolchain/experimental-eqv/XenonRecomp \
  --clang /caminho/clang++ --work build/eqv-test
```

O diretório de trabalho deve ser novo e ficar em build/. No ambiente desta sessão,
o Clang isolado não tinha compiler-rt UBSan: foi usado `--system-ubsan`, que liga
libubsan do sistema Linux. Isso não é necessário em toolchains com runtime completo.

## Geração do título e limites

Uma nova tentativa privada com o binário experimental removeu os 40 diagnósticos
EQV: **1603 ocorrências em 27 variantes**, contra 1643/28. Continuam 242 arquivos
C++ comerciais privados, sem aprovação para compilação nativa do jogo. Não se
conclui que cada ocorrência do log seja alcançável; dados embutidos e limites de
funções ainda exigem análise. Nenhum branch, import ou serviço foi ignorado.

A tentativa inicial direta falhou por não criar o diretório de saída, e o host
upstream terminou com SIGSEGV sem log. Após conferir os caminhos e criar a pasta,
a geração terminou e os diagnósticos foram contados. O adaptador público já cria
a pasta; não foi alterado para contornar validações.

A execução experimental foi direta e registrada separadamente. O manifesto do
adaptador continua exigindo o commit original: ele **não aceita silenciosamente**
um checkout com patch. Fonte e binário originais foram restaurados e o SHA-256
conferido contra o manifesto. O binário experimental, patch/config hashes e logs
ficam privados. Antes de promover patches ao pipeline normal, implementar uma
proveniência explícita para a série de patches e seus builds.
