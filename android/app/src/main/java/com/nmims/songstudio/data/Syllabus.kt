package com.nmims.songstudio.data

import android.content.Context
import org.json.JSONObject

data class Question(val prompt: String, val options: List<String>, val correct: Int, val explanation: String)
data class Lesson(val id: String, val index: Int, val subject: String, val unit: Int, val chapter: String,
    val title: String, val source: String, val locator: String, val summary: String, val hindi: String,
    val objectives: List<String>, val supplemental: List<String>, val lyrics: Map<String,String>,
    val quizzes: Map<String,List<Question>>, val hash: String) {
    val subjectName get() = if(subject == "calculus") "Calculus" else "BEEE"
}
class Syllabus(context: Context) {
    val topics: List<Lesson>
    init {
        val root=JSONObject(context.assets.open("syllabus.json").bufferedReader().use { it.readText() })
        val rows=root.getJSONArray("topics")
        topics=(0 until rows.length()).map { i ->
            val t=rows.getJSONObject(i)
            fun strings(key: String): List<String> { val a=t.optJSONArray(key) ?: return emptyList(); return (0 until a.length()).map { a.getString(it) } }
            Lesson(t.getString("id"),t.getInt("index"),t.getString("subject"),t.getInt("unit"),t.getString("chapter"),
                t.getString("title"),t.getString("source"),t.getString("locator"),t.getString("sourceText"),t.getString("hindiSupplement"),
                strings("objectives"),strings("supplemental"),listOf("en","hi").associateWith { t.getJSONObject("lyrics").getString(it) },
                listOf("en","hi").associateWith { lang -> val q=t.getJSONObject("quiz").getJSONArray(lang);(0 until q.length()).map { j ->
                    val v=q.getJSONObject(j);val a=v.getJSONArray("options");Question(v.getString("prompt"),(0 until a.length()).map { a.getString(it) },v.getInt("correct"),v.getString("explanation")) } }, t.getString("hash"))
        }
        require(topics.size==91 && topics.count { it.subject=="calculus" }==38 && topics.count { it.subject=="beee" }==53)
    }
}

data class MusicSettings(val genre:String="Pop",val mood:String="Uplifting",val vocal:String="Warm",
    val tempo:Int=100,val seconds:Int=30,val difficulty:String="Beginner",val repeats:Int=2,val instructions:String="") {
    fun json()=JSONObject().put("genre",genre).put("mood",mood).put("vocal",vocal).put("tempo",tempo)
        .put("seconds",seconds).put("difficulty",difficulty).put("repeats",repeats).put("instructions",instructions)
    fun caption(language:String)= "Original $genre educational song, $mood, $vocal sung vocals in ${if(language=="hi") "Hindi" else "English"}, expressive melody, instruments, drums, bass, catchy chorus. Difficulty: $difficulty. Repeat formulas $repeats times. $instructions".take(2500)
    companion object {
        fun from(j:JSONObject)=MusicSettings(j.optString("genre","Pop"),j.optString("mood","Uplifting"),j.optString("vocal","Warm"),j.optInt("tempo",100).coerceIn(60,180),j.optInt("seconds",30).coerceIn(30,240),j.optString("difficulty","Beginner"),j.optInt("repeats",2).coerceIn(1,4),j.optString("instructions").take(1500))
    }
}
