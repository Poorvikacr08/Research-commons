import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Every request to /api/... is forwarded to FastAPI.
// In Docker the backend is at http://backend:8000; locally at http://localhost:8000.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": process.env.VITE_API_PROXY || "http://localhost:8000",
    },
  },
});
