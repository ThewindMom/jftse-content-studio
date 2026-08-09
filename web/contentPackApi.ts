import type {
  ContentPackDraft,
  InstallFile,
  PreflightView,
} from "./ContentPackPanels";

export type ApiRecord = Record<string, unknown>;
export type PackManifest = ApiRecord & {
  outDir?: string;
  installPlan?: InstallFile[];
  sqlPath?: string | null;
};
export type PreflightResult = ApiRecord & PreflightView & {
  preflightPassed?: boolean;
};

export const initialContentPackDraft: ContentPackDraft = {
  name: "designer-pack",
  meshIndex: "214",
  char: "NIKI",
  itemDesc: "Studio Custom Racket",
  mapName: "Studio Custom Court",
  scenarioIds: "1",
  stageScript: "1_Emerald_Beach.set",
  includeFtm: true,
  ftmArchive: "Res/MapSet/FantaCastle.res",
  ftmMember: "FantaCastleOutSide.ftm",
};

export async function contentPackApi<T extends ApiRecord>(
  path: string,
  init?: RequestInit,
): Promise<T> {
  const response = await fetch(path, {
    headers: { "content-type": "application/json" },
    ...init,
  });
  const data = (await response.json()) as T & {
    error?: string;
    detail?: string;
  };
  if (!response.ok) {
    throw new Error(data.detail ?? data.error ?? `HTTP ${response.status}`);
  }
  return data;
}
