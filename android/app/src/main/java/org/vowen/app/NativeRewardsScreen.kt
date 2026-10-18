package org.vowen.app

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.Image
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.rememberScrollState
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.layout.ContentScale
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.Alignment
import androidx.compose.ui.unit.sp
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.unit.dp
import java.util.UUID
import java.time.OffsetDateTime
import java.time.ZoneId
import java.time.format.DateTimeFormatter
import java.util.Locale

data class RewardActions(val refresh:()->Unit,val save:(RewardDefinition?,RewardContent)->Unit,val grant:(GrantCommand)->Unit,val transition:(RewardGrant,String)->Unit,val economy:EconomyActions?=null)

@Composable fun NativeRewardsScreen(member:Member,data:WorkspaceState,busy:Boolean,actions:RewardActions,completed:Int=0){
 val ru=member.language=="ru"
 fun t(en:String,r:String)=if(ru)r else en
 fun name(id:String)=if(id==member.id)member.display_name else data.participants.find{it.id==id}?.display_name?:t("Participant","Участник")
 fun label(status:String)=if(ru)mapOf("offered" to "Предложено","accepted" to "Принято","declined" to "Отклонено","delivered" to "Вручено","cancelled" to "Отменено","pending_approval" to "Ждёт разрешения","redeemed" to "Погашено")[status]?:status else status
 var rid by remember(member.id){mutableStateOf("")};val relation=data.relations.find{it.id==rid};val upper=relation?.dominant_user_id==member.id;val manager=member.shop_role=="dominant"
 var contextOpen by remember{mutableStateOf(false)}
 var tab by remember{mutableStateOf(0)};var library by remember{mutableStateOf(false)};var opened by remember{mutableStateOf("")}
 var productMode by remember{mutableStateOf(false)};var selectedProduct by remember{mutableStateOf<ShopListing?>(null)};var editing by remember{mutableStateOf(false)};var selected by remember{mutableStateOf<RewardDefinition?>(null)}
 var offering by remember{mutableStateOf<RewardDefinition?>(null)};var recipient by remember{mutableStateOf("")};var expanded by remember{mutableStateOf(false)}
 var requestKey by remember{mutableStateOf(UUID.randomUUID().toString())}
 LaunchedEffect(completed){editing=false;offering=null}
 val grants=data.rewardGrants.filter{g->relation==null||(g.issuer_id==relation.dominant_user_id&&g.recipient_id==relation.submissive_user_id&&(g.relation_id==null||g.relation_id==rid))}
 Column(Modifier.fillMaxWidth(),verticalArrangement=Arrangement.spacedBy(12.dp)){
  Row(Modifier.fillMaxWidth(),verticalAlignment=Alignment.CenterVertically,horizontalArrangement=Arrangement.spacedBy(8.dp)){
   Text(t("Rewards","Награды"),style=MaterialTheme.typography.headlineSmall,modifier=Modifier.weight(1f))
   Box{
    val partner=relation?.let{name(if(upper)it.submissive_user_id else it.dominant_user_id)}
    TextButton(onClick={contextOpen=true},contentPadding=PaddingValues(horizontal=4.dp),modifier=Modifier.semantics{contentDescription=partner?.let{member.display_name+" · "+it}?:t("Choose relationship","Выберите отношения")}){
     RewardAvatar(member.display_name)
     Icon(painterResource(if(relation==null)android.R.drawable.ic_menu_myplaces else if(relation.status=="paused")android.R.drawable.ic_media_pause else if(upper)android.R.drawable.ic_media_next else android.R.drawable.ic_media_previous),null,modifier=Modifier.size(18.dp))
     if(partner!=null)RewardAvatar(partner)
     Icon(painterResource(android.R.drawable.arrow_down_float),null,modifier=Modifier.size(14.dp))
    }
    DropdownMenu(contextOpen,{contextOpen=false}){data.relations.forEach{r->DropdownMenuItem(text={Text(name(if(r.dominant_user_id==member.id)r.submissive_user_id else r.dominant_user_id))},onClick={rid=r.id;contextOpen=false})}}
   }
   if(manager)IconButton(onClick={library=true}){Icon(painterResource(android.R.drawable.ic_menu_agenda),t("Library","Библиотека"))}
  }
  TabRow(selectedTabIndex=tab,containerColor=MaterialTheme.colorScheme.background){listOf(t("Shop","Магазин"),if(member.shop_role in listOf("dominant","switch"))t("Requests","Запросы")+data.rewardGrants.count{it.status=="pending_approval"&&it.issuer_id==member.id}.let{if(it>0)" · $it" else ""} else t("Received","Получено")).forEachIndexed{index,title->Tab(selected=tab==index,onClick={tab=index},text={Text(title)})}}
  if(tab==0)actions.economy?.let{NativeShop(member,data,busy,completed,it,rid,{rid=it},{selected=null;selectedProduct=null;productMode=true;editing=true},showContext=false,edit={item->selectedProduct=item;selected=RewardDefinition(id=item.product_id!!,version_id=item.reward_version_id,revision=item.product_revision?:1,title=item.title,description=item.description,conditions=item.conditions,cover=item.cover,category=item.category);productMode=true;editing=true})}
  if(tab==1){if(grants.isEmpty())Text(t("No rewards here yet.","Здесь пока нет наград."),style=MaterialTheme.typography.bodySmall)
   grants.forEach{g->OutlinedCard(Modifier.fillMaxWidth()){
    TextButton(onClick={opened=if(opened==g.id)"" else g.id},modifier=Modifier.fillMaxWidth()){Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.spacedBy(10.dp)){
     NativeRewardCover(g.cover,Modifier.size(54.dp),maxSidePx=160)
     Column(Modifier.weight(1f)){Text(g.title,style=MaterialTheme.typography.titleMedium);Text(label(g.status),style=MaterialTheme.typography.labelSmall)}
    }}
    if(opened==g.id)Column(Modifier.padding(12.dp),verticalArrangement=Arrangement.spacedBy(8.dp)){
     Text(name(g.issuer_id)+" → "+name(g.recipient_id),style=MaterialTheme.typography.bodySmall);Text(g.description);if(!g.conditions.isNullOrBlank())Text(g.conditions)
     if(g.source=="purchase"){
      g.purchase_amount?.let{Text("$it "+t("coins","монет")+" · "+if(g.status=="pending_approval")t("Reserved","В резерве") else if(g.status in listOf("declined","cancelled"))t("Reservation released","Резерв снят") else t("Charged","Списано"),style=MaterialTheme.typography.bodySmall)}
      if(g.issuer_id==member.id&&g.status=="pending_approval")Row{OutlinedButton(onClick={actions.transition(g,"approve")},enabled=!busy&&!member.paused){Text(t("Approve","Разрешить"))};TextButton(onClick={actions.transition(g,"reject")},enabled=!busy){Text(t("Reject","Отказать"))}}
      if(g.recipient_id==member.id&&g.status=="pending_approval")TextButton(onClick={actions.transition(g,"cancel")},enabled=!busy){Text(t("Withdraw request","Отозвать запрос"))}
      if(g.status=="accepted")OutlinedButton(onClick={actions.transition(g,"redeem")},enabled=!busy){Text(t("Redeem after completion","Погасить после выполнения"))}
     }
     if(g.recipient_id==member.id&&g.status=="offered")Row{OutlinedButton(onClick={actions.transition(g,"accept")},enabled=!busy){Text(t("Accept reward","Принять награду"))};TextButton(onClick={actions.transition(g,"decline")},enabled=!busy){Text(t("Decline","Отклонить"))}}
     if(g.issuer_id==member.id&&g.status=="accepted"&&g.source!="purchase")OutlinedButton(onClick={actions.transition(g,"deliver")},enabled=!busy&&!member.paused){Text(t("Mark delivered","Отметить вручение"))}
     if(g.issuer_id==member.id&&g.source!="purchase"&&g.status in listOf("offered","accepted"))TextButton(onClick={actions.transition(g,"cancel")},enabled=!busy&&!member.paused){Text(t("Cancel reward","Отменить награду"))}
     g.history.forEach{h->Text(label(h.status)+" · "+h.created_at,style=MaterialTheme.typography.bodySmall)}
    }
   }}
  }
 }
 if(library)RuleTaskDialog(t("Reward library","Библиотека наград"),busy,{library=false}){
  OutlinedButton(onClick={library=false;productMode=false;selected=null;editing=true},enabled=!busy&&!member.paused){Text(t("New reward","Новая награда"))}
  data.rewards.forEach{r->Row(horizontalArrangement=Arrangement.spacedBy(12.dp)){
   NativeRewardCover(r.cover,Modifier.size(64.dp),maxSidePx=160)
   Column(Modifier.weight(1f)){Text(r.title,style=MaterialTheme.typography.titleMedium);TextButton(onClick={library=false;productMode=false;selected=r;editing=true},enabled=!busy&&!member.paused){Text(t("Edit","Изменить"))};TextButton(onClick={library=false;offering=r;recipient=relation?.submissive_user_id?:"";requestKey=UUID.randomUUID().toString()},enabled=!busy&&!member.paused){Text(t("Offer reward","Выдать награду"))}}
  }}
 }
 if(editing)key(selected?.id,selected?.revision){
  var title by remember{mutableStateOf(selected?.title?:"")};var description by remember{mutableStateOf(selected?.description?:"")};var conditions by remember{mutableStateOf(selected?.conditions?:"")}
  var price by remember{mutableStateOf((selectedProduct?.price?:10).toString())};var publicProduct by remember{mutableStateOf(selectedProduct?.audience_all?:true)}
  var cover by remember{mutableStateOf(selected?.cover?:"dinner")};var category by remember{mutableStateOf(selected?.category?:"dates")}
  RuleTaskDialog(if(productMode){if(selected==null)t("New product","Новый товар") else t("Edit product","Редактирование товара")}else if(selected==null)t("New reward","Новая награда") else t("Edit reward","Редактирование награды"),busy,{editing=false}){
   OutlinedTextField(title,{if(it.length<=200)title=it},label={Text(t("Title","Название"))},enabled=!busy,modifier=Modifier.fillMaxWidth())
   OutlinedTextField(description,{if(it.length<=10000)description=it},label={Text(t("Description","Описание"))},enabled=!busy,modifier=Modifier.fillMaxWidth())
   OutlinedTextField(conditions,{if(it.length<=10000)conditions=it},label={Text(t("Conditions","Условия"))},enabled=!busy,modifier=Modifier.fillMaxWidth())
   if(productMode){OutlinedTextField(price,{price=it},label={Text(t("Price in coins","Цена в монетах"))},modifier=Modifier.fillMaxWidth(),enabled=!busy);Row{Checkbox(publicProduct,{publicProduct=it},enabled=!busy);Text(t("Available to everyone","Доступен всем"),modifier=Modifier.padding(top=12.dp))}}
   Text(t("Cover","Обложка"),style=MaterialTheme.typography.labelMedium)
   if(cover.startsWith("reward-"))NativeRewardCover(cover,Modifier.fillMaxWidth().height(140.dp))
   Row(Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()),horizontalArrangement=Arrangement.spacedBy(8.dp)){listOf("dinner","breakfast","cinema","walk").forEach{c->OutlinedCard(onClick={cover=c},modifier=Modifier.width(80.dp),border=BorderStroke(if(cover==c)2.dp else 1.dp,if(cover==c)MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.outlineVariant)){Image(painterResource(rewardCover(c)),c,Modifier.fillMaxWidth().aspectRatio(4f/3f),contentScale=ContentScale.Crop)}}}
   var categoryMenu by remember{mutableStateOf(false)}
   Box{
    OutlinedButton(onClick={categoryMenu=true}){Text(rewardCategories.firstOrNull{it.id==category}?.let{t(it.en,it.ru)}?:category)}
    DropdownMenu(expanded=categoryMenu,onDismissRequest={categoryMenu=false}){
     rewardCategories.forEach{c->DropdownMenuItem(text={Text(t(c.en,c.ru))},onClick={category=c.id;categoryMenu=false})}
    }
   }
   if(selected!=null)Text(if(productMode)t("Existing purchases keep their original conditions.","У существующих покупок сохраняются исходные условия.") else t("Existing items keep their version.","Существующие лоты сохраняют свою версию."),style=MaterialTheme.typography.bodySmall)
   OutlinedButton(onClick={if(productMode){val item=selectedProduct;if(item==null)actions.economy?.createProduct?.invoke(ShopProductContent(title=title,description=description,conditions=conditions,cover=cover,category=category,price=price.toInt(),audience_all=publicProduct)) else actions.economy?.editProduct?.invoke(item,ShopProductEdit(title=title,description=description,conditions=conditions,cover=cover,category=category,price=price.toInt(),audience_all=publicProduct,expected_version=item.product_revision?:1))}else actions.save(selected,RewardContent(title=title,description=description,conditions=conditions,cover=cover,category=category))},enabled=!busy&&!member.paused&&title.isNotBlank()&&description.isNotBlank()&&(!productMode||(price.toIntOrNull()?.let{it in 1..1000000000}==true&&actions.economy?.createProduct!=null&&actions.economy?.editProduct!=null))){Text(if(productMode)t("Save product","Сохранить товар") else t("Save reward","Сохранить награду"))}
  }
 }
 offering?.let{r->RuleTaskDialog(t("Offer reward","Выдать награду"),busy,{offering=null}){
  Text(r.title)
  Box{TextButton(onClick={expanded=true},enabled=!busy){Text(data.participants.find{it.id==recipient}?.display_name?:t("Recipient","Получатель"))};DropdownMenu(expanded,{expanded=false}){data.participants.filter{p->data.relations.any{it.dominant_user_id==member.id&&it.submissive_user_id==p.id&&it.status=="active"&&"rewards.grant" in it.scopes}}.forEach{p->DropdownMenuItem(text={Text(p.display_name)},onClick={recipient=p.id;requestKey=UUID.randomUUID().toString();expanded=false})}}}
  OutlinedButton(onClick={actions.grant(GrantCommand(reward_version_id=r.version_id,recipient_id=recipient,idempotency_key=requestKey))},enabled=!busy&&!member.paused&&recipient.isNotEmpty()){Text(t("Confirm reward offer","Подтвердить выдачу"))}
 }}
}

@Composable private fun RewardAvatar(name:String){Surface(shape=CircleShape,color=MaterialTheme.colorScheme.surfaceVariant,modifier=Modifier.size(32.dp)){Box(contentAlignment=Alignment.Center){Text(name.take(1),fontSize=18.sp,lineHeight=18.sp,color=MaterialTheme.colorScheme.primary,style=MaterialTheme.typography.bodyLarge.copy(platformStyle=androidx.compose.ui.text.PlatformTextStyle(includeFontPadding=false)))}}}
