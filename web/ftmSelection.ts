export type FtmChoice = {
  sourcePath: string;
  label: string;
  memberCandidate: string;
};

function normalizePath(path: string): string {
  return path
    .trim()
    .replace(/\\/g, "/")
    .replace(/\/+/g, "/")
    .replace(/^\.?\//, "")
    .replace(/\/$/, "");
}

function withFtmSuffix(path: string): string {
  return /\.ftm$/i.test(path) ? path : `${path}.ftm`;
}

export function buildFtmChoices(paths: readonly string[]): FtmChoice[] {
  return paths
    .map(normalizePath)
    .filter(Boolean)
    .map((sourcePath) => {
      const label = withFtmSuffix(sourcePath);
      return {
        sourcePath,
        label,
        memberCandidate: label.split("/").pop() ?? label,
      };
    });
}

export function resolveFtmMember(
  sourcePath: string,
  archiveMembers: readonly string[],
): string | null {
  const expected = withFtmSuffix(normalizePath(sourcePath)).toLowerCase();
  const candidates = archiveMembers.map((member) => ({
    original: member,
    normalized: normalizePath(member).toLowerCase(),
  }));
  const pathMatches = candidates.filter(({ normalized }) =>
    expected === normalized || expected.endsWith(`/${normalized}`)
  );
  if (pathMatches.length === 1) return pathMatches[0].original;

  const basename = expected.split("/").pop();
  const basenameMatches = candidates.filter(
    ({ normalized }) => normalized.split("/").pop() === basename,
  );
  return basenameMatches.length === 1 ? basenameMatches[0].original : null;
}
