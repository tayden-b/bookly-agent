import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Dev: vite serves the UI on :5173 and proxies /api to FastAPI on :8000.
// Prod: `npm run build` outputs dist/, which FastAPI serves directly.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: { "/api": "http://localhost:8000" },
  },
});
