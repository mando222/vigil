import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import { fileURLToPath } from 'url'
import { dirname, resolve } from 'path'

// Get __dirname equivalent in ES modules
const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  // Load env from root directory (parent of frontend)
  const env = loadEnv(mode, resolve(__dirname, '..'), '')
  
  // If DEV_MODE is set in root .env, pass it to frontend as VITE_DEV_MODE
  const devMode = env.DEV_MODE === 'true' ? 'true' : 'false'
  
  return {
    plugins: [react()],
    server: {
      port: 6988,
      host: '127.0.0.1', // Use IPv4 explicitly
      proxy: {
        '/api': {
          target: 'http://127.0.0.1:6987', // Use IPv4 explicitly instead of localhost
          changeOrigin: true,
        },
      },
    },
    build: {
      outDir: 'build',
    },
    define: {
      // Make DEV_MODE from root .env available as VITE_DEV_MODE in frontend
      'import.meta.env.VITE_DEV_MODE': JSON.stringify(devMode),
    },
  }
})

