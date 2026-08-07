package com.pinkelephant.talk

import android.media.AudioAttributes
import android.media.MediaPlayer
import com.facebook.react.bridge.Promise
import com.facebook.react.bridge.ReactApplicationContext
import com.facebook.react.bridge.ReactContextBaseJavaModule
import com.facebook.react.bridge.ReactMethod
import java.io.File
import java.util.concurrent.Executors

class CantoneseTtsModule(reactContext: ReactApplicationContext) :
    ReactContextBaseJavaModule(reactContext) {

    private val appContext = reactContext
    private val audioDir = File(appContext.cacheDir, "cntts")
    private val executor = Executors.newSingleThreadExecutor()
    private val initLock = Object()
    private var nativeReady = false
    private var player: MediaPlayer? = null

    init {
        audioDir.mkdirs()
    }

    private fun ensureNative(): Boolean {
        if (nativeReady) return true
        synchronized(initLock) {
            if (nativeReady) return true
            try {
                val dataPath = File(appContext.filesDir, "espeak-ng-data")
                if (!File(dataPath, "phontab").exists()) {
                    dataPath.mkdirs()
                    copyAssetDir("espeak-ng-data", dataPath)
                }
                System.loadLibrary("cantonese_tts")
                val rc = nativeInit(dataPath.absolutePath)
                if (rc < 0) return false
                nativeReady = true
            } catch (_: Throwable) {
                nativeReady = false
            }
        }
        return nativeReady
    }

    private fun copyAssetDir(assetPath: String, dest: File) {
        val assets = appContext.assets
        val names = assets.list(assetPath) ?: emptyArray()
        dest.mkdirs()
        for (name in names) {
            val srcPath = if (assetPath.isEmpty()) name else "$assetPath/$name"
            val target = File(dest, name)
            if (assets.list(srcPath) != null) {
                copyAssetDir(srcPath, target)
            } else {
                val input = assets.open(srcPath)
                input.use { `in` -> target.outputStream().use { `out` -> `in`.copyTo(`out`) } }
            }
        }
    }

    override fun getConstants(): Map<String, Any> = emptyMap()

    override fun getName(): String = "CantoneseTts"

    @ReactMethod
    fun isReady(promise: Promise) {
        promise.resolve(nativeReady)
    }

    @ReactMethod
    fun setVoice(voice: String, promise: Promise) {
        promise.resolve(nativeReady)
    }

    @ReactMethod
    fun speak(text: String, voice: String?, promise: Promise) {
        val v = voice ?: "yue"
        executor.execute {
            try {
                if (!ensureNative()) {
                    promise.reject("CNTTS_INIT_FAILED", "Cantonese engine could not start")
                    return@execute
                }
                stopPlayback()
                audioDir.mkdirs()
                val wav = File(audioDir, "out.wav")
                val ok = nativeSpeak(text, v, wav.absolutePath, 160)
                if (ok && wav.exists()) {
                    playAudio(wav.absolutePath)
                    promise.resolve(true)
                } else {
                    promise.resolve(false)
                }
            } catch (e: Exception) {
                promise.reject("CNTTS_FAILED", e.message)
            }
        }
    }

    @ReactMethod
    fun stop(promise: Promise) {
        stopPlayback()
        promise.resolve(true)
    }

    private fun stopPlayback() {
        val p = player
        player = null
        if (p != null) {
            if (p.isPlaying) p.stop()
            p.release()
        }
    }

    private fun playAudio(path: String) {
        player?.release()
        player = MediaPlayer()
        player?.setDataSource(path)
        player?.prepare()
        player?.setAudioAttributes(
            AudioAttributes.Builder()
                .setUsage(AudioAttributes.USAGE_MEDIA)
                .setContentType(AudioAttributes.CONTENT_TYPE_SPEECH)
                .build(),
        )
        player?.start()
    }

    private external fun nativeInit(dataPath: String): Int
    private external fun nativeSpeak(text: String, voice: String, outPath: String, rate: Int): Boolean
    private external fun nativeTerminate(): Boolean
}