import {defineComponent,h} from 'vue'
import {parseWikiMarkdown,renderWikiMarkdown} from './markdown'
export default defineComponent({
 props:{source:{type:String,required:true}},
 setup:props=>()=>h('div',{class:'wiki-prose'},renderWikiMarkdown(parseWikiMarkdown(props.source).tokens)),
})
