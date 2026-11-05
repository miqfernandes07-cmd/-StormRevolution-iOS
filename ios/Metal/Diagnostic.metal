#include <metal_stdlib>
using namespace metal;
struct VertexOut { float4 position [[position]]; float3 color; };
vertex VertexOut diagnostic_vertex(uint index [[vertex_id]]) {
  const float2 positions[3] = {float2(0, .7), float2(-.7, -.7), float2(.7, -.7)};
  const float3 colors[3] = {float3(1, .4, .1), float3(.2, .4, 1), float3(.2, 1, .7)};
  return {float4(positions[index], 0, 1), colors[index]};
}
fragment float4 diagnostic_fragment(VertexOut value [[stage_in]]) { return float4(value.color, 1); }
