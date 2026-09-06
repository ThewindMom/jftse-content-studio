# Compositing, masks and image processing

Select by purpose and evidence below. Identify a route/source card before querying SQLite or proposing API identifiers.

## Compositor image blur — `compositor-image-blur`

CompositorNodeBlur blurs images with multiple blur modes.

Choose when: Blur an image in the compositor.

Search aliases: làm mờ ảnh, blur ảnh, image blur, compositor blur

Evidence: `bpy.types.CompositorNodeBlur.html#bpy.types.CompositorNodeBlur` — Blur images with multiple modes.

Read next: `bpy.types.CompositorNodeBlur.html`, `bpy.types.Scene.html#bpy.types.Scene.compositing_node_group`, `bpy.types.NodeLinks.html`

Limits: The class description does not enumerate sockets or detailed modes. Do not use remembered older blur properties; read supplied metadata and inspect runtime sockets.

## Glare, flares and glow in an image — `compositor-glare-glow`

CompositorNodeGlare adds lens flares, fog and glow around bright image regions.

Choose when: Create effects around bright image regions, often requested as glow or bloom.

Search aliases: quầng sáng, glow, glare, lens flare, bloom, phát sáng quanh vùng sáng

Evidence: `bpy.types.CompositorNodeGlare.html#bpy.types.CompositorNodeGlare` — Add lens flares, fog and glow around bright image regions.

Read next: `bpy.types.CompositorNodeGlare.html`, `bpy.types.Scene.html#bpy.types.Scene.compositing_node_group`, `bpy.types.Node.html#bpy.types.Node.inputs`

Limits: The bloom alias maps intent; it does not establish a BLOOM enum or Eevee bloom property. Obtain modes, thresholds and sockets from skill data/runtime.

## Chroma keying and despill — `compositor-chroma-key-despill`

CompositorNodeKeying removes a backdrop through chroma keying and corrects backdrop color spill.

Choose when: Remove a backdrop by color and optionally correct its color cast.

Search aliases: tách phông xanh, xóa phông màu, chroma key, green screen, despill, khử ám màu

Evidence: `bpy.types.CompositorNodeKeying.html#bpy.types.CompositorNodeKeying` — Remove a backdrop through chroma keying and correct its color cast with despill.

Read next: `bpy.types.CompositorNodeKeying.html`, `bpy.types.CompositorNodeImage.html`, `bpy.types.CompositorNodeAlphaOver.html`

Limits: The source does not promise arbitrary background removal or automatic key-color detection. Inspect image data and supported sockets/values; do not infer semantic segmentation.

## Foreground over background compositing — `compositor-foreground-over-background`

CompositorNodeAlphaOver overlays a foreground image on a background.

Choose when: Combine identified foreground and background images.

Search aliases: ghép ảnh, ghép nền, alpha over, overlay foreground, composite foreground background

Evidence: `bpy.types.CompositorNodeAlphaOver.html#bpy.types.CompositorNodeAlphaOver` — Overlay a foreground image on a background image.

Read next: `bpy.types.CompositorNodeAlphaOver.html`, `bpy.types.CompositorNodeImage.html`, `bpy.types.NodeLinks.html`

Limits: The description does not establish socket index order, straight/premultiplied handling or background removal. Read socket and alpha-source contracts before linking.

## Compositor image file output — `compositor-file-output`

CompositorNodeOutputFile writes image files; this snapshot exposes directory, file_name, file_output_items and format.

Choose when: Save compositor output with specified paths and formats.

Search aliases: xuất ảnh compositor, file output, ghi ảnh, output passes, write image file

Evidence: `bpy.types.CompositorNodeOutputFile.html#bpy.types.CompositorNodeOutputFile` — Write image files with this version's directory, file_name, file_output_items and format properties.

Read next: `bpy.types.CompositorNodeOutputFile.html`, `bpy.types.NodeCompositorFileOutputItems.html`, `bpy.types.ImageFormatSettings.html`

Limits: Do not use remembered base_path/file_slots properties when this snapshot documents directory/file_output_items. Path-template documentation is external and unbundled; do not invent missing template syntax.

## Ray-traced render denoising — `compositor-render-denoise`

CompositorNodeDenoise is described as denoising Cycles and other ray-traced renders.

Choose when: Denoise a ray-traced render in the compositor.

Search aliases: khử nhiễu, denoise, render noise, ảnh render nhiễu

Evidence: `bpy.types.CompositorNodeDenoise.html#bpy.types.CompositorNodeDenoise` — Denoise Cycles and other ray-traced renders.

Read next: `bpy.types.CompositorNodeDenoise.html`, `bpy.types.CompositorNodeRLayers.html`, `bpy.types.Node.html#bpy.types.Node.inputs`

Limits: The class does not fully document required sockets, auxiliary passes or denoiser libraries. Read available data and verify the runtime instead of supplying remembered Cycles configuration.

## 2D depth of field from depth or mask — `compositor-depth-of-field`

CompositorNodeDefocus applies 2D depth of field using a Z-depth map or mask, with documented bokeh, f_stop, blur_max and use_zbuffer.

Choose when: Apply depth of field during image processing using depth or mask data.

Search aliases: xóa phông theo độ sâu, defocus, depth of field, bokeh, Z depth blur

Evidence: `bpy.types.CompositorNodeDefocus.html#bpy.types.CompositorNodeDefocus` — Apply 2D depth of field using a Z-depth map or mask, with bokeh and f_stop.

Read next: `bpy.types.CompositorNodeDefocus.html`, `bpy.types.ViewLayer.html#bpy.types.ViewLayer.use_pass_z`, `bpy.types.CompositorNodeRLayers.html`

Limits: This is not camera optics configuration or proof that depth/mask data exists. Read the distinction between Z-buffer and image inputs and inspect the data.

## Cryptomatte object and material masks — `cryptomatte-object-material-masks`

CompositorNodeCryptomatteV2 creates object/material mattes from Cryptomatte render passes; ViewLayer.use_pass_cryptomatte_object outputs a pass for object isolation.

Choose when: Create object/material mattes from a render or image containing Cryptomatte passes.

Search aliases: mask vật thể, mask vật liệu, cryptomatte, object matte, material matte, tách vật thể compositing

Evidence: `bpy.types.CompositorNodeCryptomatteV2.html#bpy.types.CompositorNodeCryptomatteV2` — Create individual object/material mattes from Cryptomatte passes with RENDER or IMAGE sources.; `bpy.types.ViewLayer.html#bpy.types.ViewLayer.use_pass_cryptomatte_object` — Render an object pass for isolation during compositing.

Read next: `bpy.types.CompositorNodeCryptomatteV2.html`, `bpy.types.ViewLayer.html#bpy.types.ViewLayer.use_pass_cryptomatte_object`, `bpy.types.ViewLayer.html#bpy.types.ViewLayer.use_pass_cryptomatte_material`

Limits: This is not object recognition in arbitrary images. Confirm passes and IDs, read source/layer_name and verify engine support.

## Discover all source pages in this domain

`python3 scripts/features.py pages compositor` lists 112 source cards with pagination. Each card retains its source name and description excerpt. Catalog discovery does not require SQLite.

Source pages remain discoverable even without an authored route. Read their descriptions/definitions before planning; do not supply missing behavior from model knowledge.
