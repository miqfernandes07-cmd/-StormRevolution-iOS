# Análise reproduzível do executável

O `default.xex` comercial não foi fornecido nesta sessão. Não existem mapa de
funções do Storm, contagem real de imports/instruções, shaders identificados
ou prova de inicialização. Valores de identidade vêm da documentação Android;
ver [REFERENCES.md](REFERENCES.md). Fixtures sintéticas não comprovam o jogo.

## Entrada e isolamento

Guardar XEX, recursos, executáveis derivados, C++ gerado e relatórios detalhados
apenas em `private/` ou diretórios de build ignorados. Não adicionar hashes de
recursos ainda desconhecidos nem endereços inventados ao perfil do jogo.
Não enviar XEX ou saída proprietária como artefato público de CI.

O relatório de identidade deve comparar tamanho, SHA-1, Title ID, Media ID,
versão e máscara de região. SHA-1 serve para compatibilidade com a referência,
não autenticação criptográfica moderna; registrar SHA-256 adicional do arquivo.
A referência publicada não substitui validação do arquivo efetivo. Qualquer
arquivo modificado ou title update exige novo perfil e nova recompilação.

## Formato observado

Fonte de layout: Xenia `xex2_info.h` e uso em `xex_module.cc`, no commit
registrado em REFERENCES. O container XEX usa campos inteiros big-endian;
um PE reconstruído tem cabeçalhos little-endian. Não confundir offsets do
arquivo, RVA de PE e endereço virtual do Xbox.

| Estrutura | Campos úteis |
| --- | --- |
| Cabeçalho fixo (24 bytes) | `XEX2`, flags, offset da imagem, reservado, offset de segurança, número de headers opcionais |
| Header opcional (8 bytes) | chave e valor inline/offset; byte inferior da chave determina forma/tamanho |
| Execution info (`0x00040006`) | media ID, versão, versão base, title ID, plataforma, tabela, disco, total de discos, save ID |
| File format (`0x000003FF`) | tamanho, criptografia (u16), compressão (u16), parâmetros |
| Imports (`0x000103FF`) | tamanho, bytes da tabela de strings, número de strings, strings com padding de 4 bytes, bibliotecas |
| Biblioteca importada | tamanho, digest, ID, versão, versão mínima, índice do nome (u16), contagem (u16), endereços guest |
| Segurança | tamanho da imagem em `+0x4`, flags em `+0x10C`, load address em `+0x110`, export table em `+0x160`, região em `+0x178`, contagem de páginas em `+0x180` |
| Descritor de páginas (`+0x184`) | palavra tipo/contagem e digest SHA-1; tamanho de página depende dos flags da imagem |

Os registros de importação nos headers apontam para endereços guest da imagem;
não são diretamente ordinais. Resolver conteúdo das entradas exige imagem
reconstruída. Ler nomes de bibliotecas não equivale a resolver funções.
Exports também requerem resolução do endereço da tabela na imagem.

Versões XEX devem ser conferidas contra o layout real, sem transformar a
string `0.0.0.4` arbitrariamente em inteiro. A union consultada no Xenia expõe
major nos 4 bits inferiores, minor nos próximos 4, build nos próximos 16 e
qfe nos 8 superiores após leitura BE. Preservar o inteiro bruto no relatório
e testar todos os campos com valores diferentes. Conferir bitfields de
páginas com cuidado semelhante; não copiar representação C++ diretamente
para estruturas portáveis.

Todo tamanho, multiplicação, offset e contagem deve ser limitado pelo arquivo
e pelo container pai. Rejeitar truncamento, sobreposição inválida e tamanho
impossível antes de alocar. Campos desconhecidos merecem diagnóstico, não
sucesso fabricado. A iteração inicial não inclui chaves proprietárias nem
descriptografia; imagem cifrada/comprimida deve produzir limitação explícita.

## Sequência para o XEX real

1. Executar o analisador local e guardar relatório em `private/reports/`.
   Conferir identidade e registrá-la antes de qualquer geração.
2. Classificar criptografia/compressão. A reconstrução offline da imagem é
   uma etapa separada, usando ferramentas e insumos legitimamente disponíveis.
   Não tratar bytes cifrados como instruções PPC.
3. Enumerar seções PE, entry point, `.pdata`, imports, exports e TLS. Mapear
   página executável versus dados; reportar intervalos não interpretados.
4. Rodar XenonAnalyse e revisar funções, chamadas diretas, tail calls,
   targets indiretos e padrões de `mtctr`/`bctr`. Identificar save/restore e
   setjmp/longjmp no próprio Storm; não transplantar offsets de outro título.
5. Produzir configuração privada com limites de funções e tabelas de salto
   verificadas. Não aceitar automaticamente switches ou funções heurísticas.
6. Gerar C++ com XenonRecomp fixado, registrar logs, bloquear instruções sem
   suporte e auditar ordenação de memória/atomics para ARM64. Deixar otimizações
   de registradores desativadas até equivalência comprovada.
7. Compilar e comparar blocos selecionados com vetores independentes e,
   quando disponível, referência de execução Xbox. Distinguir teste host,
   teste ARM64 e código gerado do executável real.
8. Resolver imports por biblioteca+ordinal, implementando apenas contratos
   usados. Um serviço ausente deve gerar erro com nome, ordinal e PC guest.
9. Instrumentar hooks gráficos/áudio, identificar corpus de shaders e formatos
   de recursos antes de escolher tradução. Manter o código gerado privado.

## Gráficos e áudio: decisões que dependem do jogo

É necessário determinar se o engine permite interceptar chamadas D3D em
nível alto ou se grava diretamente comandos Xenos/PM4. O backend Metal deve
receber estado normalizado e preservar vertex fetch/endian, tiling, formatos,
depth/stencil, blending, resolves e os comportamentos de EDRAM efetivamente
usados. Primeiro validar triângulo/textura/depth/resolve com dados próprios;
depois comparar cenas do título com captura real. Um triângulo Metal é teste
de infraestrutura, não tradução de shader Xenos.

Investigar onde vivem streams XMA, formato/container, número de canais,
loop points e callbacks. Core Audio/AVAudioEngine fornece saída PCM, não
decodifica automaticamente XMA. FFmpeg é candidato após auditoria de build e
licença, incluindo condições de relink para bibliotecas LGPL estáticas.
Não presumir que áudio japonês exista no disco NTSC-U; preservar esses dados
quando realmente presentes e compatíveis. Não distribuir dublagens ou vídeos.

## Evidência necessária para mudar o status

- Análise real: identidade, tamanho e relatório gerados sobre XEX fornecido.
- AOT real: versão das ferramentas, configuração, cobertura e log de build.
- Boot: imports resolvidos, PC inicial e primeiro frame renderizado, com log
  de dispositivo e captura não gerada artificialmente.
- Gameplay: logs e validação separada de intro, menu, seleção, arena, batalha,
  finalização e save/load.
- Desempenho: iPhone/modelo/iOS/build, resolução, duração, cena, limite de FPS,
  frame times CPU/GPU, memória e estado térmico. Nenhum FPS foi medido aqui.
