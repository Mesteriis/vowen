/** Dark-only product theme. Supersedes saved light/system preferences from older clients. */
export function applyDarkTheme():void {
 document.documentElement.dataset.theme='dark'
 try{localStorage.setItem('vowen.appearance','dark')}catch{/* Storage is optional. */}
}
