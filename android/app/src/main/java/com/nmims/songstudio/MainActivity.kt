package com.nmims.songstudio

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import com.nmims.songstudio.ui.SongStudio
import com.nmims.songstudio.ui.StudioTheme
import com.nmims.songstudio.auth.AuthScreen
import com.nmims.songstudio.auth.SessionViewModel
import androidx.lifecycle.ViewModelProvider

class MainActivity : ComponentActivity() {
    private val session by lazy { ViewModelProvider(this)[SessionViewModel::class.java] }
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        volumeControlStream = android.media.AudioManager.STREAM_MUSIC
        setContent {
            StudioTheme {
                val student = session.student
                if (student == null) AuthScreen { session.signIn(it) }
                else SongStudio(student, onLogout = { session.signOut() })
            }
        }
    }

}
