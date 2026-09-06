# Materials, shaders, textures and worlds

Select by purpose and evidence below. Identify a route/source card before querying SQLite or proposing API identifiers.

## Principled surface material — `surface-principled-material`

ShaderNodeBsdfPrincipled is described as a physically based surface shader based on OpenPBR; Material.node_tree holds the material's node tree.

Choose when: Use a physically based surface shader; read subsurface or scattering methods when those properties are required.

Search aliases: vật liệu bề mặt, shader vật lý, surface material, principled, OpenPBR

Evidence: `bpy.types.ShaderNodeBsdfPrincipled.html#bpy.types.ShaderNodeBsdfPrincipled` — Describe an OpenPBR-based physically based surface shader.; `bpy.types.Material.html#bpy.types.Material.node_tree` — Expose the node tree of a node-based material.

Read next: `bpy.types.ShaderNodeBsdfPrincipled.html`, `bpy.types.Material.html`, `bpy.types.Nodes.html`, `bpy.types.NodeLinks.html`

Limits: The class page does not list all inputs or a complete material recipe. Read node/socket data and probe the runtime; do not supply remembered socket names, values or links.

## Image texture sampling — `image-texture-sampling`

ShaderNodeTexImage samples an image file as a texture, with documented extension, interpolation and FLAT, BOX, SPHERE and TUBE projection modes.

Choose when: Use an image file in a shader network and select projection from its documented contract.

Search aliases: texture ảnh, dán ảnh lên vật thể, image texture, texture projection, image mapping

Evidence: `bpy.types.ShaderNodeTexImage.html#bpy.types.ShaderNodeTexImage` — Sample an image as a texture; projection describes ways to project a 2D image.

Read next: `bpy.types.ShaderNodeTexImage.html`, `bpy.types.BlendDataImages.html`, `bpy.types.NodeLinks.html`

Limits: Projection documentation does not establish UV availability, a loaded image or shader connections. Inspect inputs before choosing links.

## Procedural fractal Perlin noise — `procedural-noise-texture`

ShaderNodeTexNoise generates fractal Perlin noise in one to four dimensions; noise types describe sharp peaks, peaks/valleys and terrain-like signals.

Choose when: Supply noise to a shader network. Terrain wording describes the signal, not a terrain geometry recipe.

Search aliases: texture nhiễu, nhiễu thủ tục, vân ngẫu nhiên, noise texture, Perlin, fractal noise

Evidence: `bpy.types.ShaderNodeTexNoise.html#bpy.types.ShaderNodeTexNoise` — Generate fractal Perlin noise; noise_dimensions and noise_type describe dimensionality and noise forms.

Read next: `bpy.types.ShaderNodeTexNoise.html`, `bpy.types.Node.html#bpy.types.Node.inputs`

Limits: A noise name does not establish a complete node network or terrain mesh. Read noise_type, dimensions and actual sockets before connecting.

## Bump mapping from height texture — `bump-from-height`

ShaderNodeBump perturbs normals from a height texture to simulate surface detail; invert points bumps into the surface.

Choose when: Use a height texture to simulate surface detail through normals.

Search aliases: bump, bump mapping, height texture, giả gồ ghề, giả chi tiết bề mặt

Evidence: `bpy.types.ShaderNodeBump.html#bpy.types.ShaderNodeBump` — Generate a perturbed normal from a height texture to simulate detailed surfaces.

Read next: `bpy.types.ShaderNodeBump.html`, `bpy.types.ShaderNodeTexImage.html`, `bpy.types.NodeLinks.html`

Limits: The description establishes normal changes, not geometry or silhouette changes. Confirm relevant sockets from skill data/runtime.

## RGB normal map surface detail — `normal-map-surface-detail`

ShaderNodeNormalMap perturbs normals from an RGB normal image; the API describes OpenGL/DirectX conventions, normal spaces and tangent-space UV maps.

Choose when: The input is an RGB normal map; choose convention and space from the actual image data.

Search aliases: normal map, bản đồ pháp tuyến, RGB normal, DirectX normal, OpenGL normal

Evidence: `bpy.types.ShaderNodeNormalMap.html#bpy.types.ShaderNodeNormalMap` — Generate perturbed normals from an RGB normal map; describe convention, space and uv_map.

Read next: `bpy.types.ShaderNodeNormalMap.html`, `bpy.types.ShaderNodeTexImage.html`

Limits: Do not guess image convention or normal space. This route describes normals that simulate detail, not mesh changes.

## Principled volume shading — `principled-volume-shading`

ShaderNodeVolumePrincipled combines volume-shading components in one node.

Choose when: Discover a source-supported volume shader configuration.

Search aliases: shading thể tích, vật liệu thể tích, volume shading, principled volume

Evidence: `bpy.types.ShaderNodeVolumePrincipled.html#bpy.types.ShaderNodeVolumePrincipled` — Combine all volume-shading components in one node.

Read next: `bpy.types.ShaderNodeVolumePrincipled.html`, `bpy.types.Node.html#bpy.types.Node.inputs`, `bpy.types.ShaderNodeOutputMaterial.html`

Limits: The description does not supply smoke/fire simulation or a fog recipe. Do not assign those workflows without related evidence; inspect sockets and engine support.

## Lambertian emission shader — `emission-shader`

ShaderNodeEmission is described as a Lambertian emission shader.

Choose when: Add an emission component to a shader; consider compositor glare when the request specifically concerns halos around bright image regions.

Search aliases: shader phát xạ, vật liệu phát sáng, emission shader, Lambertian emission

Evidence: `bpy.types.ShaderNodeEmission.html#bpy.types.ShaderNodeEmission` — Describe a Lambertian emission shader.; `bpy.types.CompositorNodeGlare.html#bpy.types.CompositorNodeGlare` — Glare separately adds flares, fog and glow around bright image regions.

Read next: `bpy.types.ShaderNodeEmission.html`, `bpy.types.ShaderNodeOutputMaterial.html`, `bpy.types.CompositorNodeGlare.html`

Limits: This description does not establish automatic halos or illumination of other objects in every engine. Do not fill unsupported details from memory.

## Discover all source pages in this domain

`python3 scripts/features.py pages shading` lists 174 source cards with pagination. Each card retains its source name and description excerpt. Catalog discovery does not require SQLite.

Source pages remain discoverable even without an authored route. Read their descriptions/definitions before planning; do not supply missing behavior from model knowledge.
