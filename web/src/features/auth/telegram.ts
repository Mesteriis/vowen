export type TelegramWebApp = {initData:string;ready:()=>void}

function currentWebApp():TelegramWebApp|undefined {
 return (window as Window & {Telegram?:{WebApp?:TelegramWebApp}}).Telegram?.WebApp
}

/** Keep the startup screen visible until the official SDK can expose launch data. */
export async function telegramWebApp():Promise<TelegramWebApp|undefined> {
 if(currentWebApp())return currentWebApp()
 let script=document.getElementById('telegram-web-app-sdk') as HTMLScriptElement|null
 if(!script){script=document.createElement('script');script.id='telegram-web-app-sdk';script.src='https://telegram.org/js/telegram-web-app.js'}
 await new Promise<void>(resolve=>{
  const finish=()=>{clearTimeout(timer);script?.removeEventListener('load',finish);script?.removeEventListener('error',finish);resolve()}
  const timer=setTimeout(finish,3000)
  script!.addEventListener('load',finish,{once:true})
  script!.addEventListener('error',finish,{once:true})
  if(!script!.isConnected)document.head.append(script!)
 })
 return currentWebApp()
}
