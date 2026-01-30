import { FlatCompat } from '@eslint/eslintrc';
import tseslint from '@typescript-eslint/eslint-plugin';
import * as tsParserNS from '@typescript-eslint/parser';
import prettierPlugin from 'eslint-plugin-prettier';
import { dirname } from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const compat = new FlatCompat({
  baseDirectory: __dirname,
});

const tsParser = tsParserNS.default ?? tsParserNS;

const eslintConfig = [
  ...compat.extends('next/core-web-vitals', 'next/typescript'),

  {
    ignores: [
      'node_modules/**',
      '.next/**',
      'out/**',
      'build/**',
      'next-env.d.ts',
      '*.config.js',
    ],
  },

  {
    files: ['**/*.{js,jsx,ts,tsx}'],
    languageOptions: {
      parser: tsParser,
      parserOptions: {
        project: './tsconfig.json',
      },
    },
    plugins: {
      '@typescript-eslint': tseslint,
      prettier: prettierPlugin,
    },
    rules: {
      'prettier/prettier': 'warn',
      'template-curly-spacing': 'off',
      'react/no-unescaped-entities': 'off',
      indent: 'off',
      'linebreak-style': ['error', process.platform === 'win32' ? 'windows' : 'unix'],
      quotes: ['error', 'single'],
      'arrow-body-style': ['error', 'as-needed'],
      'lines-between-class-members': ['error', 'always'],
      'comma-dangle': [
        'error',
        {
          arrays: 'ignore',
          objects: 'ignore',
          imports: 'ignore',
          exports: 'never',
          functions: 'ignore',
        },
      ],
      'object-curly-spacing': ['error', 'always'],
      'comma-spacing': [
        'error',
        {
          before: false,
          after: true,
        },
      ],
      'no-multiple-empty-lines': [
        'error',
        {
          max: 1,
          maxEOF: 0,
        },
      ],
      'arrow-spacing': 'error',
      'func-call-spacing': ['error', 'never'],
      '@typescript-eslint/no-use-before-define': ['warn'],
      'prefer-template': 'error',
      'space-infix-ops': [
        'error',
        {
          int32Hint: false,
        },
      ],
      'react-hooks/rules-of-hooks': 'error',
      'react-hooks/exhaustive-deps': 0,
      'no-useless-escape': 0,
      'no-confusing-arrow': 0,
      'no-use-before-define': 'off',
      'no-undef': 0,
      'no-unsafe-optional-chaining': 0,

      '@typescript-eslint/consistent-type-definitions': ['error', 'interface'],
      '@typescript-eslint/no-explicit-any': 'off',
      '@typescript-eslint/no-non-null-assertion': 'off',
      '@typescript-eslint/no-unused-vars': [
        'warn',
        { argsIgnorePattern: '^_', varsIgnorePattern: '^_' },
      ],

      '@next/next/no-img-element': 'off',
    },
  },
];

export default eslintConfig;
