import axios from "axios";

const BASE_URL = process.env.REACT_APP_API_URL || "http://127.0.0.1:8000";

const client = axios.create({
  baseURL: BASE_URL,
  timeout: 300_000, // 5 min — agents can be slow
  headers: { "Content-Type": "application/json" },
});

/**
 * Send a research query to the backend.
 * @param {string} query - The user's research question.
 * @returns {Promise<{summary: string, insights: string[], sources: string[], query: string, timestamp: string, duration_seconds: number}>}
 */
export async function sendQuery(query) {
  const response = await client.post("/query", { query });
  return response.data;
}

/**
 * Fetch full research history from the backend.
 * @returns {Promise<Array>}
 */
export async function fetchHistory() {
  const response = await client.get("/history");
  return response.data;
}

/**
 * Clear all research history on the backend.
 */
export async function clearHistory() {
  await client.delete("/history");
}

export default client;
