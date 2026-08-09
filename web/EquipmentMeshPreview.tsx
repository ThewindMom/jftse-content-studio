import { useEffect, useMemo, useRef, useState } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import {
  buildSkinnedMesh,
  captureBoneRest,
  driveBonesFromAni,
  resolveDriveMode,
  type BoneRestState,
  type DriveMode,
  type SkinParsePayload,
} from "./skinnedBody";

type ResolvedMesh = {
  ok?: boolean;
  error?: string;
  resolved: {
    archive: string;
    member: string;
    path: string;
    char: string;
    index: string;
    desc: string;
  };
  mesh: {
    positions: number[][];
    indices: number[];
    uvs?: number[][];
    vertexCount: number;
    decodeMode: string;
    materials?: Array<{ name?: string; texCandidate?: string }>;
    confidence?: { solidArea?: number; score?: number };
  };
  equipmentMaterialTable?: {
    count: number;
    stems: string[];
    records?: Array<{ index: number; stem: string; texCandidate: string }>;
  } | null;
  hasMultiMaterial?: boolean;
  silhouette?: {
    mode?: string;
    stemCount?: number;
    stems?: string[];
    note?: string;
  };
};

type BoneAttach = {
  ok?: boolean;
  hasAttach?: boolean;
  attachBone?: string;
  attach?: {
    name: string;
    position: number[];
    matrix4: number[];
  } | null;
  bones?: Array<{ name: string; position: number[]; matrix4?: number[] }>;
  skeleton?: SkinParsePayload["skeleton"];
};

type AniTrack = {
  index: number;
  name: string | null;
  frameCount: number;
  times: number[];
  positions: number[][];
  rotations?: number[][] | null;
  hasRotations?: boolean;
  start?: number[] | null;
  end?: number[] | null;
};

type MotionCatalogEntry = {
  index: number;
  name: string;
  clipIndex: number | null;
  offset?: number | null;
  hasFloat3Clip?: boolean;
};

type AniPayload = {
  ok?: boolean;
  error?: string;
  detail?: string;
  ani?: {
    duration: number;
    frameCount: number;
    trackCount: number;
    layout?: string;
    sampled?: boolean;
    hasRotations?: boolean;
    driveMode?: string;
    rotationSource?: string;
    clipIndex?: number;
    motion?: string;
    motionCatalog?: MotionCatalogEntry[];
    tracks: AniTrack[];
    sectionProbe?: {
      motionCatalog?: MotionCatalogEntry[];
      clientDecoderHypothesis?: {
        motionCatalog?: MotionCatalogEntry[];
      };
    };
  };
};

/** Prefer API motionCatalog; fall back to nested sectionProbe copies. */
export function extractMotionCatalog(
  ani: AniPayload["ani"] | null | undefined,
): MotionCatalogEntry[] {
  if (!ani) return [];
  const nested =
    ani.motionCatalog ??
    ani.sectionProbe?.motionCatalog ??
    ani.sectionProbe?.clientDecoderHypothesis?.motionCatalog ??
    [];
  return nested.filter(
    (m) => m && typeof m.name === "string" && m.name.length > 0,
  );
}

function dist3(a: number[], b: number[]): number {
  const dx = (a[0] ?? 0) - (b[0] ?? 0);
  const dy = (a[1] ?? 0) - (b[1] ?? 0);
  const dz = (a[2] ?? 0) - (b[2] ?? 0);
  return Math.sqrt(dx * dx + dy * dy + dz * dz);
}

function pickRacketTrack(
  tracks: AniTrack[],
  attachPos: number[] | null,
): number {
  const named = tracks.findIndex((t) => t.name && /racket/i.test(t.name));
  if (named >= 0) return named;
  if (!attachPos) return 0;
  let best = 0;
  let bestD = Infinity;
  tracks.forEach((t, i) => {
    const start = t.start ?? t.positions[0];
    if (!start) return;
    const d = dist3(start, attachPos);
    if (d < bestD) {
      bestD = d;
      best = i;
    }
  });
  return best;
}

function sampleTrack(track: AniTrack, frame: number): number[] | null {
  if (!track.positions.length) return null;
  const i = Math.max(0, Math.min(track.positions.length - 1, frame));
  return track.positions[i] ?? null;
}

/**
 * Equipment mesh + body SkinnedMesh (skin/parse + ordered bone palette).
 * ANI drives bones with quats when present, else position-only FK experiment.
 * Racket still places via Bone_Racket bind matrix + optional float3 delta.
 */
export function EquipmentMeshPreview({
  active,
  meshIndex,
  char = "NIKI",
}: {
  active: boolean;
  meshIndex: string;
  char?: string;
}) {
  const mountRef = useRef<HTMLDivElement | null>(null);
  const racketRef = useRef<THREE.Mesh | null>(null);
  const markerRef = useRef<THREE.Mesh | null>(null);
  const skinnedRef = useRef<THREE.SkinnedMesh | null>(null);
  const skeletonBonesRef = useRef<THREE.Bone[]>([]);
  const boneRestRef = useRef<BoneRestState | null>(null);
  const bindMatrixRef = useRef<THREE.Matrix4 | null>(null);
  const restLocalRef = useRef<THREE.Matrix4>(new THREE.Matrix4());
  const [label, setLabel] = useState("Resolving equipment mesh…");
  const [modeBadge, setModeBadge] = useState("bind pose");
  const [driveMode, setDriveMode] = useState<DriveMode>("bind");
  const [ani, setAni] = useState<AniPayload["ani"] | null>(null);
  const [trackIndex, setTrackIndex] = useState(0);
  const [frame, setFrame] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [aniError, setAniError] = useState("");
  const [aniBusy, setAniBusy] = useState(false);
  const [motionName, setMotionName] = useState("");
  const [packBusy, setPackBusy] = useState(false);
  const [packStatus, setPackStatus] = useState("");
  const [packError, setPackError] = useState("");
  const [packDesc, setPackDesc] = useState("Custom racket");
  const [lastInstallPlan, setLastInstallPlan] = useState<
    Array<{ source: string; destRelative: string }>
  >([]);
  const motionCatalog = useMemo(() => extractMotionCatalog(ani), [ani]);
  const reducedMotion =
    typeof window !== "undefined" &&
    window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

  const frameCount = ani?.frameCount ?? 0;
  const duration = ani?.duration ?? 0;
  const activeTrack = ani?.tracks[trackIndex] ?? null;
  const timeLabel = useMemo(() => {
    if (!ani || frameCount < 1) return "—";
    const t = duration * (frame / Math.max(frameCount - 1, 1));
    return `${t.toFixed(3)}s · frame ${frame}/${frameCount - 1}`;
  }, [ani, duration, frame, frameCount]);

  // Load racket mesh + bind attach + body skinned mesh
  useEffect(() => {
    if (!active) return;
    let cancelled = false;
    const controller = new AbortController();
    let cleanup: (() => void) | undefined;
    void (async () => {
      try {
        const [meshRes, attachRes, skinRes] = await Promise.all([
          fetch(
            `/api/item-mesh/resolve?meshIndex=${encodeURIComponent(meshIndex)}&char=${encodeURIComponent(char)}`,
            { signal: controller.signal },
          ),
          fetch(
            `/api/bone-attach?char=${encodeURIComponent(char)}&attachBone=Bone_Racket`,
            { signal: controller.signal },
          ),
          fetch(
            `/api/skin/parse?char=${encodeURIComponent(char)}&includeVertices=1&maxVertices=2000`,
            { signal: controller.signal },
          ),
        ]);
        const data = (await meshRes.json()) as ResolvedMesh;
        const attachBody = (await attachRes.json()) as BoneAttach;
        const skinBody = (await skinRes.json()) as SkinParsePayload;
        if (!meshRes.ok || !data.ok) {
          throw new Error(data.error ?? `HTTP ${meshRes.status}`);
        }
        if (cancelled) return;

        const attach = attachBody.hasAttach ? attachBody.attach : null;
        let skinNote = "";
        if (skinRes.ok && skinBody.ok && skinBody.skin) {
          skinNote =
            ` · skin ${skinBody.skin.vertexCount ?? "?"}v` +
            ` · palette ${skinBody.skeleton?.boneCount ?? "?"} bones` +
            (skinBody.skeletonCoversSkin ? " (covers indices)" : "");
        }
        const stems =
          data.silhouette?.stems ??
          data.equipmentMaterialTable?.stems ??
          data.mesh.materials?.map((m) => m.name).filter(Boolean) ??
          [];
        const matNote =
          stems.length > 0
            ? ` · mats ${stems.slice(0, 4).join(",")}${stems.length > 4 ? "…" : ""}`
            : "";
        setLabel(
          `${data.resolved.member} · mesh#${data.resolved.index} · ${data.mesh.vertexCount} verts` +
            (attach
              ? ` · socket ${attach.name} (${attach.position.map((v) => v.toFixed(2)).join(", ")})`
              : " · no Bone_Racket (origin fallback)") +
            skinNote +
            matNote +
            (data.hasMultiMaterial ? " · multi-mat" : "") +
            (data.resolved.desc ? ` · ${data.resolved.desc}` : ""),
        );
        setModeBadge(attach ? "bind pose" : "origin fallback");
        setDriveMode("bind");

        const mount = mountRef.current;
        if (!mount) return;
        mount.replaceChildren();
        const scene = new THREE.Scene();
        scene.background = new THREE.Color(0x0b1020);
        const camera = new THREE.PerspectiveCamera(
          45,
          mount.clientWidth / Math.max(mount.clientHeight, 1),
          0.01,
          5000,
        );
        const renderer = new THREE.WebGLRenderer({ antialias: true });
        renderer.setPixelRatio(window.devicePixelRatio || 1);
        renderer.setSize(mount.clientWidth, mount.clientHeight);
        mount.appendChild(renderer.domElement);
        const controls = new OrbitControls(camera, renderer.domElement);
        controls.enableDamping = true;
        scene.add(new THREE.HemisphereLight(0xffffff, 0x223344, 1.15));
        const dir = new THREE.DirectionalLight(0xffffff, 0.95);
        dir.position.set(4, 8, 3);
        scene.add(dir);
        const fill = new THREE.DirectionalLight(0x88aaff, 0.25);
        fill.position.set(-6, 2, -4);
        scene.add(fill);
        scene.add(new THREE.AxesHelper(2));

        // Body SkinnedMesh from skin vertices + ordered bone palette
        let skinnedDispose: (() => void) | undefined;
        if (skinRes.ok && skinBody.ok) {
          const built = buildSkinnedMesh(skinBody);
          if (built) {
            scene.add(built.mesh);
            skinnedRef.current = built.mesh;
            skeletonBonesRef.current = built.bones;
            boneRestRef.current = captureBoneRest(
              built.bones,
              built.parentIndex,
            );
            skinnedDispose = () => {
              built.mesh.geometry.dispose();
              const mat = built.mesh.material;
              if (Array.isArray(mat)) mat.forEach((m) => m.dispose());
              else mat.dispose();
            };
          }
        }

        if (attach?.position) {
          const marker = new THREE.Mesh(
            new THREE.SphereGeometry(0.12, 14, 14),
            new THREE.MeshStandardMaterial({
              color: 0xff6688,
              emissive: 0x441122,
            }),
          );
          marker.position.set(
            attach.position[0]!,
            attach.position[1]!,
            attach.position[2]!,
          );
          scene.add(marker);
          markerRef.current = marker;
        } else {
          markerRef.current = null;
        }

        // Racket equipment mesh at Bone_Racket
        const geometry = new THREE.BufferGeometry();
        const positions = new Float32Array(data.mesh.positions.length * 3);
        data.mesh.positions.forEach((p, i) => {
          positions[i * 3] = p[0]!;
          positions[i * 3 + 1] = p[1]!;
          positions[i * 3 + 2] = p[2]!;
        });
        geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
        if (data.mesh.uvs && data.mesh.uvs.length === data.mesh.positions.length) {
          const uvs = new Float32Array(data.mesh.uvs.length * 2);
          data.mesh.uvs.forEach((uv, i) => {
            uvs[i * 2] = uv[0]!;
            uvs[i * 2 + 1] = uv[1]!;
          });
          geometry.setAttribute("uv", new THREE.BufferAttribute(uvs, 2));
        }
        if (data.mesh.indices.length >= 3) geometry.setIndex(data.mesh.indices);
        geometry.computeVertexNormals();
        geometry.computeBoundingBox();
        const material = new THREE.MeshStandardMaterial({
          color: 0xc0c8d8,
          metalness: 0.28,
          roughness: 0.42,
          side: THREE.DoubleSide,
        });
        const stem = data.resolved.member.replace(/\.dat$/i, "");
        // Prefer equipment material table stems (positional Tex keys) for silhouette.
        const equipStems =
          data.equipmentMaterialTable?.records?.map((r) => r.texCandidate) ??
          data.equipmentMaterialTable?.stems?.map((s) => `${s}.tex`) ??
          data.silhouette?.stems?.map((s) => (s.endsWith(".tex") ? s : `${s}.tex`)) ??
          [];
        const texCandidates = [
          ...equipStems,
          ...(data.mesh.materials ?? [])
            .map((m) => m.texCandidate)
            .filter((x): x is string => Boolean(x)),
          `${stem}00.tex`,
          `${stem}.tex`,
        ];
        const tryTex = (i: number) => {
          if (i >= texCandidates.length) return;
          const member = texCandidates[i]!;
          new THREE.TextureLoader().load(
            `/api/mesh-studio/texture?archive=${encodeURIComponent(data.resolved.archive)}&member=${encodeURIComponent(member)}`,
            (map) => {
              if (cancelled) {
                map.dispose();
                return;
              }
              map.colorSpace = THREE.SRGBColorSpace;
              map.anisotropy = 4;
              material.map = map;
              material.color.set(0xffffff);
              material.needsUpdate = true;
            },
            undefined,
            () => tryTex(i + 1),
          );
        };
        tryTex(0);

        const racket = new THREE.Mesh(geometry, material);
        restLocalRef.current.identity();
        if (attach?.matrix4 && attach.matrix4.length === 16) {
          const m = new THREE.Matrix4().fromArray(attach.matrix4);
          bindMatrixRef.current = m.clone();
          racket.applyMatrix4(m);
        } else if (attach?.position) {
          racket.position.set(
            attach.position[0]!,
            attach.position[1]!,
            attach.position[2]!,
          );
          bindMatrixRef.current = null;
        } else {
          bindMatrixRef.current = null;
        }
        racket.updateMatrix();
        restLocalRef.current.copy(racket.matrix);
        scene.add(racket);
        racketRef.current = racket;

        const focusObj = skinnedRef.current ?? racket;
        const box = new THREE.Box3().setFromObject(focusObj);
        const center = new THREE.Vector3();
        const size = new THREE.Vector3();
        box.getCenter(center);
        box.getSize(size);
        const radius = Math.max(size.x, size.y, size.z, 0.5);
        controls.target.copy(center);
        const distance = radius * 2.6;
        camera.position.set(
          center.x + distance * 0.7,
          center.y + distance * 0.45,
          center.z + distance * 0.9,
        );
        camera.near = Math.max(radius / 500, 0.01);
        camera.far = Math.max(radius * 40, 200);
        camera.updateProjectionMatrix();

        let raf = 0;
        const tick = () => {
          controls.update();
          renderer.render(scene, camera);
          raf = requestAnimationFrame(tick);
        };
        tick();
        cleanup = () => {
          cancelAnimationFrame(raf);
          controls.dispose();
          renderer.dispose();
          geometry.dispose();
          material.dispose();
          skinnedDispose?.();
          racketRef.current = null;
          markerRef.current = null;
          skinnedRef.current = null;
          skeletonBonesRef.current = [];
          boneRestRef.current = null;
          mount.replaceChildren();
        };
      } catch (err) {
        if (!cancelled) {
          setLabel(err instanceof Error ? err.message : String(err));
        }
      }
    })();
    return () => {
      cancelled = true;
      controller.abort();
      cleanup?.();
    };
  }, [active, meshIndex, char]);

  // Apply live frame: skeleton hierarchical drive + racket delta
  useEffect(() => {
    if (!active) return;
    const bones = skeletonBonesRef.current;
    const boneRest = boneRestRef.current;
    if (ani && bones.length > 0 && boneRest) {
      const mode = resolveDriveMode(ani.hasRotations, { hierarchical: true });
      const applied = driveBonesFromAni(
        bones,
        ani.tracks,
        frame,
        mode,
        boneRest,
      );
      setDriveMode(applied);
      const live = playing ? "live " : "";
      if (applied === "quat") setModeBadge(`${live}quat FK`.trim());
      else if (applied === "hierarchical-fk")
        setModeBadge(`${live}hierarchical FK`.trim());
      else if (applied === "position-only-fk")
        setModeBadge(`${live}pos-only FK`.trim());
      else setModeBadge("bind pose");
      skinnedRef.current?.skeleton.bones.forEach((b) => b.updateMatrixWorld(true));
    }

    const racket = racketRef.current;
    if (!racket || !activeTrack) return;
    const pos = sampleTrack(activeTrack, frame);
    if (!pos) return;
    const start = activeTrack.start ?? activeTrack.positions[0];
    if (!start) return;
    const dx = pos[0]! - start[0]!;
    const dy = pos[1]! - start[1]!;
    const dz = pos[2]! - start[2]!;
    const restLocal = restLocalRef.current;
    const delta = new THREE.Matrix4().makeTranslation(dx, dy, dz);
    const composed = restLocal.clone().multiply(delta);
    racket.matrixAutoUpdate = false;
    racket.matrix.copy(composed);
    racket.matrixWorldNeedsUpdate = true;
    if (markerRef.current) {
      markerRef.current.position.setFromMatrixPosition(composed);
    }
  }, [active, activeTrack, frame, playing, ani]);

  useEffect(() => {
    if (!active || !playing || !ani || frameCount < 2 || reducedMotion) return;
    const fps = frameCount / Math.max(duration, 0.001);
    const interval = Math.max(1000 / Math.min(fps, 60), 16);
    const id = window.setInterval(() => {
      setFrame((f) => (f + 1) % frameCount);
    }, interval);
    return () => window.clearInterval(id);
  }, [active, playing, ani, frameCount, duration, reducedMotion]);

  const loadAni = async (motionOverride?: string) => {
    setAniBusy(true);
    setAniError("");
    setPlaying(false);
    try {
      const playerMap: Record<string, string> = {
        NIKI: "PlayerA",
        LUN: "PlayerB",
        LUNLUN: "PlayerB",
        DHAN: "PlayerC",
        DHANPIR: "PlayerC",
        LUCY: "PlayerD",
        SHUA: "PlayerE",
        POCHI: "PlayerF",
        AL: "PlayerG",
        PIKARO: "PlayerE",
        RONA: "PlayerF",
      };
      const charKey = char.toUpperCase();
      const folder = playerMap[charKey] ?? "PlayerA";
      const archive = `Res/Player/${folder}/AniA.res`;
      const stemByFolder: Record<string, string> = {
        PlayerA: "Niki",
        PlayerB: "LunLun",
        PlayerC: "Dhanpir",
        PlayerD: "Lucy",
        PlayerE: "Shua",
        PlayerF: "Pochi",
        PlayerG: "Al",
      };
      const stem = stemByFolder[folder] ?? "Niki";
      const members = [`${stem}AniA.ani`, "NikiAniA.ani"];
      const motion = (motionOverride ?? motionName).trim() || "Rootidle.ani";
      let lastErr = "ANI not found";
      for (const member of members) {
        const qs = new URLSearchParams({
          archive,
          member,
          maxFrames: "0",
          char,
          motion,
        });
        const res = await fetch(`/api/ani/parse?${qs.toString()}`);
        const body = (await res.json()) as AniPayload;
        if (res.ok && body.ok && body.ani) {
          setAni(body.ani);
          const catalog = extractMotionCatalog(body.ani);
          const resolved =
            body.ani.motion ??
            catalog.find((m) => m.clipIndex === body.ani!.clipIndex)?.name ??
            motion;
          setMotionName(resolved);
          const attachRes = await fetch(
            `/api/bone-attach?char=${encodeURIComponent(char)}&attachBone=Bone_Racket`,
          );
          const attachBody = (await attachRes.json()) as BoneAttach;
          const attachPos = attachBody.attach?.position ?? null;
          const idx = pickRacketTrack(body.ani.tracks, attachPos);
          setTrackIndex(idx);
          setFrame(0);
          const mode = resolveDriveMode(body.ani.hasRotations, {
            hierarchical: true,
          });
          setDriveMode(mode);
          const rotSrc = body.ani.rotationSource;
          setModeBadge(
            mode === "quat"
              ? rotSrc === "hierarchical-derived"
                ? "derived-quat scrub"
                : "quat scrub"
              : mode === "hierarchical-fk"
                ? "hierarchical FK scrub"
                : "pos-only FK scrub",
          );
          const motionLabel = resolved ? ` · motion ${resolved}` : "";
          setLabel(
            (prev) =>
              `${prev.split(" · ANI")[0]} · ANI ${member}${motionLabel} · ${body.ani!.frameCount}f · clip ${body.ani!.clipIndex ?? 0} · track ${idx}` +
              (body.ani!.layout ? ` · ${body.ani!.layout}` : "") +
              ` · drive ${body.ani!.driveMode ?? mode}`,
          );
          setAniBusy(false);
          return;
        }
        lastErr = body.detail ?? body.error ?? `HTTP ${res.status}`;
      }
      setAniError(lastErr);
      setAni(null);
    } catch (err) {
      setAniError(err instanceof Error ? err.message : String(err));
      setAni(null);
    } finally {
      setAniBusy(false);
    }
  };

  return (
    <div className="equipment-preview">
      <div
        className="mesh-viewport equipment-viewport"
        ref={mountRef}
        aria-label="Equipment and skinned body preview"
        style={{ minHeight: 220 }}
      />
      <div className="path-row">
        <span
          className={`chip ${modeBadge.includes("live") || modeBadge.includes("scrub") || modeBadge.includes("FK") ? "ok" : ""}`}
        >
          {modeBadge}
        </span>
        <span className="chip">{driveMode}</span>
        <div className="mono empty">{label}</div>
      </div>
      <div className="actions">
        <button
          className="btn"
          type="button"
          disabled={aniBusy}
          onClick={() => void loadAni()}
        >
          {aniBusy ? "Loading ANI…" : "Load character ANI"}
        </button>
        {ani && (
          <>
            <button
              className="btn primary"
              type="button"
              disabled={reducedMotion}
              onClick={() => setPlaying((p) => !p)}
            >
              {playing ? "Pause" : "Play"}
            </button>
            {motionCatalog.length > 0 && (
              <label className="inline-label">
                Motion
                <select
                  value={motionName}
                  disabled={aniBusy}
                  aria-label="Named multi-clip motion"
                  onChange={(e) => {
                    const next = e.target.value;
                    setMotionName(next);
                    void loadAni(next);
                  }}
                >
                  {motionCatalog.map((m) => (
                    <option key={`${m.index}-${m.name}`} value={m.name}>
                      {m.name.replace(/\.ani$/i, "")}
                      {m.clipIndex != null ? ` (#${m.clipIndex})` : ""}
                    </option>
                  ))}
                </select>
              </label>
            )}
            <label className="inline-label">
              Bone track
              <select
                value={trackIndex}
                onChange={(e) => {
                  setTrackIndex(Number(e.target.value));
                  setFrame(0);
                }}
              >
                {ani.tracks.map((t) => (
                  <option key={t.index} value={t.index}>
                    #{t.index}
                    {t.name ? ` ${t.name}` : ""}
                  </option>
                ))}
              </select>
            </label>
          </>
        )}
      </div>
      {ani && (
        <label>
          Scrub · {timeLabel}
          <input
            type="range"
            min={0}
            max={Math.max(frameCount - 1, 0)}
            value={frame}
            onChange={(e) => {
              setPlaying(false);
              setFrame(Number(e.target.value));
            }}
            aria-label="Animation frame scrubber"
          />
        </label>
      )}
      {aniError && (
        <div className="mono" style={{ color: "var(--danger)" }} role="alert">
          {aniError}
        </div>
      )}
      <div className="field-grid" style={{ marginTop: 12 }}>
        <label>
          Custom item name
          <input
            value={packDesc}
            onChange={(e) => setPackDesc(e.target.value)}
            aria-label="Custom equipment name"
          />
        </label>
      </div>
      <div className="actions">
        <button
          className="btn primary"
          type="button"
          disabled={packBusy || !meshIndex}
          onClick={() => {
            void (async () => {
              setPackBusy(true);
              setPackError("");
              setPackStatus("Building equipment pack…");
              try {
                const res = await fetch("/api/equipment/pack", {
                  method: "POST",
                  headers: { "content-type": "application/json" },
                  body: JSON.stringify({
                    meshIndex,
                    char,
                    desc: packDesc,
                    part: "Racket",
                  }),
                });
                const body = (await res.json()) as {
                  ok?: boolean;
                  error?: string;
                  sql?: string;
                  newIndex?: number;
                  installPlan?: Array<{ source: string; destRelative: string }>;
                  outDir?: string;
                };
                if (!res.ok || !body.ok) {
                  throw new Error(body.error ?? `HTTP ${res.status}`);
                }
                setLastInstallPlan(body.installPlan ?? []);
                setPackStatus(
                  `Pack ready · newIndex ${body.newIndex} · ${body.outDir} · SQL ${body.sql}`,
                );
              } catch (err) {
                setPackError(err instanceof Error ? err.message : String(err));
                setPackStatus("Pack failed");
              } finally {
                setPackBusy(false);
              }
            })();
          }}
        >
          {packBusy ? "Packing…" : "Pack equipment (mesh + catalog + SQL)"}
        </button>
        <button
          className="btn primary"
          type="button"
          disabled={packBusy || lastInstallPlan.length === 0}
          onClick={() => {
            void (async () => {
              setPackBusy(true);
              setPackError("");
              setPackStatus("Installing equipment pack to local client…");
              try {
                const res = await fetch("/api/client/install", {
                  method: "POST",
                  headers: { "content-type": "application/json" },
                  body: JSON.stringify({ files: lastInstallPlan }),
                });
                const body = (await res.json()) as {
                  ok?: boolean;
                  error?: string;
                  installed?: Record<string, string>;
                };
                if (!res.ok || !body.ok) {
                  throw new Error(body.error ?? `HTTP ${res.status}`);
                }
                setPackStatus(
                  `Installed · ${Object.keys(body.installed ?? {}).join(", ")}`,
                );
              } catch (err) {
                setPackError(err instanceof Error ? err.message : String(err));
                setPackStatus("Install failed");
              } finally {
                setPackBusy(false);
              }
            })();
          }}
        >
          Install pack to local client
        </button>
      </div>
      {packStatus && <div className="empty mono">{packStatus}</div>}
      {packError && (
        <div className="mono" style={{ color: "var(--danger)" }} role="alert">
          {packError}
        </div>
      )}
      <div className="empty">
        Body: SkinnedMesh from /api/skin/parse + ordered 304-byte bone palette.
        ANI drive: <code>quat</code> with <code>rotationSource=hierarchical-derived</code>{" "}
        unit local rotations from named float3 multi-clips + skeleton (when char is set);
        else runtime <code>hierarchical-fk</code>. On-disk dense float4 / section-B still unrecovered
        (see <code>/api/ani/section-b-status</code>). Racket: Bone_Racket + equipment material table
        stems when present. Authoring: pack + catalog + SQL; local install only. Pixel-true multi-submesh
        DX9 silhouette remains best-effort recovery, not a full FVF material graph.
      </div>
    </div>
  );
}
