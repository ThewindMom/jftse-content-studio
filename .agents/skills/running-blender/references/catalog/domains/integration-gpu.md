# Python integration, math, GPU and UI

Select by purpose and evidence below. Identify a route/source card before querying SQLite or proposing API identifiers.

## Runtime, build and context inspection — `runtime-build-context-inspection`

bpy.app exposes version, background state and build options; context depends on the accessed area and operators need suitable context.

Choose when: Inspect API, engine and operator availability in the running Blender before CLI implementation.

Search aliases: phiên bản Blender, background, headless, build options, operator poll, kiểm tra runtime

Evidence: `bpy.app.html#bpy.app.version` — version returns a major/minor/micro tuple.; `bpy.app.html#bpy.app.background` — background is True when started without a UI using -b.; `bpy.app.html#bpy.app.build_options` — The snapshot exposes build options including fluid, usd, alembic and cycles.; `bpy.ops.html` — Wrong context may raise RuntimeError; poll helps check it and CANCELLED may not raise.; `bpy.context.html` — Available context members depend on the accessed area.

Read next: `bpy.app.html`, `bpy.ops.html`, `bpy.types.Context.html`

Limits: Documented build_options describe the documentation build; inspect the actual runtime. No exception does not establish success: operators can return CANCELLED without raising.

## Application event handlers — `application-event-handlers`

bpy.app.handlers provides callback lists; persistent retains callbacks when another file is loaded.

Choose when: Run logic on frame events or Blender load/render lifecycle events.

Search aliases: handler, frame change, load post, callback Blender, sự kiện nạp file, sự kiện đổi frame

Evidence: `bpy.app.handlers.html` — Provide callback lists including frame_change_pre/load_post, with warnings about changing data during rendering.; `bpy.app.handlers.html#bpy.app.handlers.persistent` — A decorator retains callbacks across file loads.

Read next: `bpy.app.handlers.html`, `info_gotchas_threading.html`

Limits: Handlers are removed on file load by default; persistent is a separate choice. The source warns that simultaneous handler data changes and render/viewport access can crash; read the warning and choose appropriate synchronization.

## Application timers — `application-timer-callbacks`

bpy.app.timers.register calls a function after a delay; return a float to schedule the next call or None to unregister.

Choose when: Schedule callbacks within a Blender process that remains running.

Search aliases: timer, chạy sau vài giây, callback định kỳ, application timer, lặp callback

Evidence: `bpy.app.timers.html#bpy.app.timers.register` — Register a no-argument function with first_interval in seconds; None unregisters and a float sets the next delay.; `info_gotchas_threading.html` — Python integration is not thread-safe; the source limits threading and discusses multiprocessing for Blender-independent code.

Read next: `bpy.app.timers.html`, `info_gotchas_threading.html`

Limits: Timers do not run after the CLI process exits and are not an external scheduler. Do not substitute remembered Python threads that access Blender data; read the separate threading limitations.

## RNA property message bus — `rna-property-notifications`

bpy.msgbus receives RNA property-change notifications; subscribe_rna registers callbacks for a property or struct/property pair.

Choose when: Respond to property changes made through the Python data API or UI fields.

Search aliases: message bus, msgbus, theo dõi property, RNA notification, property change callback

Evidence: `bpy.msgbus.html` — Receive RNA/Python/UI field changes, excluding animation and viewport movement; callbacks are deferred until after operators.; `bpy.msgbus.html#bpy.msgbus.subscribe_rna` — Subscribe to notifications; file loads clear subscriptions and PERSISTENT preserves ID remapping.

Read next: `bpy.msgbus.html`, `bpy.app.handlers.html`

Limits: Animation and object movement in the 3D Viewport do not trigger msgbus according to the source; select another route for those events. Loading another blend clears subscriptions; msgbus PERSISTENT preserves ID remapping, not file-load subscriptions.

## Custom operators, properties and UI — `custom-operators-properties-ui`

bpy.utils.register_class registers Blender subclasses; bpy.props defines their properties; Panel contains UI elements.

Choose when: Create reusable operators/properties or controls inside Blender.

Search aliases: custom operator, custom property, addon panel, bảng điều khiển, mở rộng Blender, đăng ký class

Evidence: `bpy.utils.html#bpy.utils.register_class` — Register supported subclasses including Operator, Panel, PropertyGroup and Node.; `bpy.props.html` — Define properties for registered classes; avoid direct use and observe callback threading warnings.; `bpy.types.Panel.html#bpy.types.Panel` — Panel contains UI elements; the snapshot leaves context/region/space combinations as a TODO under bl_context.

Read next: `bpy.utils.html#bpy.utils.register_class`, `bpy.props.html`, `bpy.types.Operator.html`, `bpy.types.Panel.html`, `bpy.ops.html`

Limits: A Panel is UI; class creation does not establish display or interaction in background -b. Assign bpy.props results to registered classes rather than using them directly; property callbacks may run in threaded contexts.

## GPU drawing and offscreen buffers — `gpu-drawing-offscreen`

gpu exposes GPU wrappers, geometry batches and GPUOffScreen; the 5.2 source includes gpu.init for background initialization.

Choose when: Draw through the GPU API, process offscreen buffers or render a 3D View into a texture.

Search aliases: GPU offscreen, vẽ GPU, offscreen buffer, shader drawing, GPU batch, viewport texture

Evidence: `gpu.html` — Expose GPU wrappers and geometry batches with vertex/index buffers.; `gpu.html#gpu.init` — Initialize the GPU for background use; failure raises SystemError.; `gpu.types.html#gpu.types.GPUOffScreen` — Access offscreen buffers; draw_view3d needs a scene, view layer, SpaceView3D and Region.; `gpu.shader.html` — Initialize shader uniforms to avoid retaining earlier values.; `gpu.types.html#gpu.types.GPUOffScreen.free` — Freeing offscreen resources makes associated framebuffer, texture and render objects inaccessible.

Read next: `gpu.html`, `gpu.shader.html`, `gpu.types.html#gpu.types.GPUOffScreen`, `gpu_extras.batch.html`

Limits: GPU use is not necessarily UI-only: gpu.init documents background use but may raise SystemError. GPUOffScreen.draw_view3d still requires SpaceView3D and Region; do not assume they exist in -b. Initialize shader uniforms explicitly; freeing offscreen resources makes framebuffer, texture and render objects inaccessible.

## GPU compute shaders — `gpu-compute-dispatch`

GPUShaderCreateInfo accepts GLSL compute source; create_from_info creates a shader; gpu.compute.dispatch runs workgroup dimensions and capabilities reports support.

Choose when: Use compute shaders directly through Blender's GPU API.

Search aliases: compute shader, GPU compute, GLSL compute, dispatch GPU, tính toán GPU

Evidence: `gpu.types.html#gpu.types.GPUShaderCreateInfo.compute_source` — Accept GLSL compute shader source; include examples and an external cross-compilation documentation link.; `gpu.shader.html#gpu.shader.create_from_info` — Create GPUShader from GPUShaderCreateInfo.; `gpu.compute.html#gpu.compute.dispatch` — Dispatch compute work using a shader and x/y/z group counts.; `gpu.capabilities.html#gpu.capabilities.compute_shader_support_get` — Return whether compute shaders are supported.

Read next: `gpu.html#gpu.init`, `gpu.capabilities.html`, `gpu.types.html#gpu.types.GPUShaderCreateInfo`, `gpu.compute.html`

Limits: The name GPU does not establish compute availability; check compute_shader_support_get and initialize the runtime. GLSL cross-compilation documentation is linked outside the corpus; do not fill that missing content from memory. A dispatch API does not prove shader correctness, input/output data, synchronization or numerical results.

## Discover all source pages in this domain

`python3 scripts/features.py pages integration-gpu` lists 404 source cards with pagination. Each card retains its source name and description excerpt. Catalog discovery does not require SQLite.

Source pages remain discoverable even without an authored route. Read their descriptions/definitions before planning; do not supply missing behavior from model knowledge.
