module.exports = {
  root: true,
  env: { browser: true, es2021: true },
  extends: [
    "eslint:recommended",
    "plugin:@typescript-eslint/recommended",
    "plugin:react-hooks/recommended",
  ],
  parser: "@typescript-eslint/parser",
  ignorePatterns: ["dist", "node_modules", ".eslintrc.cjs", "vite.config.ts"],
  rules: {
    "@typescript-eslint/no-explicit-any": "warn",
  },
};
