import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  resolve: {
    preserveSymlinks: true
  },
  optimizeDeps: {
    noDiscovery: true,
    include: ["react", "react-dom", "react-dom/client"]
  },
  server: {
    port: 5173,
    host: "127.0.0.1"
  }
});
