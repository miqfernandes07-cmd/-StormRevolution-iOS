# Analisador XEX2

Implementação independente em Python 3.10+, somente biblioteca padrão. Lê metadados
big-endian sem executar o arquivo, descriptografar, descompactar ou incluir chaves.

```bash
python3 tools/xex_analysis/xex.py private/game/default.xex \
  --reference config/game_reference.json --output private/reports/xex.json
python3 -m unittest discover -s tests -p test_xex.py -v
```

Saídas: 0 = metadados analisados (e referência corresponde, se fornecida); 1 = erro
estrutural/I/O; 2 = metadados analisados, referência divergente. Nenhuma saída prova
compatibilidade de execução. SHA-1 identifica a referência; SHA-256 também é registrado.
O tamanho exato de 11.776.000 bytes vem da documentação Android, não de inspeção local.

O relatório contém cabeçalho, flags, entrypoint, base, tamanho da imagem, máscara
regional, versão crua e decodificada, Media/Title ID, descritores de páginas e
bibliotecas importadas com endereços de registros. Esses registros apontam para a
imagem carregada: os ordinais ainda não são resolvidos. Páginas executáveis não são
confundidas com seções PE nem com funções. Região é uma máscara de elegibilidade;
NTSC-U habilitado não prova edição exclusiva NTSC-U. A versão usa a disposição de
bits observada em Xenia: major bits 28–31, minor 24–27, build 8–23, QFE 0–7.

Valida limites, contagens, duplicações e sobreposição dos cabeçalhos. Limite de leitura:
512 MiB e 4096 headers opcionais. Rejeita estruturas truncadas, nomes sem terminador e ranges fora dos 32 bits.
Não valida assinatura RSA, hashes internos, autenticidade nem todos os invariantes
XEX/PE. Não imprime campos de chave, assinaturas ou bytes do jogo. Funciona em XEX2;
XEX1 e patches requerem implementação adicional.

Ainda pendentes: extração da imagem, PE, exports, ordinais, identificação de funções,
tabelas de salto e inventário PPC completo. Esses itens aparecem explicitamente como
pendentes no JSON. O tradutor sintético separado diagnostica instruções desconhecidas
com endereço e palavra; não se aplica diretamente ao payload codificado de um XEX.

Os testes constroem os próprios contêineres artificiais em memória. A palavra `blr`
no payload é apenas dado sintético, não uma imagem PE completa ou prova de boot.
