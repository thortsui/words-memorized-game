import { defineConfig } from 'vite';
// base './' 讓 GitHub Pages 子路徑也能直接載入
export default defineConfig({ base: './', build: { target: 'es2020' } });
