# Sculpting, brushes and painting

Select by purpose and evidence below. Identify a route/source card before querying SQLite or proposing API identifiers.

## Sculpt mesh deformation filters — `sculpt-mesh-filters`

sculpt.mesh_filter modifies the current mesh with filters including smooth, inflate, sphere, random, volume-preserving surface smooth, sharpen and enhance details.

Choose when: Apply a sculpt filter whose documented effect matches the intended change.

Search aliases: làm trơn sculpt, phồng mesh, tăng chi tiết bề mặt, sculpt mesh filter, inflate mesh, surface smooth, sharpen cavities

Evidence: `bpy.ops.sculpt.html#bpy.ops.sculpt.mesh_filter` — Apply a filter to the current mesh; list and describe filter types.; `info_gotchas_operators.html` — Operators use context and can fail poll.

Read next: `bpy.ops.sculpt.html#bpy.ops.sculpt.mesh_filter`, `info_gotchas_operators.html`

Limits: The API does not confirm operation in every background context; the operator guide requires context/poll checks.

## Sculpt mask filters and face sets — `sculpt-masks-face-sets`

mask_filter smooths, sharpens, grows, shrinks or changes mask contrast; face_sets_create creates face sets from a mask, visible region, whole mesh or Edit Mode selection.

Choose when: Adjust a mask or group faces from an existing selection source.

Search aliases: mở rộng mask sculpt, thu nhỏ mask, làm mềm mask, tạo face set, mask filter, grow shrink mask, face sets

Evidence: `bpy.ops.sculpt.html#bpy.ops.sculpt.mask_filter` — Filter the current mask with listed filter_type values.; `bpy.ops.sculpt.html#bpy.ops.sculpt.face_sets_create` — Create face sets from masked, visible, all or selected faces.; `info_gotchas_operators.html` — Operators use context.

Read next: `bpy.ops.sculpt.html#bpy.ops.sculpt.mask_filter`, `bpy.ops.sculpt.html#bpy.ops.sculpt.face_sets_create`, `info_gotchas_operators.html`

Limits: Masks and face sets are different outputs; select the operation matching the requested output. Both APIs are operators and require a valid context.

## Sculpt brush strokes — `sculpt-brush-strokes`

sculpt.brush_stroke applies a geometry stroke using OperatorStrokeElement data, normal/invert mode, brush toggle and pen flip.

Choose when: The task requires brush strokes and can supply stroke data with an appropriate context.

Search aliases: nét cọ sculpt, điêu khắc bằng brush, sculpt stroke, brush sculpt, sculpt brush stroke

Evidence: `bpy.ops.sculpt.html#bpy.ops.sculpt.brush_stroke` — Apply a sculpt stroke using OperatorStrokeElement; override_location can be recomputed from mouse_event.; `info_gotchas_operators.html` — Operators obtain their working data from context.

Read next: `bpy.ops.sculpt.html#bpy.ops.sculpt.brush_stroke`, `bpy.types.OperatorStrokeElement.html`, `bpy.types.Brush.html`, `info_gotchas_operators.html`

Limits: The page describes stroke and mouse_event but does not provide an editor-context setup for background CLI use.

## Assign vertex group weights — `paint-vertex-weights`

VertexGroup.add assigns weights to vertex indices with replace/add/subtract modes; paint.weight_set fills the active group with the current paint weight.

Choose when: Use VertexGroup.add for explicit indexed weights; inspect weight_set to fill the active group using the current paint weight.

Search aliases: gán weight, trọng số đỉnh, vertex group weights, weight paint fill, assign vertex weights

Evidence: `bpy.types.VertexGroup.html#bpy.types.VertexGroup.add` — Add vertices by index with weight 0..1 and REPLACE/ADD/SUBTRACT.; `bpy.ops.paint.html#bpy.ops.paint.weight_set` — Fill the active vertex group with the current paint weight.

Read next: `bpy.types.VertexGroup.html#bpy.types.VertexGroup.add`, `bpy.types.VertexGroups.html`, `bpy.ops.paint.html#bpy.ops.paint.weight_set`, `info_gotchas_operators.html`

Limits: VertexGroup.add does not infer appropriate weights; weight_set uses the active group and current paint weight.

## Fill active vertex color layer — `paint-vertex-color-fill`

paint.vertex_color_set fills the active vertex color layer using the current paint color; use_alpha selects opaque or existing alpha.

Choose when: Fill the active color layer with the paint color and choose alpha handling.

Search aliases: tô màu vertex, fill màu vertex, vertex color fill, paint vertex color, active color layer

Evidence: `bpy.ops.paint.html#bpy.ops.paint.vertex_color_set` — Fill the active vertex color layer; use_alpha selects opaque alpha or preserves existing alpha.; `info_gotchas_operators.html` — The operator works through context.

Read next: `bpy.ops.paint.html#bpy.ops.paint.vertex_color_set`, `bpy.types.Attribute.html`, `info_gotchas_operators.html`

Limits: The source only describes the active layer and current paint color; it does not establish layer creation or render material setup.

## Paint strokes into an image — `paint-image-strokes`

paint.image_paint paints a stroke into an image using OperatorStrokeElement data, normal/invert mode, brush toggle and pen flip.

Choose when: Apply an image paint stroke with specified stroke data and context.

Search aliases: vẽ texture bằng cọ, nét cọ lên ảnh, image paint stroke, texture painting, paint image

Evidence: `bpy.ops.paint.html#bpy.ops.paint.image_paint` — Paint a stroke into an image with stroke, mode, brush_toggle and pen_flip.; `info_gotchas_operators.html` — Operators use context and can fail poll.

Read next: `bpy.ops.paint.html#bpy.ops.paint.image_paint`, `bpy.types.OperatorStrokeElement.html`, `bpy.types.ImagePaint.html`, `info_gotchas_operators.html`

Limits: The operator page does not provide a complete background CLI paint context; it does not establish that stroke data alone is sufficient.

## Discover all source pages in this domain

`python3 scripts/features.py pages sculpt-paint` lists 36 source cards with pagination. Each card retains its source name and description excerpt. Catalog discovery does not require SQLite.

Source pages remain discoverable even without an authored route. Read their descriptions/definitions before planning; do not supply missing behavior from model knowledge.
