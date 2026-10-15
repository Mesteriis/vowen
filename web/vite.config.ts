import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
export default defineConfig({plugins:[vue()],server:{proxy:{'/api':process.env.VOWEN_API_URL ?? 'http://127.0.0.1:8000','/health':process.env.VOWEN_API_URL ?? 'http://127.0.0.1:8000'}}})
