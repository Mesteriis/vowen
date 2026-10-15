import { defineConfig } from '@playwright/test'
export default defineConfig({testDir:'./e2e',use:{baseURL:'http://127.0.0.1:5174',locale:'en-US'},workers:1,webServer:[
 {command:'uv run --project ../backend python ../scripts/e2e_server.py',url:'http://127.0.0.1:8001/health/ready',reuseExistingServer:false},
 {command:'VOWEN_API_URL=http://127.0.0.1:8001 pnpm dev --port 5174',url:'http://127.0.0.1:5174',reuseExistingServer:false}
]})
