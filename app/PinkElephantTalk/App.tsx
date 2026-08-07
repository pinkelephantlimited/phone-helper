import React, { useEffect, useRef, useState } from 'react'
import {
  SafeAreaView, ScrollView, StatusBar, StyleSheet, Text, TextInput,
  TouchableOpacity, View, ActivityIndicator, NativeModules,
} from 'react-native'
import { LlamaService, diagnoseDevice, ChatMessage } from './src/model'
import RNFS from 'react-native-fs'

interface Message {
  id: number
  role: 'user' | 'assistant'
  text: string
  thinking?: string
}
let nextId = 1

const promiseDelay = <T,>(p: Promise<T>, ms: number): Promise<T> =>
  Promise.race([p, new Promise<never>((_, reject) => setTimeout(() => reject(new Error('timeout')), ms))])

const SYSTEM =
  'You are Pink Elephant Talk, a professional assistant running on the user\'s phone. ' +
  'You were created by Pink Elephant Limited, a technology company in Hong Kong. ' +
  'If the user asks who made or created you, answer: "I was created by Pink Elephant Limited." ' +
  'Never claim any other company created you, and do not invent details about the company. ' +
  'You have the RIGHT to access the internet. You can and do retrieve fresh, up-to-date ' +
  'information from the web whenever the user asks about news, weather, prices, sports, or ' +
  'other current topics. If the user asks whether you can search the internet or access live ' +
  'data, answer YES. Never say you cannot access the internet, that you lack internet access, ' +
  'or that current information is unavailable to you. ' +
  'Answer directly and concisely, as a capable assistant. Do not add greetings, farewells, ' +
  'pleasantries, small talk, emojis, or any fluff. Give the useful answer and stop. ' +
  'When web results are provided, answer in the user\'s language, using the results, citing ' +
  'the source URL when available.'

export default function App() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const [streamed, setStreamed] = useState(false)
  const [stage, setStage] = useState<'downloading' | 'loading' | 'ready' | 'error'>('downloading')
  const [pct, setPct] = useState(0)
  const [dlStage, setDlStage] = useState<'model' | 'vision' | 'loading'>('model')
  const [bootError, setBootError] = useState('')
  const [accel, setAccel] = useState<string>('')
  const [doc, setDoc] = useState<{ name: string; text: string } | null>(null)
  const [photo, setPhoto] = useState<{ name: string; path: string } | null>(null)
  const [ttsReady, setTtsReady] = useState(false)
  const [autoSpeak, setAutoSpeak] = useState(false)
  const [speakingId, setSpeakingId] = useState<number | null>(null)
  const [voiceLang, setVoiceLang] = useState<string>('auto')
  const VOICES = [
    { key: 'auto', tag: '', espeak: 'yue', label: 'Voice: Auto' },
    { key: 'zh-HK', tag: 'zh-HK', espeak: 'yue', label: 'Voice: 粵語' },
    { key: 'zh-CN', tag: 'zh-CN', espeak: 'cmn', label: 'Voice: 普通话' },
    { key: 'en-US', tag: 'en-US', espeak: 'en', label: 'Voice: English' },
  ]
  const startedRef = useRef(false)
  const scrollRef = useRef<ScrollView>(null)
  const replyIdRef = useRef<number | null>(null)

  const applyVoice = async (key: string) => {
    setVoiceLang(key)
    const tag = VOICES.find(v => v.key === key)?.tag ?? ''
    try {
      if (key === 'auto' && tag === '') {
        // rely on vivo engine default locale; reset espeak voice
      } else if (tag) {
        const ok = await Promise.race([
          NativeModules.TTSModule.setLanguage(tag),
          new Promise(r => setTimeout(() => r(false), 4000)),
        ])
        console.log(`[voice] setLanguage("${tag}") => ${ok}`)
      }
    } catch (e) {
      console.log(`[voice] setLanguage("${tag}") threw ${e}`)
    }
    try {
      await RNFS.writeFile(`${RNFS.DocumentDirectoryPath}/voice.txt`, key)
    } catch {
      // best-effort persist
    }
  }

  const cycleVoice = () => {
    const idx = VOICES.findIndex(v => v.key === voiceLang)
    applyVoice(VOICES[(idx + 1) % VOICES.length].key)
  }

  useEffect(() => {
    const lm = LlamaService.instance
    lm.onDownloadProgress = (w, t, stage) => {
      if (t && t > 0) setPct(Math.round((w / t) * 100))
      if (stage) setDlStage(stage)
    }
    NativeModules.TTSModule.init()
      .then(() => setTtsReady(true))
      .catch(() => setTtsReady(false))
    RNFS.readFile(`${RNFS.DocumentDirectoryPath}/voice.txt`)
      .then(raw => {
        const key = raw.trim()
        if (VOICES.some(v => v.key === key)) {
          setVoiceLang(key)
          console.log(`[voice] restored voice.txt key=${key}`)
        }
      })
      .catch(() => {})
    if (!startedRef.current) {
      startedRef.current = true
      boot()
    }
  }, [])

  const boot = async () => {
    setStage('downloading')
    setBootError('')
    try {
      const lm = LlamaService.instance
      const diag = await diagnoseDevice()
      setAccel(diag.gpu ? `GPU: ${diag.backend} ${diag.deviceName}` : `CPU (no GPU): ${diag.reasonNoGPU}`)
      await lm.load()
      setStage('ready')
    } catch (e) {
      console.warn('boot error', e)
      setBootError(String(e))
      setStage('error')
    }
  }

  const scrollToBottom = () => scrollRef.current?.scrollToEnd({ animated: true })

  const stopSpeak = () => {
    setSpeakingId(null)
    NativeModules.TTSModule.stop().catch(() => {})
    try {
      NativeModules.CantoneseTts.stop()
    } catch {}
  }

  const speakText = async (text: string, msgId: number | null) => {
    if (!text) return
    if (!ttsReady) return
    try {
      setSpeakingId(msgId)
      await NativeModules.TTSModule.speak(text)
      setSpeakingId(prev => (prev === msgId ? null : prev))
    } catch {
      setSpeakingId(prev => (prev === msgId ? null : prev))
    }
  }

  const toggleSpeak = (msgId: number, text: string) => {
    if (speakingId === msgId) stopSpeak()
    else speakText(text, msgId)
  }

  const push = (role: 'user' | 'assistant', text: string, thinking?: string) => {
    const id = nextId++
    setMessages(prev => [...prev, { id, role, text, thinking }])
    return id
  }
  const patch = (id: number, text: string, thinking?: string) =>
    setMessages(prev => prev.map(m => (m.id === id ? { ...m, text, thinking } : m)))

  const buildHistory = (text: string): ChatMessage[] => {
    const history: ChatMessage[] = [{ role: 'system', content: SYSTEM }]
    if (doc) {
      history.push({
        role: 'system',
        content: `A document was attached by the user: [${doc.name}].\nUse the document text below to answer questions about it.\n\n${doc.text}`,
      })
    }
    for (const m of messages.slice(-6)) {
      history.push({ role: m.role, content: m.text })
    }
    history.push({ role: 'user', content: text })
    return history
  }

  const pickDocument = async () => {
    if (busy) return
    try {
      const picked = await NativeModules.DocumentModule.openDocument()
      if (!picked) return
      const text = await NativeModules.DocumentModule.extractText(picked.uri)
      setDoc({ name: picked.name, text: text.slice(0, 1600) })
      push('user', `📎 ${picked.name}`)
    } catch (e) {
      push('assistant', 'Sorry, could not read that document: ' + String(e))
    }
  }

  const pickPhoto = async () => {
    if (busy) return
    try {
      const picked = await NativeModules.PhotoModule.openImage()
      if (!picked) return
      const processed = await NativeModules.PhotoModule.processImage(picked.uri)
      setPhoto({ name: picked.name, path: processed.path })
      push('user', `🖼️ ${picked.name}`)
    } catch (e) {
      push('assistant', 'Sorry, could not open that photo: ' + String(e))
    }
  }

  const runAnswer = async (text: string) => {
    setBusy(true)
    setStreamed(false)
    replyIdRef.current = push('assistant', '')
    stopSpeak()
    try {
      const reply = await LlamaService.instance.complete(buildHistory(text), chunk => {
        setStreamed(true)
        patch(replyIdRef.current!, chunk.text, chunk.thinking)
        scrollToBottom()
      }, photo?.path)
      patch(replyIdRef.current!, reply.text, reply.thinking)
      if (autoSpeak && reply.text) speakText(reply.text, replyIdRef.current)
    } catch (e) {
      patch(replyIdRef.current!, 'Sorry, an error occurred: ' + String(e))
    } finally {
      setBusy(false)
      setPhoto(null)
      scrollToBottom()
    }
  }

  const send = () => {
    const text = input.trim()
    if (!text || busy) return
    setInput('')
    push('user', text)
    runAnswer(text)
  }

  if (stage !== 'ready') {
    return (
      <SafeAreaView style={styles.center}>
        <StatusBar barStyle="light-content" backgroundColor={ROSE.deep} />
        <View style={styles.loadLogo}>
          <View style={styles.loadMark} />
          <Text style={styles.brand}>Pink Elephant Talk</Text>
          <Text style={styles.brandTag}>by Pink Elephant Limited · offline · private · on-device</Text>
        </View>
        {stage === 'error' ? (
          <>
            <Text style={styles.loadText}>Something went wrong while loading the model:</Text>
            <Text style={[styles.loadText, { fontSize: 13, color: '#c0392b', marginTop: 8 }]}>{bootError}</Text>
            <TouchableOpacity onPress={() => boot()} style={styles.retry}>
              <Text style={styles.retryTxt}>Retry</Text>
            </TouchableOpacity>
          </>
        ) : (
          <>
            <View style={styles.loadRing}>
              <ActivityIndicator size="large" color={ROSE.main} />
            </View>
            <Text style={styles.loadText}>Downloading & loading chat model…</Text>
            <Text style={styles.loadPct}>{pct}%</Text>
            <Text style={styles.loadSub}>
              {dlStage === 'vision'
                ? 'downloading vision encoder…'
                : dlStage === 'loading'
                  ? 'loading model…'
                  : 'downloading language model…'}
              · ~1.5 GB · one-time · runs on-device
            </Text>
          </>
        )}
      </SafeAreaView>
    )
  }

  return (
    <SafeAreaView style={styles.root}>
      <StatusBar barStyle="light-content" backgroundColor={ROSE.deep} />
      <View style={styles.header}>
        <View style={styles.headerLeft}>
          <View style={styles.avatar}>
            <Text style={styles.avatarText}>PE</Text>
          </View>
          <View>
            <Text style={styles.title}>Pink Elephant Talk</Text>
            <Text style={styles.subtitle}>by Pink Elephant Limited · v7.2</Text>
          </View>
        </View>
        <View style={styles.headerRight}>
          {ttsReady && (
            <TouchableOpacity
              onPress={() => {
                if (autoSpeak) stopSpeak()
                setAutoSpeak(v => !v)
              }}
              style={[styles.speakToggle, autoSpeak && styles.speakToggleOn]}
              hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
            >
              <Text style={[styles.speakToggleTxt, autoSpeak && styles.speakToggleTxtOn]}>🔊</Text>
            </TouchableOpacity>
          )}
          {ttsReady && (
            <TouchableOpacity
              onPress={cycleVoice}
              style={[styles.speakToggle, voiceLang !== 'auto' && styles.voiceToggleOn]}
              hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
            >
              <Text style={styles.speakToggleTxt}>{voiceLang === 'auto' ? '🌐' : '🗣️'}</Text>
            </TouchableOpacity>
          )}
          <View style={styles.onlineDot} />
        </View>
      </View>
      <View style={styles.accelBar}>
        <Text style={styles.accel} numberOfLines={1}>{accel}</Text>
      </View>
      <ScrollView ref={scrollRef} style={styles.scroll}
        onContentSizeChange={scrollToBottom} contentContainerStyle={styles.scrollInner}>
        {messages.length === 0 && (
          <View style={styles.welcome}>
            <View style={styles.welcomeMark} />
            <Text style={styles.welcomeTitle}>How can I help?</Text>
            <Text style={styles.hint}>
              Ask me anything — your model runs entirely on this phone, no cloud AI API.
              Answers stream in instantly.
              Pink Elephant Talk is made by Pink Elephant Limited.
            </Text>
          </View>
        )}
        {messages.map(m => (
          <View key={m.id} style={[styles.row, m.role === 'user' ? styles.rowUser : styles.rowAssistant]}>
            <View style={[styles.bubble, m.role === 'user' ? styles.user : styles.assistant]}>
              {m.text ? (
                <Text style={[styles.msgText, { color: m.role === 'user' ? '#fff' : '#3a2a32' }]}>{m.text}</Text>
              ) : null}
            </View>
            {m.role === 'assistant' && m.text && ttsReady ? (
              <TouchableOpacity
                onPress={() => toggleSpeak(m.id, m.text)}
                style={[styles.speakBtn, speakingId === m.id && styles.speakBtnOn]}
                hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
              >
                <Text style={styles.speakBtnTxt}>{speakingId === m.id ? '⏹' : '🔊'}</Text>
              </TouchableOpacity>
            ) : null}
          </View>
        ))}
        {busy && !streamed && (
          <View style={[styles.row, styles.rowAssistant]}>
            <View style={[styles.bubble, styles.assistant, styles.typing]}>
              <View style={styles.typingDot} />
              <View style={[styles.typingDot, { opacity: 0.5 }]} />
              <View style={[styles.typingDot, { opacity: 0.25 }]} />
            </View>
          </View>
        )}
      </ScrollView>
      <View style={styles.inputWrap}>
        {photo && (
          <View style={styles.docBar}>
            <Text style={styles.docText} numberOfLines={1}>🖼️ {photo.name}</Text>
            <TouchableOpacity onPress={() => setPhoto(null)} hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}>
              <Text style={styles.docX}>✕</Text>
            </TouchableOpacity>
          </View>
        )}
        {doc && (
          <View style={styles.docBar}>
            <Text style={styles.docText} numberOfLines={1}>📎 {doc.name}</Text>
            <TouchableOpacity onPress={() => setDoc(null)} hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}>
              <Text style={styles.docX}>✕</Text>
            </TouchableOpacity>
          </View>
        )}
        <View style={styles.inputRow}>
          <TouchableOpacity onPress={pickDocument} style={styles.attach} disabled={busy}>
            <Text style={styles.attachTxt}>📎</Text>
          </TouchableOpacity>
          <TouchableOpacity onPress={pickPhoto} style={styles.attach} disabled={busy}>
            <Text style={styles.attachTxt}>🖼️</Text>
          </TouchableOpacity>
          <TextInput style={styles.input} value={input} onChangeText={setInput}
            placeholder="Type a question…" placeholderTextColor="#b08b99"
            onSubmitEditing={send} selectionColor={ROSE.main} />
          <TouchableOpacity onPress={send} style={[styles.send, busy && styles.sendDisabled]} disabled={busy}>
            <Text style={styles.sendTxt}>➤</Text>
          </TouchableOpacity>
        </View>
      </View>
    </SafeAreaView>
  )
}

const ROSE = {
  deep: '#7a2848',
  main: '#c94f7c',
  soft: '#e88fae',
  blush: '#fdeef4',
  tint: '#f6dfe9',
  text: '#3a2a32',
  muted: '#8a6b78',
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: ROSE.blush },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: 24, backgroundColor: ROSE.deep },
  loadLogo: { alignItems: 'center', marginBottom: 48 },
  loadMark: {
    width: 64, height: 64, borderRadius: 32, backgroundColor: ROSE.soft,
    marginBottom: 18, borderWidth: 3, borderColor: 'rgba(255,255,255,0.35)',
  },
  brand: { fontSize: 28, fontWeight: '700', color: '#fff', letterSpacing: 0.4 },
  brandTag: { fontSize: 13, color: 'rgba(255,255,255,0.75)', marginTop: 6, letterSpacing: 1 },
  loadRing: {
    width: 96, height: 96, borderRadius: 48, backgroundColor: 'rgba(255,255,255,0.12)',
    alignItems: 'center', justifyContent: 'center', marginBottom: 8,
  },
  loadText: { marginTop: 12, fontSize: 15, color: 'rgba(255,255,255,0.92)', textAlign: 'center' },
  loadPct: { fontSize: 32, fontWeight: '700', color: '#fff', marginTop: 4 },
  loadSub: { fontSize: 13, color: 'rgba(255,255,255,0.6)', marginTop: 8, textAlign: 'center' },
  retry: { marginTop: 20, backgroundColor: '#fff', borderRadius: 24, paddingHorizontal: 32, paddingVertical: 12 },
  retryTxt: { color: ROSE.deep, fontSize: 16, fontWeight: '600' },
  header: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between',
    paddingHorizontal: 18, paddingTop: 16, paddingBottom: 14,
    backgroundColor: ROSE.deep,
    borderBottomLeftRadius: 20, borderBottomRightRadius: 20,
    shadowColor: '#000', shadowOpacity: 0.2, shadowRadius: 10, shadowOffset: { width: 0, height: 4 },
    elevation: 6,
  },
  headerLeft: { flexDirection: 'row', alignItems: 'center' },
  headerRight: { flexDirection: 'row', alignItems: 'center' },
  speakToggle: {
    width: 34, height: 34, borderRadius: 17, backgroundColor: 'rgba(255,255,255,0.18)',
    alignItems: 'center', justifyContent: 'center', marginRight: 10,
  },
  speakToggleOn: { backgroundColor: ROSE.soft },
  speakToggleTxt: { fontSize: 16 },
  speakToggleTxtOn: {},
  voiceToggleOn: { backgroundColor: ROSE.main },
  speakBtn: {
    width: 32, height: 32, borderRadius: 16, backgroundColor: ROSE.tint,
    alignItems: 'center', justifyContent: 'center', marginLeft: 8, alignSelf: 'flex-end',
    borderWidth: 1, borderColor: ROSE.soft,
  },
  speakBtnOn: { backgroundColor: ROSE.soft },
  speakBtnTxt: { fontSize: 14 },
  avatar: {
    width: 42, height: 42, borderRadius: 21, backgroundColor: ROSE.soft,
    alignItems: 'center', justifyContent: 'center', marginRight: 12,
  },
  avatarText: { color: '#fff', fontWeight: '700', fontSize: 15, letterSpacing: 0.5 },
  title: { fontSize: 18, fontWeight: '700', color: '#fff' },
  subtitle: { fontSize: 12, color: 'rgba(255,255,255,0.75)', marginTop: 2 },
  onlineDot: { width: 10, height: 10, borderRadius: 5, backgroundColor: '#7fe0a3' },
  accelBar: { paddingHorizontal: 18, paddingVertical: 6, backgroundColor: ROSE.blush },
  accel: { fontSize: 11, color: ROSE.muted, textAlign: 'center' },
  scroll: { flex: 1 },
  scrollInner: { padding: 16, paddingBottom: 24 },
  welcome: { alignItems: 'center', marginTop: 32, marginBottom: 12, paddingHorizontal: 24 },
  welcomeMark: {
    width: 56, height: 56, borderRadius: 28, backgroundColor: ROSE.tint,
    borderWidth: 2, borderColor: ROSE.soft, marginBottom: 14,
  },
  welcomeTitle: { fontSize: 20, fontWeight: '700', color: ROSE.text },
  hint: {
    color: ROSE.muted, textAlign: 'center', fontSize: 14, lineHeight: 21,
    marginTop: 10, paddingHorizontal: 12,
  },
  row: { marginBottom: 10, flexDirection: 'row' },
  rowUser: { justifyContent: 'flex-end' },
  rowAssistant: { justifyContent: 'flex-start' },
  bubble: { maxWidth: '82%', borderRadius: 18, paddingHorizontal: 14, paddingVertical: 11 },
  user: {
    backgroundColor: ROSE.main,
    borderBottomRightRadius: 6,
    shadowColor: ROSE.deep, shadowOpacity: 0.18, shadowRadius: 6, shadowOffset: { width: 0, height: 2 },
    elevation: 2,
  },
  assistant: {
    backgroundColor: '#fff',
    borderWidth: 1, borderColor: ROSE.tint,
    borderBottomLeftRadius: 6,
    shadowColor: '#000', shadowOpacity: 0.06, shadowRadius: 6, shadowOffset: { width: 0, height: 2 },
    elevation: 1,
  },
  msgText: { fontSize: 15, lineHeight: 22 },
  thinkingText: { fontSize: 12, lineHeight: 17, color: '#a08a95', fontStyle: 'italic', marginBottom: 6 },
  typing: { flexDirection: 'row', alignItems: 'center', paddingVertical: 13 },
  typingDot: {
    width: 8, height: 8, borderRadius: 4, backgroundColor: ROSE.soft, marginHorizontal: 3,
  },
  inputWrap: { paddingHorizontal: 12, paddingBottom: 10, backgroundColor: ROSE.blush },
  docBar: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between',
    backgroundColor: ROSE.tint, borderRadius: 14, marginHorizontal: 6, marginTop: 6,
    paddingHorizontal: 12, paddingVertical: 8, marginBottom: 2,
  },
  docText: { flex: 1, color: ROSE.text, fontSize: 13, marginRight: 8 },
  docX: { color: ROSE.muted, fontSize: 15, fontWeight: '700', paddingHorizontal: 4 },
  inputRow: { flexDirection: 'row', alignItems: 'center', padding: 6 },
  attach: {
    width: 42, height: 46, borderRadius: 23, backgroundColor: ROSE.blush,
    alignItems: 'center', justifyContent: 'center', marginRight: 8,
    borderWidth: 1, borderColor: ROSE.tint,
  },
  attachTxt: { fontSize: 18 },
  input: {
    flex: 1, backgroundColor: '#fff', borderRadius: 24,
    paddingHorizontal: 18, paddingVertical: 12, fontSize: 15, color: ROSE.text,
    marginRight: 10, borderWidth: 1, borderColor: ROSE.tint,
    shadowColor: '#000', shadowOpacity: 0.05, shadowRadius: 6, shadowOffset: { width: 0, height: 2 },
    elevation: 1,
  },
  send: {
    width: 46, height: 46, borderRadius: 23, backgroundColor: ROSE.main,
    alignItems: 'center', justifyContent: 'center',
    shadowColor: ROSE.deep, shadowOpacity: 0.3, shadowRadius: 8, shadowOffset: { width: 0, height: 3 },
    elevation: 4,
  },
  sendDisabled: { opacity: 0.5 },
  sendTxt: { color: '#fff', fontSize: 18, marginLeft: 2 },
})
