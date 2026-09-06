# Motion tracking and movie clips

Select by purpose and evidence below. Identify a route/source card before querying SQLite or proposing API identifiers.

## Movie clip marker tracking — `movie-clip-marker-tracking`

MovieTracking holds match-moving data; bpy.ops.clip.track_markers tracks selected markers backward or across a sequence rather than one image.

Choose when: Track markers in footage; inspect clip/tracking data before invoking the operator.

Search aliases: tracking marker, theo dõi điểm, motion tracking, track markers, theo dõi footage

Evidence: `bpy.types.MovieTracking.html#bpy.types.MovieTracking` — Expose match-moving data for tracking.; `bpy.ops.clip.html#bpy.ops.clip.track_markers` — Track selected markers backward or across a sequence.

Read next: `bpy.types.MovieClip.html`, `bpy.types.MovieTracking.html`, `bpy.types.MovieTrackingTracks.html`, `bpy.ops.clip.html#bpy.ops.clip.track_markers`

Limits: Marker tracking is not arbitrary object recognition. It requires suitable context and selection; do not promise background CLI operation without a successful poll in that context.

## Marker-based 2D footage stabilization — `movie-clip-two-dimensional-stabilization`

MovieTrackingStabilization stabilizes footage in 2D using markers, with location/rotation/scale influence, an anchor frame and automatic scaling to cover gaps.

Choose when: Stabilize 2D footage using existing tracking data.

Search aliases: ổn định video, chống rung, 2D stabilization, stabilize footage, marker stabilization

Evidence: `bpy.types.MovieTrackingStabilization.html#bpy.types.MovieTrackingStabilization` — Describe marker-based 2D stabilization with anchor frame, location/rotation/scale and autoscale.

Read next: `bpy.types.MovieTrackingStabilization.html`, `bpy.types.MovieTracking.html`, `bpy.types.CompositorNodeStabilize.html`

Limits: This does not establish correction of all shake or rolling shutter. Suitable tracks and output checks are required; the route does not automatically create tracking input.

## Camera motion solving from tracks — `camera-motion-solve-from-tracks`

bpy.ops.clip.solve_camera solves camera motion from tracks. MovieTrackingReconstruction stores solved cameras, average_error and is_valid.

Choose when: Solve camera motion from existing tracks and inspect reconstruction validity/error.

Search aliases: camera tracking, solve camera, match moving, giải camera, khôi phục chuyển động camera

Evidence: `bpy.ops.clip.html#bpy.ops.clip.solve_camera` — Solve camera motion from tracks.; `bpy.types.MovieTrackingReconstruction.html#bpy.types.MovieTrackingReconstruction` — Expose reconstruction cameras, average_error and is_valid.

Read next: `bpy.ops.clip.html#bpy.ops.clip.solve_camera`, `bpy.types.MovieTrackingReconstruction.html`, `bpy.types.MovieTrackingSettings.html`, `bpy.types.MovieTrackingCamera.html`

Limits: The source does not guarantee a solve for all footage or supply complete calibration/background-context requirements. Report success only when the actual operator and reconstruction support it.

## Discover all source pages in this domain

`python3 scripts/features.py pages tracking` lists 30 source cards with pagination. Each card retains its source name and description excerpt. Catalog discovery does not require SQLite.

Source pages remain discoverable even without an authored route. Read their descriptions/definitions before planning; do not supply missing behavior from model knowledge.
