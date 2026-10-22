const JSON_HEADERS = { "Content-Type": "application/json" };

async function req(path, options = {}) {
  let res;
  try {
    res = await fetch(path, options);
  } catch {
    throw new Error("连不上后端：先在 backend/ 目录启动 FastAPI（默认 127.0.0.1:8000）");
  }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || `请求失败（${res.status}）`);
  return data;
}

const post = (path, body) =>
  req(path, { method: "POST", headers: JSON_HEADERS, body: JSON.stringify(body) });

const put = (path, body) =>
  req(path, { method: "PUT", headers: JSON_HEADERS, body: JSON.stringify(body) });

export const fetchFamilies = () => req("/api/families");
export const fetchFamily = (id) => req(`/api/families/${id}`);
export const fetchDue = () => req("/api/study/due");
export const buildQueue = (payload) => post("/api/study/queue", payload);
export const commitRatings = (payload) => post("/api/study/commit", payload);
export const clearProgress = () => req("/api/study/progress", { method: "DELETE" });
export const startGrouping = (payload) => post("/api/generate/group", payload);
export const startBatch = (groups) => post("/api/generate/batch", { groups });
export const fetchJob = (id) => req(`/api/generate/${id}`);
export const saveGenerated = (id, picks) => post(`/api/generate/${id}/save`, { picks });
export const discardJob = (id) => req(`/api/generate/${id}`, { method: "DELETE" });
export const fetchSettings = () => req("/api/settings");
export const saveSettings = (payload) => put("/api/settings", payload);
