package org.vowen.app

import kotlinx.serialization.json.Json
import java.net.URLEncoder

/** Uses the existing authenticated transport; Wiki never uses relationship context. */
class WikiApi(private val api:Api) {
 private val json=Json{ignoreUnknownKeys=true;encodeDefaults=false;explicitNulls=false}
 private fun query(value:String)=URLEncoder.encode(value,"UTF-8")
 suspend fun thumbnail(path:String):ByteArray=api.wikiThumbnail(path)
 suspend fun referenceLinks(kind:String):List<WikiReferenceLink> = json.decodeFromString(api.call("/wiki/reference-links/${query(kind)}"))
 suspend fun tree():WikiTreeView=json.decodeFromString(api.call("/wiki/tree"))
 suspend fun page(uid:String):WikiPageView=json.decodeFromString(api.call("/wiki/pages/$uid"))
 suspend fun search(q:String,section:String,offset:Int=0):WikiSearchView=json.decodeFromString(api.call("/wiki/search?q=${query(q)}&offset=$offset"+if(section.isNotBlank())"&section_uid=${query(section)}" else ""))
 suspend fun edit(uid:String):WikiEditView=json.decodeFromString(api.call("/wiki/admin/pages/$uid"))
 suspend fun list(mode:String,offset:Int=0):List<WikiEditView>{require(mode in listOf("drafts","published","archived"));return json.decodeFromString(api.call("/wiki/admin/pages?state=$mode&offset=$offset"))}
 suspend fun create(command:WikiPageCreate):WikiEditView=json.decodeFromString(api.call("/wiki/admin/pages","POST",json.encodeToString(command)))
 suspend fun save(uid:String,command:WikiPageSave):WikiEditView=json.decodeFromString(api.call("/wiki/admin/pages/$uid","PATCH",json.encodeToString(command)))
 suspend fun publish(uid:String,command:WikiPublish):WikiEditView=json.decodeFromString(api.call("/wiki/admin/pages/$uid/publish","POST",json.encodeToString(command)))
 suspend fun archive(uid:String,command:WikiArchive):WikiEditView=json.decodeFromString(api.call("/wiki/admin/pages/$uid/archive","POST",json.encodeToString(command)))
 suspend fun history(uid:String,offset:Int=0):List<WikiRevisionView> = json.decodeFromString(api.call("/wiki/admin/pages/$uid/revisions?offset=$offset"))
 suspend fun seed():WikiSeedResult=json.decodeFromString(api.call("/wiki/admin/seed-references","POST"))
 suspend fun saveSection(uid:String?,command:WikiSectionSave):WikiTreeView=json.decodeFromString(api.call("/wiki/admin/sections"+(uid?.let{"/$it"}?:""),if(uid==null)"POST" else "PATCH",json.encodeToString(command)))
 suspend fun deleteSection(uid:String,version:Int,treeVersion:Int){api.call("/wiki/admin/sections/$uid?expected_version=$version&expected_tree_version=$treeVersion","DELETE")}
 suspend fun references(kind:String):List<ReferenceEntry>{require(kind in listOf("practices","poses","devices"));return json.decodeFromString(api.call("/references/$kind"))}
}
