import client from "./client";

export async function getAnalyticsSummary() {
  return client.get("/analytics/summary");
}
