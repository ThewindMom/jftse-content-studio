# Curves, 3D text, hair, point clouds and volumes

Select by purpose and evidence below. Identify a route/source card before querying SQLite or proposing API identifiers.

## Curves splines bevel and extrusion — `curves-splines-and-thickness`

Curve stores curves, splines and NURBS; create POLY, BEZIER or NURBS splines and set bevel radius and extrusion along local Z.

Choose when: Describe geometry as splines and use Curve bevel/extrusion properties.

Search aliases: đường cong Bézier, đường NURBS, tạo dây theo đường, curve spline, bezier path, curve bevel, curve extrusion

Evidence: `bpy.types.Curve.html` — A Curve data-block stores curves, splines and NURBS.; `bpy.types.CurveSplines.html#bpy.types.CurveSplines.new` — Add a POLY, BEZIER or NURBS spline.; `bpy.types.Curve.html#bpy.types.Curve.bevel_depth` — Bevel radius excludes extrusion.; `bpy.types.Curve.html#bpy.types.Curve.extrude` — Add depth along local Z, along the curve and perpendicular to normals.

Read next: `bpy.types.Curve.html`, `bpy.types.CurveSplines.html#bpy.types.CurveSplines.new`, `bpy.types.Spline.html`, `bpy.types.BezierSplinePoint.html`

Limits: bevel_depth excludes extrusion; the source defines extrude along local Z, along the curve and perpendicular to its normals.

## Text curve geometry — `curves-text-geometry`

TextCurve stores text in a curve data-block, with body holding the text; StringToCurves generates a paragraph with a font and stores each character as a curve instance.

Choose when: Create text geometry or curve instances in Geometry Nodes.

Search aliases: chữ 3D, hình học chữ, text object, text curve, string to curves, font geometry

Evidence: `bpy.types.TextCurve.html` — A curve data-block stores text.; `bpy.types.TextCurve.html#bpy.types.TextCurve.body` — body holds the text object's content.; `bpy.types.GeometryNodeStringToCurves.html` — Generate a paragraph with a font, storing each character as a curve instance.

Read next: `bpy.types.TextCurve.html`, `bpy.types.Curve.html`, `bpy.types.GeometryNodeStringToCurves.html`

Limits: These sources describe text geometry; they do not establish sequencer titles or screen font drawing.

## Hair curves data — `curves-hair-data`

Curves is a hair-curves data-block with geometry attributes; add_curves accepts a point count for each curve.

Choose when: Create hair-curves data with specified point counts per curve.

Search aliases: dữ liệu tóc, hair curves, thêm sợi tóc, curves strands, hair geometry attributes

Evidence: `bpy.types.Curves.html` — A hair-curves data-block exposes geometry attributes.; `bpy.types.Curves.html#bpy.types.Curves.add_curves` — sizes specifies the number of points in each curve.

Read next: `bpy.types.Curves.html`, `bpy.types.Curves.html#bpy.types.Curves.add_curves`, `bpy.types.Attribute.html`, `bpy.ops.sculpt_curves.html`

Limits: add_curves only describes curve sizes; it does not establish a complete grooming or hairstyle workflow.

## Volume grids mesh to volume and volume to mesh — `volume-grids-and-conversion`

Volume stores 3D grids; MeshToVolume creates fog volume from a mesh surface and VolumeToMesh creates a surface mesh from volume. VolumeGrids.load reads grid lists and metadata from a file.

Choose when: Use volume grids or a documented mesh/volume conversion.

Search aliases: tạo volume từ mesh, chuyển volume thành mesh, đọc volume file, fog volume, volume grids, mesh to volume, volume to mesh

Evidence: `bpy.types.Volume.html` — A Volume data-block stores 3D volume grids.; `bpy.types.VolumeGrids.html#bpy.types.VolumeGrids.load` — Load grid lists and metadata from a file and return a success boolean.; `bpy.types.GeometryNodeMeshToVolume.html` — Create fog volume following an input mesh surface.; `bpy.types.GeometryNodeVolumeToMesh.html` — Create a mesh on a volume surface.

Read next: `bpy.types.Volume.html`, `bpy.types.VolumeGrids.html`, `bpy.types.GeometryNodeMeshToVolume.html`, `bpy.types.GeometryNodeVolumeToMesh.html`

Limits: VolumeGrids.load only promises grid lists and metadata; success does not prove all voxels are loaded or the volume renders correctly.

## Point cloud positions and radii — `point-cloud-fields`

PointCloud is a point-cloud data-block; GeometryNodePoints generates points with positions and radii defined by fields.

Choose when: Create points with position/radius data rather than mesh faces.

Search aliases: đám mây điểm, tập điểm 3D, point cloud, points radii, generate points from fields

Evidence: `bpy.types.PointCloud.html` — A point-cloud data-block exposes geometry attributes.; `bpy.types.GeometryNodePoints.html` — Generate a point cloud with positions and radii defined by fields.; `bpy.types.PointCloud.html#bpy.types.PointCloud.points` — points is a read-only collection in this snapshot.

Read next: `bpy.types.PointCloud.html`, `bpy.types.GeometryNodePoints.html`, `bpy.types.Attribute.html`

Limits: PointCloud.points is documented as a read-only collection; do not infer an add_points method on the data-block.

## Metaball blobby surfaces — `metaball-blobby-surfaces`

MetaBall defines blobby surfaces and contains MetaElement items.

Choose when: Use the documented blobby surface type and continue selecting its elements through the API.

Search aliases: metaball, bề mặt blob, khối mềm dạng blob, blobby surfaces, metaball elements

Evidence: `bpy.types.MetaBall.html` — A metaball data-block defines blobby surfaces.; `bpy.types.MetaBall.html#bpy.types.MetaBall.elements` — A collection contains metaball elements.

Read next: `bpy.types.MetaBall.html`, `bpy.types.MetaBallElements.html`, `bpy.types.MetaElement.html`

Limits: A blobby surface description does not establish fluid or soft-body simulation.

## Discover all source pages in this domain

`python3 scripts/features.py pages curves-volumes` lists 59 source cards with pagination. Each card retains its source name and description excerpt. Catalog discovery does not require SQLite.

Source pages remain discoverable even without an authored route. Read their descriptions/definitions before planning; do not supply missing behavior from model knowledge.
