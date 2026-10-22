package org.vowen.app

import androidx.activity.compose.BackHandler
import androidx.compose.foundation.ExperimentalFoundationApi
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.relocation.BringIntoViewRequester
import androidx.compose.foundation.relocation.bringIntoViewRequester
import androidx.compose.foundation.text.ClickableText
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalConfiguration
import androidx.compose.ui.platform.LocalUriHandler
import androidx.compose.ui.text.*
import androidx.compose.ui.text.font.FontStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.window.Dialog
import kotlinx.coroutines.launch

@Composable
fun NativeWikiScreen(state:WikiState,isAdmin:Boolean,ru:Boolean) {
 val scope=rememberCoroutineScope();var drawer by remember{mutableStateOf(false)};var sections by remember{mutableStateOf(false)};var discard by remember{mutableStateOf(false)};var pending by remember{mutableStateOf<(() -> Unit)?>(null)}
 fun navigate(block:()->Unit){if(state.dirty){pending=block;discard=true}else{state.discardDraft();block()}}
 fun page(uid:String){navigate{scope.launch{state.openPage(uid)};drawer=false}}
 fun section(uid:String){navigate{state.openSection(uid);drawer=false}}
 LaunchedEffect(state){state.action{state.refresh()}}
 BackHandler(state.editing||drawer||state.hasBack){when{drawer->drawer=false;state.editing->navigate{state.discardDraft()};else->scope.launch{state.back()}}}
 if(discard)AlertDialog(onDismissRequest={discard=false},title={Text(if(ru)"Несохранённые изменения" else "Unsaved changes")},text={Text(if(ru)"Уйти без сохранения?" else "Discard changes?")},confirmButton={TextButton(onClick={state.discardDraft();discard=false;pending?.invoke();pending=null}){Text(if(ru)"Уйти" else "Leave")}},dismissButton={TextButton(onClick={discard=false}){Text(if(ru)"Остаться" else "Stay")}})
 if(drawer)Dialog(onDismissRequest={drawer=false}){Surface(shape=MaterialTheme.shapes.large){Column(Modifier.widthIn(max=380.dp).heightIn(max=600.dp).verticalScroll(rememberScrollState()).padding(20.dp)){Text(if(ru)"Разделы" else "Sections",style=MaterialTheme.typography.headlineSmall);TextButton(onClick={section("")}){Text(if(ru)"Вся библиотека" else "Library")};state.tree?.let{WikiNativeTree(it,null,state.page?.uid,{page(it)},{section(it)})};TextButton(onClick={drawer=false}){Text(if(ru)"Закрыть" else "Close")}}}}
 if(sections&&isAdmin)NativeWikiSections(state,ru){sections=false}
 Column(Modifier.fillMaxWidth(),verticalArrangement=Arrangement.spacedBy(16.dp)){
  Text("Wiki",style=MaterialTheme.typography.headlineLarge)
  Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.SpaceBetween){TextButton(onClick={drawer=true}){Text(if(ru)"Разделы" else "Sections")};if(isAdmin)TextButton(onClick={navigate{scope.launch{state.edit(null)}}}){Text(if(ru)"Новая страница" else "New page")}}
  OutlinedTextField(value=state.query,onValueChange={state.query=it.take(200)},label={Text(if(ru)"Поиск по Wiki" else "Search Wiki")},modifier=Modifier.fillMaxWidth(),singleLine=true,trailingIcon={TextButton(onClick={navigate{scope.launch{state.search()}}}){Text(if(ru)"Найти" else "Search")}})
  if(isAdmin){Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.spacedBy(6.dp)){listOf("published","drafts","archived").forEach{mode->TextButton(onClick={navigate{scope.launch{state.list(mode)}}}){Text(when(mode){"drafts"->if(ru)"Черновики" else "Drafts";"archived"->if(ru)"Архив" else "Archive";else->if(ru)"Библиотека" else "Library"})}}};Row{TextButton(onClick={sections=true},enabled=!state.busy){Text(if(ru)"Управление разделами" else "Manage sections")};TextButton(onClick={scope.launch{state.action{val result=state.api.seed();state.refresh();state.notice=if(ru)"Добавлено: ${result.created}" else "Added: ${result.created}"}}},enabled=!state.busy){Text(if(ru)"Импорт" else "Import")}}}
  state.error?.let{Text(if(ru)"Действие не выполнено. Текст сохранён в этом окне. Проверьте соединение, версию и права." else "Action failed. Your text is kept here. Check connection, version and access.",color=MaterialTheme.colorScheme.error)}
  state.notice?.let{Text(it)}
  if(state.busy)LinearProgressIndicator(Modifier.fillMaxWidth())
  if(state.editing){NativeWikiEditor(state,isAdmin,ru){navigate{state.discardDraft()}}}else{
   Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.spacedBy(24.dp)){
    if(LocalConfiguration.current.screenWidthDp>=1100)state.tree?.let{tree->Column(Modifier.width(220.dp).heightIn(max=640.dp).verticalScroll(rememberScrollState())){WikiNativeTree(tree,null,state.page?.uid,{page(it)},{section(it)})}}
    Column(Modifier.weight(1f).widthIn(max=780.dp),verticalArrangement=Arrangement.spacedBy(14.dp)){
     when{
      state.mode!="published"&&isAdmin->{state.adminRows.forEach{p->TextButton(onClick={scope.launch{state.edit(p.uid)}},modifier=Modifier.fillMaxWidth()){Text(p.document.title.ifBlank{if(ru)"Без названия" else "Untitled"})}};if(state.adminRows.isEmpty())Text(if(ru)"Здесь пока пусто." else "Nothing here yet.");Row{TextButton(onClick={scope.launch{state.list(state.mode,(state.adminOffset-50).coerceAtLeast(0))}},enabled=state.adminOffset>0){Text("←")};TextButton(onClick={scope.launch{state.list(state.mode,state.adminOffset+50)}},enabled=state.adminRows.size==50){Text("→")}}}
      state.results!=null->{val result=state.results!!;Text(if(ru)"Найдено: ${result.total}" else "Found: ${result.total}");result.items.forEach{p->WikiNativePageRow(p){page(p.uid)}};Row{TextButton(onClick={scope.launch{state.search((result.offset-50).coerceAtLeast(0))}},enabled=result.offset>0){Text("←")};TextButton(onClick={scope.launch{state.search(result.offset+50)}},enabled=result.offset+50<result.total){Text("→")}}}
      state.page!=null->{val p=state.page!!;WikiNativeArticle(p,state.tree,state.api,ru,isAdmin,{section(it)},{page(it)}){scope.launch{state.edit(p.uid)}}}
      else->{val selected=state.tree?.sections?.find{it.uid==state.section};Text(selected?.title?:if(ru)"Библиотека знаний" else "Knowledge library",style=MaterialTheme.typography.headlineMedium);if(!selected?.description.isNullOrBlank())Text(selected!!.description);state.tree?.sections?.filter{(it.parent_uid?:"")==state.section}?.forEach{s->OutlinedButton(onClick={section(s.uid)},modifier=Modifier.fillMaxWidth().heightIn(min=60.dp)){Text(s.title)}};state.tree?.pages?.filter{it.section_uid==state.section}?.forEach{p->WikiNativePageRow(p){page(p.uid)}}}
     }
    }
   }
  }
 }
}

@Composable private fun WikiNativePageRow(page:WikiPageSummary,onClick:()->Unit){TextButton(onClick=onClick,modifier=Modifier.fillMaxWidth().heightIn(min=48.dp)){Column(Modifier.fillMaxWidth()){Text(page.title,style=MaterialTheme.typography.titleMedium);if(page.summary.isNotBlank())Text(page.summary,maxLines=2,style=MaterialTheme.typography.bodySmall)}}}
@Composable private fun WikiNativeTree(tree:WikiTreeView,parent:String?,selected:String?,page:(String)->Unit,section:(String)->Unit){
 tree.sections.filter{it.parent_uid==parent}.forEach{s->var expanded by remember(s.uid){mutableStateOf(false)};Row{TextButton(onClick={expanded=!expanded}){Text(if(expanded)"⌄" else "›")};TextButton(onClick={section(s.uid);expanded=true}){Text(s.title)}};if(expanded)Column(Modifier.padding(start=16.dp)){WikiNativeTree(tree,s.uid,selected,page,section)}}
 tree.pages.filter{it.section_uid==parent}.forEach{p->TextButton(onClick={page(p.uid)},modifier=Modifier.fillMaxWidth()){Text((if(selected==p.uid)"• " else "")+p.title)}}
}

@Composable private fun WikiNativeArticle(page:WikiPageView,tree:WikiTreeView?,api:WikiApi,ru:Boolean,admin:Boolean,onSection:(String)->Unit,onPage:(String)->Unit,onEdit:()->Unit){
 var relatedReferences by remember(page.revision_uid){mutableStateOf<List<ReferenceEntry>>(emptyList())}
 var referenceError by remember(page.revision_uid){mutableStateOf(false)}
 LaunchedEffect(page.revision_uid){try{val found=mutableListOf<ReferenceEntry>();for((kind,ids) in listOf("practices" to (page.document.practice_uids.orEmpty()+listOfNotNull(page.practice_uid)),"poses" to (page.document.pose_uids.orEmpty()+listOfNotNull(page.pose_uid)),"devices" to (page.document.device_uids.orEmpty()+listOfNotNull(page.device_uid)))){if(ids.isNotEmpty())found+=api.references(kind).filter{it.uid in ids}};relatedReferences=found}catch(e:kotlinx.coroutines.CancellationException){throw e}catch(_:Exception){referenceError=true}}
 val crumbs=remember(page.document.section_uid,tree){val list=mutableListOf<WikiSectionView>();var uid:String?=page.document.section_uid;repeat(8){val s=tree?.sections?.find{it.uid==uid};if(s!=null){list.add(0,s);uid=s.parent_uid}};list}
 crumbs.forEach{s->TextButton(onClick={onSection(s.uid)}){Text(s.title)}}
 Text(page.document.title,style=MaterialTheme.typography.headlineLarge)
 page.document.summary?.takeIf{it.isNotBlank()}?.let{Text(it)}
 if(admin)TextButton(onClick=onEdit){Text(if(ru)"Редактировать" else "Edit")}
 WikiThumbnail(api,page.document.thumbnail,Modifier.fillMaxWidth().height(180.dp))
 WikiMarkdownBody(page.document.body?:"",onPage=onPage)
 val uri=LocalUriHandler.current
 page.document.sources.orEmpty().forEach{s->wikiSafeUrl(s.url)?.let{url->TextButton(onClick={uri.openUri(url)}){Text(s.name?:s.url)}}}
 if(relatedReferences.isNotEmpty())Text(if(ru)"В справочниках" else "Reference details",style=MaterialTheme.typography.titleLarge)
 relatedReferences.forEach{reference->var expanded by remember(reference.uid){mutableStateOf(false)};TextButton(onClick={expanded=!expanded}){Text(reference.name)};if(expanded)Text(reference.description)}
 if(referenceError)Text(if(ru)"Связанные справочники временно недоступны." else "Reference details unavailable.")
 page.related_pages.forEach{p->WikiNativePageRow(p){onPage(p.uid)}}
}

@OptIn(ExperimentalFoundationApi::class)
@Composable internal fun WikiMarkdownBody(source:String,onPage:((String)->Unit)?=null){
 val blocks=remember(source){parseWikiMarkdown(source)};val requests=remember(source){blocks.filter{it.anchor!=null}.associate{it.anchor!! to BringIntoViewRequester()}};val scope=rememberCoroutineScope();val uri=LocalUriHandler.current
 Column(verticalArrangement=Arrangement.spacedBy(16.dp)){
  if(requests.isNotEmpty()){var toc by remember{mutableStateOf(false)};TextButton(onClick={toc=!toc}){Text("☷")};if(toc)blocks.filter{it.anchor!=null}.forEach{b->TextButton(onClick={scope.launch{requests[b.anchor]?.bringIntoView()}}){Text(b.spans.joinToString(""){it.text})}}}
  blocks.forEach{b->if(b.kind=="rule")HorizontalDivider()else{
   val text=buildAnnotatedString{if(b.kind=="bullet")append("• ");b.spans.forEach{s->if(s.url!=null)pushStringAnnotation("url",s.url);withStyle(SpanStyle(fontWeight=if(s.bold)FontWeight.Bold else FontWeight.Normal,fontStyle=if(s.italic)FontStyle.Italic else FontStyle.Normal)){append(s.text)};if(s.url!=null)pop()}}
   val style=if(b.level>0)MaterialTheme.typography.headlineSmall else MaterialTheme.typography.bodyLarge
   ClickableText(text=text,style=style.copy(color=MaterialTheme.colorScheme.onBackground),modifier=(b.anchor?.let{Modifier.bringIntoViewRequester(requests.getValue(it))}?:Modifier),onClick={offset->text.getStringAnnotations("url",offset,offset).firstOrNull()?.item?.let{url->val target=wikiLinkedPage(url);if(target!=null)onPage?.invoke(target)else if(url.startsWith("#"))scope.launch{requests[url.drop(1)]?.bringIntoView()}else uri.openUri(url)}})
  }}
 }
}
