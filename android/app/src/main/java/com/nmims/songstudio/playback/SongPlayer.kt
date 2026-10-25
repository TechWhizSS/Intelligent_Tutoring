package com.nmims.songstudio.playback

import android.content.Context
import android.media.AudioManager
import androidx.compose.ui.platform.LocalContext
import android.media.AudioAttributes
import android.media.MediaPlayer
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.compose.LocalLifecycleOwner
import com.nmims.songstudio.ui.Lime
import com.nmims.songstudio.ui.Panel
import kotlinx.coroutines.delay
import java.io.File

@Composable
fun SongPlayer(file: File, revision: Int) {
    val context = LocalContext.current
    val audioManager = remember { context.getSystemService(Context.AUDIO_SERVICE) as AudioManager }
    var mediaVolume by remember { mutableIntStateOf(audioManager.getStreamVolume(AudioManager.STREAM_MUSIC)) }
    val maxVolume = audioManager.getStreamMaxVolume(AudioManager.STREAM_MUSIC).coerceAtLeast(1)
    val lifecycle = LocalLifecycleOwner.current.lifecycle
    var player by remember { mutableStateOf<MediaPlayer?>(null) }
    var ready by remember { mutableStateOf(false) }
    var playing by remember { mutableStateOf(false) }
    var position by remember { mutableFloatStateOf(0f) }
    var duration by remember { mutableFloatStateOf(1f) }
    var error by remember { mutableStateOf("") }
    DisposableEffect(file.absolutePath, revision) {
        val p = MediaPlayer()
        player = p; ready = false; playing = false; error = ""; position = 0f
        p.setAudioAttributes(AudioAttributes.Builder().setUsage(AudioAttributes.USAGE_MEDIA).setContentType(AudioAttributes.CONTENT_TYPE_MUSIC).build())
        p.setVolume(1f, 1f)
        p.setOnPreparedListener { ready = true; duration = it.duration.toFloat().coerceAtLeast(1f) }
        p.setOnCompletionListener { playing = false; position = duration }
        p.setOnErrorListener { _, _, _ -> ready = false; playing = false; error = "This audio could not be played. Try generating the song again."; true }
        runCatching { p.setDataSource(file.absolutePath); p.prepareAsync() }
            .onFailure { error = "The audio file cannot be opened." }
        val observer = LifecycleEventObserver { _, event ->
            if (event == Lifecycle.Event.ON_RESUME) mediaVolume = audioManager.getStreamVolume(AudioManager.STREAM_MUSIC)
            if (event == Lifecycle.Event.ON_STOP && playing) { p.pause(); playing = false }
        }
        lifecycle.addObserver(observer)
        onDispose { lifecycle.removeObserver(observer); p.release(); player = null; ready = false; playing = false }
    }
    LaunchedEffect(playing) {
        while (playing) {
            position = player?.currentPosition?.toFloat() ?: 0f
            mediaVolume = audioManager.getStreamVolume(AudioManager.STREAM_MUSIC)
            delay(200)
        }
    }
    fun time(ms: Float): String { val seconds = ms.toInt() / 1000; return "%d:%02d".format(seconds / 60, seconds % 60) }
    Panel(Lime) {
        Text("YOUR LEARNING SOUNDTRACK", style = MaterialTheme.typography.labelSmall)
        Text("Ready to listen", style = MaterialTheme.typography.titleLarge)
        Text("Audio saved on this phone. Review the words and formula pronunciation.", style = MaterialTheme.typography.bodySmall)
        if (error.isNotBlank()) Text(error, color = MaterialTheme.colorScheme.error)
        Text("Device media volume: ${mediaVolume * 100 / maxVolume}%", style = MaterialTheme.typography.bodySmall)
        OutlinedButton(onClick = {
            audioManager.adjustStreamVolume(AudioManager.STREAM_MUSIC, AudioManager.ADJUST_RAISE, AudioManager.FLAG_SHOW_UI)
            mediaVolume = audioManager.getStreamVolume(AudioManager.STREAM_MUSIC)
        }, enabled = mediaVolume < maxVolume) { Text("Increase device volume") }
        Slider(value = position.coerceIn(0f, duration), onValueChange = { position = it; player?.seekTo(it.toInt()) }, valueRange = 0f..duration, enabled = ready)
        Text("${time(position)} / ${time(duration)}")
        Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            Button(enabled = ready, onClick = {
                player?.let { p ->
                    if (playing) p.pause() else {
                        if (position >= duration) { p.seekTo(0); position = 0f }
                        p.start()
                    }
                    playing = p.isPlaying
                }
            }) { Text(if (playing) "Pause" else "Play song") }
            OutlinedButton(enabled = ready, onClick = { player?.seekTo(0); position = 0f }) { Text("Replay") }
        }
    }
}
