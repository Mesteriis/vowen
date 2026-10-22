import MarkdownIt,{type Token} from 'markdown-it'
import {h,type VNodeChild} from 'vue'
const wikiPageRoute=/^#wiki\?page=[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i
const parser=new MarkdownIt('commonmark',{html:false,linkify:false,typographer:false})
export function wikiHref(value:string):string|null {
 if(wikiPageRoute.test(value)||/^#[-\w]+$/.test(value))return value
 if(/[\s\\\u0000-\u001f]/u.test(value))return null
 try{const u=new URL(value);return (u.protocol==='http:'||u.protocol==='https:')&&!u.username&&!u.password?u.href:null}catch{return null}
}
export function parseWikiMarkdown(source:string){
 const tokens=parser.parse(source.slice(0,100000),{})
 const headings:{id:string,text:string,level:number}[]=[]
 for(let i=0;i<tokens.length;i++){const token=tokens[i];if(token.type==='heading_open'){const id='heading-'+(headings.length+1);token.attrSet('id',id);headings.push({id,text:tokens[i+1]?.content??'',level:Number(token.tag.slice(1))})}}
 return {tokens,headings}
}
const safeTags=new Set(['p','h1','h2','h3','h4','h5','h6','em','strong','ul','ol','li','blockquote','a','code','pre'])
export function renderWikiMarkdown(tokens:Token[]):VNodeChild[]{
 const result:VNodeChild[]=[]
 const stack:{tag:string,props:Record<string,unknown>,children:VNodeChild[]}[]=[]
 const add=(node:VNodeChild)=>(stack.at(-1)?.children??result).push(node)
 for(const token of tokens){
  if(token.type==='inline'){for(const node of renderWikiMarkdown(token.children??[]))add(node);continue}
  if(token.nesting===1&&safeTags.has(token.tag)){
   const props:Record<string,unknown>={}
   if(token.type==='heading_open')props.id=String(token.attrGet('id')??'')
   if(token.tag==='ol')props.start=String(token.attrGet('start')??'1')
   if(token.tag==='a'){const href=wikiHref(String(token.attrGet('href')??''));if(href){props.href=href;props.rel='noopener noreferrer';if(!href.startsWith('#'))props.target='_blank';else if(!wikiPageRoute.test(href))props.onClick=(event:MouseEvent)=>{event.preventDefault();if(typeof document!=='undefined')document.getElementById(href.slice(1))?.scrollIntoView({behavior:window.matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth',block:'start'})}}}
   stack.push({tag:token.tag,props,children:[]});continue
  }
  if(token.nesting===-1&&safeTags.has(token.tag)){const current=stack.pop();if(current)add(h(current.tag,current.props,current.children));continue}
  if(token.type==='fence'||token.type==='code_block'){add(h('pre',h('code',token.content)));continue}
  if(token.type==='code_inline'){add(h('code',token.content));continue}
  if(token.type==='softbreak'||token.type==='hardbreak'){add(h('br'));continue}
  if(token.type==='hr'){add(h('hr'));continue}
  if(token.type==='image'){add(token.content);continue}
  if(token.content)add(token.content)
 }
 while(stack.length){const current=stack.pop()!;add(h(current.tag,current.props,current.children))}
 return result
}
