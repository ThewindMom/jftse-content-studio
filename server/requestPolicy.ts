export class RequestPolicyError extends Error {
  constructor(
    readonly code: string,
    readonly status: 400 | 413,
  ) {
    super(code);
    this.name = "RequestPolicyError";
  }
}

type IntegerPolicy = {
  name: string;
  minimum: number;
  maximum: number;
  fallback?: number;
};

export function parseBoundedInteger(
  raw: string | null,
  policy: IntegerPolicy,
): number {
  if (raw === null || raw === "") {
    if (policy.fallback !== undefined) return policy.fallback;
    throw new RequestPolicyError(`INVALID_${policy.name.toUpperCase()}`, 400);
  }
  if (!/^-?\d+$/.test(raw)) {
    throw new RequestPolicyError(`INVALID_${policy.name.toUpperCase()}`, 400);
  }
  const value = Number(raw);
  if (
    !Number.isSafeInteger(value) ||
    value < policy.minimum ||
    value > policy.maximum
  ) {
    throw new RequestPolicyError(`INVALID_${policy.name.toUpperCase()}`, 400);
  }
  return value;
}

export async function readJsonObject(
  request: Request,
  maximumBytes: number,
): Promise<Record<string, unknown>> {
  const declaredLength = request.headers.get("content-length");
  if (declaredLength !== null) {
    const length = Number(declaredLength);
    if (!Number.isSafeInteger(length) || length < 0) {
      throw new RequestPolicyError("INVALID_CONTENT_LENGTH", 400);
    }
    if (length > maximumBytes) {
      throw new RequestPolicyError("REQUEST_BODY_TOO_LARGE", 413);
    }
  }

  const reader = request.body?.getReader();
  if (!reader) throw new RequestPolicyError("INVALID_JSON", 400);
  const decoder = new TextDecoder();
  let bytesRead = 0;
  let text = "";
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      bytesRead += value.byteLength;
      if (bytesRead > maximumBytes) {
        await reader.cancel();
        throw new RequestPolicyError("REQUEST_BODY_TOO_LARGE", 413);
      }
      text += decoder.decode(value, { stream: true });
    }
    text += decoder.decode();
  } finally {
    reader.releaseLock();
  }

  let parsed: unknown;
  try {
    parsed = JSON.parse(text);
  } catch {
    throw new RequestPolicyError("INVALID_JSON", 400);
  }
  if (parsed === null || typeof parsed !== "object" || Array.isArray(parsed)) {
    throw new RequestPolicyError("JSON_OBJECT_REQUIRED", 400);
  }
  return parsed as Record<string, unknown>;
}
