const API_URL = (
  process.env.NEXT_PUBLIC_API_URL ||
  (process.env.NODE_ENV === "production" ? "/api" : "http://localhost:8000")
).replace(/\/$/, "");

export async function fetchApi<T>(
  path: string,
  signal?: AbortSignal,
): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    signal: signal
      ? AbortSignal.any([signal, AbortSignal.timeout(15000)])
      : AbortSignal.timeout(15000),
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(
      response.status === 404
        ? "This job could not be found."
        : `The job service returned an error (${response.status}). Please try again.`,
    );
  }
  return response.json() as Promise<T>;
}
