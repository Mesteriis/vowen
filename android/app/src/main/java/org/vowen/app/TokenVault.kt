package org.vowen.app

import android.content.Context
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import java.io.File
import java.security.KeyStore
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

/** Key lives in Android Keystore; encrypted, origin-bound blob is excluded from backup. */
class TokenVault(context: Context) {
 private val file = File(context.noBackupFilesDir, "refresh.bin")
 private val alias = "vowen-refresh-v1"
 private fun key(): SecretKey {
  val store = KeyStore.getInstance("AndroidKeyStore").apply { load(null) }
  (store.getKey(alias, null) as? SecretKey)?.let { return it }
  return KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, "AndroidKeyStore").apply {
   init(KeyGenParameterSpec.Builder(alias, KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT)
    .setBlockModes(KeyProperties.BLOCK_MODE_GCM).setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
    .setKeySize(256).build())
  }.generateKey()
 }
 fun save(origin: String, refresh: String) {
  val cipher = Cipher.getInstance("AES/GCM/NoPadding")
  cipher.init(Cipher.ENCRYPT_MODE, key())
  cipher.updateAAD(origin.toByteArray(Charsets.UTF_8))
  val blob = cipher.iv + cipher.doFinal(refresh.toByteArray(Charsets.UTF_8))
  val temporary = File(file.parentFile, "refresh.tmp")
  temporary.writeBytes(blob)
  check(temporary.renameTo(file))
 }
 fun load(origin: String): String? {
  if(!file.exists()) return null
  return try {
   val blob=file.readBytes()
   require(blob.size > 28)
   val cipher=Cipher.getInstance("AES/GCM/NoPadding")
   cipher.init(Cipher.DECRYPT_MODE,key(),GCMParameterSpec(128,blob.copyOfRange(0,12)))
   cipher.updateAAD(origin.toByteArray(Charsets.UTF_8))
   String(cipher.doFinal(blob.copyOfRange(12,blob.size)),Charsets.UTF_8)
  } catch (_: Exception) { clear(); null }
 }
 fun clear() {
  file.delete()
  File(file.parentFile,"refresh.tmp").delete()
  KeyStore.getInstance("AndroidKeyStore").apply { load(null); deleteEntry(alias) }
 }
}
