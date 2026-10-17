/**
 * Single source of truth for browser-to-API requests.
 *
 * Configure NEXT_PUBLIC_API_URL in the frontend deployment to point at the
 * FastAPI service (for example, https://enterprise-doc-intelligence-api-final2.onrender.com).
 * Local development falls back to localhost; production never silently targets localhost.
 */
const configuredApiUrl = process.env.NEXT_PUBLIC_API_URL?.trim();
const localDevelopmentUrl =
  process.env.NODE_ENV === "development" ? "http://localhost:8000" : "";

export const API_BASE_URL = (configuredApiUrl || localDevelopmentUrl).replace(/\/+$/, "");

export function apiUrl(path: string): string {
  if (!API_BASE_URL) {
    throw new Error(
      "The API is not configured. Set NEXT_PUBLIC_API_URL to the deployed FastAPI service URL.",
    );
  }

  return `${API_BASE_URL}${path.startsWith("/") ? path : `/${path}`}`;
}
