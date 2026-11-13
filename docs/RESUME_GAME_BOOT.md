# Retomada direta do boot comercial

Prioridade: execução do título. Não refazer interface, importação ou layout de
controles para tentar resolver a ausência de gameplay. O IPA 0.2.1 é infraestrutura.

## Estado salvo

- Última execução comercial comprovada: diagnóstico privado de 11 funções AOT
  compiladas/ligadas, oito entradas observadas, reserva de 1 MiB e commit de
  64 KiB; parou em `KeGetCurrentProcessType`. Não é boot Xbox qualificado.
- Agora implementados get/set do byte PIB+0x2f, inicial USER=1, e inicialização
  dos campos conhecidos de critical section, incluindo spin count. Adaptadores
  reais do probe compilados e executados com contexto sintético e UBSan.
- Esses novos handlers **ainda não foram reexecutados sobre o título**. Enter,
  TryEnter, Leave, scheduler/KTHREAD/TLS e a ABI inicial permanecem pendentes.
- `private/game/default.xex` foi recuperado novamente do arquivo fornecido,
  isoladamente por HTTP Range. 11.776.000 bytes, CRC32 e SHA-1 conferidos:
  c9c1cf1fc4d7a535542edb1aae19751d4ed7e090.
- Hash SHA-256: b9fd8ac231a96560db2b54340880f2c3d7e8d4cd4cfa1153112077f2fa8af777.
  Nunca enviar esse arquivo ou C++ comercial para Git/CI pública.

## Próxima implementação

1. Reconstruir a toolchain privada XenonRecomp no commit e série de 13 patches
   registrados em `config/xenon_experimental_series.json`. Os comandos públicos de
   build/revisão estão em `.github/workflows/aot-tests.yml`. O compilador usado
   antes era Clang19.1.7; o novo workspace só possui GCC14 e não retém a toolchain.
2. Recriar a imagem original antes de patches de import, configuração e saída
   privadas. Os antigos `image-pristine.bin`, `generated-thirteen` e config do
   diagnóstico foram perdidos na recriação do ambiente; não fingir que existem.
   Consultar KERNEL_BRINGUP/VSCR_DISPATCH para hashes e evidências históricas.
3. Config do probe agora exige `process_block`: endereço PIB guest32 alinhado,
   com 0x60 bytes livres de conflitos. Somente o byte conhecido será mapeado.
   Rever layout e hashes antes de executar; não reaproveitar digest anterior.
4. Selecionar/qualificar novamente as funções do prefixo real e executar
   `tools/recompilation/prefix_probe.py` com config revisada, toolchain verificada
   e UBSan. Guardar logs comerciais somente em `private/`. Corrigir o próximo
   contrato observado, mantendo dependências ausentes com diagnóstico explícito.
5. Resolver as 79 chamadas omitidas/19909 palavras zero do inventário anterior,
   revisar funções/branches/modo CPU e só então qualificar a imagem completa.
6. Implementar a tradução gráfica Xenos/Metal e os serviços realmente chamados;
   o renderer atual só desenha um triângulo diagnóstico. XMA/áudio do título e
   gameplay também não estão integrados. Código ARM64 sozinho não resolve isso.

## Validação atual

Linux x86_64/GCC14.2/UBSan: 10/10 CTest, 99 Python, 1069 verificações do novo
módulo. Incluem preservação de campos desconhecidos, falhas sem escrita parcial,
conflitos do PIB, tipos inválidos, arredondamento/wrap de spin e ABI dos wrappers.
Rodar `cmake --build build --parallel 2` e
`ctest --test-dir build --output-on-failure`. CI deste marco registrada à parte;
nenhum resultado antigo deve ser atribuído a estes novos handlers.

O usuário não precisa fornecer uma “imagem AOT” pronta. O projeto deve produzi-la
com sua cópia do jogo. Arquivos privados continuam fora do Git e podem desaparecer
quando o ambiente é substituído; os relatórios públicos não são backups do jogo.
