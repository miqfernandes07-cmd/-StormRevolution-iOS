# Gráficos — fronteira de backend

O único renderer existente está em `ios/Metal/`: triângulo MSL de diagnóstico,
limite de frames em voo e escala configurável/adaptativa. Não recebe comandos Xenos.
Ainda não existe interface de comandos guest normalizados: definir após identificar
se o Storm usa hooks D3D ou escrita direta PM4. Tradução de shaders, vertex fetch,
texturas tiled, formatos, depth/stencil e resolves/EDRAM continuam pendentes.
O diagnóstico não substitui nenhum desses caminhos e não representa uma cena do jogo.
