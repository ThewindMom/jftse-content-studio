export type HarnessResult = {
  status: "passed" | "failed";
  ready: boolean;
  timedOut: boolean;
  exitCode: number;
  rolledBack: boolean;
  stdout: string;
  stderr: string;
  capture: { relativePath: string; sha256: string } | null;
  captureDataUrl: string | null;
  before: { sha256: string };
  after: { sha256: string };
};

export function ClientHarnessReceipt({
  result,
}: {
  result: HarnessResult;
}) {
  return (
    <div className="harness-result">
      <dl className="kv">
        <div>
          <dt>Before</dt>
          <dd>{result.before.sha256}</dd>
        </div>
        <div>
          <dt>After</dt>
          <dd>{result.after.sha256}</dd>
        </div>
        <div>
          <dt>Capture</dt>
          <dd>{result.capture?.sha256 ?? "No capture"}</dd>
        </div>
      </dl>
      {result.captureDataUrl && (
        <img alt="Managed client capture" src={result.captureDataUrl} />
      )}
      <details>
        <summary>Process logs</summary>
        <pre>{`${result.stdout}\n${result.stderr}`.trim()}</pre>
      </details>
    </div>
  );
}
