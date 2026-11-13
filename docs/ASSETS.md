# Recursos fornecidos e armazenamento privado

O ZIP indicado pelo usuário foi inspecionado por leituras HTTP parciais, sem
baixar os 7.431.884.205 bytes completos. O diretório central ZIP64 contém
29 entradas: 21 arquivos e 8 diretórios, com 9.433.995.676 bytes descompactados.
Não foram identificados caminhos inseguros, symlinks ou entradas cifradas no
índice; isso não valida CRC, integridade ou formatos de todos os recursos.

| Extensão | Arquivos |
| --- | ---: |
| .xex | 1 |
| .cpk | 7 |
| .bin | 2 |
| .xfbin | 3 |
| .nsh | 6 |
| Sem extensão | 2 |

Não há APK no índice. As extensões não comprovam o conteúdo dos containers,
a presença de áudio japonês nem a completude de uma edição do jogo.

Somente o Default.xex foi descompactado isoladamente: header local, método
DEFLATE, tamanho de 11.776.000 bytes, CRC32 e SHA-1 foram conferidos. SHA-1
`c9c1cf1fc4d7a535542edb1aae19751d4ed7e090`, idêntico à referência e à cópia
anterior. O original foi preservado. Relatórios, índice e cópia ficam sob
`private/`; nenhum recurso foi publicado no GitHub ou enviado à CI.

Este ambiente tem aproximadamente 7 GB livres e não comporta os 9,43 GB
extraídos. Para armazenar também o ZIP, são necessários mais de 16,87 GB,
além de espaço para ferramentas, builds e saídas de recompilação. A importação
iOS 0.2.0 recebe ZIP/ZIP64 e usa staging: requer espaço para a nova cópia
descompactada, mais 256 MiB livres, além do ZIP e de qualquer instalação anterior. A extração de containers CPK, a
identificação de shaders, texturas e streams XMA ainda precisam de implementação.


## Conferência do ZIP com o novo importador — 2026-11-13

Após recriar o workspace, 68.981 bytes de metadados foram obtidos por HTTP Range.
O índice, cabeçalhos locais e descriptors foram reunidos em um arquivo **esparso
somente de metadados**, ocupando 143.360 bytes físicos. O construtor real
`ZipArchive` aceitou as 29 entradas e o total de 9.433.995.676 bytes com UBSan.
Métodos encontrados: Stored/Deflate; flags 0/8; caminhos ASCII.
Isso confirma a leitura estrutural pelo parser atual, **não extração completa ou
CRC de payload**. Não se tentou extrair o arquivo esparso (seus payloads estão
ausentes); nenhum dado incompleto foi tratado como cópia utilizável do jogo.
[Relatório agregado](validation/zip-real-metadata-2026-11-13.json).
