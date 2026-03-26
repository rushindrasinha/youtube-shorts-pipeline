/** @type {import("eslint").Linter.Config} */
module.exports = {
  extends: ["eslint:recommended", "prettier"],
  env: { node: true, es2022: true },
  parserOptions: { ecmaVersion: "latest", sourceType: "module" },
  overrides: [
    {
      files: ["**/*.ts", "**/*.tsx"],
      parser: "@typescript-eslint/parser",
      extends: ["plugin:@typescript-eslint/recommended"],
    },
  ],
  ignorePatterns: ["node_modules/", "dist/", ".next/", ".turbo/"],
};
