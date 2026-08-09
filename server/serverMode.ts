export function developmentServeOptions(
  environment: Record<string, string | undefined>,
): { development?: { hmr: true; console: true } } {
  if (environment.JFTSE_STUDIO_DEV !== "1") return {};
  return { development: { hmr: true, console: true } };
}
