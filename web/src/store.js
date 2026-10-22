import { reactive } from "vue";
import * as api from "./api";

export const state = reactive({
  families: [],
  dueTotal: 0,
  today: "",
  loaded: false,
  error: "",
  busy: false,
  session: null,
  summary: null,
});

export function human(date) {
  if (!date) return "";
  const [, m, d] = date.split("-");
  return `${Number(m)}月${Number(d)}日`;
}

export function familyById(id) {
  return state.families.find((f) => f.id === Number(id)) || null;
}

// 便签墙和词族页翻页共用这一个顺序：没学过的排前面，学过的排后面，
// 组内保持接口给的 id 升序（sort 是稳定的）。两边不一致的话「下一族」就不是墙上的下一张。
export function wallOrder(list) {
  return [...list].sort((a, b) => (a.learned ? 1 : 0) - (b.learned ? 1 : 0));
}

// 取墙上相邻的一族。按 wallOrder 的下标取，不按 id±1：智能体生成的族被拒过就会跳号。
export function neighborFamily(id, dir) {
  const order = wallOrder(state.families);
  const i = order.findIndex((f) => f.id === Number(id));
  return i < 0 ? null : order[i + dir] || null;
}

export async function loadFamilies() {
  try {
    const data = await api.fetchFamilies();
    state.families = data.families;
    state.dueTotal = data.dueTotal;
    state.today = data.today;
    state.loaded = true;
    state.error = "";
  } catch (e) {
    state.error = e.message;
  }
}

export async function startSession({ mode, familyId = null, pool = "all" }) {
  state.busy = true;
  state.error = "";
  try {
    const data = await api.buildQueue({ mode, familyId, pool });
    state.session = { mode, familyId, pool, items: data.items, index: 0, results: [] };
    return true;
  } catch (e) {
    state.error = e.message;
    return false;
  } finally {
    state.busy = false;
  }
}

export function rate(word, rating) {
  const session = state.session;
  if (!session) return;
  if (!session.results.some((r) => r.word === word)) session.results.push({ word, rating });
  session.index += 1;
}

export async function commitSession() {
  const session = state.session;
  if (!session || !session.results.length) return null;
  state.busy = true;
  try {
    const data = await api.commitRatings({
      results: session.results,
      familyId: session.familyId,
    });
    state.summary = {
      mode: session.mode,
      familyId: session.familyId,
      items: session.items.length,
      scheduled: data.scheduled,
      rolledBackRoots: data.rolledBackRoots,
      familyRoot: data.familyRoot,
      nextDate: data.nextDate,
    };
    state.session = null;
    await loadFamilies();
    return state.summary;
  } catch (e) {
    state.error = e.message;
    return null;
  } finally {
    state.busy = false;
  }
}

export async function resetProgress() {
  state.error = "";
  try {
    await api.clearProgress();
    await loadFamilies();
    return true;
  } catch (e) {
    state.error = e.message;
    return false;
  }
}
