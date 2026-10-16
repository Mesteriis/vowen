package org.vowen.app

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import java.util.UUID

data class EconomyActions(val load:(String)->Unit,val credit:(String,CreditCommand)->Unit,val listing:(String,ListingCommand)->Unit,val purchase:(ShopListing,String)->Unit,val toggle:(ShopListing)->Unit)

@Composable fun NativeShop(member:Member,data:WorkspaceState,busy:Boolean,completed:Int,actions:EconomyActions){
 val ru=member.language=="ru"
 fun t(en:String,rus:String)=if(ru)rus else en
 var rid by remember(member.id){mutableStateOf("")};var expanded by remember{mutableStateOf(false)}
 val relation=data.relations.find{it.id==rid}
 val manager=relation?.dominant_user_id==member.id
 val allowed=relation?.let{it.status=="active"&&"rewards.grant" in it.scopes&&it.consent_user_ids.size==2&&!member.paused}?:false
 val wallet=data.wallet?.takeIf{it.relation_id==rid}
 val listings=if(data.economyRelationId==rid)data.shop else emptyList()
 LaunchedEffect(rid,data.economyRelationId){if(rid.isNotEmpty()&&data.economyRelationId!=rid)actions.load(rid)}
 var crediting by remember(rid){mutableStateOf(false)};var adding by remember(rid){mutableStateOf(false)};var history by remember(rid){mutableStateOf(false)}
 LaunchedEffect(completed){crediting=false;adding=false}
 Text(t("Relationship shop","Магазин отношений"),style=MaterialTheme.typography.titleLarge)
 Box{TextButton(onClick={expanded=true},enabled=!busy){Text(relation?.let{r->data.participants.find{it.id==if(manager)r.submissive_user_id else r.dominant_user_id}?.display_name}?:t("Choose relationship","Выберите отношения"))};DropdownMenu(expanded,{expanded=false}){data.relations.forEach{r->DropdownMenuItem(text={Text((data.participants.find{it.id==if(r.dominant_user_id==member.id)r.submissive_user_id else r.dominant_user_id}?.display_name?:r.id)+" · "+r.status)},onClick={rid=r.id;expanded=false})}}}
 if(relation==null)return
 Text((if(manager)t("Coins for ","Монеты участника: ")+(data.participants.find{it.id==relation.submissive_user_id}?.display_name?:t("Participant","Участник"))+": " else t("Your balance: ","Ваш баланс: "))+(wallet?.balance?.toString()?:"—")+t(" coins"," монет"),style=MaterialTheme.typography.titleMedium)
 if(!allowed)Text(t("Purchases and credits unavailable. History is preserved.","Покупки и начисления недоступны. История сохраняется."))
 if(manager&&allowed)Row{TextButton(onClick={crediting=!crediting},enabled=!busy){Text(t("Grant coins","Начислить монеты"))};TextButton(onClick={adding=!adding},enabled=!busy&&data.rewards.isNotEmpty()){Text(t("Add shop item","Добавить лот"))}}
 if(crediting){
  var amount by remember(rid){mutableStateOf("10")};var comment by remember(rid){mutableStateOf("")}
  val key=remember(rid,amount,comment){UUID.randomUUID().toString()}
  OutlinedTextField(amount,{amount=it},label={Text(t("Coin amount","Количество монет"))},enabled=!busy)
  OutlinedTextField(comment,{if(it.length<=2000)comment=it},label={Text(t("Credit comment","Комментарий к начислению"))},enabled=!busy)
  VowenActionButton(onClick={actions.credit(rid,CreditCommand(amount=amount.toInt(),comment=comment,idempotency_key=key))},enabled=!busy&&allowed&&comment.isNotBlank()&&amount.toIntOrNull()?.let{it in 1..1000000000}==true){Text(t("Confirm credit","Подтвердить начисление"))}
 }
 if(adding){
  var reward by remember(rid){mutableStateOf("")};var rewardOpen by remember{mutableStateOf(false)};var price by remember(rid){mutableStateOf("10")}
  Box{TextButton(onClick={rewardOpen=true},enabled=!busy){Text(data.rewards.find{it.version_id==reward}?.title?:t("Shop reward","Награда для магазина"))};DropdownMenu(rewardOpen,{rewardOpen=false}){data.rewards.forEach{r->DropdownMenuItem(text={Text(r.title)},onClick={reward=r.version_id;rewardOpen=false})}}}
  OutlinedTextField(price,{price=it},label={Text(t("Price in coins","Цена в монетах"))},enabled=!busy)
  VowenActionButton(onClick={actions.listing(rid,ListingCommand(price=price.toInt(),reward_version_id=reward))},enabled=!busy&&allowed&&reward.isNotEmpty()&&price.toIntOrNull()?.let{it in 1..1000000000}==true){Text(t("Save shop item","Сохранить лот"))}
 }
 listings.forEach{s->Column(Modifier.fillMaxWidth().padding(vertical=8.dp)){
  Text(s.title,style=MaterialTheme.typography.titleMedium);Text(s.description);Text("${s.price} "+t("coins","монет"))
  val key=remember(s.id,completed){UUID.randomUUID().toString()}
  if(!manager)VowenActionButton(onClick={actions.purchase(s,key)},enabled=!busy&&allowed&&s.active&&(wallet?.balance?:0L)>=s.price){Text(t("Buy","Купить"))}
  else TextButton(onClick={actions.toggle(s)},enabled=!busy&&allowed){Text(if(s.active)t("Hide item","Скрыть лот") else t("Restore item","Вернуть лот"))}
 }}
 TextButton(onClick={history=!history}){Text(t("Coin history","История монет"))}
 if(history)wallet?.entries?.forEach{e->Text((if(e.amount>0)"+" else "")+e.amount+" · "+e.kind);if(e.comment.isNotBlank())Text(e.comment);Text(e.created_at,style=MaterialTheme.typography.bodySmall)}
}
