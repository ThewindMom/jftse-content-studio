# Capability catalog before API lookup

Read this entire page before opening SQLite. This catalog supplies Blender context to the agent; do not add capabilities, APIs, enums or workflows from pretrained Blender knowledge.

The catalog contains 112 source-backed routes, 2192 source-page cards and 26775 inventory entries. An API card is a discovery entry point, not proof of a documented workflow or working CLI implementation.

| Domain | Search aliases (English / Vietnamese) | Authored routes | Source cards |
|---|---|---|---|
| [Scenes, objects, collections and transforms](domains/scene.md) | cảnh, đối tượng, vị trí, xoay, scene, object, collection, transform | 4 | 35 |
| [Mesh, BMesh and modifiers](domains/geometry.md) | lưới, hình học, bo cạnh, cắt khối, mesh, bmesh, modifier, topology | 15 | 118 |
| [Geometry Nodes, fields and instances](domains/geometry-nodes.md) | nút hình học, phân bố, nhân bản, geometry nodes, instance, field | 6 | 510 |
| [Curves, 3D text, hair, point clouds and volumes](domains/curves-volumes.md) | đường cong, chữ 3d, tóc, thể tích, curve, text geometry, hair, volume, grid | 6 | 59 |
| [Sculpting, brushes and painting](domains/sculpt-paint.md) | điêu khắc, tô màu, trọng số, sculpt, paint, brush, weight | 6 | 36 |
| [UV maps, images and texture baking](domains/uv.md) | trải uv, tọa độ uv, nướng texture, uv, unwrap, image, bake | 3 | 18 |
| [Materials, shaders, textures and worlds](domains/shading.md) | vật liệu, bề mặt, shader, material, texture, world | 7 | 174 |
| [Lights, cameras and shadows](domains/lights-shadows.md) | ánh sáng, đèn, đổ bóng, bóng, camera, light, shadow, reflection | 4 | 27 |
| [Rendering, passes, color and image output](domains/render.md) | kết xuất, render, pass, màu, png, output, color management | 5 | 31 |
| [Compositing, masks and image processing](domains/compositor.md) | hậu kỳ, ghép ảnh, khử nhiễu, compositing, mask, denoise, keying | 8 | 112 |
| [Video editing, titles and audio](domains/video-audio.md) | dựng phim, chữ video, âm thanh, video, sequencer, text strip, audio | 5 | 66 |
| [Grease Pencil, 2D strokes and Freestyle](domains/grease-pencil-freestyle.md) | vẽ 2d, nét vẽ, grease pencil, freestyle, line art, stroke | 3 | 130 |
| [Motion tracking and movie clips](domains/tracking.md) | bám chuyển động, giải camera, tracking, movie clip, camera solve | 3 | 30 |
| [Keyframes, drivers, rigs and constraints](domains/animation-rigging.md) | chuyển động, khung hình chính, xương, rig, animation, keyframe, driver, constraint | 11 | 119 |
| [Simulation, physics and caches](domains/simulation.md) | mô phỏng, vải, chất lỏng, khói, vật lý, simulation, physics, fluid, cloth, rigid body, particle | 10 | 58 |
| [Files, import/export, libraries and assets](domains/files-assets.md) | tệp, nhập, xuất, tài nguyên, file, import, export, library, asset | 9 | 71 |
| [Python integration, math, GPU and UI](domains/integration-gpu.md) | tích hợp, tiện ích, giao diện, toán, python, math, gpu, ui, registration | 7 | 404 |
| [API guides, enums and source indices](domains/api-guides.md) | tài liệu, hướng dẫn, enum, index, api reference, gotchas | 0 | 258 |

## Selecting a route

1. Match the request to the domains above using the supplied language and context. Do not guess API identifiers.
2. Read the domain file and compare purpose, selection criteria and gaps. `features.py match` searches English/Vietnamese aliases using JSON only, without opening the database.
3. Read selected routes with `features.py show ID` for source excerpts, limits and seed queries. Select multiple routes for combined tasks.
4. If no route fits, inspect domain page cards (`features.py pages DOMAIN`) and select only behavior supported by source descriptions. Missing descriptions do not permit inferring behavior from names.
5. If evidence is still insufficient, report `insufficient_skill_evidence`, identify the missing fact and request source material or clarification of the output. Do not substitute model memory.

## Status values

- `documented_route_runtime_unverified`: a source-backed description and query route; inspect the actual API/runtime before execution.
- `api_discovery_only`: a source page/API exists, but this card is not an authored task route; read the source before proceeding.
- `identifier_only`: introductory text does not sufficiently describe behavior. Preserve the gap; a class name is not evidence.

Routes and cards derive from the bundled API corpus. Blender Manual and web content have not been added to this layer. The catalog does not establish background-mode support for every feature.
