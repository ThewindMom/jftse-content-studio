# UV maps, images and texture baking

Select by purpose and evidence below. Identify a route/source card before querying SQLite or proposing API identifiers.

## UV layers and face corner coordinates — `uv-explicit-coordinates`

UVLoopLayers.new adds a UV map; MeshUVLoopLayer.uv holds face-corner UV coordinates associated with mesh loops.

Choose when: Assign known UV coordinates by face corner, or create/inspect a UV layer directly.

Search aliases: tạo UV map, tọa độ UV, gán UV thủ công, UV layer, face corner UV, explicit UV coordinates

Evidence: `bpy.types.UVLoopLayers.html#bpy.types.UVLoopLayers.new` — Add a UV map layer to a Mesh.; `bpy.types.MeshUVLoopLayer.html#bpy.types.MeshUVLoopLayer.uv` — Face-corner UV coordinates form a Float2AttributeValue collection.; `bpy.types.Mesh.html` — Polygons reference loops; corner data such as UVs is attached to loops.

Read next: `bpy.types.UVLoopLayers.html#bpy.types.UVLoopLayers.new`, `bpy.types.MeshUVLoopLayer.html#bpy.types.MeshUVLoopLayer.uv`, `bpy.types.Float2AttributeValue.html`, `bpy.types.Mesh.html`

Limits: UVs belong to face corners; do not assume one UV per vertex without supporting evidence. A read-only uv collection does not mean every contained Float2AttributeValue is immutable; read the value type.

## UV unwrap and smart projection — `uv-unwrap-projection`

uv.unwrap unwraps the mesh being edited; smart_project projection-unwraps selected faces with angle_limit and island spacing.

Choose when: Have Blender compute UVs from a mesh or selected faces instead of supplying coordinates.

Search aliases: trải UV, mở UV, unwrap mesh, smart UV project, projection unwrap, giảm méo UV

Evidence: `bpy.ops.uv.html#bpy.ops.uv.unwrap` — Unwrap the mesh object being edited with the listed methods.; `bpy.ops.uv.html#bpy.ops.uv.smart_project` — Projection-unwrap selected mesh faces; angle_limit controls projection grouping/distortion.; `info_gotchas_operators.html` — Operators use context and can fail poll.

Read next: `bpy.ops.uv.html#bpy.ops.uv.unwrap`, `bpy.ops.uv.html#bpy.ops.uv.smart_project`, `info_gotchas_operators.html`

Limits: unwrap refers to an object being edited and smart_project to selected faces; these operators depend on context and can fail poll.

## Pack UV islands into UV or UDIM space — `uv-pack-islands`

pack_islands transforms UV islands to fill UV/UDIM space, with rotation, scale, margin and packing-target options.

Choose when: Existing UV islands need arrangement in UV or UDIM space.

Search aliases: xếp UV, đóng gói UV islands, pack UV, UV packing, UDIM islands, tối ưu diện tích UV

Evidence: `bpy.ops.uv.html#bpy.ops.uv.pack_islands` — Transform islands to fill UV/UDIM space; describe rotate, scale, margin and udim_source.; `info_gotchas_operators.html` — Operators obtain their targets from context.

Read next: `bpy.ops.uv.html#bpy.ops.uv.pack_islands`, `info_gotchas_operators.html`

Limits: pack_islands transforms islands; it does not prove that the mesh has been unwrapped. This operator depends on context as described in the operator guide.

## Discover all source pages in this domain

`python3 scripts/features.py pages uv` lists 18 source cards with pagination. Each card retains its source name and description excerpt. Catalog discovery does not require SQLite.

Source pages remain discoverable even without an authored route. Read their descriptions/definitions before planning; do not supply missing behavior from model knowledge.
