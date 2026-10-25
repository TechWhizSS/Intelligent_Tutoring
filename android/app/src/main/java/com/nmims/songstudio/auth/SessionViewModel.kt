package com.nmims.songstudio.auth

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.ViewModel

class SessionViewModel : ViewModel() {
    var student by mutableStateOf<Student?>(null)
        private set
    fun signIn(value: Student) { student = value }
    fun signOut() { student = null }
}
