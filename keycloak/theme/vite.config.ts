import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { keycloakify } from "keycloakify/vite-plugin";

export default defineConfig({
    plugins: [
        react(),
        keycloakify({
            accountThemeImplementation: "none",
            themeName: "startech",
            keycloakVersionTargets: {
                "22-to-25": false,
                "all-other-versions": "startech-theme.jar"
            }
        })
    ]
});
