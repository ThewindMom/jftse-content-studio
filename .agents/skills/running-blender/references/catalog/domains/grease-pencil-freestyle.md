# Grease Pencil, 2D strokes and Freestyle

Select by purpose and evidence below. Identify a route/source card before querying SQLite or proposing API identifiers.

## Grease Pencil shadow effect — `grease-pencil-shadow-effect`

ShaderFx affects Grease Pencil objects. ShaderFxShadow provides shadow offset, color, scale, rotation and pixel blur; ObjectShaderFx.new adds an effect.

Choose when: Apply the documented shadow effect to an existing Grease Pencil object.

Search aliases: đổ bóng, bóng Grease Pencil, bóng nét vẽ, Grease Pencil shadow, ShaderFxShadow, bóng 2D

Evidence: `bpy.types.ShaderFx.html#bpy.types.ShaderFx` — Effects apply to Grease Pencil objects.; `bpy.types.ShaderFxShadow.html#bpy.types.ShaderFxShadow` — Describe a shadow effect with offset, shadow_color, scale, rotation and pixel blur.; `bpy.types.ObjectShaderFx.html#bpy.types.ObjectShaderFx.new` — Add a shader effect by name and type.

Read next: `bpy.types.ShaderFx.html`, `bpy.types.ShaderFxShadow.html`, `bpy.types.ObjectShaderFx.html#bpy.types.ObjectShaderFx.new`, `bpy_types_enum_items/object_shaderfx_type_items.html`

Limits: A request for a 2D shadow does not extend this route to arbitrary images or meshes. Verify object type, effect enum and render behavior; the source is not a complete recipe.

## Grease Pencil glow effect — `grease-pencil-glow-effect`

ShaderFxGlow is a Grease Pencil effect with glow_color, mode, opacity, size and a color-selection threshold; use_glow_under has a Regular blend-mode limitation.

Choose when: Apply glow to a Grease Pencil object rather than a compositor image or emission shader.

Search aliases: glow Grease Pencil, quầng sáng nét vẽ, Grease Pencil glow, ShaderFxGlow

Evidence: `bpy.types.ShaderFx.html#bpy.types.ShaderFx` — ShaderFx affects Grease Pencil objects.; `bpy.types.ShaderFxGlow.html#bpy.types.ShaderFxGlow` — Describe glow parameters and the use_glow_under limitation with Regular blend mode.

Read next: `bpy.types.ShaderFxGlow.html`, `bpy.types.ObjectShaderFx.html#bpy.types.ObjectShaderFx.new`, `bpy_types_enum_items/object_shaderfx_type_items.html`

Limits: The glow name does not determine mode or size. Read blending rules and verify the runtime; the source does not support use_glow_under with Regular blend mode.

## Freestyle contours, silhouettes and edges — `freestyle-edge-lines`

FreestyleLineSet associates lines with styles and selects contours, silhouettes, creases and other edges; FreestyleSettings offers scripting/parameter-editor modes and a separate render pass.

Choose when: Select and render documented edge/contour types through FreestyleLineSet.

Search aliases: đường viền vật thể, silhouette, Freestyle, render nét, contour lines, crease edges

Evidence: `bpy.types.FreestyleLineSet.html#bpy.types.FreestyleLineSet` — Select contours, silhouettes, creases and material boundaries and reference a linestyle.; `bpy.types.FreestyleSettings.html#bpy.types.FreestyleSettings` — Configure Freestyle per ViewLayer with SCRIPT/EDITOR modes and as_render_pass.

Read next: `bpy.types.FreestyleLineSet.html`, `bpy.types.FreestyleSettings.html`, `bpy.types.FreestyleLineStyle.html`, `freestyle.html`

Limits: This is not every Grease Pencil workflow or a guarantee of any cartoon style. Read edge selection, style and engine contracts; the snapshot is not a complete artistic recipe.

## Discover all source pages in this domain

`python3 scripts/features.py pages grease-pencil-freestyle` lists 130 source cards with pagination. Each card retains its source name and description excerpt. Catalog discovery does not require SQLite.

Source pages remain discoverable even without an authored route. Read their descriptions/definitions before planning; do not supply missing behavior from model knowledge.
