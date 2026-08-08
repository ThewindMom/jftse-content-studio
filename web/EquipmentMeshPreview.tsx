import React, { useEffect, useMemo, useRef, useState } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";

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
  bones?: Array<{ name: string; position: number[] }>;
};

type AniTrack = {
  index: number;
  name: string | null;
  frameCount: number;
  times: number[];
  positions: number[][];
  start?: number[] | null;
  end?: number[] | null;
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
    tracks: AniTrack[];
  };
};

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
  // Prefer name match
  const named = tracks.findIndex(
    (t) => t.name && /racket/i.test(t.name),
  );
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

function sampleTrack(
  track: AniTrack,
  frame: number,
): number[] | null {
  if (!track.positions.length) return null;
  const i = Math.max(0, Math.min(track.positions.length - 1, frame));
  return track.positions[i] ?? null;
}

/**
 * Equipment mesh + Bone_Racket attach pose, optional ANI scrub for live socket sample.
 * RE: Rtm00 AttachBone=Bone_Racket; body DAT stores 4×4 bind pose at socket.
 * matrix4 is D3D/Three column-major (tx @ 12–14) — use Matrix4.fromArray as-is.
 * Live mode samples ANI float3 tracks (not full DX9 quat skinning).
 */
export function EquipmentMeshPreview({
  meshIndex,
  char = "NIKI",
}: {
  meshIndex: string;
  char?: string;
}) {
  const mountRef = useRef<HTMLDivElement | null>(null);
  const racketRef = useRef<THREE.Mesh | null>(null);
  const markerRef = useRef<THREE.Mesh | null>(null);
  const bindMatrixRef = useRef<THREE.Matrix4 | null>(null);
  const restLocalRef = useRef<THREE.Matrix4>(new THREE.Matrix4());
  const [label, setLabel] = useState("Resolving equipment mesh…");
  const [modeBadge, setModeBadge] = useState("bind pose");
  const [ani, setAni] = useState<AniPayload["ani"] | null>(null);
  const [trackIndex, setTrackIndex] = useState(0);
  const [frame, setFrame] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [aniError, setAniError] = useState("");
  const [aniBusy, setAniBusy] = useState(false);
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

  // Load mesh + bind attach
  useEffect(() => {
    let cancelled = false;
    let cleanup: (() => void) | undefined;
    void (async () => {
      try {
        const [meshRes, attachRes] = await Promise.all([
          fetch(
            `/api/item-mesh/resolve?meshIndex=${encodeURIComponent(meshIndex)}&char=${encodeURIComponent(char)}`,
          ),
          fetch(
            `/api/bone-attach?char=${encodeURIComponent(char)}&attachBone=Bone_Racket`,
          ),
        ]);
        const data = (await meshRes.json()) as ResolvedMesh;
        const attachBody = (await attachRes.json()) as BoneAttach;
        if (!meshRes.ok || !data.ok) {
          throw new Error(data.error ?? `HTTP ${meshRes.status}`);
        }
        if (cancelled) return;

        const attach = attachBody.hasAttach ? attachBody.attach : null;
        // Best-effort skin table stats for body (does not block mesh preview)
        let skinNote = "";
        try {
          const skinRes = await fetch(
            `/api/skin/parse?char=${encodeURIComponent(char)}`,
          );
          const skinBody = (await skinRes.json()) as {
            ok?: boolean;
            skin?: { vertexCount?: number; runCount?: number; boneIndexCount?: number };
          };
          if (skinRes.ok && skinBody.ok && skinBody.skin) {
            skinNote = ` · skin ${skinBody.skin.vertexCount ?? "?"}v/${skinBody.skin.runCount ?? "?"} runs/${skinBody.skin.boneIndexCount ?? "?"} bones`;
          }
        } catch {
          /* optional */
        }
        setLabel(
          `${data.resolved.member} · mesh#${data.resolved.index} · ${data.mesh.vertexCount} verts` +
            (attach
              ? ` · socket ${attach.name} (${attach.position.map((v) => v.toFixed(2)).join(", ")})`
              : " · no Bone_Racket (origin fallback)") +
            skinNote +
            (data.resolved.desc ? ` · ${data.resolved.desc}` : ""),
        );
        setModeBadge(attach ? "bind pose" : "origin fallback");

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
        // Prefer equipment material stem from meta when present
        const texCandidates = [
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
        // Capture post-bind matrix as rest for live offsets
        racket.updateMatrix();
        restLocalRef.current.copy(racket.matrix);
        scene.add(racket);
        racketRef.current = racket;

        const box = new THREE.Box3().setFromObject(racket);
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
          racketRef.current = null;
          markerRef.current = null;
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
      cleanup?.();
    };
  }, [meshIndex, char]);

  // Apply live frame to racket + marker
  useEffect(() => {
    const racket = racketRef.current;
    if (!racket || !activeTrack) return;
    const pos = sampleTrack(activeTrack, frame);
    if (!pos) return;
    const start = activeTrack.start ?? activeTrack.positions[0];
    if (!start) return;
    // Delta from track start → apply as translation on rest bind pose
    const dx = pos[0]! - start[0]!;
    const dy = pos[1]! - start[1]!;
    const dz = pos[2]! - start[2]!;
    const rest = restLocalRef.current;
    const delta = new THREE.Matrix4().makeTranslation(dx, dy, dz);
    const composed = rest.clone().multiply(delta);
    racket.matrixAutoUpdate = false;
    racket.matrix.copy(composed);
    racket.matrixWorldNeedsUpdate = true;
    if (markerRef.current) {
      // Same composed matrix origin as the racket root (bind * ANI delta)
      markerRef.current.position.setFromMatrixPosition(composed);
    }
    setModeBadge(playing ? "live scrub" : "scrub");
  }, [activeTrack, frame, playing]);

  // Play loop
  useEffect(() => {
    if (!playing || !ani || frameCount < 2 || reducedMotion) return;
    const fps = frameCount / Math.max(duration, 0.001);
    const interval = Math.max(1000 / Math.min(fps, 60), 16);
    const id = window.setInterval(() => {
      setFrame((f) => (f + 1) % frameCount);
    }, interval);
    return () => window.clearInterval(id);
  }, [playing, ani, frameCount, duration, reducedMotion]);

  const loadAni = async () => {
    setAniBusy(true);
    setAniError("");
    setPlaying(false);
    try {
      // Canonical char → Player folder (matches python/char_player.py + body meshes)
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
        // aliases kept for old UI tokens
        PIKARO: "PlayerE",
        RONA: "PlayerF",
      };
      const charKey = char.toUpperCase();
      const folder = playerMap[charKey] ?? "PlayerA";
      const archive = `Res/Player/${folder}/AniA.res`;
      // Prefer common member names (body mesh stems)
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
      let lastErr = "ANI not found";
      for (const member of members) {
        const res = await fetch(
          `/api/ani/parse?archive=${encodeURIComponent(archive)}&member=${encodeURIComponent(member)}&maxFrames=0`,
        );
        const body = (await res.json()) as AniPayload;
        if (res.ok && body.ok && body.ani) {
          setAni(body.ani);
          // Need attach position — re-fetch light
          const attachRes = await fetch(
            `/api/bone-attach?char=${encodeURIComponent(char)}&attachBone=Bone_Racket`,
          );
          const attachBody = (await attachRes.json()) as BoneAttach;
          const attachPos = attachBody.attach?.position ?? null;
          const idx = pickRacketTrack(body.ani.tracks, attachPos);
          setTrackIndex(idx);
          setFrame(0);
          setModeBadge("scrub");
          setLabel(
            (prev) =>
              `${prev.split(" · ANI")[0]} · ANI ${member} · ${body.ani!.frameCount}f · track ${idx}` +
              (body.ani!.layout ? ` · ${body.ani!.layout}` : ""),
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
        aria-label="Equipment mesh preview"
        style={{ minHeight: 220 }}
      />
      <div className="path-row">
        <span className={`chip ${modeBadge.includes("live") || modeBadge === "scrub" ? "ok" : ""}`}>
          {modeBadge}
        </span>
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
            <label className="inline-label">
              Track
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
      <div className="empty">
        Racket at Bone_Racket bind matrix. ANI scrub applies float3 track delta onto the bind pose
        (not full DX9 quat skinning). Prefer isolated local client for playtest truth.
      </div>
    </div>
  );
}
