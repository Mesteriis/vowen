import {expect,type Page} from '@playwright/test'

export async function openSection(page:Page,section:string){
 const desktop=page.locator(`.workspace-nav a[href="#${section}"]`)
 if(await desktop.isVisible())await desktop.click()
 else{
  const primary=page.locator(`.mobile-bottom-nav a[href="#${section}"]`)
  if(await primary.isVisible())await primary.click()
  else{
   await page.locator('.mobile-bottom-nav button').click()
   await page.locator(`dialog.navigation-sheet a[href="#${section}"]`).click()
  }
 }
 await expect(page.locator('.startup-screen')).toHaveCount(0)
}
export async function proposeRelationship(page:Page){
 await openSection(page,'relations')
 await page.getByText('Propose a relationship',{exact:true}).click()
}
