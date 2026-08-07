package com.pinkelephant.talk

import android.app.Activity
import android.content.ContentResolver
import android.content.Intent
import android.net.Uri
import android.provider.OpenableColumns
import com.facebook.react.bridge.Arguments
import com.facebook.react.bridge.Promise
import com.facebook.react.bridge.ReactApplicationContext
import com.facebook.react.bridge.ReactContextBaseJavaModule
import com.facebook.react.bridge.ReactMethod
import com.tom_roush.pdfbox.android.PDFBoxResourceLoader
import com.tom_roush.pdfbox.pdmodel.PDDocument
import com.tom_roush.pdfbox.text.PDFTextStripper
import java.util.zip.ZipInputStream

class DocumentModule(reactContext: ReactApplicationContext) :
    ReactContextBaseJavaModule(reactContext) {

    override fun getName(): String = "DocumentModule"

    companion object {
        const val REQUEST_OPEN_DOCUMENT = 9001
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
            map.putString("name", ctx?.let { displayName(it.contentResolver, uri) } ?: "document")
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
            return uri.lastPathSegment ?: "document"
        }
    }

    @ReactMethod
    fun openDocument(promise: Promise) {
        val activity = currentActivity
        if (activity == null) {
            promise.reject("NO_ACTIVITY", "No activity available")
            return
        }
        val intent = Intent(Intent.ACTION_OPEN_DOCUMENT).apply {
            addCategory(Intent.CATEGORY_OPENABLE)
            type = "*/*"
            putExtra(
                Intent.EXTRA_MIME_TYPES,
                arrayOf(
                    "text/plain",
                    "application/pdf",
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    "application/msword",
                ),
            )
            addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
        }
        try {
            pendingPromise = promise
            pendingContext = reactApplicationContext
            activity.startActivityForResult(intent, REQUEST_OPEN_DOCUMENT)
        } catch (e: Exception) {
            pendingPromise = null
            pendingContext = null
            promise.reject("PICK_FAILED", e.message)
        }
    }

    @ReactMethod
    fun extractText(uriString: String, promise: Promise) {
        try {
            val uri = Uri.parse(uriString)
            val resolver = reactApplicationContext.contentResolver
            val mime = resolver.getType(uri) ?: ""
            val input = resolver.openInputStream(uri)
                ?: throw Exception("Cannot open document")
            val text = when {
                mime.contains("pdf") -> extractPdf(input)
                mime.contains("wordprocessingml") -> extractDocx(input)
                mime == "application/msword" -> throw Exception(
                    "Legacy .doc files are not supported yet; please save as .docx or .txt",
                )
                else -> input.bufferedReader(Charsets.UTF_8).use { it.readText() }
            }
            if (text.isBlank()) {
                promise.reject("EMPTY_DOCUMENT", "No extractable text found in this document")
                return
            }
            promise.resolve(text)
        } catch (e: Exception) {
            promise.reject("EXTRACT_FAILED", e.message ?: e.toString())
        }
    }

    private fun extractPdf(input: java.io.InputStream): String {
        PDFBoxResourceLoader.init(reactApplicationContext.applicationContext)
        val doc = PDDocument.load(input.buffered())
        return try {
            val stripper = PDFTextStripper()
            stripper.getText(doc)
        } finally {
            doc.close()
            input.close()
        }
    }

    private fun extractDocx(input: java.io.InputStream): String {
        val zip = ZipInputStream(input.buffered())
        val paragraphs = ArrayList<String>()
        try {
            var entry = zip.nextEntry
            while (entry != null) {
                if (entry.name == "word/document.xml") {
                    val xml = zip.bufferedReader(Charsets.UTF_8).use { it.readText() }
                    val parts = Regex("<w:p[ >]").split(xml)
                    for (part in parts) {
                        val run = Regex("<w:t[^>]*>([^<]*)</w:t>")
                            .findAll(part)
                            .joinToString("") { it.groupValues[1] }
                            .trim()
                        if (run.isNotEmpty()) paragraphs.add(run)
                    }
                    break
                }
                zip.closeEntry()
                entry = zip.nextEntry
            }
        } finally {
            zip.close()
        }
        return paragraphs.joinToString("\n")
    }
}
