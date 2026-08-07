package com.pinkelephant.talk

import android.media.AudioManager
import android.os.Bundle
import android.speech.tts.TextToSpeech
import android.speech.tts.UtteranceProgressListener
import com.facebook.react.bridge.Arguments
import com.facebook.react.bridge.Promise
import com.facebook.react.bridge.ReactApplicationContext
import com.facebook.react.bridge.ReactContextBaseJavaModule
import com.facebook.react.bridge.ReactMethod
import java.util.Locale

class TTSModule(reactContext: ReactApplicationContext) :
    ReactContextBaseJavaModule(reactContext), TextToSpeech.OnInitListener {

    companion object {
        private const val UTTERANCE_ID = "pink_elephant_utterance"
    }

    private var tts: TextToSpeech? = null
    private var ready = false
    private var pendingInit: Promise? = null
    private var pendingDone: Promise? = null

    init {
        tts = TextToSpeech(reactContext.applicationContext, this)
    }

    override fun getName(): String = "TTSModule"

    override fun onInit(status: Int) {
        if (status == TextToSpeech.SUCCESS) {
            ready = true
            tts?.setLanguage(Locale.getDefault())
            tts?.setOnUtteranceProgressListener(object : UtteranceProgressListener() {
                override fun onStart(utteranceId: String?) {}
                override fun onDone(utteranceId: String?) {
                    resolveDone()
                }
                @Deprecated("Deprecated in Java")
                override fun onError(utteranceId: String?) {
                    resolveDone()
                }
                override fun onError(utteranceId: String?, errorCode: Int) {
                    resolveDone()
                }
                @Deprecated("Deprecated in Java")
                override fun onStop(utteranceId: String?, interrupted: Boolean) {
                    resolveDone()
                }
            })
        }
        val p = pendingInit
        pendingInit = null
        if (p != null) {
            if (ready) p.resolve(true)
            else p.reject("TTS_INIT_FAILED", "Voice output could not be initialized ($status)")
        }
    }

    private fun resolveDone() {
        val p = pendingDone
        pendingDone = null
        p?.resolve(true)
    }

    @ReactMethod
    fun init(promise: Promise) {
        if (ready) {
            promise.resolve(true)
            return
        }
        pendingInit = promise
    }

    @ReactMethod
    fun isReady(promise: Promise) {
        promise.resolve(ready)
    }

    @ReactMethod
    fun speak(text: String, promise: Promise) {
        val t = tts
        if (!ready || t == null) {
            promise.reject("TTS_NOT_READY", "Voice output is not ready")
            return
        }
        if (text.isBlank()) {
            promise.resolve(true)
            return
        }
        resolveDone()
        t.stop()
        val params = Bundle().apply {
            putInt(TextToSpeech.Engine.KEY_PARAM_STREAM, AudioManager.STREAM_MUSIC)
            putFloat(TextToSpeech.Engine.KEY_PARAM_VOLUME, 1.0f)
        }
        val res = t.speak(text, TextToSpeech.QUEUE_FLUSH, params, UTTERANCE_ID)
        if (res == TextToSpeech.ERROR) {
            promise.reject("TTS_SPEAK_FAILED", "The phone could not play speech")
        } else {
            pendingDone = promise
        }
    }

    @ReactMethod
    fun stop(promise: Promise) {
        resolveDone()
        tts?.stop()
        promise.resolve(true)
    }

    @ReactMethod
    fun setLanguage(languageTag: String, promise: Promise) {
        val t = tts
        if (t == null) {
            promise.resolve(false)
            return
        }
        val result = t.setLanguage(Locale.forLanguageTag(languageTag))
        promise.resolve(
            result == TextToSpeech.LANG_AVAILABLE ||
                result == TextToSpeech.LANG_COUNTRY_AVAILABLE ||
                result == TextToSpeech.LANG_COUNTRY_VAR_AVAILABLE,
        )
    }

    @ReactMethod
    fun getVoices(promise: Promise) {
        val t = tts
        if (t == null) {
            promise.resolve(Arguments.createArray())
            return
        }
        val arr = Arguments.createArray()
        t.voices?.forEach { v -> arr.pushString(v.name) }
        promise.resolve(arr)
    }

    @ReactMethod
    fun shutdown(promise: Promise) {
        resolveDone()
        tts?.stop()
        tts?.shutdown()
        tts = null
        ready = false
        promise.resolve(true)
    }

    override fun onCatalystInstanceDestroy() {
        try {
            tts?.stop()
            tts?.shutdown()
        } catch (_: Exception) {
        }
        tts = null
        ready = false
        super.onCatalystInstanceDestroy()
    }
}
