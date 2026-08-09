type MapCreatorPackagePanelProps = {
  missing: string[];
  spawnCount: number;
  packageStatus: string;
  manifest: string;
  onResolve: () => void;
  onExport: () => void;
};

export function MapCreatorPackagePanel({
  missing,
  spawnCount,
  packageStatus,
  manifest,
  onResolve,
  onExport,
}: MapCreatorPackagePanelProps) {
  return (
    <>
      <div className="map-package-panel">
        <div>
          <strong>Dependency graph</strong>
          <p className="status">
            {missing.length === 0
              ? "Design references acknowledged; runtime outputs are verified during build."
              : `${missing.length} design references need acknowledgement before build.`}
          </p>
          <ul className="dependency-list">
            {missing.map((dependency) => (
              <li key={dependency}>{dependency}</li>
            ))}
          </ul>
        </div>
        <div className="actions">
          <button className="btn" onClick={onResolve} type="button">
            Acknowledge design references
          </button>
          <button
            className="btn primary"
            disabled={missing.length > 0 || spawnCount < 2}
            onClick={onExport}
            type="button"
          >
            Build stock-template runtime pack
          </button>
        </div>
      </div>
      {packageStatus && (
        <p className="status" role="status">
          {packageStatus}
        </p>
      )}
      {manifest && (
        <details className="manifest-output" open>
          <summary>Runtime package receipt and design manifest</summary>
          <pre>{manifest}</pre>
        </details>
      )}
    </>
  );
}
