import {openSection,proposeRelationship} from './workspace'
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
 await expect(page.locator('.startup-screen')).toHaveCount(0)
}

test('closed access, bilateral relationship and personal pause through actual API',async({browser,page})=>{
 const errors:string[]=[]
 page.on('pageerror',e=>errors.push(e.message))
 await telegram(page,100000000201)
 await expect(page.getByRole('heading',{name:/Demo 1/})).toBeVisible()
 await proposeRelationship(page)
 await page.getByRole('combobox',{name:'Participant',exact:true}).selectOption({label:'Demo 2'})
 await page.getByLabel('Agreement text',{exact:true}).fill('Synthetic agreement for E2E')
 await page.getByRole('button',{name:'Propose',exact:true}).click()
 await expect(page.getByText('Version 1 · Consents 0/2')).toBeVisible()
 await page.getByRole('button',{name:'Accept this exact version and scopes'}).click()
 await expect(page.getByText('Version 2 · Consents 1/2')).toBeVisible()
 const other=await browser.newContext({locale:'en-US'})
 const second=await other.newPage()
 await telegram(second,100000000202)
 await openSection(second,'relations')
 await second.getByRole('button',{name:'Accept this exact version and scopes'}).click()
 await expect(second.getByText('Version 3 · Consents 2/2')).toBeVisible()
 await second.getByRole('button',{name:'Personal pause',exact:true}).click()
 await expect(second.getByRole('button',{name:'End personal pause'})).toBeVisible()
 await second.getByRole('button',{name:'End personal pause'}).click()
 await expect(second.getByRole('button',{name:'Personal pause',exact:true})).toBeVisible()
 await page.getByRole('button',{name:'Refresh',exact:true}).click()
 await expect(page.getByText('Version 3 · Consents 2/2')).toBeVisible()
 await page.screenshot({path:'test-results/m1-desktop.png',fullPage:true})
 await page.setViewportSize({width:390,height:844})
 await expect(page.locator('body')).toHaveJSProperty('scrollWidth',390)
 await page.screenshot({path:'test-results/m1-mobile.png',fullPage:true})
 expect(errors).toEqual([])
 await other.close()
})

test('unknown Telegram identity is denied without self-registration',async({page})=>{
 await telegram(page,100000000299)
 await expect(page.getByRole('alert')).toContainText('Sign-in failed')
 await expect(page.getByRole('heading',{name:'Relationships'})).toHaveCount(0)
})

test('profile preferences persist after refresh without exposing operator fields',async({page})=>{
 await telegram(page,100000000203)
 await openSection(page,'profile')
 await page.getByLabel('Display name',{exact:true}).fill('Updated demo')
 await page.getByLabel('IANA timezone',{exact:true}).fill('Europe/Madrid')
 await page.getByRole('checkbox',{name:'switch',exact:true}).check()
 await page.getByRole('button',{name:'Save profile',exact:true}).click()
 await expect(page.getByRole('button',{name:'Updated demo · My profile',exact:true})).toBeVisible()
 await page.getByRole('button',{name:'Refresh',exact:true}).click()
 await expect(page.getByLabel('IANA timezone',{exact:true})).toHaveValue('Europe/Madrid')
 await expect(page.getByRole('checkbox',{name:'switch',exact:true})).toBeChecked()
 await expect(page.getByText('Profile labels do not grant permissions.')).toBeVisible()
})

test('Telegram launch keeps the preloader until verification and never flashes the login form',async({page})=>{
 let release:()=>void=()=>{}
 const held=new Promise<void>(resolve=>{release=resolve})
 await page.route('https://telegram.org/**',route=>route.fulfill({body:''}))
 await page.addInitScript(raw=>Object.assign(window,{Telegram:{WebApp:{initData:raw,ready:()=>{}}}}),signed(100000000204))
 await page.route('**/api/v1/auth/telegram/miniapp',async route=>{await held;await route.continue()})
 await page.goto('/',{waitUntil:'domcontentloaded'})
 await expect(page.getByRole('status',{name:'Loading Vowen'})).toBeVisible()
 await expect(page.locator('.entry-workspace')).toHaveCount(0)
 await expect(page.getByRole('button',{name:'Sign in with Telegram'})).toHaveCount(0)
 release()
 await expect(page.getByRole('heading',{name:/Demo 4/})).toBeVisible()
 await expect(page.locator('.startup-screen')).toHaveCount(0)
 await expect(page.locator('.entry-workspace')).toHaveCount(0)
 await expect(page.getByRole('combobox',{name:'Relationship context'})).toBeVisible()
})
