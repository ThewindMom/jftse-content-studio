# Mesh, BMesh and modifiers

Select by purpose and evidence below. Identify a route/source card before querying SQLite or proposing API identifiers.

## Mesh from explicit vertices edges and faces — `mesh-from-explicit-data`

Mesh.from_pydata accepts vertex coordinates and edge/face indices; an empty edge list causes edges to be inferred from polygons.

Choose when: The output can be specified as coordinates and geometry connections.

Search aliases: tạo mesh bằng tọa độ, dựng đa giác, mesh từ mảng, vertices edges faces, from_pydata, procedural mesh arrays

Evidence: `bpy.types.Mesh.html#bpy.types.Mesh.from_pydata` — Create a mesh from vertices, edges and faces; infer missing edges from polygons; warn about invalid data.; `bpy.types.Mesh.html#bpy.types.Mesh.validate` — validate returns True if invalid data was corrected or removed.

Read next: `bpy.types.Mesh.html#bpy.types.Mesh.from_pydata`, `bpy.types.Mesh.html#bpy.types.Mesh.validate`, `info_gotchas_meshes.html`

Limits: from_pydata does not prevent invalid mesh data; the source calls for validation when input validity is not guaranteed.

## Connected topology editing with BMesh — `mesh-connected-topology-editing`

BMesh exposes geometry connectivity and mesh editing operations such as split, separate, collapse and dissolve.

Choose when: Edit connectivity flexibly rather than only construct mesh storage arrays.

Search aliases: sửa topology, chỉnh liên kết đỉnh cạnh mặt, tách cạnh, dissolve, collapse, connected mesh editing, BMesh

Evidence: `bmesh.html` — The introduction describes connectivity and split/separate/collapse/dissolve editing; Disk/Radial data is not exposed.; `bmesh.html#bmesh.from_edit_mesh` — Retrieve the BMesh of a mesh in Edit Mode.; `info_gotchas_meshes.html` — Edit Mode has separate data and obj.data may be out of sync.

Read next: `bmesh.html`, `bmesh.types.html`, `bmesh.ops.html`, `info_gotchas_meshes.html`

Limits: bmesh.from_edit_mesh requires a mesh already in Edit Mode; obj.data may not be synchronized with Edit Mode. The BMesh page states that Disk/Radial data is not exposed to Python.

## Extrude a face region — `mesh-extrude-region`

BMesh extrude_face_region creates extruded geometry from input edges/faces and returns geometry; it does not transform positions itself.

Choose when: Create extruded geometry from a selected BMesh region.

Search aliases: đùn mặt, extrude mặt, kéo dài vùng mesh, extrude faces, face region extrusion

Evidence: `bmesh.ops.html#bmesh.ops.extrude_face_region` — Extrude faces without transformation; accept edges/faces and return geom.

Read next: `bmesh.ops.html#bmesh.ops.extrude_face_region`, `bmesh.ops.html#bmesh.ops.translate`, `bmesh.html`

Limits: The source explicitly states that extrude_face_region does not transform; displacement requires a separately documented transformation operation.

## Bisect mesh with a plane — `mesh-plane-cut`

BMesh bisect_plane cuts a mesh using a plane point and normal, with options to remove either side.

Choose when: Specify a cutting plane and the side to keep or remove.

Search aliases: cắt đôi mesh, cắt theo mặt phẳng, plane cut, bisect mesh, trim geometry

Evidence: `bmesh.ops.html#bmesh.ops.bisect_plane` — Cut a mesh with a plane; document plane_co, plane_no and clear_outer/clear_inner.

Read next: `bmesh.ops.html#bmesh.ops.bisect_plane`, `bmesh.html`

Limits: The bisect_plane description does not promise to cap the cut automatically.

## Weld nearby vertices and triangulate faces — `mesh-weld-and-triangulate`

remove_doubles merges groups of vertices within a distance threshold; triangulate splits quads and n-gons into triangles.

Choose when: Merge nearby vertices or convert faces into triangles using the documented topology operations.

Search aliases: gộp đỉnh trùng, hàn đỉnh, tam giác hóa, remove doubles, merge by distance, triangulate faces

Evidence: `bmesh.ops.html#bmesh.ops.remove_doubles` — Find and merge vertex groups closer than dist.; `bmesh.ops.html#bmesh.ops.triangulate` — Split quads and n-gons into triangles.; `bpy.types.Mesh.html#bpy.types.Mesh.calc_loop_triangles` — Compute loop triangle tessellation.

Read next: `bmesh.ops.html#bmesh.ops.remove_doubles`, `bmesh.ops.html#bmesh.ops.triangulate`, `bmesh.html`

Limits: Mesh.calc_loop_triangles computes tessellation; this is not the same as changing topology with bmesh.ops.triangulate.

## Geometry attributes by name type and domain — `mesh-geometry-attributes`

An Attribute stores data attached to geometry elements, with a name, data type and domain such as points, curves or faces.

Choose when: Store typed data on a geometry domain for later reading or processing.

Search aliases: thuộc tính hình học, dữ liệu trên đỉnh, thuộc tính trên mặt, geometry attribute, named data, point face domain

Evidence: `bpy.types.Attribute.html` — Explain geometry attributes, unique names, types and domains.; `bpy.types.AttributeGroupMesh.html#bpy.types.AttributeGroupMesh.new` — Add an attribute with name, type and domain.

Read next: `bpy.types.Attribute.html`, `bpy.types.AttributeGroupMesh.html#bpy.types.AttributeGroupMesh.new`, `bpy_types_enum_items/attribute_domain_items.html`, `bpy_types_enum_items/attribute_type_items.html`

Limits: Name, type and domain are separate properties; do not infer a domain solely from vertex count.

## Boolean intersection union and difference — `modifier-boolean`

The Boolean modifier supports intersection, union and difference of meshes; a collection can supply operand meshes.

Choose when: Represent mesh intersection, union or subtraction as a modifier.

Search aliases: khoét lỗ bằng vật thể, trừ khối, giao khối, hợp khối, boolean modifier, mesh union, mesh difference, mesh intersection

Evidence: `bpy.types.BooleanModifier.html#bpy.types.BooleanModifier.operation` — INTERSECT keeps common geometry; UNION combines additively; DIFFERENCE subtracts.; `bpy.types.BooleanModifier.html` — collection supplies mesh objects for the Boolean operation.

Read next: `bpy.types.BooleanModifier.html`, `bpy.types.ObjectModifiers.html#bpy.types.ObjectModifiers.new`, `bpy_types_enum_items/object_modifier_type_items.html`

## Bevel edges and vertices — `geometry-bevel`

BevelModifier rounds edges/vertices; bmesh.ops.bevel operates on geometry with offset, segments and profile.

Choose when: Round edges/vertices; select the modifier route to retain a modifier, or BMesh when editing topology directly.

Search aliases: bo cạnh, bo góc, vát cạnh, làm tròn cạnh, bevel, round edges, chamfer

Evidence: `bpy.types.BevelModifier.html` — The modifier rounds edges and vertices.; `bmesh.ops.html#bmesh.ops.bevel` — Bevel edges/vertices with offset, segments and profile; profile 0.5 is described as round.

Read next: `bpy.types.BevelModifier.html`, `bmesh.ops.html#bmesh.ops.bevel`, `bpy.types.ObjectModifiers.html#bpy.types.ObjectModifiers.new`

## Array duplication modifier — `modifier-array`

ArrayModifier duplicates geometry with a copy count, constant offset and a curve for fitting array length.

Choose when: Create an array controlled by modifier count and spacing.

Search aliases: tạo dãy vật thể, lặp hình học, nhân theo khoảng cách, array modifier, repeated geometry, duplicate array

Evidence: `bpy.types.ArrayModifier.html` — Describe array duplication, count, constant_offset_displace and a curve for fitting length.

Read next: `bpy.types.ArrayModifier.html`, `bpy.types.ObjectModifiers.html#bpy.types.ObjectModifiers.new`

## Mirror modifier — `modifier-mirror`

MirrorModifier exposes mirroring axes, a reference object and a merge distance for mirrored vertices.

Choose when: Mirror geometry across axes or relative to a reference object using a modifier.

Search aliases: đối xứng mesh, phản chiếu hình học, mirror mesh, symmetrical model, mirror modifier

Evidence: `bpy.types.MirrorModifier.html` — Describe mirroring, mirror_object and the vertex merge threshold.; `bpy.types.MirrorModifier.html#bpy.types.MirrorModifier.use_axis` — An array of three flags enables mirroring by axis.

Read next: `bpy.types.MirrorModifier.html`, `bpy.types.ObjectModifiers.html#bpy.types.ObjectModifiers.new`

## Solidify shell thickness — `modifier-solidify`

SolidifyModifier creates a solid skin; thickness controls its shell thickness.

Choose when: Create a shell with thickness from input geometry.

Search aliases: tạo độ dày, làm vỏ dày, solidify, shell thickness, thicken surface

Evidence: `bpy.types.SolidifyModifier.html` — Create a solid skin and compensate for sharp angles.; `bpy.types.SolidifyModifier.html#bpy.types.SolidifyModifier.thickness` — thickness sets shell thickness.

Read next: `bpy.types.SolidifyModifier.html`, `bpy.types.ObjectModifiers.html#bpy.types.ObjectModifiers.new`

## Subdivision surface — `modifier-subdivision`

SubsurfModifier provides Catmull-Clark for smooth curved surfaces and Simple for subdividing faces without changing shape.

Choose when: Increase surface subdivisions and explicitly choose whether to curve the surface.

Search aliases: chia nhỏ bề mặt, làm mịn bằng subdivision, subdivision surface, Catmull-Clark, simple subdivision

Evidence: `bpy.types.SubsurfModifier.html#bpy.types.SubsurfModifier.subdivision_type` — CATMULL_CLARK creates a smooth curved surface; SIMPLE subdivides without changing shape.

Read next: `bpy.types.SubsurfModifier.html`, `bpy.types.ObjectModifiers.html#bpy.types.ObjectModifiers.new`

## Remesh regular topology — `modifier-remesh`

RemeshModifier generates a new surface with regular topology following the input mesh; adaptivity reduces detail where less is needed and creates triangles.

Choose when: Replace surface topology with a new mesh following the input shape.

Search aliases: remesh, tạo lại lưới, topology đều, voxel remesh modifier, rebuild mesh surface

Evidence: `bpy.types.RemeshModifier.html` — Generate regular surface topology from an input mesh; adaptivity creates triangles when simplifying.

Read next: `bpy.types.RemeshModifier.html`, `bpy.types.ObjectModifiers.html#bpy.types.ObjectModifiers.new`

Limits: The source says adaptivity can create triangles; it does not promise all-quad output.

## Decimate geometry — `modifier-decimate`

DecimateModifier offers edge collapse, un-subdivision and planar dissolve; ratio controls the target triangle ratio for collapse.

Choose when: Reduce geometry with a documented decimation method.

Search aliases: giảm polygon, giảm số mặt, mesh nhẹ hơn, decimate, polygon reduction, low poly reduction

Evidence: `bpy.types.DecimateModifier.html` — Describe COLLAPSE, UNSUBDIV and DISSOLVE.; `bpy.types.DecimateModifier.html#bpy.types.DecimateModifier.ratio` — Target triangle ratio applies only to collapse.

Read next: `bpy.types.DecimateModifier.html`, `bpy.types.ObjectModifiers.html#bpy.types.ObjectModifiers.new`

Limits: The source limits ratio to collapse; do not use it as a common control for every decimate_type.

## Shrinkwrap to a target — `modifier-shrinkwrap`

ShrinkwrapModifier wraps an object onto a target, with an auxiliary target and cull_face controls for projection based on face orientation.

Choose when: Make geometry follow a target mesh through shrink wrapping.

Search aliases: áp lưới lên bề mặt, bám mesh mục tiêu, shrinkwrap, wrap mesh to target, project vertices onto mesh

Evidence: `bpy.types.ShrinkwrapModifier.html` — Describe wrapping to a target, auxiliary_target and cull_face.

Read next: `bpy.types.ShrinkwrapModifier.html`, `bpy.types.ObjectModifiers.html#bpy.types.ObjectModifiers.new`

Limits: The shrinkwrap description does not establish a complete automatic retopology workflow.

## Discover all source pages in this domain

`python3 scripts/features.py pages geometry` lists 118 source cards with pagination. Each card retains its source name and description excerpt. Catalog discovery does not require SQLite.

Source pages remain discoverable even without an authored route. Read their descriptions/definitions before planning; do not supply missing behavior from model knowledge.
