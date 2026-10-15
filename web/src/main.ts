import { createApp } from 'vue'
import App from './App.vue'
import GuestEntry from './features/forms/GuestEntry.vue'
import './style.css'
const guest=/^\/(f|r)\//.test(location.pathname)
if(!guest){const script=document.createElement('script');script.src='https://telegram.org/js/telegram-web-app.js';document.head.append(script)}
createApp(guest?GuestEntry:App).mount('#app')
