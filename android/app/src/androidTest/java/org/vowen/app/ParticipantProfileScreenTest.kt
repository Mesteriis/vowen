package org.vowen.app

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.ui.test.*
import androidx.compose.ui.test.junit4.createComposeRule
import org.junit.Assert.assertEquals
import org.junit.Rule
import org.junit.Test

class ParticipantProfileScreenTest {
 @get:Rule val compose=createComposeRule()
 @Test fun wizardSkipAdvancesWithoutRequiringAnAnswer(){
  var requested=0
  compose.setContent{MaterialTheme{NativeProfileWizard(3,false,true,{requested=it},{},{}){Text("Не указано")}}}
  compose.onNodeWithTag("profile-wizard-skip").performClick()
  assertEquals(4,requested)
 }
}
