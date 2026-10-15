import { test, expect, type Page } from '@playwright/test'
import { createHmac } from 'node:crypto'

function signed(id:number) {
 const fields:Record<string,string> = {auth_date:String(Math.floor(Date.now()/1000)),query_id:'synthetic-'+id,user:JSON.stringify({id,first_name:'Demo'})}
 const secret=createHmac('sha256','WebAppData').update('123456:synthetic_test_token_not_a_real_credential').digest()
 fields.hash=createHmac('sha256',secret).update(Object.entries(fields).sort(([a],[b])=>a.localeCompare(b)).map(([k,v])=>`${k}=${v}`).join('\n')).digest('hex')
 return new URLSearchParams(fields).toString()
}
async function telegram(page:Page,id:number) {
 await page.route('https://telegram.org/**',route=>route.fulfill({contentType:'application/javascript',body:''}))
 await page.addInitScript(raw=>{Object.assign(window,{Telegram:{WebApp:{initData:raw,ready:()=>{}}}})},signed(id))
 await page.goto('/')
 await page.getByRole('button',{name:'Sign in with Telegram'}).click()
}

test('closed access, bilateral relationship and personal pause through actual API',async({browser,page})=>{
 const errors:string[]=[]
 page.on('pageerror',e=>errors.push(e.message))
 await telegram(page,100000000201)
 await expect(page.getByRole('heading',{name:'Demo 1',exact:true})).toBeVisible()
 await page.getByRole('combobox',{name:'Participant',exact:true}).selectOption({label:'Demo 2'})
 await page.getByLabel('Agreement text',{exact:true}).fill('Synthetic agreement for E2E')
 await page.getByRole('button',{name:'Propose',exact:true}).click()
 await expect(page.getByText('proposed · v1 · 0/2')).toBeVisible()
 await page.getByRole('button',{name:'Accept this exact version and scopes'}).click()
 await expect(page.getByText('proposed · v2 · 1/2')).toBeVisible()
 const other=await browser.newContext({locale:'en-US'})
 const second=await other.newPage()
 await telegram(second,100000000202)
 await second.getByRole('button',{name:'Accept this exact version and scopes'}).click()
 await expect(second.getByText('active · v3 · 2/2')).toBeVisible()
 await second.getByRole('button',{name:'Personal pause',exact:true}).click()
 await expect(second.getByRole('button',{name:'End personal pause'})).toBeVisible()
 await second.getByRole('button',{name:'End personal pause'}).click()
 await expect(second.getByRole('button',{name:'Personal pause',exact:true})).toBeVisible()
 await page.getByRole('button',{name:'Refresh',exact:true}).click()
 await expect(page.getByText('active · v3 · 2/2')).toBeVisible()
 await page.screenshot({path:'test-results/m1-desktop.png',fullPage:true})
 await page.setViewportSize({width:390,height:844})
 await expect(page.locator('body')).toHaveJSProperty('scrollWidth',390)
 await page.screenshot({path:'test-results/m1-mobile.png',fullPage:true})
 expect(errors).toEqual([])
 await other.close()
})

test('unknown Telegram identity is denied without self-registration',async({page})=>{
 await telegram(page,100000000299)
 await expect(page.getByRole('alert')).toContainText('ACCESS_DENIED')
 await expect(page.getByRole('heading',{name:'Relationships'})).toHaveCount(0)
})
