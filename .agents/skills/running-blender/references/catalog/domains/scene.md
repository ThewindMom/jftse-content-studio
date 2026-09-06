# Scenes, objects, collections and transforms

Select by purpose and evidence below. Identify a route/source card before querying SQLite or proposing API identifiers.

## Create objects and link collections — `scene-object-assembly`

Create an object in the database using a data-block, or None for an empty; linking it to a collection is a separate API operation.

Choose when: Assemble objects or empties and specify the collection that contains them.

Search aliases: dựng cảnh, thêm vật thể, tạo object, tổ chức collection, scene assembly, create object, link collection, empty object

Evidence: `bpy.types.BlendDataObjects.html#bpy.types.BlendDataObjects.new` — Create a database object; object_data can be None for an empty.; `bpy.types.CollectionObjects.html#bpy.types.CollectionObjects.link` — Add an object to a collection.

Read next: `bpy.types.BlendDataObjects.html#bpy.types.BlendDataObjects.new`, `bpy.types.CollectionObjects.html#bpy.types.CollectionObjects.link`, `bpy.types.Scene.html`

Limits: BlendDataObjects.new only creates the database object; use CollectionObjects.link to add it to a collection.

## Object transforms and parenting — `scene-transforms-parenting`

Object exposes a world-space transformation matrix and a reference to its parent object.

Choose when: Set spatial transforms or establish object parenting.

Search aliases: di chuyển vật thể, xoay vật thể, đặt vị trí, cha con, phân cấp object, world transform, parent object, matrix_world

Evidence: `bpy.types.Object.html#bpy.types.Object.matrix_world` — matrix_world is the world-space transformation matrix.; `bpy.types.Object.html#bpy.types.Object.parent` — parent references the parent object.

Read next: `bpy.types.Object.html#bpy.types.Object.matrix_world`, `bpy.types.Object.html#bpy.types.Object.parent`, `bpy.types.Object.html#bpy.types.Object.matrix_parent_inverse`, `mathutils.html`

Limits: The parent description identifies the parent object; it does not establish how to preserve the world transform when changing parents.

## Collection and child object instancing — `scene-collection-instancing`

An Object can instance an existing collection or instance child objects on vertices or faces.

Choose when: Use Object instancing with an existing collection or parent-child object relationship.

Search aliases: lặp collection, instance bộ vật thể, nhân vật thể trên đỉnh, collection instance, vertex instancing, face instancing

Evidence: `bpy.types.Object.html#bpy.types.Object.instance_collection` — instance_collection uses an existing collection.; `bpy.types.Object.html#bpy.types.Object.instance_type` — VERTS and FACES instance child objects on vertices or faces; COLLECTION enables collection instancing.

Read next: `bpy.types.Object.html#bpy.types.Object.instance_type`, `bpy.types.Object.html#bpy.types.Object.instance_collection`, `bpy.types.Depsgraph.html#bpy.types.Depsgraph.object_instances`

## Evaluated geometry and instances — `scene-evaluated-geometry`

The dependency graph exposes evaluated animation, constraints and modifiers; to_mesh creates a temporary mesh owned by the object.

Choose when: Measure, inspect or retrieve evaluated geometry rather than only the original data.

Search aliases: mesh sau modifier, đo kết quả biến dạng, hình học đã đánh giá, đọc instances, evaluated geometry, evaluated mesh, dependency graph, geometry after modifiers

Evidence: `bpy.types.Depsgraph.html` — The Evaluated ID example describes animation, constraints and modifiers in evaluated state.; `bpy.types.ID.html#bpy.types.ID.evaluated_get` — Return the ID from the last evaluation without guaranteeing graph re-evaluation.; `bpy.types.Object.html#bpy.types.Object.to_mesh` — Create a temporary mesh owned by the object and release it with to_mesh_clear.

Read next: `bpy.types.Depsgraph.html`, `bpy.types.Context.html#bpy.types.Context.evaluated_depsgraph_get`, `bpy.types.Object.html#bpy.types.Object.to_mesh`, `bpy.types.Depsgraph.html#bpy.types.Depsgraph.object_instances`

Limits: ID.evaluated_get returns the last evaluation result; it does not guarantee that the graph has been evaluated. Object.to_mesh creates temporary data that requires to_mesh_clear; do not link it directly to an object in the main database.

## Discover all source pages in this domain

`python3 scripts/features.py pages scene` lists 35 source cards with pagination. Each card retains its source name and description excerpt. Catalog discovery does not require SQLite.

Source pages remain discoverable even without an authored route. Read their descriptions/definitions before planning; do not supply missing behavior from model knowledge.
