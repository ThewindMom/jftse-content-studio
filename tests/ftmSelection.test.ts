import { describe, expect, test } from "bun:test";
import {
  buildFtmChoices,
  resolveFtmMember,
} from "../web/ftmSelection.ts";

describe("FTM project selection", () => {
  test("normalizes Windows separators and adds the FTM suffix", () => {
    expect(
      buildFtmChoices([
        String.raw`Res\MapSet\FantaCastle\FantaCastleOutSide`,
      ]),
    ).toEqual([
      {
        label: "Res/MapSet/FantaCastle/FantaCastleOutSide.ftm",
        memberCandidate: "FantaCastleOutSide.ftm",
        sourcePath: "Res/MapSet/FantaCastle/FantaCastleOutSide",
      },
    ]);
  });

  test("keeps nested duplicate basenames distinguishable", () => {
    const choices = buildFtmChoices([
      "Res/MapSet/RegionA/Court",
      "Res/MapSet/RegionB/Court.ftm",
    ]);

    expect(choices.map((choice) => choice.label)).toEqual([
      "Res/MapSet/RegionA/Court.ftm",
      "Res/MapSet/RegionB/Court.ftm",
    ]);
    expect(choices.map((choice) => choice.memberCandidate)).toEqual([
      "Court.ftm",
      "Court.ftm",
    ]);
  });

  test("prefers a matching member path before basename fallback", () => {
    const members = [
      "RegionA/Court.ftm",
      "RegionB/Court.ftm",
      "FantaCastleOutSide.FTM",
    ];

    expect(
      resolveFtmMember("Res/MapSet/RegionB/Court", members),
    ).toBe("RegionB/Court.ftm");
    expect(
      resolveFtmMember(
        String.raw`Res\MapSet\FantaCastle\FantaCastleOutSide`,
        members,
      ),
    ).toBe("FantaCastleOutSide.FTM");
  });

  test("does not guess between ambiguous basename matches", () => {
    expect(
      resolveFtmMember("Res/MapSet/Unknown/Court", [
        "RegionA/Court.ftm",
        "RegionB/Court.ftm",
      ]),
    ).toBeNull();
  });

  test("returns an empty picker for an empty project", () => {
    expect(buildFtmChoices([])).toEqual([]);
    expect(resolveFtmMember("Court", [])).toBeNull();
  });
});
