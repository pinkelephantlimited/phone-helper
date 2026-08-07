#include <jni.h>
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <espeak-ng/speak_lib.h>
#include <espeak-ng/espeak_ng.h>

#define SAMPLE_RATE 22050
#define NUM_CHANNELS 1
#define BITS_PER_SAMPLE 16

static FILE *out_wav = NULL;
static long data_start = 0;

static int on_wav_data(short *wav, int numsamples, espeak_EVENT *events) {
    (void)events;
    if (wav == NULL || numsamples <= 0 || out_wav == NULL) return 0;
    if (data_start == 0) {
        data_start = 1;
        long size = 0;
        fseek(out_wav, 0, SEEK_END);
        size = ftell(out_wav);
        fseek(out_wav, 0, SEEK_SET);
        unsigned char hdr[44];
        memset(hdr, 0, sizeof(hdr));
        hdr[0]='R'; hdr[1]='I'; hdr[2]='F'; hdr[3]='F';
        hdr[4]=(unsigned char)((size-8)&0xff);
        hdr[5]=(unsigned char)(((size-8)>>8)&0xff);
        hdr[6]=(unsigned char)(((size-8)>>16)&0xff);
        hdr[7]=(unsigned char)(((size-8)>>24)&0xff);
        hdr[8]='W'; hdr[9]='A'; hdr[10]='V'; hdr[11]='E';
        hdr[12]='f'; hdr[13]='m'; hdr[14]='t'; hdr[15]=' ';
        hdr[16]=16; hdr[17]=0; hdr[18]=0; hdr[19]=0;
        hdr[20]=1; hdr[21]=0;
        hdr[22]=NUM_CHANNELS;
        hdr[24]=(unsigned char)(SAMPLE_RATE&0xff);
        hdr[25]=(unsigned char)((SAMPLE_RATE>>8)&0xff);
        hdr[26]=(unsigned char)((SAMPLE_RATE>>16)&0xff);
        hdr[27]=(unsigned char)((SAMPLE_RATE>>24)&0xff);
        unsigned int byte_rate = SAMPLE_RATE * NUM_CHANNELS * (BITS_PER_SAMPLE/8);
        hdr[28]=(unsigned char)(byte_rate&0xff);
        hdr[29]=(unsigned char)((byte_rate>>8)&0xff);
        hdr[30]=(unsigned char)((byte_rate>>16)&0xff);
        hdr[31]=(unsigned char)((byte_rate>>24)&0xff);
        hdr[32]=NUM_CHANNELS*(BITS_PER_SAMPLE/8);
        hdr[34]=BITS_PER_SAMPLE;
        hdr[36]='d'; hdr[37]='a'; hdr[38]='t'; hdr[39]='a';
        fwrite(hdr, 1, 44, out_wav);
    }
    fwrite(wav, 2, (size_t)numsamples, out_wav);
    return 0;
}

JNIEXPORT jint JNICALL
Java_com_pinkelephant_talk_CantoneseTtsModule_nativeInit(JNIEnv *env, jobject thiz, jstring dataPath) {
    (void)thiz;
    const char *path = (*env)->GetStringUTFChars(env, dataPath, NULL);
    int result = espeak_Initialize(AUDIO_OUTPUT_SYNCHRONOUS, 0, path, 0);
    (*env)->ReleaseStringUTFChars(env, dataPath, path);
    if (result < 0) return (jint)result;
    espeak_SetSynthCallback(on_wav_data);
    espeak_SetParameter(espeakRATE, 160, 0);
    return 0;
}

JNIEXPORT jboolean JNICALL
Java_com_pinkelephant_talk_CantoneseTtsModule_nativeSpeak(JNIEnv *env, jobject thiz, jstring text, jstring voice, jstring outPath, jint rate) {
    (void)thiz;
    const char *t = (*env)->GetStringUTFChars(env, text, NULL);
    const char *v = (*env)->GetStringUTFChars(env, voice, NULL);
    const char *o = (*env)->GetStringUTFChars(env, outPath, NULL);

    out_wav = fopen(o, "wb");
    data_start = 0;
    if (out_wav == NULL) {
        (*env)->ReleaseStringUTFChars(env, text, t);
        (*env)->ReleaseStringUTFChars(env, voice, v);
        (*env)->ReleaseStringUTFChars(env, outPath, o);
        return JNI_FALSE;
    }
    espeak_SetParameter(espeakRATE, rate, 0);
    espeak_SetVoiceByName(v);

    /* Chunk long text into sentence-sized pieces and synthesize each one
       individually. espeak-ng in SYNCHRONOUS mode is only reliably safe for
       short utterances; a single huge espeak_Synth() calls trigger a known
       thread race (FORTIFY: pthread_mutex_lock on a destroyed mutex). */
    espeak_ERROR err = EE_OK;
    size_t len = strlen(t);
    size_t start = 0;
    const char *cjk = "。！？；：、，…！？.!?;:\n";
    while (start < len) {
        size_t end = len;
        if (len - start > 220) {
            end = start + 220;
            while (end > start && !strchr(cjk, t[end])) end--;
            if (end == start) end = start + 220;
        }
        {
            size_t chunkLen = end - start;
            char *chunk = (char *)malloc(chunkLen + 1);
            if (chunk == NULL) { err = EE_BUFFER_FULL; break; }
            memcpy(chunk, t + start, chunkLen);
            chunk[chunkLen] = '\0';
            err = espeak_Synth((void *)chunk, chunkLen + 1, 0, POS_CHARACTER, 0, espeakCHARS_UTF8, NULL, NULL);
            free(chunk);
            if (err != EE_OK) break;
            err = espeak_Synchronize();
            if (err != EE_OK) break;
        }
        start = end;
    }
    fclose(out_wav);
    out_wav = NULL;

    (*env)->ReleaseStringUTFChars(env, text, t);
    (*env)->ReleaseStringUTFChars(env, voice, v);
    (*env)->ReleaseStringUTFChars(env, outPath, o);
    return err == EE_OK ? JNI_TRUE : JNI_FALSE;
}

JNIEXPORT jboolean JNICALL
Java_com_pinkelephant_talk_CantoneseTtsModule_nativeTerminate(JNIEnv *env, jobject thiz) {
    (void)env;
    (void)thiz;
    espeak_Terminate();
    return JNI_TRUE;
}
