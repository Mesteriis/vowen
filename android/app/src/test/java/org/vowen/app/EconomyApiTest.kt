package org.vowen.app

import kotlinx.coroutines.runBlocking
import kotlinx.serialization.json.*
import okhttp3.OkHttpClient
import okhttp3.Protocol
import okhttp3.Response
import okhttp3.ResponseBody.Companion.toResponseBody
import org.junit.Assert.*
import org.junit.Test

class EconomyApiTest {
 @Test fun creditsKeepRelationshipCommentAndIdempotencyKey()=runBlocking{
  val requests=mutableListOf<Triple<String,String,JsonObject>>()
  val state=InstanceSession().apply{select("https://test.example");accessToken="synthetic"}
  val transport=OkHttpClient.Builder().addInterceptor{chain->
   val r=chain.request();val sink=okio.Buffer();r.body?.writeTo(sink)
   requests.add(Triple(r.url.encodedPath,r.method,if(r.body==null)buildJsonObject{} else Json.parseToJsonElement(sink.readUtf8()).jsonObject))
   assertEquals("Bearer synthetic",r.header("Authorization"))
   val body=Json.encodeToString(RelationWallet(relation_id="relation-a",balance=3000000000L,entries=emptyList()))
   Response.Builder().request(r).protocol(Protocol.HTTP_1_1).code(200).message("Synthetic").body(body.toResponseBody()).build()
  }.build()
  val api=Api(state,client=transport)
  val command=CreditCommand(amount=20,comment="For your effort",idempotency_key="same-request")
  assertEquals(3000000000L,api.creditCoins("relation-a",command).balance)
  api.creditCoins("relation-a",command)
  assertEquals(requests[0],requests[1])
  assertEquals("/api/v1/relations/relation-a/wallet/credits",requests[0].first)
  assertEquals("For your effort",requests[0].third["comment"]!!.jsonPrimitive.content)
 }
 @Test fun ritualBundleKeepsAllSelectedRewardsAndCurrency(){
  val encoded=Json.encodeToString(RitualAssign(idempotency_key="retry",recipient_id="participant",reviewer_ids=emptyList(),approval_required=false,reward_version_ids=listOf("lot-a","lot-b"),currency_amount=20,schedule=RitualSchedule(kind="daily",timezone="UTC",hour=9,minute=0,start_date="2026-10-16")))
  val body=Json.parseToJsonElement(encoded).jsonObject
  assertEquals(2,body["reward_version_ids"]!!.jsonArray.size)
  assertEquals(20,body["currency_amount"]!!.jsonPrimitive.int)
 }
 @Test fun ritualRewardEditsSendExpectedRevisionAndExplicitEmptyBundle()=runBlocking{
  val state=InstanceSession().apply{select("https://test.example");accessToken="synthetic"}
  val a=RitualAssignment(true,description="demo",effective=true,id="assignment",issuer_id="a",recipient_id="b",reviewer_ids=listOf("a"),revision=7,ritual_version_id="v",schedule=RitualSchedule(8,"daily",0,"2026-10-16","UTC"),status="active",title="Morning")
  val transport=OkHttpClient.Builder().addInterceptor{chain->
   val r=chain.request();val sink=okio.Buffer();r.body!!.writeTo(sink);val body=Json.parseToJsonElement(sink.readUtf8()).jsonObject
   assertEquals("PUT",r.method);assertEquals("/api/v1/ritual-assignments/assignment/rewards",r.url.encodedPath)
   assertEquals(7,body["expected_version"]!!.jsonPrimitive.int)
   assertEquals(0,body["currency_amount"]!!.jsonPrimitive.int)
   assertEquals(0,body["reward_version_ids"]!!.jsonArray.size)
   Response.Builder().request(r).protocol(Protocol.HTTP_1_1).code(200).message("Synthetic").body(Json.encodeToString(a).toResponseBody()).build()
  }.build()
  assertEquals("assignment",Api(state,client=transport).ritualRewards(a,RewardBundleEdit(0,7,emptyList())).id)
 }

}
