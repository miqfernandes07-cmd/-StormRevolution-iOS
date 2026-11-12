# Auditoria das referências públicas

Consulta: 2026-11-05, pelo conector GitHub, lendo árvore, README, licenças e os
arquivos indicados abaixo. Os SHAs identificam o estado consultado; não foram
executados os ports de terceiros. Declarações de execução feitas pelos autores
não são medições deste projeto. Nenhum código desses projetos foi incorporado
nesta primeira iteração. Atualização: o XenonRecomp fixado abaixo foi depois
compilado e executado privadamente sobre o XEX fornecido; os ports de terceiros
continuam sem execução nesta sessão.

| Projeto | Commit consultado | Licença observada | Decisão inicial |
| --- | --- | --- | --- |
| [XenonRecomp](https://github.com/hedge-dev/XenonRecomp) | `ddd128bcca99fe8bfbb99bea583c972351fa6ace` | MIT no `LICENSE.md`; dependências têm licenças próprias | Candidato principal para preparação AOT, com auditoria ARM obrigatória |
| [UnleashedRecomp](https://github.com/hedge-dev/UnleashedRecomp) | `cf829a9eca8fb680fba4b0409ddeb6ca92f22e3c` | GPL v3 no `COPYING`; componentes adaptados identificados como GPL-3.0-or-later pelo SpeedBreaker | Referência de integração; não copiar silenciosamente para código MIT |
| [SpeedBreaker](https://github.com/SpeedBreakerProject/speedbreaker) | `496451a836f2f38d3163b696b8940e4f6730dc43` | GPL-3.0-or-later, `COPYING`, cabeçalhos e `THIRD_PARTY_NOTICES.md` | Referência concreta de iOS/ARM, memória, arquivos e ciclo de vida; renderer usa Vulkan/MoltenVK |
| [Xenia](https://github.com/xenia-project/xenia) | `95a5c3ee250f80c3b9d139658649d9ffb6db3eec` | BSD-3-Clause no `LICENSE`; verificar arquivos e dependências separadamente | Referência de formatos e semântica, sem integrar emulador completo |
| [Storm Android](https://github.com/Masterllgod/naruto-storm-revolution-port-nativo) | `e80494bcd46adfca9e4efd08eff04a5f4f93e406` | Não há licença geral de código na árvore; notices enumeram componentes externos | Referência de identidade/controles; fonte do port não está publicada |
| [Xenon-Recomp alternativo](https://github.com/nimauria/Xenon-Recomp) | `0b0bfb7b34ad0cd11488e2624860715a83179d0e` | MIT no `LICENSE`; dependências com notices próprios | Observar análise/IR; ARM64 ainda é objetivo, não alternativa pronta |

## XenonRecomp

Lidos: `README.md`, `LICENSE.md`, `CMakeLists.txt`, `.gitmodules`,
`XenonUtils/ppc_context.h`, `XenonUtils/xex.h`, `XenonUtils/xex.cpp` e
`XenonRecomp/recompiler.cpp`.

O [README fixado](https://github.com/hedge-dev/XenonRecomp/blob/ddd128bcca99fe8bfbb99bea583c972351fa6ace/README.md)
descreve tradução PPC para C++, sem fornecer runtime. O contexto contém os
registradores, e cada função recebe contexto e base da memória de endereços
guest de 32 bits. O código gerado é compilado antes da execução.

Há suporte ARM64 explícito via SIMDe. O
[contexto](https://github.com/hedge-dev/XenonRecomp/blob/ddd128bcca99fe8bfbb99bea583c972351fa6ace/XenonUtils/ppc_context.h)
contém caminho `__aarch64__` para FPCR e rotinas SIMDe. Isso sustenta a
viabilidade da arquitetura, mas não prova a correção do Storm em ARM. SIMD tem
ordem dos 16 bytes invertida em relação ao guest, e FPU/VMX têm políticas
diferentes para denormais. Validar permutações, saturação, NaN, arredondamento,
loads/stores desalinhados e VMX128.

Riscos encontrados no código do emissor:

- `lwsync` é emitido como operação vazia; isso exige revisão para a ordenação
  mais fraca de ARM64.
- `lwarx` salva o valor lido; `stwcx.` usa compare-and-swap. Isso não modela
  automaticamente endereço/grânulo/invalidade da reserva ou o caso ABA.
- Desvios indiretos precisam de tabela de funções; tabelas de salto dependem
  de análise e configuração. O `default` de switches pode ser
  `__builtin_unreachable()`, perigoso com descoberta incompleta.
- O README declara MMIO e exceções sem suporte completo. Uma recompilação que
  compila pode ainda conter diagnósticos, traps e caminhos inválidos.
- Endereços de save/restore, setjmp/longjmp, funções e hooks são específicos
  do executável. Não reutilizar endereços do Sonic ou do Need for Speed.

Ferramentas: CMake >= 3.20 e Clang >= 18, clone com submódulos; testar o Clang
Apple efetivamente selecionado na CI, sem inferir sua equivalência só pelo
número de versão do Xcode. CLI publicada:

```text
XenonAnalyse INPUT.xex OUTPUT-switch-tables.toml
XenonRecomp CONFIG.toml PATH/XenonUtils/ppc_context.h
```

Dependências declaradas em `.gitmodules`: xxHash, fmt, toml++, libmspack,
tiny-AES-c e SIMDe. A licença MIT do projeto não substitui a análise de cada
uma. Em particular libmspack é LGPL; manter preparação offline separada evita
adicioná-la desnecessariamente ao IPA. Qualquer futura integração do loader
no app precisará revisar as obrigações de distribuição. Não copiar chaves
embutidas de loaders de referência para este repositório.

Auditoria adicional da cópia fixada, durante o build host: o disassembler
`ppc-dis.c` declara GPL-2.0-or-later e `disasm.c` GPL-1.0-or-later. Portanto,
o `LICENSE.md` MIT não descreve sozinho as obrigações dos binários das ferramentas.
Também foram identificados libmspack (LGPL-2.1), TinySHA1 (ISC), fmt, SIMDe e
toml++ (MIT), tiny-AES-c (Unlicense) e xxHash (BSD-2-Clause). Essas ferramentas
foram mantidas privadas; nenhum desses componentes foi ligado ao app ou
redistribuído aqui. Antes de distribuir ferramentas ou integrar seus headers,
revisar o conjunto de fontes, notices e obrigações aplicáveis ao artefato.

## SpeedBreaker

Lidos: `README.md`, `COPYING`, `THIRD_PARTY_NOTICES.md`,
`scripts/ios/README.md`, `runtime/CMakeLists.txt`,
`runtime/cpu/ppc_context.h`, `runtime/platform/ios_files.mm` e
`runtime/gpu/shader_translator.cpp`.

O [CMake do runtime](https://github.com/SpeedBreakerProject/speedbreaker/blob/496451a836f2f38d3163b696b8940e4f6730dc43/runtime/CMakeLists.txt)
usa MoltenVK estático no iOS, Vulkan, SDL3, glslang e FFmpeg. O tradutor
converte microcódigo Xenos em GLSL; não é um backend Metal nativo pronto para
transplante. O caminho observado é Xenos → GLSL/SPIR-V → MoltenVK → Metal.
Este projeto mantém como requisito seu próprio backend Metal/MSL; adotar
esse renderer inteiro seria uma alteração arquitetural, além da licença GPL.

O arquivo iOS lido usa APIs de acesso a URLs com escopo de segurança. A
documentação descreve suspensão/retomada, pressão de memória, reserva virtual
guest grande e assinatura. São bons pontos de comparação para a ponte iOS.
Os autores relatam testes de builds assinados por Xcode em iPhones, incluindo
15 Pro Max, e distinguem esses testes do IPA experimental, que declaram ainda
não instalado. Nada disso mede o Storm no iPhone 15 Pro.

As necessidades de Extended Virtual Addressing/Increased Memory Limit e os
valores de memória relatados dizem respeito ao Need for Speed. Não transferir
automaticamente números ou entitlements para o Storm. Medir primeiro a
representação de memória adotada aqui e a disponibilidade na assinatura real.

O código GPL do runtime, inclusive trechos adaptados de Unleashed, requer
distribuição compatível e fonte correspondente se reutilizado. FFmpeg e
libmspack são componentes LGPL com condições próprias; o documento upstream
lista fontes, patches e material para relink. Uma licença de terceiro não
autoriza distribuição do executável comercial recompilado.

## UnleashedRecomp

Lidos: `README.md`, `COPYING`, `CMakeLists.txt`,
`UnleashedRecomp/kernel/memory.cpp` e `UnleashedRecomp/gpu/video.cpp`.

O [renderer](https://github.com/hedge-dev/UnleashedRecomp/blob/cf829a9eca8fb680fba4b0409ddeb6ca92f22e3c/UnleashedRecomp/gpu/video.cpp)
expõe interfaces plume D3D12/Vulkan, caches, pipelines e adaptação ao engine
do Sonic. O allocator reserva espaço guest e registra funções nativas; ele
não pode ser transplantado sem revisão da política virtual do iOS. O README
descreve XenonRecomp e XenosRecomp, especializações e correções por jogo.
Isso demonstra a quantidade de integração necessária, não um runtime genérico
pronto para Naruto. Embora CMake tenha ramificações Apple/arquitetura, o README
consultado apresenta Windows/Linux e trabalho futuro em macOS; não oferece
evidência de qualificação iOS deste projeto.

## Xenia

Lidos: `LICENSE`,
[`src/xenia/kernel/util/xex2_info.h`](https://github.com/xenia-project/xenia/blob/95a5c3ee250f80c3b9d139658649d9ffb6db3eec/src/xenia/kernel/util/xex2_info.h)
e [`src/xenia/cpu/xex_module.cc`](https://github.com/xenia-project/xenia/blob/95a5c3ee250f80c3b9d139658649d9ffb6db3eec/src/xenia/cpu/xex_module.cc).
Foram conferidos layout do XEX, execução, imports, segurança, páginas e carga
de imagem. A árvore também identifica código PPC e XMA para investigação
posterior; esses subsistemas não foram integralmente auditados nesta iteração.
Usar como referência de comportamento e futuramente aproveitar partes
isoladas BSD com atribuição. Não incorporar JIT/emulador completo ao app.

## Port Android do Storm

Lidos: árvore completa, README e `THIRD_PARTY_NOTICES.md`. A árvore contém
documentação, notices, `.gitignore` e um ícone; não contém fontes do port.
Não foram baixados APKs, assets ou saves. O README afirma expressamente que
o repositório é documental. O APK ARM64 usa ABI Android, serviços Android e
Vulkan; não é fonte recompilável para iOS.

Identidade publicada, posteriormente confirmada com o XEX fornecido:

| Campo | Referência publicada |
| --- | --- |
| Title ID | `4E4D0868` |
| Media ID | `29E320A9` |
| Versão | `0.0.0.4` |
| Região | NTSC-U somente |
| Tamanho de `default.xex` | `11776000` bytes |
| SHA-1 | `c9c1cf1fc4d7a535542edb1aae19751d4ed7e090` |

O renderizador shadowZero é creditado como derivado de projetos GPL-3.0,
mas seu código não está presente aqui. Os notices não concedem acesso nem
licença ao código ausente. Aproveitar identidade e descrição de comandos;
implementar/adaptar integração, shaders e runtime por vias públicas auditáveis.

## Framework alternativo

Lidos: `LICENSE`, `README.md`, `src/recomp/CMakeLists.txt`,
`src/cpu/codegen/emission/backend_cpp_aot.cpp` e
[`src/cpu/arm64/README.md`](https://github.com/nimauria/Xenon-Recomp/blob/0b0bfb7b34ad0cd11488e2624860715a83179d0e/src/cpu/arm64/README.md).
O emissor C++ usa IR e registra PC em fronteiras de efeitos; a organização
separa análise, geração, runtime e módulos. É material útil para recuperação
de funções e diagnóstico. O README descreve fallback dinâmico; ele não deve
entrar implicitamente no caminho AOT estrito deste projeto.

A documentação ARM64 adia explicitamente o bring-up até o caminho Windows
x86-64 de Ace Combat 6 funcionar de ponta a ponta. O README relata apenas
logo de boot daquele jogo, com renderização lenta, sem áudio/gameplay
demonstrados. Portanto não é prova de suporte ao Storm nem substituto pronto
para XenonRecomp/iOS.

## Conclusão técnica desta auditoria

PPC → C++ → Clang ARM64 AOT é uma rota tecnicamente plausível com precedente
de código público para iOS. A viabilidade do executável específico permanece
**não demonstrada**: o XEX real foi identificado e seus descritores de imports
foram lidos, mas a geração exploratória encontrou 1643 diagnósticos de instrução
sem suporte em 28 variantes. Faltam cobertura validada de instruções, funções,
tabelas de salto, serviços nativos, shader corpus, modelo gráfico do engine e
medições no aparelho.
Os maiores riscos iniciais são descoberta de fluxo indireto, semântica de
sincronização ARM64, exceções/MMIO, Xenos/EDRAM e integração de áudio XMA.

Primeira integração recomendada: pin de XenonRecomp, preparação local
privada, diagnósticos que bloqueiam geração incompleta e testes sintéticos.
Antes de incorporar código ou novas bibliotecas, registrar SHA, licença,
notices e compatibilidade; nenhuma dependência externa faz parte do runtime
desta primeira iteração por resultado desta auditoria.

## Complemento de semântica vetorial

Consultado `src/xenia/cpu/ppc/ppc_emit_altivec.cc` no mesmo SHA Xenia fixado:
LVEHX usa leitura do bloco de 16 bytes como LVX; VPKSWSS128 grava SAT além do
resultado saturado. Esses comportamentos orientam a série experimental; não se
copiou HIR/JIT para o runtime. A licença BSD-3-Clause da referência permanece.

## Complemento rotate e VX128_5

No SHA Xenia já fixado, consultados `ppc_emit_alu.cc`, `ppc_hir_builder.cc`,
`ppc_instr.h` e `ppc_opcode_table_gen.cc`. UpdateCR trunca para INT32; VX128_5
descreve os campos divididos usados por VSLDOI128. Referências BSD-3-Clause;
nenhum backend HIR/JIT ou fonte GPL do disassembler foi incorporado ao runtime.

## Complemento VSCR e binary16

Consultados `ppc_emit_altivec.cc`, `ppc_instr.h` e
`src/xenia/cpu/backend/x64/x64_seq_vector.cc` no SHA Xenia já fixado, BSD-3-Clause.
Pack half usa arredondamento em direção a zero; os layouts VX128_3/VX128_4
orientam encodings sintéticos próprios. Nenhum backend JIT foi incorporado.
O backend x64 consultado possui SAT pendente; não é um oráculo completo de flags.

Para comparar a semântica SAT/NaN/truncamento de conversão, foi lido
[`target/ppc/int_helper.c`](https://github.com/qemu/qemu/blob/29760efaf96bbe5928f8111881eddbf5ac06439e/target/ppc/int_helper.c)
no QEMU `29760efaf96bbe5928f8111881eddbf5ac06439e`. O cabeçalho do arquivo é
LGPL-2.1-or-later. Foi referência de comportamento: nenhum código, biblioteca,
decoder, emulador ou dependência QEMU foi copiado ou vinculado. A implementação
própria opera diretamente sobre bits IEEE; o teste independente usa matemática
long double para a conversão signed fixed e double para binary16.
