package org.vowen.app

import android.app.Application

/** Composition root. Production always constructs the normal HTTPS-only API transport. */
open class VowenApplication:Application(){
 open fun createApi(state:InstanceSession,load:()->String?,save:(String)->Unit,clear:()->Unit):Api = Api(state,load,save,clearRefresh=clear)
}
