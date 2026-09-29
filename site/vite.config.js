import { defineConfig } from 'vite';
import { resolve } from 'node:path';
import market from './plugins/market.js';

// GitHub Pages project site: https://macsermkiat.github.io/website/
export default defineConfig({
  base: '/website/',
  plugins: [market()],
  server: { fs: { allow: ['..'] } },
  build: {
    target: 'es2022',
    chunkSizeWarningLimit: 800,
    rolldownOptions: {
      input: {
        main: resolve(import.meta.dirname, 'index.html'),
        plain: resolve(import.meta.dirname, 'plain.html'),
      },
      // three.js in its own file: it changes far less often than the market code, so browsers keep it cached
      output: {
        codeSplitting: {
          groups: [{ name: 'three', test: /node_modules[\\/]three[\\/]/ }],
        },
      },
    },
  },
});
