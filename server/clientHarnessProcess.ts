import { kill as signalProcess, platform } from "node:process";

export async function boundedOutput(
  stream: ReadableStream<Uint8Array>,
  marker: string,
  limit: number,
): Promise<{ text: string; ready: boolean }> {
  const reader = stream.getReader();
  const decoder = new TextDecoder();
  let text = "";
  let overlap = "";
  let ready = false;
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      const chunk = decoder.decode(value, { stream: true });
      ready ||= (overlap + chunk).includes(marker);
      overlap = (overlap + chunk).slice(-Math.max(0, marker.length - 1));
      text = (text + chunk).slice(-limit);
    }
    text = (text + decoder.decode()).slice(-limit);
    return { text, ready };
  } finally {
    reader.releaseLock();
  }
}

export function terminateGroup(pid: number): void {
  for (const signal of ["SIGTERM", "SIGKILL"] as const) {
    try {
      if (platform !== "win32") signalProcess(-pid, signal);
      else signalProcess(pid, signal);
    } catch (error) {
      if ((error as NodeJS.ErrnoException).code !== "ESRCH") throw error;
    }
  }
}
