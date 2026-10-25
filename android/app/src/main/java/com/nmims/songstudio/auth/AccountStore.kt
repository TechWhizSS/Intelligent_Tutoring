package com.nmims.songstudio.auth

import android.content.Context
import java.security.MessageDigest

data class Student(val id:Long,val name:String,val email:String)
/** Explicit college-demo login: no password storage and no identity verification. */
class AccountStore(context:Context) {
    private val prefs=context.getSharedPreferences("sample-login",Context.MODE_PRIVATE)
    fun rememberedSap()=prefs.getString("sap","") ?: ""
    fun login(sap:String,password:String):Student {
        val value=sap.trim()
        require(Regex("[A-Za-z0-9_-]{3,30}").matches(value)) { "Enter a SAP ID with 3–30 letters, digits, underscores or hyphens." }
        require(password.isNotEmpty() && password.length<=200) { "Enter any nonempty sample password." }
        prefs.edit().putString("sap",value).apply()
        val bytes=MessageDigest.getInstance("SHA-256").digest(value.toByteArray())
        val id=java.nio.ByteBuffer.wrap(bytes).long.and(Long.MAX_VALUE)
        return Student(id,"Student",value)
    }
}
