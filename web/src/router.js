import { createRouter, createWebHashHistory } from "vue-router";
import { state } from "./store";
import HomeView from "./views/HomeView.vue";
import FamilyView from "./views/FamilyView.vue";
import QuizView from "./views/QuizView.vue";
import DoneView from "./views/DoneView.vue";

const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    { path: "/", name: "home", component: HomeView },
    { path: "/family/:id", name: "family", component: FamilyView, props: true },
    { path: "/quiz", name: "quiz", component: QuizView },
    { path: "/done", name: "done", component: DoneView },
  ],
  scrollBehavior: () => ({ top: 0 }),
});

router.beforeEach((to) => {
  if (to.name === "quiz" && !state.session) return { name: "home" };
  if (to.name === "done" && !state.summary) return { name: "home" };
  if (to.name === "family" && !familyExists(to.params.id)) return { name: "home" };
});

function familyExists(id) {
  return state.loaded ? state.families.some((f) => f.id === Number(id)) : true;
}

export default router;
