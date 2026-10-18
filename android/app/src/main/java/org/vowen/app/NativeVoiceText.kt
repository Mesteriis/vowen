package org.vowen.app

import android.app.Activity
import android.content.ActivityNotFoundException
import android.content.Intent
import android.speech.RecognizerIntent
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.painterResource
import java.util.Locale

/** The system handles microphone UI. Vowen receives text and never stores audio. */
@Composable fun NativeVoiceText(value:String,onChange:(String)->Unit,ru:Boolean,busy:Boolean){
 var message by remember{mutableStateOf("")}
 val current by rememberUpdatedState(value)
 val change by rememberUpdatedState(onChange)
 val launcher=rememberLauncherForActivityResult(ActivityResultContracts.StartActivityForResult()){result->
  if(result.resultCode==Activity.RESULT_OK){val words=result.data?.getStringArrayListExtra(RecognizerIntent.EXTRA_RESULTS)?.firstOrNull();if(!words.isNullOrBlank())change((current+if(current.isBlank())words else " "+words).take(5000))}
 }
 Column{
  OutlinedTextField(value,{onChange(it.take(5000))},label={Text(if(ru)"Комментарий (необязательно)" else "Comment (optional)")},enabled=!busy,modifier=Modifier.fillMaxWidth(),trailingIcon={IconButton(onClick={try{launcher.launch(Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL,RecognizerIntent.LANGUAGE_MODEL_FREE_FORM).putExtra(RecognizerIntent.EXTRA_LANGUAGE,if(ru)"ru-RU" else Locale.getDefault().toLanguageTag()).putExtra(RecognizerIntent.EXTRA_PREFER_OFFLINE,true))}catch(_:ActivityNotFoundException){message=if(ru)"Используйте диктовку клавиатуры в этом поле." else "Use keyboard dictation in this field."}},enabled=!busy){Icon(painterResource(android.R.drawable.ic_btn_speak_now),if(ru)"Надиктовать комментарий" else "Dictate comment")}})
  Text(if(ru)"Речь распознаёт системный сервис, возможно онлайн." else "Your system speech service may use online recognition.",style=MaterialTheme.typography.bodySmall)
  if(message.isNotEmpty())Text(message,style=MaterialTheme.typography.bodySmall)
 }
}
