import { fileURLToPath, URL } from "node:url";
import vue from "@vitejs/plugin-vue";

const API = process.env.WORDMEMO_API || "http://127.0.0.1:8000";
const proxy = { "/api": { target: API }, "/assets": { target: API } };

export default {
  plugins: [vue()],
  resolve: { alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) } },
  server: { port: 5273, strictPort: true, proxy },
  preview: { port: 5274, strictPort: true, proxy },
  // dist/assets 会让给简笔画图片的 /assets 挂载位，构建产物改放 static。
  build: { assetsDir: "static" },
};
