package com.pinkelephant.talk

import android.app.Activity
import android.content.ActivityNotFoundException
import android.content.Intent
import android.speech.RecognizerIntent
import com.facebook.react.bridge.Arguments
import com.facebook.react.bridge.Promise
import com.facebook.react.bridge.ReactApplicationContext
import com.facebook.react.bridge.ReactContextBaseJavaModule
import com.facebook.react.bridge.ReactMethod
import java.util.Locale

class SpeechModule(reactContext: ReactApplicationContext) :
    ReactContextBaseJavaModule(reactContext) {

    override fun getName(): String = "SpeechModule"

    companion object {
        const val REQUEST_RECOGNIZE = 9003
        @Volatile
        var pendingPromise: Promise? = null

        fun handleActivityResult(resultCode: Int, data: Intent?) {
            val p = pendingPromise ?: return
            pendingPromise = null
            if (resultCode != Activity.RESULT_OK || data == null) {
                p.reject("VOICE_CANCELLED", "Voice input was cancelled")
                return
            }
            val results = data.getStringArrayListExtra(RecognizerIntent.EXTRA_RESULTS)
            val text = results?.firstOrNull()?.takeIf { it.isNotBlank() }
            if (text == null) {
                p.reject("VOICE_NO_RESULT", "No speech was recognized")
                return
            }
            val map = Arguments.createMap()
            map.putString("text", text)
            p.resolve(map)
        }
    }

    @ReactMethod
    fun recognize(languageTag: String?, promise: Promise) {
        val activity = currentActivity
        if (activity == null) {
            promise.reject("NO_ACTIVITY", "No activity available")
            return
        }
        val intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
            putExtra(
                RecognizerIntent.EXTRA_LANGUAGE_MODEL,
                RecognizerIntent.LANGUAGE_MODEL_FREE_FORM,
            )
            putExtra(RecognizerIntent.EXTRA_PROMPT, "Speak your question for Pink Elephant Talk")
            putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, true)
            val tag = languageTag?.takeIf { it.isNotBlank() }
            if (tag != null) {
                putExtra(RecognizerIntent.EXTRA_LANGUAGE, tag)
            } else {
                putExtra(RecognizerIntent.EXTRA_LANGUAGE, Locale.getDefault().toLanguageTag())
            }
        }
        try {
            pendingPromise = promise
            activity.startActivityForResult(intent, REQUEST_RECOGNIZE)
        } catch (e: ActivityNotFoundException) {
            pendingPromise = null
            promise.reject("NO_RECOGNIZER", "No voice recognizer is installed on this phone")
        } catch (e: Exception) {
            pendingPromise = null
            promise.reject("VOICE_FAILED", e.message ?: e.toString())
        }
    }
}
