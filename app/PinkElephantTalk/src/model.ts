import { initLlama, getBackendDevicesInfo, LlamaContext } from 'llama.rn'
import RNFS from 'react-native-fs'
import * as web from './web'

const MODEL_URL =
  'https://huggingface.co/pinkelephantlimited/pink-elephant-talk/resolve/main/models/Qwen3VL-2B-Instruct-Q4_K_M.gguf'

const MODEL_PATH = `${RNFS.DocumentDirectoryPath}/qwen3vl-2b-instruct-q4_k_m.gguf`

const MMPROJ_URL =
  'https://huggingface.co/pinkelephantlimited/pink-elephant-talk/resolve/main/models/mmproj-Qwen3VL-2B-Instruct-Q8_0.gguf'

const MMPROJ_PATH = `${RNFS.DocumentDirectoryPath}/mmproj-qwen3vl-2b-instruct-q8_0.gguf`

const OLD_MODEL_PATH = `${RNFS.DocumentDirectoryPath}/qwen3-1.7b-instruct-q4_k_m.gguf`
const THINKING_MODEL_PATH = `${RNFS.DocumentDirectoryPath}/qwen3vl-2b-thinking-q4_k_m.gguf`
const THINKING_MMPROJ_PATH = `${RNFS.DocumentDirectoryPath}/mmproj-qwen3vl-2b-thinking-q8_0.gguf`

const MEDIA_MARKER = '<__media__>'

export const MODEL_SIZE_BYTES = 1107409952
export const MMPROJ_SIZE_BYTES = 445053216

const THINK_START = '<think>'
const THINK_END = '</think>'

function safeStringify(v: unknown): string {
  try {
    const seen = new WeakSet()
    return JSON.stringify(v, (k, val) => {
      if (typeof val === 'object' && val !== null) {
        if (seen.has(val)) return '[circular]'
        seen.add(val)
      }
      return val
    })
  } catch {
    return '[unserializable]'
  }
}

function fixBrand(reply: StreamedReply): StreamedReply {
  if (!reply.text || !/pink elephant/i.test(reply.text)) return reply
  const text = reply.text
    .replace(/\bPink Elephants?\b/gi, 'Pink Elephant')
    .replace(/\bPink Elephant (Ltd\.?|Inc\.?|Corp\.?|Co\.?|Company|Corporation|Group)\b/gi, 'Pink Elephant Limited')
    .replace(/\bPink Elephant\b(?! Limited)(?! Talk)/g, 'Pink Elephant Limited')
  return { ...reply, text }
}

export interface LlamaDiagnostics {
  gpu: boolean
  reasonNoGPU: string
  backend: string
  deviceName: string
  devices: string[]
}

export async function diagnoseDevice(): Promise<LlamaDiagnostics> {
  try {
    const devs = await getBackendDevicesInfo()
    const gpu = devs.find(d => d.backend === 'OPENCL' || d.backend === 'VULKAN' || d.type === 'GPU')
    return {
      gpu: !!gpu,
      reasonNoGPU: gpu ? '' : 'No GPU backend available (OpenCL/Vulkan) on this device',
      backend: gpu?.backend ?? 'CPU',
      deviceName: gpu?.deviceName ?? '',
      devices: devs.map(d => `${d.backend}:${d.type}:${d.deviceName}`),
    }
  } catch (e) {
    return { gpu: false, reasonNoGPU: String(e), backend: 'CPU', deviceName: '', devices: [] }
  }
}

export interface ChatMessage {
  role: 'system' | 'user' | 'assistant'
  content: string
}

function formatChat(messages: ChatMessage[], imagePath?: string): string {
  let out = ''
  for (let i = 0; i < messages.length; i++) {
    const m = messages[i]
    let content = m.content
    if (imagePath && i === messages.length - 1) {
      content = `${MEDIA_MARKER}\n${content}`
    }
    out += `<|im_start|>${m.role}\n${content}<|im_end|>\n`
  }
  out += `<|im_start|>assistant\n`
  return out
}

export interface StreamedReply {
  thinking: string
  text: string
}

export function parseStream(raw: string): StreamedReply {
  const ts = raw.indexOf(THINK_START)
  const te = raw.indexOf(THINK_END)
  if (ts !== -1 && te !== -1 && te > ts) {
    return {
      thinking: raw.slice(ts + THINK_START.length, te),
      text: raw.slice(te + THINK_END.length).trim(),
    }
  }
  if (ts !== -1) {
    return { thinking: raw.slice(ts + THINK_START.length), text: '' }
  }
  if (te !== -1) {
    return {
      thinking: raw.slice(0, te).trim(),
      text: raw.slice(te + THINK_END.length).trim(),
    }
  }
  return { thinking: '', text: raw.trim() }
}

export class LlamaService {
  private ctx: LlamaContext | null = null
  private static _instance: LlamaService
  static get instance(): LlamaService {
    if (!this._instance) this._instance = new LlamaService()
    return this._instance
  }

  modelReady = false
  onDownloadProgress:
    | ((written: number, total: number | null, stage?: 'model' | 'vision' | 'loading') => void)
    | null = null

  private async fileComplete(path: string, expectedBytes: number): Promise<boolean> {
    try {
      const s = await RNFS.stat(path)
      return s.size === expectedBytes
    } catch {
      return false
    }
  }

  private async download(
    url: string,
    dest: string,
    expectedBytes: number,
    stage: 'model' | 'vision' = 'model',
  ): Promise<void> {
    if (await this.fileComplete(dest, expectedBytes)) return
    if (await RNFS.exists(dest)) await RNFS.unlink(dest)

    const CHUNK = 16 * 1024 * 1024
    const chunkDir = `${dest}.chunks`
    if (await RNFS.exists(chunkDir)) {
      try {
        await RNFS.unlink(chunkDir)
      } catch {
        // best-effort stale-chunk cleanup
      }
    }
    await RNFS.mkdir(chunkDir)

    const numChunks = Math.ceil(expectedBytes / CHUNK)

    for (let i = 0; i < numChunks; i++) {
      const start = i * CHUNK
      const end = Math.min(start + CHUNK - 1, expectedBytes - 1)
      const chunkLen = end - start + 1
      const chunkPath = `${chunkDir}/${i}.part`

      if (await this.fileComplete(chunkPath, chunkLen)) continue

      let ok = false
      let lastErr: Error | null = null
      for (let attempt = 0; attempt < 5; attempt++) {
        if (await RNFS.exists(chunkPath)) {
          try {
            await RNFS.unlink(chunkPath)
          } catch {
            // best-effort
          }
        }
        try {
          const job = RNFS.downloadFile({
            fromUrl: url,
            toFile: chunkPath,
            headers: { Range: `bytes=${start}-${end}` },
            connectionTimeout: 60000,
            readTimeout: 60000,
            begin: () => {},
            progress: p => this.onDownloadProgress?.(p.bytesWritten + start, expectedBytes, stage),
          })
          const res = await job.promise
          if (res.statusCode >= 400 && res.statusCode !== 206 && res.statusCode !== 200) {
            throw new Error(`chunk ${i} http ${res.statusCode}`)
          }
          const st = await RNFS.stat(chunkPath)
          if (st.size !== chunkLen) throw new Error(`chunk ${i} size ${st.size}/${chunkLen}`)
          ok = true
          this.onDownloadProgress?.(end + 1, expectedBytes, stage)
          break
        } catch (e) {
          lastErr = e as Error
          await new Promise(r => setTimeout(r, 1500))
        }
      }
      if (!ok) throw lastErr ?? new Error(`chunk ${i} failed`)
    }

    for (let i = 0; i < numChunks; i++) {
      const chunkPath = `${chunkDir}/${i}.part`
      const b64 = await RNFS.readFile(chunkPath, 'base64')
      await RNFS.appendFile(dest, b64, 'base64')
    }

    const st = await RNFS.stat(dest)
    if (st.size !== expectedBytes) {
      await RNFS.unlink(dest)
      throw new Error(`model download size mismatch: got ${st.size}, expected ${expectedBytes}`)
    }
    try {
      await RNFS.unlink(chunkDir)
    } catch {
      // best-effort
    }
  }

  async ensureFiles(): Promise<void> {
    await this.download(MODEL_URL, MODEL_PATH, MODEL_SIZE_BYTES, 'model')
    await this.download(MMPROJ_URL, MMPROJ_PATH, MMPROJ_SIZE_BYTES, 'vision')
    if (await RNFS.exists(THINKING_MODEL_PATH)) {
      try {
        await RNFS.unlink(THINKING_MODEL_PATH)
      } catch {
        // cleanup best-effort
      }
    }
    if (await RNFS.exists(THINKING_MMPROJ_PATH)) {
      try {
        await RNFS.unlink(THINKING_MMPROJ_PATH)
      } catch {
        // cleanup best-effort
      }
    }
    if (await RNFS.exists(OLD_MODEL_PATH)) {
      try {
        await RNFS.unlink(OLD_MODEL_PATH)
      } catch {
        // old model cleanup is best-effort
      }
    }
  }

  async load(): Promise<void> {
    if (this.ctx) return
    await this.ensureFiles()
    const diag = await diagnoseDevice()
    const layerCount = 28
    const opts = {
      model: MODEL_PATH,
      n_ctx: 2048,
      n_threads: 8,
      n_gpu_layers: diag.gpu ? layerCount : 0,
    }
    try {
      this.ctx = await initLlama(opts, pct =>
        this.onDownloadProgress?.(Math.round(pct), 100, 'loading'),
      )
    } catch (e) {
      const err = e as any
      const detail =
        `[initLlama failed] message=${err?.message} name=${err?.name}\n` +
        `stringify=${safeStringify(err)}\n` +
        `stack=${err?.stack}`
      console.warn(detail)
      throw new Error(detail)
    }
    try {
      await this.ctx.initMultimodal({
        path: MMPROJ_PATH,
        use_gpu: false,
        image_min_tokens: 1024,
        image_max_tokens: 1024,
      })
    } catch (e) {
      console.warn('initMultimodal failed', e)
      throw new Error(`[initMultimodal failed] ${String(e)}`)
    }
    this.modelReady = true
  }

  async complete(
    history: ChatMessage[],
    onToken?: (reply: StreamedReply) => void,
    imagePath?: string,
  ): Promise<StreamedReply> {
    if (!this.ctx) throw new Error('model not loaded')

    const streamToUI = (raw: string) => {
      if (!onToken) return
      onToken(parseStream(raw))
    }

    const last = history[history.length - 1]
    const userText = last && last.role === 'user' ? last.content : ''

    let injected = false
    const datedHistory = history.map(m => {
      if (!injected && m.role === 'system') {
        injected = true
        return {
          ...m,
          content: `${m.content}\n\nToday is ${web.todayStr()}. Use this for questions about the date, day of week, or current time.`,
        }
      }
      return m
    })

    const preWeb = web.shouldSearch(userText)
    const direct = await this.generate(
      formatChat(datedHistory, imagePath),
      preWeb ? undefined : streamToUI,
      imagePath,
    )
    const directParsed = parseStream(direct)
    const searchMatch = directParsed.text.match(/\[search:\s*([^\]]+)\]/i)
    const needWeb = searchMatch || preWeb
    if (!needWeb) return fixBrand(directParsed)

    const query = searchMatch ? searchMatch[1] : userText
    let context = 'No web results were found for the query below.\n'
    try {
      const { results, summary } = await web.webQuery(query)
      const condensed = web.condenseForModel(results, summary)
      if (condensed) context = condensed
    } catch (e) {
      context = `Web search failed: ${String(e)}\n`
    }

    onToken?.({ thinking: 'Searching the web for the latest information…', text: '' })

    const finalHistory: ChatMessage[] = [
      ...datedHistory,
      {
        role: 'user',
        content:
          'Use the web results below to answer my question. Give ONE concise final answer in my language and cite the source URL when available. Do not repeat yourself or restate any earlier content.\n\n' +
          context,
      },
    ]
    const final = await this.generate(
      formatChat(finalHistory, imagePath),
      onToken ? streamToUI : undefined,
      imagePath,
    )
    const finalParsed = parseStream(final)
    if (finalParsed.text) return fixBrand(finalParsed)
    return {
      thinking: '',
      text: 'I could not find a reliable answer to that. Try rephrasing, or ask about something else.',
    }
  }

  private async generate(
    prompt: string,
    onToken?: (raw: string) => void,
    imagePath?: string,
  ): Promise<string> {
    if (!this.ctx) throw new Error('model not loaded')
    let out = ''
    const completionParams: Record<string, unknown> = {
      prompt,
      n_predict: 1024,
      temperature: 0.4,
      top_k: 40,
      top_p: 0.9,
      min_p: 0.05,
      penalty_last_n: 512,
      penalty_repeat: 1.3,
      penalty_freq: 0.05,
      penalty_present: 0.05,
      dry_multiplier: 1.2,
      dry_base: 1.75,
      dry_allowed_length: 2,
    }
    if (imagePath) completionParams.media_paths = [imagePath]
    await this.ctx.completion(
      completionParams,
      token => {
        out += token.token
        onToken?.(out)
      },
    )
    return out
  }

  async release(): Promise<void> {
    if (this.ctx) {
      await this.ctx.release()
      this.ctx = null
      this.modelReady = false
    }
  }
}
