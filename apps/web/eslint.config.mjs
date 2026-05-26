import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

const eslintConfig = [
  {
    ignores: [".next/**", ".next-dev/**", "node_modules/**"],
  },
  ...nextVitals,
  ...nextTs,
  {
    rules: {
      // Pre-existing codebase patterns — fix in a dedicated cleanup pass
      "@typescript-eslint/no-explicit-any": "warn",
    },
  },
];

export default eslintConfig;
