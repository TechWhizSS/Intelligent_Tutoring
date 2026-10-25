package com.nmims.songstudio.ui

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import com.nmims.songstudio.auth.Student
import com.nmims.songstudio.data.SongDatabase
import com.nmims.songstudio.data.SongRecord
import com.nmims.songstudio.data.SongRepository
import com.nmims.songstudio.playback.AudioFiles
import com.nmims.songstudio.playback.SongPlayer
import kotlinx.coroutines.launch
import java.text.SimpleDateFormat
import java.util.*

/**
 * Saved Songs library screen.
 * Displays only songs the logged-in student has explicitly saved (★ favourited).
 * Completely decoupled and independent from existing navigation.
 */
@Composable
fun SongLibraryScreen(student: Student, onBack: () -> Unit) = StudioTheme {
    val context = LocalContext.current
    val repo = remember { SongRepository(context.applicationContext, SongDatabase.get(context).songDao()) }
    val songs by repo.saved(student.id).collectAsState(initial = emptyList())
    var selectedSong by remember { mutableStateOf<SongRecord?>(null) }
    var confirmDelete by remember { mutableStateOf<SongRecord?>(null) }
    val scope = rememberCoroutineScope()

    Surface(Modifier.fillMaxSize(), color = Paper) {
        Column(
            Modifier.safeDrawingPadding().verticalScroll(rememberScrollState())
                .padding(horizontal = 24.dp, vertical = 20.dp),
            verticalArrangement = Arrangement.spacedBy(18.dp)
        ) {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Text("SAT / SONG STUDIO", style = MaterialTheme.typography.labelSmall)
                TextButton(onClick = onBack) { Text("← Back") }
            }
            Text("Your saved\nsongs.", style = MaterialTheme.typography.headlineLarge)
            Text("${songs.size} saved song${if (songs.size != 1) "s" else ""}", style = MaterialTheme.typography.bodyMedium)

            if (songs.isEmpty()) {
                Panel(Lavender) {
                    Text("NO SAVED SONGS YET", style = MaterialTheme.typography.labelSmall)
                    Text("Save your favourite songs", style = MaterialTheme.typography.titleLarge)
                    Text("After generating a song, tap the ☆ Save button to keep it in your permanent library.")
                }
            }

            // Detail view for a selected song
            val selected = selectedSong
            if (selected != null) {
                Panel(Lime) {
                    Text("NOW PLAYING", style = MaterialTheme.typography.labelSmall)
                    Text(selected.songTitle, style = MaterialTheme.typography.titleLarge)
                    Text("${selected.topicTitle} · ${selected.category} · ${selected.styleName}")
                    Text("${selected.referenceTitle} · ${formatDate(selected.createdAt)}", style = MaterialTheme.typography.bodySmall)
                    Text("Origin: ${selected.generationMode}", style = MaterialTheme.typography.bodySmall)
                }
                val audioFile = remember(selected.audioFileKey) { AudioFiles.file(context, selected.audioFileKey) }
                if (audioFile.exists()) {
                    // Compatible with standard SongPlayer(file, revision)
                    SongPlayer(
                        file = audioFile,
                        revision = 0
                    )
                    AudioExport(audioFile, selected.topicTitle.replace(Regex("[^A-Za-z0-9]+"),"-"))
                } else {
                    Panel(Lavender) {
                        Text("AUDIO UNAVAILABLE", style = MaterialTheme.typography.labelSmall)
                        Text("The audio file for this song is no longer available on this device.", color = MaterialTheme.colorScheme.error)
                        Text("The lyrics are still preserved below.")
                    }
                }
                // Lyrics display
                Panel(Lavender) {
                    Text("LYRICS", style = MaterialTheme.typography.labelSmall)
                    Text(selected.lyrics, style = MaterialTheme.typography.bodyLarge)
                }
                Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                    OutlinedButton(onClick = { selectedSong = null }) { Text("← Song list") }
                    OutlinedButton(onClick = {
                        scope.launch {
                            val updated = repo.toggleSaved(selected)
                            selectedSong = updated
                        }
                    }) {
                        Text(if (selected.saved) "★ Saved" else "☆ Save")
                    }
                    OutlinedButton(
                        onClick = { confirmDelete = selected },
                        colors = ButtonDefaults.outlinedButtonColors(contentColor = MaterialTheme.colorScheme.error)
                    ) { Text("Delete") }
                }
            } else {
                // Saved songs list
                songs.forEach { song ->
                    SongCard(
                        song = song,
                        audioExists = remember(song.audioFileKey) { AudioFiles.file(context, song.audioFileKey).exists() },
                        onClick = { selectedSong = song },
                        onToggleSave = { scope.launch { repo.toggleSaved(song) } },
                        onDelete = { confirmDelete = song }
                    )
                }
            }

            // Delete confirmation dialog
            val toDelete = confirmDelete
            if (toDelete != null) {
                AlertDialog(
                    onDismissRequest = { confirmDelete = null },
                    title = { Text("Delete song?") },
                    text = { Text("\"${toDelete.songTitle}\" will be removed from your library. This cannot be undone.") },
                    confirmButton = {
                        TextButton(onClick = {
                            scope.launch {
                                repo.deleteRecord(toDelete)
                                if (selectedSong?.id == toDelete.id) selectedSong = null
                                confirmDelete = null
                            }
                        }) { Text("Delete", color = MaterialTheme.colorScheme.error) }
                    },
                    dismissButton = { TextButton(onClick = { confirmDelete = null }) { Text("Cancel") } }
                )
            }

            HorizontalDivider()
            Text("SAVED SONGS LIBRARY", style = MaterialTheme.typography.labelSmall)
            Spacer(Modifier.height(12.dp))
        }
    }
}

/**
 * History screen showing all generated songs (including unsaved).
 * Completely decoupled and independent from existing navigation.
 */
@Composable
fun SongHistoryScreen(student: Student, onBack: () -> Unit) = StudioTheme {
    val context = LocalContext.current
    val repo = remember { SongRepository(context.applicationContext, SongDatabase.get(context).songDao()) }
    val songs by repo.history(student.id).collectAsState(initial = emptyList())
    var selectedSong by remember { mutableStateOf<SongRecord?>(null) }
    var confirmDelete by remember { mutableStateOf<SongRecord?>(null) }
    var confirmClear by remember { mutableStateOf(false) }
    val scope = rememberCoroutineScope()

    Surface(Modifier.fillMaxSize(), color = Paper) {
        Column(
            Modifier.safeDrawingPadding().verticalScroll(rememberScrollState())
                .padding(horizontal = 24.dp, vertical = 20.dp),
            verticalArrangement = Arrangement.spacedBy(18.dp)
        ) {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Text("SAT / SONG STUDIO", style = MaterialTheme.typography.labelSmall)
                TextButton(onClick = onBack) { Text("← Back") }
            }
            Text("Your song\nhistory.", style = MaterialTheme.typography.headlineLarge)
            Text("${songs.size} audio track${if (songs.size != 1) "s" else ""}", style = MaterialTheme.typography.bodyMedium)

            if (songs.isEmpty()) {
                Panel(Lavender) {
                    Text("NO SONGS YET", style = MaterialTheme.typography.labelSmall)
                    Text("Generate your first song", style = MaterialTheme.typography.titleLarge)
                    Text("Complete the four-step workflow to create educational songs. They will appear here automatically.")
                }
            }

            val selected = selectedSong
            if (selected != null) {
                Panel(Lime) {
                    Text(if (selected.saved) "★ SAVED" else "HISTORY", style = MaterialTheme.typography.labelSmall)
                    Text(selected.songTitle, style = MaterialTheme.typography.titleLarge)
                    Text("${selected.topicTitle} · ${selected.category} · ${selected.styleName}")
                    Text("${selected.referenceTitle} · ${formatDate(selected.createdAt)}", style = MaterialTheme.typography.bodySmall)
                    Text("Origin: ${selected.generationMode}", style = MaterialTheme.typography.bodySmall)
                    Text("Mode: ${selected.generationMode.replace('_', ' ')}", style = MaterialTheme.typography.bodySmall)
                }
                val audioFile = remember(selected.audioFileKey) { AudioFiles.file(context, selected.audioFileKey) }
                if (audioFile.exists()) {
                    SongPlayer(
                        file = audioFile,
                        revision = 0
                    )
                    AudioExport(audioFile, selected.topicTitle.replace(Regex("[^A-Za-z0-9]+"),"-"))
                } else {
                    Panel(Lavender) {
                        Text("AUDIO UNAVAILABLE", style = MaterialTheme.typography.labelSmall)
                        Text("The audio file for this song has been removed.", color = MaterialTheme.colorScheme.error)
                    }
                }
                Panel(Lavender) {
                    Text("LYRICS", style = MaterialTheme.typography.labelSmall)
                    Text(selected.lyrics, style = MaterialTheme.typography.bodyLarge)
                }
                Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                    OutlinedButton(onClick = { selectedSong = null }) { Text("← History list") }
                    OutlinedButton(onClick = {
                        scope.launch {
                            val updated = repo.toggleSaved(selected)
                            selectedSong = updated
                        }
                    }) { Text(if (selected.saved) "★ Unsave" else "☆ Save") }
                    OutlinedButton(
                        onClick = { confirmDelete = selected },
                        colors = ButtonDefaults.outlinedButtonColors(contentColor = MaterialTheme.colorScheme.error)
                    ) { Text("Delete") }
                }
            } else {
                // Song cards list
                songs.forEach { song ->
                    SongCard(
                        song = song,
                        audioExists = remember(song.audioFileKey) { AudioFiles.file(context, song.audioFileKey).exists() },
                        onClick = { selectedSong = song },
                        onToggleSave = { scope.launch { repo.toggleSaved(song) } },
                        onDelete = { confirmDelete = song }
                    )
                }
                if (songs.any { !it.saved }) {
                    OutlinedButton(
                        onClick = { confirmClear = true },
                        modifier = Modifier.fillMaxWidth(),
                        colors = ButtonDefaults.outlinedButtonColors(contentColor = MaterialTheme.colorScheme.error)
                    ) { Text("Clear unsaved history") }
                }
            }

            // Delete confirmation dialog
            val toDelete = confirmDelete
            if (toDelete != null) {
                AlertDialog(
                    onDismissRequest = { confirmDelete = null },
                    title = { Text("Delete song?") },
                    text = { Text("\"${toDelete.songTitle}\" and its audio will be removed. This cannot be undone.") },
                    confirmButton = {
                        TextButton(onClick = {
                            scope.launch {
                                repo.deleteRecord(toDelete)
                                if (selectedSong?.id == toDelete.id) selectedSong = null
                                confirmDelete = null
                            }
                        }) { Text("Delete", color = MaterialTheme.colorScheme.error) }
                    },
                    dismissButton = { TextButton(onClick = { confirmDelete = null }) { Text("Cancel") } }
                )
            }
            if (confirmClear) {
                AlertDialog(
                    onDismissRequest = { confirmClear = false },
                    title = { Text("Clear unsaved history?") },
                    text = { Text("All unsaved history entries will be removed. Saved songs are not affected.") },
                    confirmButton = {
                        TextButton(onClick = {
                            scope.launch { repo.clearUnsavedHistory(student.id); confirmClear = false }
                        }) { Text("Clear", color = MaterialTheme.colorScheme.error) }
                    },
                    dismissButton = { TextButton(onClick = { confirmClear = false }) { Text("Cancel") } }
                )
            }

            HorizontalDivider()
            Text("SONG HISTORY", style = MaterialTheme.typography.labelSmall)
            Spacer(Modifier.height(12.dp))
        }
    }
}

/** Compact card for song lists used by both Library and History screens. */
@Composable
private fun SongCard(
    song: SongRecord,
    audioExists: Boolean,
    onClick: () -> Unit,
    onToggleSave: () -> Unit,
    onDelete: () -> Unit
) {
    Panel(if (song.saved) Lime else Lavender) {
        Row(Modifier.fillMaxWidth().clickable(onClick = onClick)) {
            Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                Text(
                    if (song.saved) "★ SAVED" else "HISTORY",
                    style = MaterialTheme.typography.labelSmall
                )
                Text(song.songTitle, style = MaterialTheme.typography.titleLarge, maxLines = 1, overflow = TextOverflow.Ellipsis)
                Text("${song.topicTitle} · ${song.category}", maxLines = 1, overflow = TextOverflow.Ellipsis)
                Text(
                    "${song.referenceTitle} · ${formatDate(song.createdAt)}${if (!audioExists) " · Audio missing" else ""}",
                    style = MaterialTheme.typography.bodySmall,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis
                )
                if (song.durationMs > 0) {
                    val secs = song.durationMs / 1000
                    Text("Duration: ${secs / 60}:%02d".format(secs % 60), style = MaterialTheme.typography.bodySmall)
                }
            }
        }
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            TextButton(onClick = onClick) { Text("Open") }
            TextButton(onClick = onToggleSave) { Text(if (song.saved) "Unsave" else "Save") }
            TextButton(onClick = onDelete) { Text("Delete", color = MaterialTheme.colorScheme.error) }
        }
    }
}

private fun formatDate(timestamp: Long): String =
    SimpleDateFormat("dd MMM yyyy, HH:mm", Locale.getDefault()).format(Date(timestamp))
