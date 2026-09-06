# Files, import/export, libraries and assets

Select by purpose and evidence below. Identify a route/source card before querying SQLite or proposing API identifiers.

## Open and save blend files — `blend-file-open-save`

wm.open_mainfile opens a Blender file; wm.save_as_mainfile saves the current file to a specified location.

Choose when: Load a .blend project or save a script's output as .blend.

Search aliases: mở blend, lưu blend, save scene, open blend file, dự án Blender

Evidence: `bpy.ops.wm.html#bpy.ops.wm.open_mainfile` — Open a Blender file with load_ui and use_scripts options.; `bpy.ops.wm.html#bpy.ops.wm.save_as_mainfile` — Save the current file with copy, compress and relative_remap options.

Read next: `bpy.ops.wm.html#bpy.ops.wm.open_mainfile`, `bpy.ops.wm.html#bpy.ops.wm.save_as_mainfile`, `bpy.path.html`

Limits: Opening a file replaces current data; identify the requested input and output files. Do not enable use_scripts or overwrite unrelated files automatically; read load/save options and inspect the created file.

## Blend library linking and appending — `blend-library-datablocks`

BlendDataLibraries.load exposes available data-block names and links/appends selected names when its context ends; write saves selected data-blocks and indirect references.

Choose when: Reuse part of another .blend file or package data-blocks as a library.

Search aliases: append, link library, thư viện blend, lấy object từ file khác, data-block library

Evidence: `bpy.types.BlendDataLibraries.html#bpy.types.BlendDataLibraries.load` — The context manager returns input/output; output names are linked or appended on exit and input is read-only.; `bpy.types.BlendDataLibraries.html#bpy.types.BlendDataLibraries.write` — Write data-blocks to a blend file, expanding indirectly referenced data-blocks.

Read next: `bpy.types.BlendDataLibraries.html`, `bpy.types.CollectionObjects.html`, `bpy.path.html#bpy.path.abspath`

Limits: Treat context-manager input as read-only and place selected names in its output as documented. Choose link/append and paths according to the request; loading a data-block does not prove collection membership.

## Asset marking and metadata — `asset-metadata-marking`

ID.asset_mark enables data-block reuse through the Asset Browser; AssetMetaData stores description, author, tags and a catalog identifier.

Choose when: Mark a reusable data-block and prepare asset metadata.

Search aliases: asset, asset browser, tạo thư viện asset, asset metadata, gắn tag, catalog asset

Evidence: `bpy.types.ID.html#bpy.types.ID.asset_mark` — Enable reuse through the Asset Browser with previews, descriptions and tags.; `bpy.types.AssetMetaData.html#bpy.types.AssetMetaData` — Metadata includes author, description and catalog_id; catalog_id must be an RFC4122 UUID.

Read next: `bpy.types.ID.html#bpy.types.ID.asset_mark`, `bpy.types.AssetMetaData.html`, `bpy.types.BlendDataLibraries.html`

Limits: Marking an asset does not establish library configuration or publication. catalog_id must meet the source's UUID requirement; a catalog name is not its ID.

## OBJ and STL file exchange — `obj-stl-exchange`

wm.obj_import loads Wavefront OBJ scenes; wm operators import/export OBJ and STL with scale, axis and object-selection parameters.

Choose when: Exchange files in OBJ or STL format.

Search aliases: OBJ, STL, nhập mesh, xuất obj, xuất stl, Wavefront

Evidence: `bpy.ops.wm.html#bpy.ops.wm.obj_import` — Load a Wavefront OBJ scene with scale and forward/up axes.; `bpy.ops.wm.html#bpy.ops.wm.obj_export` — OBJ export declares export_selected_objects, apply_modifiers, scale and axes.; `bpy.ops.wm.html#bpy.ops.wm.stl_import` — Import STL as an object.; `bpy.ops.wm.html#bpy.ops.wm.stl_export` — Save the scene as an STL file.

Read next: `bpy.ops.wm.html#bpy.ops.wm.obj_import`, `bpy.ops.wm.html#bpy.ops.wm.obj_export`, `bpy.ops.wm.html#bpy.ops.wm.stl_import`, `bpy.ops.wm.html#bpy.ops.wm.stl_export`

Limits: Successful STL export does not prove printability or watertightness. Read scale, axes and modifier options and verify runtime operators; do not use remembered older operator names.

## glTF 2.0 file exchange — `gltf-file-exchange`

import_scene.gltf loads glTF 2.0; export_scene.gltf exports scenes with documented geometry, material, animation, skin and morph options.

Choose when: Exchange glTF/GLB or inspect glTF 2.0 transfer options.

Search aliases: glTF, GLB, gltf 2.0, xuất glb, nhập gltf

Evidence: `bpy.ops.import_scene.html#bpy.ops.import_scene.gltf` — Import glTF 2.0 with glb/gltf filters.; `bpy.ops.export_scene.html#bpy.ops.export_scene.gltf` — Export a scene to glTF 2.0 with export_animations, export_skins and export_morph parameters.

Read next: `bpy.ops.import_scene.html#bpy.ops.import_scene.gltf`, `bpy.ops.export_scene.html#bpy.ops.export_scene.gltf`

Limits: Export options do not guarantee faithful transfer of every shader, constraint or animation. Verify operator registration, read the actual export_format enum and validate the file in a suitable consumer.

## FBX file exchange — `fbx-file-exchange`

import_scene.fbx loads FBX; export_scene.fbx writes FBX with object, axis, armature and animation-baking options.

Choose when: Exchange files in FBX format.

Search aliases: FBX, xuất fbx, nhập fbx, fbx animation, fbx armature

Evidence: `bpy.ops.import_scene.html#bpy.ops.import_scene.fbx` — Import FBX with animation and bone-orientation options.; `bpy.ops.export_scene.html#bpy.ops.export_scene.fbx` — Write FBX with bake_anim and armature options; global_scale warns about importer support for scaled armatures.

Read next: `bpy.ops.import_scene.html#bpy.ops.import_scene.fbx`, `bpy.ops.export_scene.html#bpy.ops.export_scene.fbx`

Limits: The documentation warns that some importers do not support scaled armatures; verify the target consumer. Default bake/axis/bone options do not guarantee correctness; read parameters and validate by re-import or target consumer.

## USD scene exchange — `usd-scene-exchange`

wm.usd_import imports a USD stage into the scene; wm.usd_export writes a USD archive with geometry, light, camera, material, animation and unit options.

Choose when: Exchange USD scenes or inspect source-documented USDZ export options.

Search aliases: USD, USDZ, USD stage, xuất usd, nhập usd

Evidence: `bpy.ops.wm.html#bpy.ops.wm.usd_import` — Import a USD stage with camera, light, geometry, skeleton and material options.; `bpy.ops.wm.html#bpy.ops.wm.usd_export` — Export a USD archive; the signature includes export_animation, convert_scene_units and usdz_downscale_size.

Read next: `bpy.ops.wm.html#bpy.ops.wm.usd_import`, `bpy.ops.wm.html#bpy.ops.wm.usd_export`, `bpy.app.html#bpy.app.build_options`

Limits: USDZ parameters do not establish compatibility with every target consumer; read the options and test. Verify USD build support and exported/imported scene content, including units and material conversion.

## Alembic archive exchange — `alembic-archive-exchange`

wm.alembic_import loads Alembic archives; wm.alembic_export writes scenes with frame ranges, transform/geometry samples and data options.

Choose when: Exchange Alembic files or inspect frame-range scene export to this archive format.

Search aliases: Alembic, ABC, xuất abc, nhập abc, alembic archive

Evidence: `bpy.ops.wm.html#bpy.ops.wm.alembic_import` — Load an Alembic archive with set_frame_range and as_background_job.; `bpy.ops.wm.html#bpy.ops.wm.alembic_export` — Export an Alembic archive with start/end, xsamples, gsamples and UV, normal, hair and particle options.

Read next: `bpy.ops.wm.html#bpy.ops.wm.alembic_import`, `bpy.ops.wm.html#bpy.ops.wm.alembic_export`, `bpy.app.html#bpy.app.build_options`

Limits: The API does not prove preservation of every Blender data type; verify the required fields. as_background_job does not guarantee operation in every CLI context; probe operators/build and inspect output files.

## External paths and packed resources — `external-assets-paths-pack`

blend_paths lists external .blend references; abspath resolves // paths; pack_all/unpack_all pack or extract .blend resources.

Choose when: Audit resource paths or move between packed and external resources.

Search aliases: pack assets, đóng gói texture, file phụ thuộc, relative path, unpack, thiếu texture

Evidence: `bpy.utils.html#bpy.utils.blend_paths` — List external paths referenced by the loaded .blend.; `bpy.path.html#bpy.path.abspath` — Resolve // paths relative to the blend file or library.; `bpy.ops.file.html#bpy.ops.file.pack_all` — Pack used external files into the .blend.; `bpy.ops.file.html#bpy.ops.file.unpack_all` — Unpack resources using the selected method.

Read next: `bpy.utils.html#bpy.utils.blend_paths`, `bpy.path.html`, `bpy.ops.file.html#bpy.ops.file.pack_all`, `bpy.ops.file.html#bpy.ops.file.unpack_all`

Limits: A path list does not prove file existence or content correctness; inspect required resources. Unpack modes write external files; use only requested destinations and behavior.

## Discover all source pages in this domain

`python3 scripts/features.py pages files-assets` lists 71 source cards with pagination. Each card retains its source name and description excerpt. Catalog discovery does not require SQLite.

Source pages remain discoverable even without an authored route. Read their descriptions/definitions before planning; do not supply missing behavior from model knowledge.
