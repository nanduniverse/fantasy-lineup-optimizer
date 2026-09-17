import { readSaved, save } from "./storage";
import type { NflCatalog, NflContext, NflRecommendationRequest, NflRecommendationResponse, RecommendationResponse } from "../types";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? (import.meta.env.PROD ? "/api" : "http://localhost:8000/api");

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, init);
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") throw error;
    throw new Error("Cannot reach the API. Check that the backend is running and try again.");
  }
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const detail = body.detail;
    const message = Array.isArray(detail)
      ? detail.map((issue: { loc?: (string | number)[]; msg?: string }) =>
          `${issue.loc?.slice(1).join(".") ?? "Input"}: ${issue.msg ?? "Invalid value"}`).join("; ")
      : typeof detail === "string" ? detail : "The request failed. Please try again.";
    throw new Error(message);
  }
  return response.json();
}

export function loadSampleRequest() {
  return request<unknown>("/sample-roster");
}

export function recommendLineup(payload: unknown): Promise<RecommendationResponse> {
  return request("/recommend-lineup", {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload),
  });
}

export async function loadNflPlayers(context: NflContext, signal?: AbortSignal): Promise<NflCatalog> {
  const query = new URLSearchParams({ season: String(context.season), target_week: String(context.target_week), scoring_format: context.scoring_format });
  const key = `catalog:${query}`;
  try {
    const data = await request<NflCatalog>(`/nfl/current/players?${query}`, { signal });
    save(key, data);
    return data;
  } catch (error) {
    if (signal?.aborted) throw error;
    const cached = readSaved<NflCatalog>(key);
    if (!cached?.players || !cached.weekly) throw error;
    return { ...cached, weekly: { ...cached.weekly, verified: false,
      warnings: [`Offline / saved data from ${new Date(cached.weekly.fetched_at).toLocaleString()}. Reconnect to verify availability and optimize.`, ...cached.weekly.warnings] } };
  }
}

export function recommendNflLineup(payload: NflRecommendationRequest): Promise<NflRecommendationResponse> {
  return request("/nfl/current/recommend-lineup", {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload),
  });
}

export function importEspnLeague(payload: import('../types').LeagueRequest, signal?: AbortSignal): Promise<import('../types').LeagueImport> {
  return request('/leagues/espn/import', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload), signal,
  });
}

export async function loadNews(signal?: AbortSignal): Promise<import('../types').NewsFeed> {
  try {
    const news = await request<import('../types').NewsFeed>('/news', { signal });
    save('news', news);
    return news;
  } catch (error) {
    if (signal?.aborted) throw error;
    const cached = readSaved<import('../types').NewsFeed>('news');
    if (!cached?.articles) throw error;
    return { ...cached, stale: true, warnings: [...cached.warnings, 'Offline / saved headlines. Reconnect to check for updates.'] };
  }
}
