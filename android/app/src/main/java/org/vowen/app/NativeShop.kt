package org.vowen.app

import androidx.compose.foundation.Image
import androidx.compose.foundation.clickable
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.animation.animateContentSize
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.sp
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.interaction.collectIsDraggedAsState
import androidx.compose.foundation.gestures.scrollBy
import androidx.compose.ui.MotionDurationScale
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.platform.LocalView
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import kotlinx.coroutines.isActive
import kotlin.coroutines.coroutineContext
import androidx.compose.foundation.lazy.items
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.platform.LocalContext
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.unit.dp
import java.util.UUID

data class EconomyActions(val load:(String)->Unit,val credit:(String,CreditCommand)->Unit,val listing:(String,ListingCommand)->Unit,val purchase:(ShopListing,String)->Unit,val toggle:(ShopListing)->Unit,val audience:((String,(List<ShopListing>)->Unit)->Unit)?=null,val saveAudience:((String,AvailabilityCommand)->Unit)?=null,val createProduct:((ShopProductContent)->Unit)?=null,val editProduct:((ShopListing,ShopProductEdit)->Unit)?=null,val removeProduct:((ShopListing)->Unit)?=null,val relationToggle:((ShopListing)->Unit)?=null)
fun rewardCover(cover:String?)=when(cover){
 "breakfast" -> R.drawable.reward_breakfast
 "cinema" -> R.drawable.reward_cinema
 "walk" -> R.drawable.reward_walk
 "reward-005" -> R.drawable.reward_005
 "reward-006" -> R.drawable.reward_006
 "reward-007" -> R.drawable.reward_007
 "reward-008" -> R.drawable.reward_008
 "reward-009" -> R.drawable.reward_009
 "reward-010" -> R.drawable.reward_010
 "reward-011" -> R.drawable.reward_011
 "reward-012" -> R.drawable.reward_012
 "reward-013" -> R.drawable.reward_013
 "reward-014" -> R.drawable.reward_014
 "reward-015" -> R.drawable.reward_015
 "reward-016" -> R.drawable.reward_016
 "reward-017" -> R.drawable.reward_017
 "reward-018" -> R.drawable.reward_018
 "reward-019" -> R.drawable.reward_019
 "reward-020" -> R.drawable.reward_020
 "reward-021" -> R.drawable.reward_021
 "reward-022" -> R.drawable.reward_022
 "reward-023" -> R.drawable.reward_023
 "reward-024" -> R.drawable.reward_024
 "reward-025" -> R.drawable.reward_025
 "reward-026" -> R.drawable.reward_026
 "reward-027" -> R.drawable.reward_027
 "reward-028" -> R.drawable.reward_028
 "reward-029" -> R.drawable.reward_029
 "reward-030" -> R.drawable.reward_030
 "reward-031" -> R.drawable.reward_031
 "reward-032" -> R.drawable.reward_032
 "reward-033" -> R.drawable.reward_033
 "reward-034" -> R.drawable.reward_034
 "reward-035" -> R.drawable.reward_035
 "reward-036" -> R.drawable.reward_036
 "reward-037" -> R.drawable.reward_037
 "reward-038" -> R.drawable.reward_038
 "reward-039" -> R.drawable.reward_039
 "reward-040" -> R.drawable.reward_040
 "reward-041" -> R.drawable.reward_041
 "reward-042" -> R.drawable.reward_042
 "reward-043" -> R.drawable.reward_043
 "reward-044" -> R.drawable.reward_044
 "reward-045" -> R.drawable.reward_045
 "reward-046" -> R.drawable.reward_046
 "reward-047" -> R.drawable.reward_047
 "reward-048" -> R.drawable.reward_048
 "reward-049" -> R.drawable.reward_049
 "reward-050" -> R.drawable.reward_050
 "reward-051" -> R.drawable.reward_051
 "reward-052" -> R.drawable.reward_052
 "reward-053" -> R.drawable.reward_053
 "reward-054" -> R.drawable.reward_054
 "reward-055" -> R.drawable.reward_055
 "reward-056" -> R.drawable.reward_056
 "reward-057" -> R.drawable.reward_057
 "reward-058" -> R.drawable.reward_058
 "reward-059" -> R.drawable.reward_059
 "reward-060" -> R.drawable.reward_060
 "reward-061" -> R.drawable.reward_061
 "reward-062" -> R.drawable.reward_062
 "reward-063" -> R.drawable.reward_063
 "reward-064" -> R.drawable.reward_064
 "reward-065" -> R.drawable.reward_065
 "reward-066" -> R.drawable.reward_066
 "reward-067" -> R.drawable.reward_067
 "reward-068" -> R.drawable.reward_068
 "reward-069" -> R.drawable.reward_069
 "reward-070" -> R.drawable.reward_070
 "reward-071" -> R.drawable.reward_071
 "reward-072" -> R.drawable.reward_072
 "reward-073" -> R.drawable.reward_073
 "reward-074" -> R.drawable.reward_074
 "reward-075" -> R.drawable.reward_075
 "reward-076" -> R.drawable.reward_076
 "reward-077" -> R.drawable.reward_077
 "reward-078" -> R.drawable.reward_078
 "reward-079" -> R.drawable.reward_079
 "reward-080" -> R.drawable.reward_080
 "reward-081" -> R.drawable.reward_081
 "reward-082" -> R.drawable.reward_082
 "reward-083" -> R.drawable.reward_083
 "reward-084" -> R.drawable.reward_084
 "reward-085" -> R.drawable.reward_085
 "reward-086" -> R.drawable.reward_086
 "reward-087" -> R.drawable.reward_087
 "reward-088" -> R.drawable.reward_088
 "reward-089" -> R.drawable.reward_089
 "reward-090" -> R.drawable.reward_090
 "reward-091" -> R.drawable.reward_091
 "reward-092" -> R.drawable.reward_092
 "reward-093" -> R.drawable.reward_093
 "reward-094" -> R.drawable.reward_094
 "reward-095" -> R.drawable.reward_095
 "reward-096" -> R.drawable.reward_096
 "reward-097" -> R.drawable.reward_097
 "reward-098" -> R.drawable.reward_098
 "reward-099" -> R.drawable.reward_099
 "reward-100" -> R.drawable.reward_100
 "reward-101" -> R.drawable.reward_101
 "reward-102" -> R.drawable.reward_102
 "reward-103" -> R.drawable.reward_103
 else -> R.drawable.reward_dinner
}

@Composable fun NativeShop(member:Member,data:WorkspaceState,busy:Boolean,completed:Int,actions:EconomyActions,relationId:String?=null,contextChanged:(String)->Unit={},create:()->Unit={},showContext:Boolean=true,edit:(ShopListing)->Unit={}){
 val ru=member.language=="ru"
 fun t(en:String,rus:String)=if(ru)rus else en
 var rid by remember(member.id,relationId){mutableStateOf(relationId?:"")};var expanded by remember{mutableStateOf(false)}
 val relation=data.relations.find{it.id==rid};val manager=member.shop_role=="dominant";val upper=relation?.dominant_user_id==member.id
 val allowed=relation?.let{it.status=="active"&&"rewards.grant" in it.scopes&&it.consent_user_ids.size==2&&!member.paused}?:false
 val wallet=data.wallet?.takeIf{it.relation_id==rid}
 var query by remember{mutableStateOf("")}
 val searchTerms=query.lowercase().replace('ё','е').trim().split(Regex("\\s+")).filter{it.isNotBlank()}
 val listings=data.shop.filter{item->val text=(item.title+" "+item.description).lowercase().replace('ё','е');searchTerms.all{text.contains(it)}}
 var detail by remember(rid){mutableStateOf<ShopListing?>(null)};var removing by remember{mutableStateOf(false)}
 var crediting by remember(rid){mutableStateOf(false)};var history by remember(rid){mutableStateOf(false)}
 LaunchedEffect(rid){actions.load(rid)}
 LaunchedEffect(completed){crediting=false;detail=null;removing=false}
 if(showContext)Box{TextButton(onClick={expanded=true},enabled=!busy){Text(relation?.let{r->data.participants.find{it.id==if(upper)r.submissive_user_id else r.dominant_user_id}?.display_name}?:t("Choose relationship","Выберите отношения"))};DropdownMenu(expanded,{expanded=false}){data.relations.forEach{r->DropdownMenuItem(text={Text(data.participants.find{it.id==if(r.dominant_user_id==member.id)r.submissive_user_id else r.dominant_user_id}?.display_name?:t("Participant","Участник"))},onClick={rid=r.id;contextChanged(r.id);expanded=false})}}}
 if(member.shop_role in listOf("bottom","switch")&&relation?.submissive_user_id==member.id)Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.SpaceBetween){Text((wallet?.balance?.toString()?:"—")+t(" coins"," монет"),style=MaterialTheme.typography.labelLarge);if((wallet?.reserved?:0)>0)Text(t("Reserved: ","В резерве: ")+wallet?.reserved,style=MaterialTheme.typography.bodySmall)}
 if(manager)Row(horizontalArrangement=Arrangement.spacedBy(8.dp)){OutlinedButton(onClick=create,enabled=!busy&&!member.paused){Text(t("New product","Новый товар"))};if(upper)OutlinedButton(onClick={crediting=true},enabled=!busy&&allowed){Text(t("Grant coins","Начислить"))}}
 if(data.shop.isNotEmpty())OutlinedTextField(value=query,onValueChange={query=it.take(200)},singleLine=true,label={Text(t("Search products","Поиск товаров"))},modifier=Modifier.fillMaxWidth(),trailingIcon={if(query.isNotEmpty())IconButton(onClick={query=""}){Icon(painterResource(android.R.drawable.ic_menu_close_clear_cancel),t("Clear search","Очистить поиск"))}})
 if(query.isNotBlank())Text(if(listings.isEmpty())t("No matching products. Try another search.","Ничего не найдено. Попробуйте другой запрос.") else t("Found: ","Найдено: ")+listings.size,style=MaterialTheme.typography.bodySmall)
 if(data.shop.isEmpty())Text(t("No available products.","Нет доступных товаров."),style=MaterialTheme.typography.bodySmall)
 fun inspect(item:ShopListing){detail=item;if(item.purchase_relation_id!=null)actions.load(item.purchase_relation_id)}
 val filmState=rememberLazyListState();var filmPaused by remember{mutableStateOf(false)}
 val dragging by filmState.interactionSource.collectIsDraggedAsState()
 var restUntil by remember{mutableLongStateOf(0L)}
 val density=LocalDensity.current.density;val hostView=LocalView.current
 LaunchedEffect(dragging){if(dragging)restUntil=android.os.SystemClock.uptimeMillis()+10000 else if(restUntil>0)restUntil=android.os.SystemClock.uptimeMillis()+10000}
 LaunchedEffect(listings.map{it.id},filmPaused,busy,detail,density,query){
  if(listings.isEmpty()||query.isNotBlank()||filmPaused||busy||detail!=null)return@LaunchedEffect
  var previous=0L
  while(isActive){
   val now=withFrameNanos{it};val delta=if(previous==0L)0f else ((now-previous)/1000000000f).coerceAtMost(.048f);previous=now
   if((coroutineContext[MotionDurationScale]?.scaleFactor?:1f)>0f&&hostView.hasWindowFocus()&&!filmState.isScrollInProgress&&android.os.SystemClock.uptimeMillis()>=restUntil){
    filmState.scrollBy(delta*12f*density)
    if(filmState.firstVisibleItemIndex>=listings.size)filmState.scrollToItem(filmState.firstVisibleItemIndex-listings.size,filmState.firstVisibleItemScrollOffset)
   }
  }
 }
 if(listings.isNotEmpty()&&query.isBlank())Box(Modifier.fillMaxWidth()){
  LazyRow(state=filmState,modifier=Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.spacedBy(8.dp)){
   itemsIndexed(listings+listings,key={index,item->item.id+":"+index}){_,item->IconButton(onClick={inspect(item)},enabled=!busy,modifier=Modifier.size(104.dp,120.dp)){
    NativeRewardCover(item.cover,Modifier.fillMaxSize().clip(RoundedCornerShape(8.dp)),maxSidePx=256,disabled=!item.active)
   }}
  }
  FilledTonalIconToggleButton(checked=filmPaused,onCheckedChange={filmPaused=it},modifier=Modifier.align(androidx.compose.ui.Alignment.BottomEnd).size(44.dp)){
   Icon(painterResource(if(filmPaused)android.R.drawable.ic_media_play else android.R.drawable.ic_media_pause),if(filmPaused)t("Resume automatic scrolling","Продолжить автопрокрутку") else t("Pause automatic scrolling","Остановить автопрокрутку"))
  }
 }
 BoxWithConstraints(Modifier.fillMaxWidth()){
  val wideLayout=maxWidth>=700.dp
  val categories=rewardCategories.filter{c->listings.any{(it.category?:"together")==c.id}}
  Column(verticalArrangement=Arrangement.spacedBy(18.dp)){
   categories.chunked(if(wideLayout)2 else 1).forEach{group->
    Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.spacedBy(24.dp)){
     group.forEach{c->Column(Modifier.weight(1f)){
      NativeShopCollection(t(c.en,c.ru),listings.filter{(it.category?:"together")==c.id},4,busy,ru,::inspect)
     }}
     if(wideLayout&&group.size==1)Spacer(Modifier.weight(1f))
    }
   }
  }
 }
 if(wallet!=null&&(manager||(member.shop_role in listOf("bottom","switch")&&relation?.submissive_user_id==member.id))){TextButton(onClick={history=!history}){Text(t("Coin history","История монет"))};if(history)wallet.entries.forEach{e->Text((if(e.amount>0)"+" else "")+e.amount+" · "+e.created_at,style=MaterialTheme.typography.bodySmall);if(e.comment.isNotBlank())Text(e.comment,style=MaterialTheme.typography.bodySmall)}}
 if(crediting)MarketTaskDialog(t("Grant coins","Начислить монеты"),busy,{crediting=false}){
  var amount by remember(rid){mutableStateOf("10")};var comment by remember(rid){mutableStateOf("")};val key=remember(rid,amount,comment){UUID.randomUUID().toString()}
  OutlinedTextField(amount,{amount=it},label={Text(t("Coins","Монеты"))},enabled=!busy,modifier=Modifier.fillMaxWidth())
  OutlinedTextField(comment,{if(it.length<=2000)comment=it},label={Text(t("Comment","Комментарий"))},enabled=!busy,modifier=Modifier.fillMaxWidth())
  OutlinedButton(onClick={actions.credit(rid,CreditCommand(amount=amount.toInt(),comment=comment,idempotency_key=key))},enabled=!busy&&allowed&&manager&&comment.isNotBlank()&&amount.toIntOrNull()?.let{it in 1..1000000000}==true){Text(t("Confirm credit","Подтвердить начисление"))}
 }
 detail?.let{item->val key=remember(item.id,item.purchase_relation_id,completed){UUID.randomUUID().toString()};val itemWallet=data.wallet?.takeIf{it.relation_id==item.purchase_relation_id};MarketTaskDialog(item.title,busy,{detail=null;removing=false}){
  NativeRewardCover(item.cover,Modifier.fillMaxWidth().heightIn(max=150.dp).aspectRatio(4f/3f),disabled=!item.active)
  Text("${item.price} "+t("coins","монет"),style=MaterialTheme.typography.titleMedium);Text(item.description);if(item.conditions.isNotBlank())Text(item.conditions)
  if(item.can_manage==true){
   if(removing){Text(t("Remove this product? Purchases and history are preserved.","Удалить товар? Покупки и история сохранятся."));Row{OutlinedButton(onClick={actions.removeProduct?.invoke(item)},enabled=!busy&&actions.removeProduct!=null){Text(t("Remove product","Удалить товар"))};TextButton(onClick={removing=false},enabled=!busy){Text(t("Cancel","Отмена"))}}}
   else Row{IconButton(onClick={edit(item);detail=null},enabled=!busy){Icon(painterResource(android.R.drawable.ic_menu_edit),t("Edit product","Редактировать товар"))};IconButton(onClick={actions.toggle(item)},enabled=!busy){Icon(painterResource(android.R.drawable.ic_lock_power_off),if(item.global_enabled!=false)t("Disable product","Выключить товар") else t("Enable product","Включить товар"))};IconButton(onClick={removing=true},enabled=!busy){Icon(painterResource(android.R.drawable.ic_menu_delete),t("Remove product","Удалить товар"))}}
  }
  if(item.can_toggle==true){val target=data.relations.find{it.id==item.toggle_relation_id}?.submissive_user_id;val targetName=data.participants.find{it.id==target}?.display_name?:t("your subordinate","подчинённого");Row(verticalAlignment=androidx.compose.ui.Alignment.CenterVertically){Switch(item.relation_enabled!=false,{actions.relationToggle?.invoke(item)},enabled=!busy&&actions.relationToggle!=null);Text(t("Available for ","Доступен для ")+targetName)}}
  if(item.purchase_relation_id!=null){Text(t("Coins are reserved until your dominant approves.","Монеты резервируются до разрешения доминанта."),style=MaterialTheme.typography.bodySmall);if(itemWallet!=null&&itemWallet.balance<item.price)Text(t("Not enough available coins.","Недостаточно свободных монет."));OutlinedButton(onClick={actions.purchase(item,key)},enabled=!busy&&!member.paused&&item.active&&itemWallet!=null&&itemWallet.balance>=item.price){Text(t("Request for ","Запросить за ")+item.price)}}
  else if(item.can_manage!=true&&item.can_toggle!=true)Text(if(member.shop_role in listOf("bottom","switch"))t("Choose your dominant in the avatars above.","Выберите доминанта через аватары сверху.") else t("Viewing only","Только просмотр"),style=MaterialTheme.typography.bodySmall)
 }}
}

@Composable private fun NativeShopCollection(title:String,items:List<ShopListing>,initial:Int,busy:Boolean,ru:Boolean,open:(ShopListing)->Unit){
 if(items.isEmpty())return
 var limit by remember(title){mutableStateOf(initial)}
 Column(Modifier.fillMaxWidth().animateContentSize(),verticalArrangement=Arrangement.spacedBy(0.dp)){
  Row(Modifier.padding(bottom=6.dp),horizontalArrangement=Arrangement.spacedBy(8.dp),verticalAlignment=androidx.compose.ui.Alignment.CenterVertically){Text(title,style=MaterialTheme.typography.titleLarge);Text(items.size.toString(),style=MaterialTheme.typography.labelSmall,color=MaterialTheme.colorScheme.onSurfaceVariant)}
  items.take(limit).forEach{item->
   Row(Modifier.fillMaxWidth().clickable(enabled=!busy){open(item)}.padding(vertical=8.dp),horizontalArrangement=Arrangement.spacedBy(8.dp),verticalAlignment=androidx.compose.ui.Alignment.CenterVertically){
    NativeRewardCover(item.cover,Modifier.size(54.dp,60.dp).clip(RoundedCornerShape(8.dp)),maxSidePx=160,disabled=!item.active)
    Column(Modifier.weight(1f)){
     Text(item.title,fontSize=17.sp,maxLines=2,overflow=TextOverflow.Ellipsis)
     Text(item.description,style=MaterialTheme.typography.bodySmall,maxLines=2,overflow=TextOverflow.Ellipsis,color=MaterialTheme.colorScheme.onSurfaceVariant)
     if(!item.active)Text(if(ru)"Выключен" else "Disabled",style=MaterialTheme.typography.labelSmall,color=MaterialTheme.colorScheme.tertiary)
    }
    Text(item.price.toString(),style=MaterialTheme.typography.labelLarge,color=MaterialTheme.colorScheme.primary)
    val label=if(item.can_manage==true){if(ru)"Редактировать" else "Edit"}else if(item.can_toggle==true){if(ru)"Доступ" else "Availability"}else if(item.purchase_relation_id!=null){if(ru)"Купить" else "Buy"}else{if(ru)"Подробнее" else "Details"}
    OutlinedIconButton(onClick={open(item)},enabled=!busy,modifier=Modifier.size(44.dp)){
     Icon(painterResource(if(item.can_manage==true)android.R.drawable.ic_menu_edit else if(item.can_toggle==true)android.R.drawable.ic_menu_manage else if(item.purchase_relation_id!=null)android.R.drawable.ic_menu_send else android.R.drawable.ic_menu_info_details),label+": "+item.title,modifier=Modifier.size(20.dp))
    }
   }
   HorizontalDivider(color=MaterialTheme.colorScheme.outlineVariant)
  }
  if(limit>initial)TextButton(onClick={limit=initial},modifier=Modifier.fillMaxWidth().heightIn(min=44.dp)){Text(if(ru)"Свернуть" else "Show less",style=MaterialTheme.typography.labelMedium)}
  if(limit<items.size)TextButton(onClick={limit+=8},modifier=Modifier.fillMaxWidth().heightIn(min=44.dp)){Text((if(ru)"Показать ещё" else "Show more")+" · "+(items.size-limit),style=MaterialTheme.typography.labelMedium)}
 }
}

@Composable private fun MarketTaskDialog(title:String,busy:Boolean,close:()->Unit,content:@Composable ColumnScope.()->Unit){
 var entered by remember{mutableStateOf(false)}
 val reveal by animateFloatAsState(if(entered)1f else 0f,tween(220),label="shop-dialog")
 LaunchedEffect(Unit){entered=true}
 val maxHeight=androidx.compose.ui.platform.LocalConfiguration.current.screenHeightDp.dp*.85f
 androidx.compose.ui.window.Dialog(onDismissRequest={if(!busy)close()},properties=androidx.compose.ui.window.DialogProperties(usePlatformDefaultWidth=false)){
  Surface(Modifier.widthIn(max=520.dp).fillMaxWidth().graphicsLayer{alpha=reveal;translationY=(1f-reveal)*16.dp.toPx()},shape=androidx.compose.foundation.shape.RoundedCornerShape(12.dp)){
   Column(Modifier.heightIn(max=maxHeight).padding(16.dp).verticalScroll(rememberScrollState()),verticalArrangement=Arrangement.spacedBy(12.dp)){
    Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.SpaceBetween){Text(title,style=MaterialTheme.typography.headlineSmall,modifier=Modifier.weight(1f));IconButton(onClick=close,enabled=!busy){Icon(painterResource(android.R.drawable.ic_menu_close_clear_cancel),if(androidx.compose.ui.platform.LocalConfiguration.current.locales[0].language=="ru")"Закрыть" else "Close")}}
    content()
   }
  }
 }
}

@Composable fun NativeRewardCover(cover:String?,modifier:Modifier=Modifier,contentScale:ContentScale=ContentScale.Crop,maxSidePx:Int=640,disabled:Boolean=false){
 val resources=LocalContext.current.resources
 val resource=rewardCover(cover)
 val bitmap=remember(resource,maxSidePx){
  val bounds=android.graphics.BitmapFactory.Options().apply{inJustDecodeBounds=true}
  android.graphics.BitmapFactory.decodeResource(resources,resource,bounds)
  var sample=1
  while(maxOf(bounds.outWidth,bounds.outHeight)/(sample*2)>=maxSidePx)sample*=2
  val options=android.graphics.BitmapFactory.Options().apply{inSampleSize=sample;inScaled=false}
  android.graphics.BitmapFactory.decodeResource(resources,resource,options).asImageBitmap()
 }
 Image(bitmap,null,modifier,contentScale=contentScale,colorFilter=if(disabled)androidx.compose.ui.graphics.ColorFilter.colorMatrix(androidx.compose.ui.graphics.ColorMatrix().apply{setToSaturation(0f)}) else null)
}
