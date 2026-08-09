export function managedHarnessBuildPayload(
  profileName: string,
): Record<string, unknown> {
  return {
    name: `Managed Harness ${profileName}`,
    map: {
      draft: {
        name: `Harness ${profileName}`,
        playTime: 180,
        breathTime: 100,
      },
      scenarioIds: [1],
      stageScript: "1_Emerald_Beach.set",
    },
    stage: {
      member: "1_Emerald_Beach.set",
      fields: {},
    },
    ftm: {
      archive: "Res/MapSet/FantaCastle.res",
      member: "FantaCastleOutSide.ftm",
      blockedTiles: [{ x: 2, y: 2 }],
    },
  };
}
