# Keyframes, drivers, rigs and constraints

Select by purpose and evidence below. Identify a route/source card before querying SQLite or proposing API identifiers.

## Property keyframes — `property-keyframes`

Insert a property value at a frame; keyframe_insert creates F-Curves and animation data when needed.

Choose when: Represent a property changing at specified times.

Search aliases: keyframe, đặt khóa chuyển động, animate thuộc tính, chuyển động theo frame, thay đổi theo mốc thời gian, đổi vị trí theo các mốc thời gian, property animation

Evidence: `bpy.types.bpy_struct.html#bpy.types.bpy_struct.keyframe_insert` — Insert a property keyframe, creating F-Curves and animation data as needed; accept data_path and frame.

Read next: `bpy.types.bpy_struct.html#bpy.types.bpy_struct.keyframe_insert`, `bpy.types.Scene.html#bpy.types.Scene.frame_set`

Limits: The valid, animatable data_path for the actual object is not yet known; read the property and probe before insertion. Keyframes alone do not prove that motion or rendered images meet the request.

## Property drivers — `property-drivers`

A Driver controls a property; DriverVariable supplies inputs from RNA properties, transforms, distances between bones/objects or angles between bones.

Choose when: Make a value depend on another input or expression instead of setting individual keyframes.

Search aliases: driver, liên kết tham số, thuộc tính phụ thuộc thuộc tính khác, scripted expression, property relationship

Evidence: `bpy.types.bpy_struct.html#bpy.types.bpy_struct.driver_add` — driver_add adds a driver to the property specified by path.; `bpy.types.DriverVariable.html#bpy.types.DriverVariable` — Driver variables use RNA properties, transforms, angular differences, distances or context properties.; `bpy.types.Driver.html#bpy.types.Driver.expression` — expression stores a Scripted Expression.

Read next: `bpy.types.bpy_struct.html#bpy.types.bpy_struct.driver_add`, `bpy.types.DriverVariable.html`, `bpy.types.DriverTarget.html`

Limits: The data_path, variable sources and expression execution in the current runtime are not yet verified. Valid expression syntax does not prove the absence of dependency cycles.

## F-Curve interpolation and evaluation — `animation-curve-interpolation`

Keyframe.interpolation controls interpolation to the next keyframe; FCurve.evaluate returns the value at a frame.

Choose when: Adjust transitions between keyframes or inspect numerical animation values at specific frames.

Search aliases: nội suy, easing, đường cong chuyển động, F-Curve, interpolation, giá trị tại frame

Evidence: `bpy.types.Keyframe.html#bpy.types.Keyframe.interpolation` — Set the interpolation method for the F-Curve segment from this keyframe to the next.; `bpy.types.FCurve.html#bpy.types.FCurve.evaluate` — evaluate(frame) returns the F-Curve value at the requested frame.

Read next: `bpy.types.Keyframe.html`, `bpy_types_enum_items/beztriple_interpolation_mode_items.html`, `bpy.types.FCurve.html`

Limits: Do not select interpolation enums from memory; read the linked enum list and verify the runtime. An individual F-Curve value does not prove the final result after constraints, drivers or blending.

## Actions and NLA composition — `actions-nla-composition`

An Action contains F-Curves; NlaStrip references an Action and controls repetition and blending with other strips.

Choose when: Reuse, repeat or combine existing animation segments.

Search aliases: Action, NLA, clip animation, trộn chuyển động, lặp chuyển động, repeat action, blend actions

Evidence: `bpy.types.Action.html#bpy.types.Action` — An Action is a collection of animation F-Curves.; `bpy.types.NlaStrip.html#bpy.types.NlaStrip` — NlaStrip references an existing Action and has action_slot.; `bpy.types.NlaStrip.html#bpy.types.NlaStrip.repeat` — repeat sets the number of repetitions of the Action range.; `bpy.types.NlaStrip.html#bpy.types.NlaStrip.blend_type` — REPLACE, COMBINE, ADD, SUBTRACT and MULTIPLY combine strip results.

Read next: `bpy.types.Action.html#bpy.types.Action.slots`, `bpy.types.Action.html#bpy.types.Action.layers`, `bpy.types.NlaStrips.html`, `bpy.types.NlaStrip.html`

Limits: The 5.2 source includes Action slots and layers; do not use a remembered older Action layout. Compatibility of the Action slot with the target and the blending result remain unverified.

## Armature bone hierarchy — `armature-bone-hierarchy`

Armature contains a bone hierarchy, commonly used for character rigging; ArmatureEditBones.new creates an edit bone.

Choose when: Create or edit a rig's bone structure.

Search aliases: hệ xương, rig nhân vật, armature, bone hierarchy, tạo bone, skeleton

Evidence: `bpy.types.Armature.html#bpy.types.Armature` — An Armature data-block contains a bone hierarchy, commonly used for character rigging.; `bpy.types.EditBone.html#bpy.types.EditBone` — EditBone is a bone in an Armature data-block's Edit Mode.; `bpy.types.ArmatureEditBones.html#bpy.types.ArmatureEditBones.new` — new(name) adds a bone and returns EditBone.

Read next: `bpy.types.Armature.html`, `bpy.types.ArmatureEditBones.html`, `info_gotchas_armatures_and_bones.html`

Limits: EditBone belongs to Edit Mode; verify mode/context before creating or editing. A bone structure does not prove mesh deformation bindings or correct weights.

## Pose bone control — `bone-pose-control`

PoseBone holds bone pose data; matrix_basis accesses location, scale and rotation relative to the parent and the bone's rest state.

Choose when: Set or animate pose data on an existing armature.

Search aliases: pose, tư thế nhân vật, xoay bone, pose bone, bone transform

Evidence: `bpy.types.PoseBone.html#bpy.types.PoseBone` — PoseBone is a channel defining bone pose data within a Pose.; `bpy.types.PoseBone.html#bpy.types.PoseBone.matrix_basis` — matrix_basis accesses transforms relative to the parent and the bone's own rest state.

Read next: `bpy.types.Pose.html`, `bpy.types.PoseBone.html`, `bpy.types.bpy_struct.html#bpy.types.bpy_struct.keyframe_insert`

Limits: Do not equate pose coordinates with world space or EditBone data; read each property's coordinate-space contract. API documentation does not supply scene bone names or joint limits; inspect the actual scene.

## Copy transforms constraint — `copy-transform-constraint`

CopyTransformsConstraint copies a target's full transform and provides modes for combining it with the existing transform.

Choose when: An object or bone needs the transform of a specified target.

Search aliases: copy transforms, sao chép transform, đi theo đối tượng, constraint transform, ràng buộc chuyển động

Evidence: `bpy.types.CopyTransformsConstraint.html#bpy.types.CopyTransformsConstraint` — Copy all transforms; describe mix_mode order and shear caveats.; `bpy.types.ObjectConstraints.html#bpy.types.ObjectConstraints.new` — ObjectConstraints.new adds a constraint by type.

Read next: `bpy.types.CopyTransformsConstraint.html`, `bpy.types.Constraint.html`, `bpy.types.ObjectConstraints.html`

Limits: Do not select mix_mode, target space or owner space from memory; read this constraint's contract. The documentation warns that some matrix combinations produce shear with rotation and non-uniform scale.

## Inverse kinematics constraint — `inverse-kinematics-chain`

KinematicConstraint provides inverse kinematics; chain_count sets the affected bone count and iterations limits solver iterations.

Choose when: Control an IK relationship within a bone chain.

Search aliases: IK, inverse kinematics, động học ngược, chuỗi xương, IK constraint

Evidence: `bpy.types.KinematicConstraint.html#bpy.types.KinematicConstraint` — Describe inverse kinematics; chain_count=0 uses all bones and iterations limits solving.

Read next: `bpy.types.KinematicConstraint.html`, `bpy.types.PoseBoneConstraints.html`, `bpy.types.Constraint.html`

Limits: The API establishes IK parameters, not a complete rig for a particular character. Read target, pole, chain and constraint spaces; solver convergence and the desired pose remain unproven.

## Follow path motion — `motion-follow-path`

FollowPathConstraint locks motion to a target Curve, with frame-relative offset or curve-length offset_factor and curve-following orientation.

Choose when: Move an object or camera along a specified Curve.

Search aliases: chạy theo đường, bay theo curve, camera theo đường, follow path, path animation

Evidence: `bpy.types.FollowPathConstraint.html#bpy.types.FollowPathConstraint` — Lock motion to a Curve target; offset_factor follows length and use_curve_follow follows curve heading/banking.

Read next: `bpy.types.FollowPathConstraint.html`, `bpy.types.ObjectConstraints.html`, `bpy.types.bpy_struct.html#bpy.types.bpy_struct.keyframe_insert`

Limits: This route does not supply a Curve, keyframes or axis configuration; establish these from scene data and relevant sources. The name Follow Path does not establish constant speed; measure positions by frame when required.

## Shape key creation and values — `shape-key-values`

Object.shape_key_add creates a shape key, optionally from the current shape mix; ShapeKey.value gives its value at the current frame.

Choose when: Create or animate shape keys for an identified object.

Search aliases: shape key, blend shape, trộn hình dạng, animate shape key, morph

Evidence: `bpy.types.Object.html#bpy.types.Object.shape_key_add` — Add a shape key; from_mix creates the shape from the current mix.; `bpy.types.ShapeKey.html#bpy.types.ShapeKey.value` — value is the shape-key value at the current frame.; `bpy.types.ShapeKey.html#bpy.types.ShapeKey` — ShapeKey.points provides optimized access but excludes legacy Curve shape keys.

Read next: `bpy.types.ShapeKey.html`, `bpy.types.Key.html`, `bpy.types.bpy_struct.html#bpy.types.bpy_struct.keyframe_insert`

Limits: Object support, compatible topology and the existence of the target shape are not yet established. ShapeKey.points does not support legacy Curve shape keys; choose accessors for the actual data type.

## Bake animation to an Action — `animation-bake-action`

nla.bake records selected objects' location/scale/rotation animation into an Action; visual_keying uses final transforms including constraints.

Choose when: Record evaluated motion into an Action over a specified frame range.

Search aliases: bake animation, bake constraint, chốt chuyển động thành keyframe, visual keying, bake action

Evidence: `bpy.ops.nla.html#bpy.ops.nla.bake` — Bake transform animation into an Action; visual_keying uses final transforms; document constraint/parent removal and writing to an existing Action.

Read next: `bpy.ops.nla.html#bpy.ops.nla.bake`, `bpy.ops.html`, `bpy.types.Action.html`

Limits: This bakes animation, not necessarily simulation caches. clear_constraints, clear_parents and use_current_action modify existing data; use them only within the requested scope. Check selection, mode, poll and the resulting Action after baking.

## Discover all source pages in this domain

`python3 scripts/features.py pages animation-rigging` lists 119 source cards with pagination. Each card retains its source name and description excerpt. Catalog discovery does not require SQLite.

Source pages remain discoverable even without an authored route. Read their descriptions/definitions before planning; do not supply missing behavior from model knowledge.
