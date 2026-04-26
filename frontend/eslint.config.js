import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import { defineConfig, globalIgnores } from 'eslint/config'

export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{js,jsx}'],
    extends: [
      js.configs.recommended,
      reactHooks.configs.flat.recommended,
      reactRefresh.configs.vite,
    ],
    languageOptions: {
      ecmaVersion: 2020,
      globals: globals.browser,
      parserOptions: {
        ecmaVersion: 'latest',
        ecmaFeatures: { jsx: true },
        sourceType: 'module',
      },
    },
    rules: {
      'no-unused-vars': ['error', { varsIgnorePattern: '^[A-Z_]' }],
      // eslint-plugin-react-hooks 7.1+ ships React Compiler-aware rules
      // that flag patterns the codebase uses widely (setState in effects,
      // reading refs during render). They're useful guidance but force-
      // fixing every prior occurrence is a separate, larger refactor.
      // Keep them as 'warn' so the signal stays visible without blocking
      // CI on every push.
      'react-hooks/set-state-in-effect': 'warn',
      'react-hooks/refs': 'warn',
      'react-hooks/preserve-manual-memoization': 'warn',
      'react-hooks/purity': 'warn',
      // react-refresh complains when a file mixes a default-exported
      // component with named non-component exports (typical for
      // contexts: ``export const FooContext`` + ``export default FooProvider``).
      // The codebase relies on that pattern. Keep as a guidance warning.
      'react-refresh/only-export-components': 'warn',
    },
  },
])
