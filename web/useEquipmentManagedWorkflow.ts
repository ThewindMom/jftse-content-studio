import { useEffect, useState } from "react";

type ManagedProfile = {
  name: string;
  mode: "pass" | "fail";
};

export type EquipmentBuildWorkflow = {
  packageId: string;
  runtimeReceipt: Record<string, unknown>;
};

export type EquipmentManagedWorkflow = {
  build: EquipmentBuildWorkflow;
  profiles: ManagedProfile[];
  profileName: string;
  confirmation: "install" | "sqlApply" | null;
  install: Record<string, unknown> | null;
  audit: Record<string, unknown> | null;
  sqlApply: Record<string, unknown> | null;
  preflight: Record<string, unknown> | null;
  runtimeFields: Record<string, unknown>;
  status: string;
  error: string;
  busy: boolean;
  setProfileName(name: string): void;
  setConfirmation(value: "install" | "sqlApply" | null): void;
  createProfile(): Promise<void>;
  installPackage(): Promise<void>;
  auditSql(): Promise<void>;
  applySql(): Promise<void>;
  runPreflight(): Promise<void>;
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function message(value: unknown, fallback: string): string {
  return isRecord(value) && typeof value.error === "string"
    ? value.error
    : fallback;
}

async function request(
  path: string,
  init?: RequestInit,
): Promise<Record<string, unknown>> {
  const response = await fetch(path, init);
  const body: unknown = await response.json();
  if (!response.ok || !isRecord(body)) {
    throw new Error(message(body, "EQUIPMENT_WORKFLOW_REQUEST_FAILED"));
  }
  return body;
}

export function readEquipmentBuildWorkflow(
  value: unknown,
): EquipmentBuildWorkflow {
  if (!isRecord(value) || !isRecord(value.handoff)) {
    throw new Error("EQUIPMENT_HANDOFF_MISSING");
  }
  const packageId = value.handoff.packageId;
  if (typeof packageId !== "string" || !packageId) {
    throw new Error("EQUIPMENT_HANDOFF_MISSING");
  }
  return {
    packageId,
    runtimeReceipt: isRecord(value.runtimeReceipt)
      ? value.runtimeReceipt
      : {},
  };
}

export function useEquipmentManagedWorkflow(
  build: EquipmentBuildWorkflow,
): EquipmentManagedWorkflow {
  const [profiles, setProfiles] = useState<ManagedProfile[]>([]);
  const [profileNameState, setProfileNameState] = useState("");
  const [confirmation, setConfirmation] =
    useState<EquipmentManagedWorkflow["confirmation"]>(null);
  const [install, setInstall] = useState<Record<string, unknown> | null>(null);
  const [audit, setAudit] = useState<Record<string, unknown> | null>(null);
  const [sqlApply, setSqlApply] = useState<Record<string, unknown> | null>(null);
  const [preflight, setPreflight] = useState<Record<string, unknown> | null>(
    null,
  );
  const [status, setStatus] = useState("Choose or create a managed profile.");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const loadProfiles = async () => {
    const body = await request("/api/client-harness/profiles");
    const next = Array.isArray(body.profiles)
      ? body.profiles.filter(
          (profile): profile is ManagedProfile =>
            isRecord(profile) &&
            typeof profile.name === "string" &&
            (profile.mode === "pass" || profile.mode === "fail"),
        )
      : [];
    setProfiles(next);
    setProfileNameState((current) => current || next[0]?.name || "");
  };

  useEffect(() => {
    void loadProfiles().catch((failure) =>
      setError(failure instanceof Error ? failure.message : String(failure)),
    );
  }, []);

  useEffect(() => {
    setInstall(null);
    setAudit(null);
    setSqlApply(null);
    setPreflight(null);
    setStatus("Choose or create a managed profile.");
    setError("");
  }, [build.packageId]);

  const perform = async (
    label: string,
    work: () => Promise<Record<string, unknown>>,
    accept: (receipt: Record<string, unknown>) => void | Promise<void>,
  ) => {
    setBusy(true);
    setError("");
    try {
      const receipt = await work();
      await accept(receipt);
      setStatus(label);
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : String(failure));
    } finally {
      setBusy(false);
    }
  };

  const createProfile = () =>
    perform(
      "Disposable managed profile created.",
      () =>
        request("/api/client-harness/profiles", {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({
            name: `equipment-${build.packageId.slice(-8)}`,
            mode: "pass",
          }),
        }),
      async (receipt) => {
        await loadProfiles();
        if (
          isRecord(receipt.profile) &&
          typeof receipt.profile.name === "string"
        ) {
          setProfileNameState(receipt.profile.name);
        }
      },
    );

  const post = (
    path: string,
    body: Record<string, unknown>,
  ) =>
    request(path, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(body),
    });

  return {
    build,
    profiles,
    profileName: profileNameState,
    confirmation,
    install,
    audit,
    sqlApply,
    preflight,
    runtimeFields: isRecord(build.runtimeReceipt.fields)
      ? build.runtimeReceipt.fields
      : {},
    status,
    error,
    busy,
    setProfileName(name) {
      setProfileNameState(name);
      setInstall(null);
      setPreflight(null);
    },
    setConfirmation,
    createProfile,
    installPackage: () =>
      perform(
        "Equipment archives installed into the managed profile.",
        () =>
          post("/api/equipment-creator/install", {
            packageId: build.packageId,
            profileName: profileNameState,
          }),
        setInstall,
      ),
    auditSql: () =>
      perform(
        "Generated item SQL passed the INSERT-only audit.",
        () =>
          post("/api/equipment-creator/audit", {
            packageId: build.packageId,
          }),
        setAudit,
      ),
    applySql: () =>
      perform(
        "Audited item SQL applied to the configured database.",
        () =>
          post("/api/sql/apply", {
            path: audit?.sqlPath,
            dryRun: false,
          }),
        setSqlApply,
      ),
    runPreflight: () =>
      perform(
        "Managed preflight passed; real DX9 inspection remains manual.",
        () =>
          post("/api/equipment-creator/preflight", {
            packageId: build.packageId,
            profileName: profileNameState,
          }),
        setPreflight,
      ),
  };
}
