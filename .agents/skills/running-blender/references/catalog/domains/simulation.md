# Simulation, physics and caches

Select by purpose and evidence below. Identify a route/source card before querying SQLite or proposing API identifiers.

## Rigid body simulation — `rigid-body-simulation`

RigidBodyObject stores participant settings; RigidBodyWorld contains the simulation environment, participating collection, substeps and solver iterations.

Choose when: Simulate objects with the Rigid Body system, collision settings and a shared environment.

Search aliases: rigid body, vật thể rắn, vật rơi va chạm, rigid collision, mô phỏng va chạm

Evidence: `bpy.types.RigidBodyObject.html#bpy.types.RigidBodyObject` — Store rigid-body participant settings including collision shape and damping.; `bpy.types.RigidBodyWorld.html#bpy.types.RigidBodyWorld` — Define a self-contained environment; collection selects participants, while solver_iterations and substeps_per_frame trade accuracy for speed.; `bpy.ops.rigidbody.html#bpy.ops.rigidbody.object_add` — Add the active object as a Rigid Body.

Read next: `bpy.types.RigidBodyObject.html`, `bpy.types.RigidBodyWorld.html`, `bpy.types.PointCache.html`, `bpy.ops.ptcache.html`

Limits: Creating settings does not mean simulation has run or caches have been baked. Check the participating collection, collision shapes, frame range, runtime and evaluated results.

## Rigid body constraints — `rigid-body-joints`

RigidBodyConstraint affects objects in Rigid Body Simulation, with an impulse breaking threshold and angular limits.

Choose when: Create physical constraints between rigid-body simulation participants.

Search aliases: rigid body constraint, khớp vật lý, giới hạn góc vật lý, ràng buộc có thể đứt, physics joints

Evidence: `bpy.types.RigidBodyConstraint.html#bpy.types.RigidBodyConstraint` — Constrain rigid-body objects; breaking_threshold is the breaking impulse and angular limits are available.

Read next: `bpy.types.RigidBodyConstraint.html`, `bpy.ops.rigidbody.html`, `bpy.types.RigidBodyWorld.html`

Limits: These are distinct from pose/object transform constraints. The route name does not verify joint types, endpoints or a working simulation; read type and probe.

## Cloth simulation and collision — `cloth-simulation`

ClothSettings defines cloth simulation parameters including bending stiffness; ClothCollisionSettings manages self-collision and collisions with other objects.

Choose when: Use Cloth simulation and adjust its collision response.

Search aliases: cloth, vải, rèm, mô phỏng vải, cloth collision, self collision

Evidence: `bpy.types.ClothSettings.html#bpy.types.ClothSettings` — Define cloth bending models, stiffness and damping.; `bpy.types.ClothCollisionSettings.html#bpy.types.ClothCollisionSettings` — Configure self-collision and object collision; collision_quality trades time for quality.

Read next: `bpy.types.ClothModifier.html`, `bpy.types.ClothSettings.html`, `bpy.types.ClothCollisionSettings.html`, `bpy.types.PointCache.html`

Limits: A curtain keyword identifies a Cloth candidate; the source does not supply a curtain recipe or real-world material parameters. Verify modifiers, geometry, caches and output frames; settings alone are not simulation proof.

## Soft body simulation — `soft-body-simulation`

SoftBodySettings exposes soft-body simulation settings including bending stiffness, collision damping and aerodynamic interaction.

Choose when: Simulate an object with the Soft Body system.

Search aliases: soft body, vật thể mềm, mô phỏng đàn hồi, soft body collision

Evidence: `bpy.types.SoftBodySettings.html#bpy.types.SoftBodySettings` — Define object soft-body settings including bending stiffness, collision damping and aerodynamic interaction.

Read next: `bpy.types.SoftBodyModifier.html`, `bpy.types.SoftBodySettings.html`, `bpy.types.PointCache.html`

Limits: The settings API does not provide suitable physical parameters for every material or topology. Verify modifiers, colliders, frame evaluation and caches before claiming a working effect.

## Liquid fluid simulation — `fluid-liquid-simulation`

FluidDomainSettings provides a LIQUID domain; FluidFlowSettings provides LIQUID flow with inflow, outflow or geometry behavior.

Choose when: Explore liquid simulation using a Fluid domain and flow.

Search aliases: chất lỏng, nước, liquid, fluid simulation, inflow, outflow

Evidence: `bpy.types.FluidDomainSettings.html#bpy.types.FluidDomainSettings.domain_type` — LIQUID creates a liquid domain; GAS creates a gas domain.; `bpy.types.FluidFlowSettings.html#bpy.types.FluidFlowSettings` — flow_type=LIQUID adds liquid; flow_behavior includes INFLOW, OUTFLOW and GEOMETRY; flow_source lists only NONE.; `bpy.ops.fluid.html#bpy.ops.fluid.bake_all` — bake_all bakes the entire Fluid Simulation.

Read next: `bpy.types.FluidModifier.html`, `bpy.types.FluidDomainSettings.html`, `bpy.types.FluidFlowSettings.html`, `bpy.types.FluidEffectorSettings.html`, `bpy.ops.fluid.html`

Limits: flow_source lists only NONE in this snapshot; do not invent additional enums from memory. Domain/flow configuration does not create a simulation or baked water surface; inspect baking, caches and actual results. A water keyword does not establish a need for simulation; compare supported geometry/material routes for still-image requirements.

## Smoke and fire simulation — `fluid-smoke-fire-simulation`

Fluid provides a GAS domain and SMOKE, FIRE or BOTH flow; domain parameters control density/heat buoyancy and combustion rate.

Choose when: Simulate smoke or fire over time using Fluid.

Search aliases: khói, lửa, smoke, fire, gas simulation, fire and smoke

Evidence: `bpy.types.FluidDomainSettings.html#bpy.types.FluidDomainSettings.domain_type` — GAS creates a gas domain.; `bpy.types.FluidFlowSettings.html#bpy.types.FluidFlowSettings.flow_type` — SMOKE adds smoke, FIRE adds fire and BOTH adds both.; `bpy.types.FluidDomainSettings.html#bpy.types.FluidDomainSettings` — alpha and beta control buoyancy from smoke density/heat; burning_rate controls combustion rate.

Read next: `bpy.types.FluidModifier.html`, `bpy.types.FluidDomainSettings.html`, `bpy.types.FluidFlowSettings.html`, `bpy.ops.fluid.html`

Limits: Simulation parameters alone do not establish shading or flame appearance. Current build support, completed baking and valid caches are unverified; probe and inspect outputs.

## Physics force fields — `physics-force-fields`

FieldSettings.type distinguishes WIND along local Z, TURBULENCE noise, VORTEX rotation and DRAG that reduces movement.

Choose when: Select a candidate force for a compatible simulation system.

Search aliases: gió, trường lực, wind, force field, turbulence, vortex, lực cản

Evidence: `bpy.types.FieldSettings.html#bpy.types.FieldSettings.type` — Describe WIND, TURBULENCE, VORTEX, DRAG and other force-field enum values.

Read next: `bpy.types.FieldSettings.html`, `bpy.types.EffectorWeights.html`

Limits: Do not assume every object responds to FieldSettings; read the target simulation and effector weights. WIND is described along local Z; inspect transforms and results instead of assuming a world axis.

## Dynamic Paint canvas and brush — `dynamic-paint-canvas`

DynamicPaintSurface is a canvas surface layer with a brush collection, influence and wet-paint color spreading speed.

Choose when: Explore Dynamic Paint brush/canvas interaction.

Search aliases: dynamic paint, vệt sơn, canvas, brush simulation, wet paint, sơn động

Evidence: `bpy.types.DynamicPaintSurface.html#bpy.types.DynamicPaintSurface` — A canvas surface selects brushes with brush_collection and controls wet-paint mixing with color_spread_speed.; `bpy.types.DynamicPaintSurface.html#bpy.types.DynamicPaintSurface.surface_type` — The snapshot's surface_type enum contains only PAINT.

Read next: `bpy.types.DynamicPaintModifier.html`, `bpy.types.DynamicPaintCanvasSettings.html`, `bpy.types.DynamicPaintBrushSettings.html`, `bpy.types.DynamicPaintSurface.html`, `bpy.ops.dpaint.html`

Limits: surface_type lists only PAINT in this snapshot; do not supply other modes from memory. These parameters do not provide a complete paint-trail or baking recipe; read modifier/settings contracts and verify the runtime.

## Particle system settings — `particle-system-settings`

ParticleSettings can be shared across particle systems; the snapshot's type enum includes EMITTER and HAIR.

Choose when: Control a Particle System identified in the supplied source or scene.

Search aliases: particle, hệ hạt, particle emitter, particle hair, phát hạt

Evidence: `bpy.types.ParticleSettings.html#bpy.types.ParticleSettings` — Settings can be reused by multiple particle systems.; `bpy.types.ParticleSettings.html#bpy.types.ParticleSettings.type` — type includes EMITTER and HAIR; the anchor does not explain their workflows.

Read next: `bpy.types.ParticleSettings.html`, `bpy.types.ParticleSystem.html`, `bpy.types.PointCache.html`

Limits: Do not equate particle HAIR with all hair systems or Geometry Nodes; read the correct data type. EMITTER/HAIR establish enum values, not motion, rendering or cache recipes for a particular effect.

## Physics cache baking and inspection — `physics-cache-baking`

PointCache exposes physics cache paths, frame ranges and is_baked/is_baking; ptcache.bake is a physics baking operator.

Choose when: Execute or verify caches for a simulation using PointCache.

Search aliases: bake physics, cache mô phỏng, bake cache, point cache, kiểm tra cache

Evidence: `bpy.types.PointCache.html#bpy.types.PointCache` — PointCache is the active physics cache, with filepath, frame_start/end, is_baked/is_baking and skipped-frame status.; `bpy.ops.ptcache.html#bpy.ops.ptcache.bake` — The operator is described as Bake physics.; `bpy.ops.fluid.html#bpy.ops.fluid.bake_all` — Fluid has a separate operator for baking the entire simulation.

Read next: `bpy.types.PointCache.html`, `bpy.ops.ptcache.html`, `bpy.ops.html`

Limits: ptcache.bake is not universal; Fluid has separate baking operators. Distinguish FINISHED, is_baked and actual cache/frame data; no single signal proves the complete result.

## Discover all source pages in this domain

`python3 scripts/features.py pages simulation` lists 58 source cards with pagination. Each card retains its source name and description excerpt. Catalog discovery does not require SQLite.

Source pages remain discoverable even without an authored route. Read their descriptions/definitions before planning; do not supply missing behavior from model knowledge.
