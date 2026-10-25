package com.nmims.songstudio.data

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject
import java.security.MessageDigest

class StudioStore(context:Context,val studentId:Long) {
    private val prefs=context.getSharedPreferences("studio-drafts",Context.MODE_PRIVATE)
    private fun key(topic:String,lang:String)="draft:$studentId:$topic:$lang"
    fun draft(topic:String,lang:String):JSONObject?=prefs.getString(key(topic,lang),null)?.let { runCatching { JSONObject(it) }.getOrNull() }
    fun save(topic:String,lang:String,lyrics:String,settings:MusicSettings) {
        require(lang in listOf("en","hi"));require(lyrics.isNotBlank()&&lyrics.length<=16000)
        prefs.edit().putString(key(topic,lang),JSONObject().put("lyrics",lyrics).put("settings",settings.json()).toString()).apply()
    }
    fun audioKey(topic:String,lang:String,lyrics:String,settings:MusicSettings):String = sha("$studentId:$topic:$lang:$lyrics:${settings.json()}")
    fun quiz(topic:String,lang:String,score:Int,total:Int) { prefs.edit().putString("quiz:$studentId:$topic:$lang", "$score/$total").apply() }
    fun quizResult(topic:String,lang:String)=prefs.getString("quiz:$studentId:$topic:$lang",null)
    fun materials(topic:String):List<JSONObject> { val a=JSONArray(prefs.getString("materials:$topic","[]"));return (0 until a.length()).map { a.getJSONObject(it) } }
    fun addMaterial(topic:String,name:String,text:String) {
        require(name.length in 1..150 && text.length in 10..30000)
        val all=materials(topic)+JSONObject().put("name",name).put("text",text).put("approved",false)
        prefs.edit().putString("materials:$topic",JSONArray(all).toString()).apply()
    }
    fun approve(topic:String,index:Int) { val all=materials(topic);require(index in all.indices);all[index].put("approved",true);prefs.edit().putString("materials:$topic",JSONArray(all).toString()).apply() }
    companion object {fun sha(text:String)=MessageDigest.getInstance("SHA-256").digest(text.toByteArray()).joinToString(""){"%02x".format(it)}}
}
