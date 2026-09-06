# Lights, cameras and shadows

Select by purpose and evidence below. Identify a route/source card before querying SQLite or proposing API identifiers.

## Scene object shadow-ray controls — `scene-shadow-ray-controls`

Object.visible_shadow controls visibility to shadow rays. AreaLight.shadow_soft_size describes light size for ray-traced shadow sampling; Light.use_shadow has only type/default information in the source.

Choose when: Explore scene-object, light or shadow-ray controls; continue reading object, light and engine evidence.

Search aliases: đổ bóng, bóng vật thể, bóng xuống sàn, bóng mềm, cast shadow, soft shadow, shadow rays

Evidence: `bpy.types.Object.html#bpy.types.Object.visible_shadow` — Control object visibility to shadow rays.; `bpy.types.AreaLight.html#bpy.types.AreaLight.shadow_soft_size` — Set light size for ray-traced shadow sampling without a complete engine-specific softness contract.; `bpy.types.AreaLight.html#bpy.types.AreaLight.size` — Set area-light size, or X dimension for rectangular lights.

Read next: `bpy.types.Object.html#bpy.types.Object.visible_shadow`, `bpy.types.Light.html`, `bpy.types.AreaLight.html`, `bpy.types.RenderSettings.html#bpy.types.RenderSettings.engine`

Limits: Light.use_shadow does not document a complete shadow algorithm. Do not assume increasing AreaLight.shadow_soft_size guarantees softer shadows in every engine; AreaLight.size describes source area separately. This corpus does not supply a complete soft-shadow recipe; implement supported parts and report remaining evidence gaps.

## Shadow catcher for real footage — `shadow-catcher-real-footage`

Object.is_shadow_catcher renders only shadows and reflections on an object for compositing into real footage. Flagged objects are considered present in the footage; unflagged objects are synthetic additions.

Choose when: Composite synthetic objects into footage where an existing surface should receive rendered shadows/reflections.

Search aliases: đổ bóng, bắt bóng, ghép model vào footage, ghép vào ảnh thật, shadow catcher, real footage, compositing shadows

Evidence: `bpy.types.Object.html#bpy.types.Object.is_shadow_catcher` — Render shadows and reflections for real-footage compositing; describe the roles of flagged and unflagged objects.

Read next: `bpy.types.Object.html#bpy.types.Object.is_shadow_catcher`, `bpy.types.RenderSettings.html#bpy.types.RenderSettings.film_transparent`, `bpy.types.CompositorNodeAlphaOver.html`, `bpy.types.RenderSettings.html#bpy.types.RenderSettings.engine`

Limits: The anchor does not establish supported engines or a camera, lighting and compositing recipe. A flag alone does not complete the composite; read further and verify runtime/render output.

## Light linking and blocker collections — `light-linking-and-blockers`

ObjectLightLinking.receiver_collection defines an emitter's light-linking relationships; blocker_collection defines objects blocking that emitter's light.

Choose when: Control emitter relationships with receiver collections or light-blocker collections.

Search aliases: light linking, shadow linking, chặn ánh sáng, vật nhận sáng, blocker collection, receiver collection

Evidence: `bpy.types.ObjectLightLinking.html#bpy.types.ObjectLightLinking.receiver_collection` — A collection defines emitter light-linking relationships.; `bpy.types.ObjectLightLinking.html#bpy.types.ObjectLightLinking.blocker_collection` — A collection defines objects blocking light from the emitter.

Read next: `bpy.types.ObjectLightLinking.html`, `bpy.types.CollectionLightLinking.html`, `bpy.types.RenderSettings.html#bpy.types.RenderSettings.engine`

Limits: The source does not establish support in every engine. Read collection contracts and editing APIs and check the actual engine before promising an effect.

## Point, sun, spot and area light sources — `choose-light-source-shape`

The source describes POINT as omnidirectional, SUN as fixed-direction parallel rays, SPOT as a directional cone and AREA as a directional area source. BlendDataLights.new creates a light data-block.

Choose when: Choose a light-source shape before reading PointLight, SunLight, SpotLight or AreaLight properties.

Search aliases: tạo đèn, nguồn sáng, đèn điểm, đèn rọi, đèn diện tích, point light, sun light, spot light, area light

Evidence: `bpy_types_enum_items/light_type_items.html` — Describe POINT, SUN, SPOT and AREA source shapes.; `bpy.types.BlendDataLights.html#bpy.types.BlendDataLights.new` — Create a light data-block using the type enum.

Read next: `bpy_types_enum_items/light_type_items.html`, `bpy.types.BlendDataLights.html#bpy.types.BlendDataLights.new`, `bpy.types.AreaLight.html`, `bpy.types.SpotLight.html`, `bpy.types.PointLight.html`, `bpy.types.SunLight.html`

Limits: Source shape does not provide appropriate power, position, exposure or shadow settings. Derive these from the request, supplied evidence and output checks.

## Discover all source pages in this domain

`python3 scripts/features.py pages lights-shadows` lists 27 source cards with pagination. Each card retains its source name and description excerpt. Catalog discovery does not require SQLite.

Source pages remain discoverable even without an authored route. Read their descriptions/definitions before planning; do not supply missing behavior from model knowledge.
