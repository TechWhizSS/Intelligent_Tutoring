package com.nmims.songstudio

import androidx.compose.ui.test.*
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import com.nmims.songstudio.auth.AccountStore
import com.nmims.songstudio.data.*
import org.junit.Assert.*
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config

/** Compose and Android-resource checks; no GPU or fabricated song fixture. */
@RunWith(RobolectricTestRunner::class)
@Config(sdk=[35])
class NativeFlowTest {
    @get:Rule val ui=createAndroidComposeRule<MainActivity>()

    @Test fun sampleStudentCanDraftBothSubjectsAndOpenStudyPages() {
        ui.onNodeWithText("Try the sample student account").performScrollTo().performClick()
        ui.onNodeWithText("Generate lyrics").performScrollTo().performClick()
        ui.onNodeWithText("Save lyrics").performScrollTo().performClick()
        ui.onNodeWithText("Notes").performClick()
        ui.onNodeWithText("UPLOADED SYLLABUS SUMMARY").performScrollTo().assertIsDisplayed()
        ui.onNodeWithText("Calculus").performScrollTo().performClick()
        ui.onNodeWithText("BEEE").performClick()
        ui.onNodeWithText("Quiz").performClick()
        ui.onNodeWithText("Supplemental revision quiz").performScrollTo().assertIsDisplayed()
        ui.onNodeWithText("Studio").performClick()
        ui.onNodeWithText("Generate lyrics").performScrollTo().performClick()
        ui.onNodeWithText("Save lyrics").performScrollTo().performClick()
        val context=ui.activity.applicationContext
        val student=AccountStore(context).login("70572400001","anything")
        val store=StudioStore(context,student.id)
        assertNotNull(store.draft("calc-01","en"))
        assertNotNull(store.draft("beee-01","en"))
        ui.onNodeWithText("More").performClick()
        ui.onNodeWithText("Syllabus completeness").performScrollTo().assertIsDisplayed()
        ui.onNodeWithText("Show every unit and topic").performScrollTo().performClick()
        ui.onNodeWithText("Electrical Circuit Elements (R, L, C)").performScrollTo().assertIsDisplayed()
    }

    @Test fun allNativeSourcesAndScoresPersistOffline() {
        val context=ui.activity.applicationContext
        val student=AccountStore(context).login("unit-student","sample")
        val syllabus=Syllabus(context)
        assertEquals(91,syllabus.topics.size)
        assertEquals(38,syllabus.topics.count{it.subject=="calculus"})
        val store=StudioStore(context,student.id)
        store.save("beee-01","hi",syllabus.topics.first{it.id=="beee-01"}.lyrics.getValue("hi"),MusicSettings())
        store.quiz("beee-01","hi",2,2)
        val reopened=StudioStore(context,student.id)
        assertTrue(reopened.draft("beee-01","hi")!!.getString("lyrics").contains("[Chorus]"))
        assertEquals("2/2",reopened.quizResult("beee-01","hi"))
    }
}
