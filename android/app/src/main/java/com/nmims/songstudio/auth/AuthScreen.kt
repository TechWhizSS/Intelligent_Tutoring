package com.nmims.songstudio.auth

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.input.VisualTransformation
import androidx.compose.ui.unit.dp
import com.nmims.songstudio.ui.*

@Composable
fun AuthScreen(onLogin:(Student)->Unit) {
    val context=LocalContext.current
    val store=remember { AccountStore(context.applicationContext) }
    var sap by rememberSaveable { mutableStateOf(store.rememberedSap()) }
    var password by remember { mutableStateOf("") }
    var visible by remember { mutableStateOf(false) }
    var error by remember { mutableStateOf("") }
    Surface(Modifier.fillMaxSize(),color=Paper) {
        Column(Modifier.safeDrawingPadding().imePadding().verticalScroll(rememberScrollState()).padding(24.dp),verticalArrangement=Arrangement.spacedBy(20.dp)) {
            Column(Modifier.fillMaxWidth().background(Brush.linearGradient(listOf(Color(0xFF50241D),Color(0xFFAC4827))),RoundedCornerShape(28.dp)).padding(25.dp),verticalArrangement=Arrangement.spacedBy(18.dp)) {
                Text("♫  SYLLABUS TO SONG",color=Color(0xFFFFD8B6),style=MaterialTheme.typography.labelSmall)
                Text("Your syllabus.\nYour soundtrack.",style=MaterialTheme.typography.headlineLarge,color=Color.White)
                Text("Learn the idea. Remember the rhythm.",color=Color(0xFFFFD8B6))
                Text("MBA TECH  /  CE  /  SEMESTER I",style=MaterialTheme.typography.labelSmall,color=Color(0xFFFFC08B))
            }
            Text("Let’s find your rhythm.",style=MaterialTheme.typography.headlineMedium)
            Text("Sign in to keep your lyrics, quizzes and songs on this phone.",color=Muted)
            OutlinedTextField(sap,{sap=it},label={Text("SAP ID")},singleLine=true,modifier=Modifier.fillMaxWidth())
            OutlinedTextField(password,{password=it},label={Text("Sample password")},singleLine=true,modifier=Modifier.fillMaxWidth(),keyboardOptions=KeyboardOptions(keyboardType=KeyboardType.Password),visualTransformation=if(visible) VisualTransformation.None else PasswordVisualTransformation(),trailingIcon={TextButton(onClick={visible=!visible}){Text(if(visible) "Hide" else "Show")}})
            if(error.isNotBlank())Text(error,color=MaterialTheme.colorScheme.error)
            Button(onClick={try{onLogin(store.login(sap,password));password=""}catch(e:IllegalArgumentException){error=e.message.orEmpty()}},modifier=Modifier.fillMaxWidth().heightIn(min=52.dp),enabled=sap.isNotBlank()&&password.isNotEmpty()){Text("Enter your studio  →")}
            OutlinedButton(onClick={onLogin(store.login("70572400001","sample"))},modifier=Modifier.fillMaxWidth()){Text("Try the sample student account")}
            Panel(Lavender) { Text("COLLEGE DEMO",style=MaterialTheme.typography.labelSmall);Text("Any valid SAP ID and any nonempty password work. This does not verify a college identity. Passwords are never stored.",style=MaterialTheme.typography.bodySmall) }
            Text("English & Hindi · 91 syllabus topics\nACE-Step GPU connection + Gemini handoff",style=MaterialTheme.typography.bodySmall,color=Muted)
        }
    }
}
