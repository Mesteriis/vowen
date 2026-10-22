package org.vowen.app

import org.commonmark.node.*
import org.commonmark.parser.Parser
import java.net.URI

/** No HTML renderer, WebView, remote images or arbitrary Android intents. */
data class WikiSpan(val text:String,val bold:Boolean=false,val italic:Boolean=false,val code:Boolean=false,val url:String?=null)
data class WikiBlock(val spans:List<WikiSpan>,val level:Int=0,val anchor:String?=null,val kind:String="paragraph")
private val wikiPageRoute=Regex("^#wiki\\?page=([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})$",RegexOption.IGNORE_CASE)
fun wikiLinkedPage(value:String):String?=wikiPageRoute.matchEntire(value)?.groupValues?.get(1)
fun wikiSafeUrl(value:String):String? {
 if(wikiLinkedPage(value)!=null)return value
 if(Regex("^#[-\\w]+$").matches(value))return value
 if(value.any{it.isWhitespace()||it.code<32||it=='\\'})return null
 return try{val uri=URI(value);if(uri.scheme in listOf("http","https")&&!uri.host.isNullOrBlank()&&uri.rawUserInfo==null)value else null}catch(_:Exception){null}
}
fun parseWikiMarkdown(source:String):List<WikiBlock> {
 val root=Parser.builder().build().parse(source.take(100000));val result=mutableListOf<WikiBlock>();var headings=0
 fun spans(node:Node,bold:Boolean=false,italic:Boolean=false,code:Boolean=false,url:String?=null):List<WikiSpan>{
  if(node is Text)return listOf(WikiSpan(node.literal,bold,italic,code,url))
  if(node is Code)return listOf(WikiSpan(node.literal,bold,italic,true,url))
  if(node is HtmlInline)return listOf(WikiSpan(node.literal))
  if(node is SoftLineBreak||node is HardLineBreak)return listOf(WikiSpan("\n"))
  val out=mutableListOf<WikiSpan>();var child=node.firstChild
  while(child!=null){out+=spans(child,bold||node is StrongEmphasis,italic||node is Emphasis,code,if(node is Link)wikiSafeUrl(node.destination)else if(node is Image)null else url);child=child.next}
  return out
 }
 fun blocks(node:Node){
  when(node){
   is Heading->{headings++;result+=WikiBlock(spans(node),node.level,"heading-$headings")}
   is Paragraph->result+=WikiBlock(spans(node),kind=if(node.parent is ListItem)"bullet" else if(node.parent is BlockQuote)"quote" else "paragraph")
   is FencedCodeBlock->result+=WikiBlock(listOf(WikiSpan(node.literal,code=true)),kind="code")
   is IndentedCodeBlock->result+=WikiBlock(listOf(WikiSpan(node.literal,code=true)),kind="code")
   is HtmlBlock->result+=WikiBlock(listOf(WikiSpan(node.literal)))
   is ThematicBreak->result+=WikiBlock(emptyList(),kind="rule")
   else->{var child=node.firstChild;while(child!=null){blocks(child);child=child.next}}
  }
 }
 blocks(root);return result
}
