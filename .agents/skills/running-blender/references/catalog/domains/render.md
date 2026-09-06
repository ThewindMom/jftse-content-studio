# Rendering, passes, color and image output

Select by purpose and evidence below. Identify a route/source card before querying SQLite or proposing API identifiers.

## Still and animation rendering — `render-still-or-animation`

bpy.ops.render.render parameters describe animation rendering over a scene frame range; write_still saves to the output path when animation is off; frame_start/frame_end bound animation rendering.

Choose when: Render a still or frame range; read RenderSettings for requested paths, dimensions and formats.

Search aliases: render ảnh, render animation, xuất frame, render still, render animation range, write still

Evidence: `bpy.ops.render.html#bpy.ops.render.render` — Describe animation, write_still, frame_start, frame_end and scene.; `bpy.types.RenderSettings.html#bpy.types.RenderSettings.engine` — Expose engine with the snapshot's BLENDER_EEVEE enum.

Read next: `bpy.ops.render.html#bpy.ops.render.render`, `bpy.types.RenderSettings.html`, `bpy.types.ImageFormatSettings.html`

Limits: The operator introduction says Undocumented, but parameters have descriptions. The engine enum lists only BLENDER_EEVEE in this snapshot; it is not a complete runtime inventory and does not justify remembered Cycles settings.

## Shadow render pass — `shadow-render-pass`

ViewLayer.use_pass_shadow is described as delivering a shadow pass.

Choose when: Obtain a separate shadow layer for later rendering/compositing.

Search aliases: đổ bóng, lớp bóng, xuất bóng riêng, shadow pass, shadow render pass

Evidence: `bpy.types.ViewLayer.html#bpy.types.ViewLayer.use_pass_shadow` — Deliver a shadow pass.

Read next: `bpy.types.ViewLayer.html#bpy.types.ViewLayer.use_pass_shadow`, `bpy.types.RenderPass.html`, `bpy.types.CompositorNodeRLayers.html`, `bpy.types.CompositorNodeOutputFile.html`

Limits: The source does not define pixel values, compositing formulas or engine availability. Enabling the flag does not prove correct pass data; read pass access APIs and inspect a real render.

## Transparent world background — `transparent-world-background`

RenderSettings.film_transparent makes the world background transparent for compositing over another background.

Choose when: Composite the rendered world background over another image.

Search aliases: nền trong suốt, render alpha, transparent background, transparent film, tách nền render

Evidence: `bpy.types.RenderSettings.html#bpy.types.RenderSettings.film_transparent` — Make the world background transparent for compositing over another background.

Read next: `bpy.types.RenderSettings.html#bpy.types.RenderSettings.film_transparent`, `bpy.types.ImageFormatSettings.html`, `bpy.types.CompositorNodeAlphaOver.html`

Limits: The property does not establish alpha-capable file output, remove scene background geometry or supply a compositing recipe. Read output-format and scene-data contracts.

## Bake selected-object image textures — `bake-selected-object-textures`

bpy.ops.object.bake bakes selected-object image textures; use_selected_to_active bakes selected objects' shading onto the active object; type describes passes and engine limitations.

Choose when: Bake textures with identified source objects, active object and required pass type.

Search aliases: bake texture, bake normal, bake vật liệu, bake image textures, selected to active

Evidence: `bpy.ops.object.html#bpy.ops.object.bake` — Bake image textures with selected-to-active behavior, pass engine limitations and target/save_mode parameters.

Read next: `bpy.ops.object.html#bpy.ops.object.bake`, `bpy_types_enum_items/bake_pass_type_items.html`, `bpy_types_enum_items/bake_target_items.html`, `bpy.types.BakeSettings.html`

Limits: Read pass/target enums and confirm selection, active object and engine support. Do not supply remembered high-poly/low-poly recipes or pass choices.

## Display color management — `display-color-management`

ColorManagedViewSettings controls image display; exposure scales by 2^exposure before the display transform and gamma applies afterward, with white-balance and view_transform properties.

Choose when: Adjust display color transformation, exposure or white balance rather than surface shader properties.

Search aliases: quản lý màu, exposure, gamma, white balance, cân bằng trắng, view transform, color management

Evidence: `bpy.types.ColorManagedViewSettings.html#bpy.types.ColorManagedViewSettings` — Describe display color management, exposure/gamma order, white balance and view transforms.

Read next: `bpy.types.ColorManagedViewSettings.html`, `bpy.types.Scene.html#bpy.types.Scene.view_settings`

Limits: The snapshot's view_transform enum lists only NONE; do not choose AgX, Filmic or looks from memory. Inspect runtime color configurations; exposure changes are not light-power changes.

## Discover all source pages in this domain

`python3 scripts/features.py pages render` lists 31 source cards with pagination. Each card retains its source name and description excerpt. Catalog discovery does not require SQLite.

Source pages remain discoverable even without an authored route. Read their descriptions/definitions before planning; do not supply missing behavior from model knowledge.
