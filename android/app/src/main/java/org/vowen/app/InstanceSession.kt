package org.vowen.app

import java.net.URI

class InstanceSession {
 var origin: String = ""
  private set
 var accessToken: String? = null
 fun select(value: String): Boolean {
  val uri = URI(value.trim())
  require(uri.scheme == "https" && !uri.host.isNullOrBlank() && uri.userInfo == null &&
          uri.query == null && uri.fragment == null && (uri.path.isNullOrEmpty() || uri.path == "/"))
  val normalized = "https://${uri.rawAuthority.lowercase()}"
  val changed = normalized != origin
  if(changed) accessToken = null
  origin = normalized
  return changed
 }
 fun clear() { accessToken = null }
}
