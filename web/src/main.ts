import { createApp } from 'vue'
import App from './App.vue'
import GuestEntry from './features/forms/GuestEntry.vue'
import './style.css'
import {applyDarkTheme} from './features/appearance/theme'
applyDarkTheme()
const guest=/^\/(f|r)\//.test(location.pathname)
createApp(guest?GuestEntry:App).mount('#app')
