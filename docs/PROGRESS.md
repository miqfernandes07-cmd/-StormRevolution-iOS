# Progresso — iteração inicial, 2026-11-05

O projeto foi criado em `/workspace/StormRevolution-iOS` porque o workspace estava
vazio, sem checkout utilizável ou arquivos do jogo. Foi iniciado um repositório
Git local, sem remoto; nenhum histórico existente foi removido.

## Resultado comprovado

Compilação host Linux x86_64 com GCC 14.2.0, Python 3.12.14 e CMake 3.31.6.
Build Debug com UBSan e build Release aprovados. CTest passou nos dois grupos
(runtime C++ e ferramentas Python). Os testes sintéticos não executam o jogo.
Total final Debug: 1038 verificações C++ e 29 testes Python. Detalhes em
[TESTING.md](TESTING.md) e [log de validação](validation/host-debug-2026-11-05.log).

Não houve build CI, produção/assinatura de IPA, instalação, inicialização do app
Apple ou execução comercial. O iPhone 15 Pro/iOS 27 continua sem qualificação.

## Implementação concluída nesta iteração

- Auditoria das seis referências públicas, com commits, licenças e arquivos
  examinados. XenonRecomp tem caminho ARM64, mas requer auditoria de atomics,
  memória e fluxo indireto. SpeedBreaker usa Vulkan/MoltenVK; não fornece backend
  Metal nativo pronto. Android não publica as fontes completas.
- Analisador XEX2 independente, JSON, SHA-1/SHA-256, tamanho, Title/Media ID,
  versão, região, páginas e bibliotecas importadas. Estruturas incompletas,
  sobrepostas e fora dos limites são recusadas. Não inclui chaves.
- Tradutor AOT sintético para pequeno subconjunto inteiro PPC, emitindo C++.
  Geração/compilação/execução nativa host comprovadas; diagnósticos por palavra/PC
  para instruções e variantes não suportadas. Não é o tradutor do Storm.
- Adaptador para XenonRecomp com commit fixado, hashes e validação de identidade/
  caminhos privados; sete testes passaram. Upstream não foi executado.
- Runtime C++17 com API C, memória big-endian verificada, alocação alinhada,
  helpers vetoriais, registro de imports, relógio, input normalizado e arquivos
  locais limitados. Falta de import ou imagem AOT não retorna sucesso falso.
- Fonte de app UIKit/Objective-C++, MetalKit/MSL de diagnóstico, importação via
  Arquivos, validação, controles e configurações. Estado Apple: implementado sem
  compilação/teste nesta sessão. Ver [IOS.md](IOS.md).
- CMake e workflows de host/macOS, com empacotamento previsto de IPA não assinado.
  Nenhum material comercial entra nos artefatos públicos definidos.

## Erros encontrados e corrigidos

O workspace não era um Git checkout. Criado um repositório próprio no subdiretório.
CMake ausente: instalado isoladamente sob `/tmp`, sem alterar dependências do app.
A primeira configuração CMake detectou o compilador, mas falhou porque o arquivo de
testes ainda estava em implementação paralela. Após sua conclusão, ambos os builds
passaram. A revisão do parser encontrou aceitação indevida de referência JSON vazia
e risco de copiar headers sobrepostos repetidamente; o esquema agora é obrigatório
e os intervalos são verificados antes da cópia. Testes cobrem essas correções.

## Bloqueios técnicos reais

1. Sem `default.xex`/recursos: não é possível afirmar viabilidade específica,
   recuperar funções ou gerar o Storm. Referência documental não substitui arquivo.
2. Sem Clang/SDK Apple/Xcode ou remoto configurado: código iOS e workflow ainda
   não foram compilados/executados. Sem certificado/perfil/UDID não há instalação.
3. Renderer Xenos/Metal, shaders, EDRAM, áudio XMA, serviços guest e mapas de
   funções completos ainda exigem implementação. Não são resolvidos por importar
   dados ou compilar a interface.
4. Atomics, denormais, VMX128, exceções, MMIO e tabelas indiretas precisam de testes
   diferenciais antes de confiar no resultado AOT ARM64 do título.

## Próxima implementação prioritária

Com uma cópia local: executar identidade, guardar relatório privado, reconstruir
imagem offline e gerar inventário de imports/funções pelo XenonRecomp fixado;
revisar tabelas de salto e ABI. Em paralelo, executar o workflow Apple para corrigir
problemas reais de SDK/simulador e começar testes Metal de textura/depth/resolve.
Só depois de vincular uma imagem AOT válida tentar o entry point comercial e
implementar serviços conforme os primeiros diagnósticos reais. Não há previsão
medida de FPS nem promessa de prazo para gameplay.

## Histórico local

- `489d6c3`: analisador XEX2, perfil de identidade, testes e auditoria pública.
- `bdff73b`: runtime, AOT sintético, adaptador XenonRecomp e CI host.
- `ff7d83e`: app iOS, controles, diagnóstico Metal e workflow IPA não assinado.

Os controles receberam correção na revisão estática: gestos de reposicionamento
ficam desabilitados durante uso normal; o scroll não cancela os toques iniciados
nos controles. Isso ainda exige verificação física. `OBJCXX_STANDARD=17` foi
explicitado. Bash, plist e YAML passaram em verificação de sintaxe no Linux.
Nenhum commit foi enviado a GitHub e nenhuma execução de CI foi solicitada, pois
este repositório local não tem remoto configurado.
