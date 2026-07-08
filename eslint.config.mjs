import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";

const eslintConfig = defineConfig([
  ...nextVitals,
  // Override default ignores of eslint-config-next.
  globalIgnores([
    // Default ignores of eslint-config-next:
    ".next/**",
    "out/**",
    "build/**",
    "next-env.d.ts",
  ]),
  {
    rules: {
      // Data-fetch effects that setState after auth are intentional across NovaFlow pages.
      "react-hooks/set-state-in-effect": "off",
      // Event handlers may create ids / timestamps; purity rule is too strict for builders.
      "react-hooks/purity": "off",
    },
  },
]);

export default eslintConfig;
