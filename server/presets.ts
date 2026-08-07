export type EffectPreset = {
  id: string;
  name: string;
  summary: string;
  effect: Record<string, unknown>;
};

export const EFFECT_PRESETS: EffectPreset[] = [
  {
    id: "soft-full-racket",
    name: "Soft full-racket wind",
    summary: "Cyan feather wisps around the whole racket (current proven default).",
    effect: {
      texturePath: "Res/Effect/EftB/A_feather",
      color: "80,160,205",
      quantity: 18,
      speed: 0.3,
      life: 16,
      size: 1.4,
      offAxisSpread: 180,
      offPlaneSpread: 180,
      phase: 180,
      phaseVar: 100,
      subTexSize: "STS_64",
      subTexCount: 8,
      allowBannedAtlas: false,
      includeItemBinding: false,
    },
  },
  {
    id: "sparse-edge-wisps",
    name: "Sparse edge wisps",
    summary: "Fewer, tighter wisps for a quieter Equipment silhouette.",
    effect: {
      texturePath: "Res/Effect/EftB/A_feather",
      color: "75,155,200",
      quantity: 8,
      speed: 0.42,
      life: 10,
      size: 1.2,
      offAxisSpread: 45,
      offPlaneSpread: 20,
      phase: 5,
      phaseVar: 12,
      subTexSize: "STS_64",
      subTexCount: 8,
      allowBannedAtlas: false,
      includeItemBinding: false,
    },
  },
  {
    id: "glitter-cadence",
    name: "Glitter cadence (soft atlas)",
    summary: "Native +9 timing/spread with soft feather cards instead of lightning.",
    effect: {
      texturePath: "Res/Effect/EftB/A_feather",
      color: "90,170,210",
      quantity: 18,
      speed: 0.3,
      life: 18,
      size: 1.5,
      offAxisSpread: 180,
      offPlaneSpread: 180,
      phase: 180,
      phaseVar: 100,
      subTexSize: "STS_64",
      subTexCount: 8,
      allowBannedAtlas: false,
      includeItemBinding: false,
    },
  },
];
