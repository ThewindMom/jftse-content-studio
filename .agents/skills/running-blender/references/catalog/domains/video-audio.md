# Video editing, titles and audio

Select by purpose and evidence below. Identify a route/source card before querying SQLite or proposing API identifiers.

## Sequencer text titles — `sequencer-text-titles`

TextStrip generates text with content, font, size, position, alignment, outline and box properties. StripsTopLevel.new_effect includes TEXT for adding a text strip.

Choose when: Add text over specified intervals in a video sequence.

Search aliases: chữ trong video, tiêu đề video, text strip, video title, phụ đề bằng text

Evidence: `bpy.types.TextStrip.html#bpy.types.TextStrip` — A sequence strip generates text and exposes text-display properties.; `bpy.types.StripsTopLevel.html#bpy.types.StripsTopLevel.new_effect` — The TEXT effect adds a simple text strip.

Read next: `bpy.types.TextStrip.html`, `bpy.types.StripsTopLevel.html#bpy.types.StripsTopLevel.new_effect`, `bpy.types.Scene.html#bpy.types.Scene.sequence_editor_create`

Limits: The source does not establish speech recognition or automatic subtitle timing. The default font falls back to a UI font; inspect the supplied font and required glyph rendering.

## Text strip drop shadow — `sequencer-text-drop-shadow`

TextStrip.use_shadow displays a shadow behind text; the class also exposes shadow_angle, shadow_blur, shadow_color and shadow_offset with types/ranges.

Choose when: Apply a shadow to Video Sequencer text, distinct from 3D shadow rays or footage shadow catchers.

Search aliases: đổ bóng, bóng chữ, đổ bóng chữ, text shadow, text drop shadow, bóng chữ video

Evidence: `bpy.types.TextStrip.html#bpy.types.TextStrip.use_shadow` — Display a shadow behind text.; `bpy.types.TextStrip.html#bpy.types.TextStrip` — TextStrip generates text and exposes shadow parameters with types/ranges.

Read next: `bpy.types.TextStrip.html`, `bpy.types.StripsTopLevel.html#bpy.types.StripsTopLevel.new_effect`

Limits: shadow_blur/offset have type/range information without complete pixel-unit semantics. Do not transfer CSS numbers or 3D light controls by assumption.

## Load and trim sequencer video — `sequencer-load-trim-video`

MovieStrip loads video; StripsTopLevel.new_movie adds a clip by file, channel and frame_start. content_trim_start/end skip source frames and turn corresponding time into holds.

Choose when: Load a clip into the timeline or adjust source content at its ends according to the documented trimming semantics.

Search aliases: dựng video, nạp video, cắt đầu cuối clip, movie strip, trim video, load video

Evidence: `bpy.types.MovieStrip.html#bpy.types.MovieStrip` — A sequence strip loads video; document content trimming and deprecation.; `bpy.types.StripsTopLevel.html#bpy.types.StripsTopLevel.new_movie` — Add a movie strip with filepath, channel and frame_start.

Read next: `bpy.types.MovieStrip.html`, `bpy.types.StripsTopLevel.html#bpy.types.StripsTopLevel.new_movie`, `bpy.types.Strip.html`

Limits: The source marks animation_offset_start/end deprecated since 5.10 in favor of content_trim_start/end. Do not assume source trimming shortens the timeline; read frame ranges and inspect results.

## Timed audio strips and playback volume — `sequencer-timed-sound`

SoundStrip plays audio over an interval; volume controls level, pan applies to mono sources and sound_offset is measured in seconds. StripsTopLevel.new_sound adds a sound strip.

Choose when: Place audio on the timeline and adjust timing, volume or pan as documented.

Search aliases: thêm âm thanh, nhạc nền, sound strip, audio timeline, volume âm thanh, pan âm thanh

Evidence: `bpy.types.SoundStrip.html#bpy.types.SoundStrip` — Describe timed audio, volume, mono pan and sound_offset in seconds.; `bpy.types.StripsTopLevel.html#bpy.types.StripsTopLevel.new_sound` — Add a sound strip from a file at a timeline position.

Read next: `bpy.types.SoundStrip.html`, `bpy.types.StripsTopLevel.html#bpy.types.StripsTopLevel.new_sound`, `bpy.ops.sound.html`

Limits: A sound strip does not establish codec or mixdown support. Pan is limited to mono sources; inspect media and audio output separately.

## Sequencer transitions and effects — `sequencer-transitions-effects`

StripsTopLevel.new_effect describes CROSS fading, WIPE transitions, GLOW on bright regions, SPEED playback time-warping, GAUSSIAN_BLUR detail softening and blending effects.

Choose when: Create timeline strip effects or transitions, selecting types from new_effect descriptions.

Search aliases: chuyển cảnh, crossfade, wipe, video glow, timewarp, đổi tốc độ video, blend strips

Evidence: `bpy.types.StripsTopLevel.html#bpy.types.StripsTopLevel.new_effect` — Describe CROSS, WIPE, GLOW, SPEED, GAUSSIAN_BLUR and blending effects.

Read next: `bpy.types.StripsTopLevel.html#bpy.types.StripsTopLevel.new_effect`, `bpy.types.EffectStrip.html`, `bpy.types.SpeedControlStrip.html`, `bpy.types.WipeStrip.html`

Limits: Read each effect's inputs and settings; do not assume every effect takes two strips or uses older properties. SPEED does not establish optical-flow interpolation.

## Discover all source pages in this domain

`python3 scripts/features.py pages video-audio` lists 66 source cards with pagination. Each card retains its source name and description excerpt. Catalog discovery does not require SQLite.

Source pages remain discoverable even without an authored route. Read their descriptions/definitions before planning; do not supply missing behavior from model knowledge.
