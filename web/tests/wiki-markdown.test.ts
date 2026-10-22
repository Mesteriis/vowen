import {describe,it,expect} from 'vitest'
import {h} from 'vue'
import {renderToString} from 'vue/server-renderer'
import {parseWikiMarkdown,renderWikiMarkdown} from '../src/features/wiki/markdown'

describe('Wiki Markdown boundary',()=>{
 it('renders real headings with unique anchors',async()=>{
  const parsed=parseWikiMarkdown('# Same\n\n## Same\n\n**bold**')
  expect(parsed.headings.map(h=>h.id)).toEqual(['heading-1','heading-2'])
  const html=await renderToString(h('div',renderWikiMarkdown(parsed.tokens)))
  expect(html).toContain('<strong>bold</strong>')
  expect(html).toContain('id="heading-2"')
 })
 it('does not execute HTML or load images or dangerous links',async()=>{
  const parsed=parseWikiMarkdown('<script>alert(1)</script>\n\n<iframe src="https://evil.test"></iframe>\n\n![image](https://evil.test/a.png)\n\n[x](javascript:alert(1)) [file](file:///tmp/x) [creds](https://a:b@example.org) [safe](https://example.org)')
  const html=await renderToString(h('div',renderWikiMarkdown(parsed.tokens)))
  expect(html).not.toMatch(/<(script|iframe|img)\b/)
  expect(html).not.toMatch(/href="(javascript|file|data):/)
  expect(html).not.toContain('href="https://a:b@')
  expect(html).toContain('href="https://example.org/"')
  expect(html).toContain('&lt;script&gt;')
 })
})
it('handles an in-page link without changing the application route',()=>{
 const nodes=renderWikiMarkdown(parseWikiMarkdown('[Jump](#heading-1)').tokens)
 const paragraph=nodes[0] as import('vue').VNode
 const anchor=(paragraph.children as import('vue').VNode[])[0]
 let prevented=false
 expect(typeof anchor.props?.onClick).toBe('function')
 anchor.props?.onClick({preventDefault:()=>{prevented=true}})
 expect(prevented).toBe(true)
})
it('renders a direct Wiki page link as same-window route navigation',async()=>{
 const target='#wiki?page=11111111-2222-4333-8444-555555555555'
 const parsed=parseWikiMarkdown(`[Материал](${target})`)
 const nodes=renderWikiMarkdown(parsed.tokens)
 const paragraph=nodes[0] as import('vue').VNode
 const anchor=(paragraph.children as import('vue').VNode[])[0]
 expect(anchor.props?.href).toBe(target)
 expect(anchor.props?.target).toBeUndefined()
 expect(anchor.props?.onClick).toBeUndefined()
 const html=await renderToString(h('div',nodes))
 expect(html).toContain(`href="${target}"`)
})
it('refuses malformed internal routes and parameter injection',async()=>{
 for(const route of ['#wiki?page=bad','#wiki?page=11111111-2222-4333-8444-555555555555&admin=1','#settings?admin=1','#wiki?page=javascript:alert(1)']){
  const html=await renderToString(h('div',renderWikiMarkdown(parseWikiMarkdown(`[x](${route})`).tokens)))
  expect(html).not.toContain('href=')
 }
})
