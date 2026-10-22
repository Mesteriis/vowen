import {it,expect} from 'vitest'
import {useWikiEditor,type WikiEditorApi} from '../src/features/wiki/editor'
import type {WikiEditView} from '../src/features/wiki/api'
const original:WikiEditView={uid:'page',kind:'article',version:1,practice_uid:null,pose_uid:null,device_uid:null,draft_revision_uid:'r1',published_revision_uid:null,archived_at:null,document:{section_uid:'s',title:'Original',body:'Body',summary:'',thumbnail:null,practice_uids:[],pose_uids:[],device_uids:[],sources:[]}}
function api(error=''):WikiEditorApi{return {edit:async()=>structuredClone(original),save:async(_uid,command)=>{if(error)throw Error(error);return {...original,version:2,draft_revision_uid:'r2',document:command.document}},create:async()=>original,publish:async(_uid,command)=>{expect(command).toEqual({expected_version:2,revision_uid:'r2'});return {...original,version:3,published_revision_uid:'r2',draft_revision_uid:'r2'}},archive:async()=>original}}
for(const error of ['VERSION_CONFLICT','ACCESS_DENIED','offline'])it(`retains draft after ${error}`,async()=>{
 const editor=useWikiEditor(api(error));await editor.load('page');editor.document.value.title='Keep this'
 expect(await editor.save()).toBe(false)
 expect(editor.document.value.title).toBe('Keep this');expect(editor.dirty.value).toBe(true)
 expect(editor.error.value).toBe(error)
 expect(editor.canLeave(()=>false)).toBe(false)
})
it('saves before publishing exactly the saved revision',async()=>{
 const e=useWikiEditor(api());await e.load('page');e.document.value.title='New title'
 expect(await e.publish()).toBe(true);expect(e.version.value).toBe(3)
})
