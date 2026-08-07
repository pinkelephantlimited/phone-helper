package com.pinkelephant.talk

import android.app.Activity
import android.content.ContentResolver
import android.content.Intent
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.net.Uri
import android.provider.OpenableColumns
import com.facebook.react.bridge.Arguments
import com.facebook.react.bridge.Promise
import com.facebook.react.bridge.ReactApplicationContext
import com.facebook.react.bridge.ReactContextBaseJavaModule
import com.facebook.react.bridge.ReactMethod
import java.io.File
import java.io.FileOutputStream

class PhotoModule(reactContext: ReactApplicationContext) :
    ReactContextBaseJavaModule(reactContext) {

    override fun getName(): String = "PhotoModule"

    companion object {
        const val REQUEST_OPEN_IMAGE = 9002
        @Volatile
        var pendingPromise: Promise? = null
        @Volatile
        var pendingContext: ReactApplicationContext? = null

        fun handleActivityResult(resultCode: Int, data: Intent?) {
            val p = pendingPromise ?: return
            pendingPromise = null
            val ctx = pendingContext
            pendingContext = null
            if (resultCode != Activity.RESULT_OK || data?.data == null) {
                p.resolve(null)
                return
            }
            val uri = data.data!!
            val map = Arguments.createMap()
            map.putString("uri", uri.toString())
            map.putString("name", ctx?.let { displayName(it.contentResolver, uri) } ?: "photo")
            map.putString("mime", ctx?.contentResolver?.getType(uri) ?: "")
            p.resolve(map)
        }

        private fun displayName(resolver: ContentResolver, uri: Uri): String {
            try {
                resolver.query(uri, arrayOf(OpenableColumns.DISPLAY_NAME), null, null, null)?.use { c ->
                    if (c.moveToFirst()) {
                        val idx = c.getColumnIndex(OpenableColumns.DISPLAY_NAME)
                        if (idx >= 0) {
                            val n = c.getString(idx)
                            if (!n.isNullOrBlank()) return n
                        }
                    }
                }
            } catch (_: Exception) {
            }
            return uri.lastPathSegment ?: "photo"
        }
    }

    @ReactMethod
    fun openImage(promise: Promise) {
        val activity = currentActivity
        if (activity == null) {
            promise.reject("NO_ACTIVITY", "No activity available")
            return
        }
        val intent = Intent(Intent.ACTION_OPEN_DOCUMENT).apply {
            addCategory(Intent.CATEGORY_OPENABLE)
            type = "image/*"
            addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
        }
        try {
            pendingPromise = promise
            pendingContext = reactApplicationContext
            activity.startActivityForResult(intent, REQUEST_OPEN_IMAGE)
        } catch (e: Exception) {
            pendingPromise = null
            pendingContext = null
            promise.reject("PICK_FAILED", e.message)
        }
    }

    @ReactMethod
    fun processImage(uriString: String, promise: Promise) {
        try {
            val uri = Uri.parse(uriString)
            val resolver = reactApplicationContext.contentResolver
            val input = resolver.openInputStream(uri)
                ?: throw Exception("Cannot open image")
            val bounds = BitmapFactory.Options().apply { inJustDecodeBounds = true }
            BitmapFactory.decodeStream(input, null, bounds)
            input.close()

            var w = bounds.outWidth
            var h = bounds.outHeight
            if (w <= 0 || h <= 0) throw Exception("Cannot decode image")
            val maxDim = 1280
            var sample = 1
            while (Math.max(w, h) / (sample * 2) >= maxDim) sample *= 2

            val opts = BitmapFactory.Options().apply { inSampleSize = sample }
            val input2 = resolver.openInputStream(uri) ?: throw Exception("Cannot open image")
            val bmp = BitmapFactory.decodeStream(input2, null, opts) ?: throw Exception("Cannot decode image")
            input2.close()

            val outFile = File(
                reactApplicationContext.cacheDir,
                "photo_${System.currentTimeMillis()}.jpg",
            )
            FileOutputStream(outFile).use { fos ->
                bmp.compress(Bitmap.CompressFormat.JPEG, 90, fos)
            }
            val bmpW = bmp.width
            val bmpH = bmp.height
            bmp.recycle()

            val map = Arguments.createMap()
            map.putString("path", outFile.absolutePath)
            map.putInt("width", bmpW)
            map.putInt("height", bmpH)
            promise.resolve(map)
        } catch (e: Exception) {
            promise.reject("PROCESS_FAILED", e.message ?: e.toString())
        }
    }
}
