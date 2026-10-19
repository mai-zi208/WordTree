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
