const NEWS_RSS =
  'https://news.google.com/rss/search?q='
const WIKI_API = 'https://en.wikipedia.org/api/rest_v1/page/summary/'
const GEO_API =
  'https://geocoding-api.open-meteo.com/v1/search?count=1&language=en&format=json&name='
const METEO_API = 'https://api.open-meteo.com/v1/forecast?'

export interface WebResult {
  title: string
  url: string
  snippet: string
}

const WMO: Record<number, string> = {
  0: 'clear sky',
  1: 'mainly clear',
  2: 'partly cloudy',
  3: 'overcast',
  45: 'fog',
  48: 'depositing rime fog',
  51: 'light drizzle',
  53: 'drizzle',
  55: 'dense drizzle',
  61: 'light rain',
  63: 'rain',
  65: 'heavy rain',
  66: 'freezing rain',
  67: 'freezing rain',
  71: 'light snow',
  73: 'snow',
  75: 'heavy snow',
  77: 'snow grains',
  80: 'light rain showers',
  81: 'rain showers',
  82: 'violent rain showers',
  85: 'snow showers',
  86: 'heavy snow showers',
  95: 'thunderstorm',
  96: 'thunderstorm with light hail',
  99: 'thunderstorm with heavy hail',
}

async function getText(url: string, timeoutMs = 12000): Promise<string> {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), timeoutMs)
  try {
    const res = await fetch(url, {
      signal: controller.signal,
      headers: { 'User-Agent': 'PinkElephantTalk/1.0 (personal assistant)' },
    })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    return await res.text()
  } finally {
    clearTimeout(timer)
  }
}

function entities(s: string): string {
  return s
    .replace(/&amp;/g, '&')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/&nbsp;/g, ' ')
}

export function todayStr(): string {
  const now = new Date()
  const date = now.toLocaleDateString('en-GB', {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  })
  const time = now.toLocaleTimeString('en-GB', {
    hour: '2-digit',
    minute: '2-digit',
  })
  return `${date}, ${time}`
}

async function news(query: string): Promise<WebResult[]> {
  const lang = 'en'
  const q = encodeURIComponent(query.trim())
  const xml = await getText(
    `${NEWS_RSS}${q}&hl=${lang}-US&gl=US&ceid=US:${lang}`,
  )
  const items = [...xml.matchAll(/<item>([\s\S]*?)<\/item>/g)]
  const out: WebResult[] = []
  for (const [, item] of items) {
    const title = entities((item.match(/<title>(?:<!\[CDATA\[)?([\s\S]*?)(?:\]\]>)?<\/title>/) || [])[1] ?? '')
    const link = (item.match(/<link>(?:<!\[CDATA\[)?([\s\S]*?)(?:\]\]>)?<\/link>/) || [])[1] ?? ''
    if (!title || !link) continue
    out.push({ title: title.trim(), url: link, snippet: title.trim() })
    if (out.length >= 5) break
  }
  return out
}

async function fetchWiki(query: string): Promise<WebResult | null> {
  const title = encodeURIComponent(query.trim().replace(/^the\s+/i, ''))
  let json: unknown
  try {
    const text = await getText(`${WIKI_API}${title}`)
    json = JSON.parse(text)
  } catch {
    return null
  }
  const w = json as { title?: string; extract?: string; content_urls?: { desktop?: { page?: string }; titles?: { page?: string } } }
  if (!w.extract) return null
  return {
    title: w.title ?? query,
    url: w.content_urls?.titles?.page ?? '',
    snippet: w.extract,
  }
}

const PLACES: Array<[RegExp, string]> = [
  [/\bhong kong\b|香港/i, 'Hong Kong'],
  [/\btaipei\b|台北|臺北/i, 'Taipei'],
  [/\btokyo\b|東京/i, 'Tokyo'],
  [/\blondon\b|倫敦/i, 'London'],
  [/\bparis\b|巴黎/i, 'Paris'],
  [/\bnew york\b|紐約/i, 'New York'],
  [/\bsydney\b|雪梨|悉尼/i, 'Sydney'],
  [/\bsingapore\b|新加坡/i, 'Singapore'],
  [/\bseoul\b|首爾|首尔/i, 'Seoul'],
  [/\bbeijing\b|北京/i, 'Beijing'],
  [/\bshanghai\b|上海/i, 'Shanghai'],
  [/\bbangkok\b|曼谷/i, 'Bangkok'],
  [/\bdubai\b|杜拜|迪拜/i, 'Dubai'],
  [/\bberlin\b|柏林/i, 'Berlin'],
  [/\bmadrid\b|馬德里|马德里/i, 'Madrid'],
  [/\brome\b|羅馬|罗马/i, 'Rome'],
  [/\boslo\b|奧斯陸|奥斯陆/i, 'Oslo'],
  [/\bamsterdam\b|阿姆斯特丹/i, 'Amsterdam'],
  [/\bbrussels\b|布魯塞爾|布鲁塞尔/i, 'Brussels'],
  [/\btoronto\b|多倫多|多伦多/i, 'Toronto'],
  [/\bsan francisco\b|舊金山|旧金山/i, 'San Francisco'],
  [/\blos angeles\b|洛杉磯|洛杉矶/i, 'Los Angeles'],
  [/\bchicago\b|芝加哥/i, 'Chicago'],
  [/\bmoscow\b|莫斯科/i, 'Moscow'],
  [/\bdelhi\b|德里/i, 'Delhi'],
  [/\bmumbai\b|孟買|孟买/i, 'Mumbai'],
  [/\bjakarta\b|雅加達|雅加达/i, 'Jakarta'],
  [/\bmanila\b|馬尼拉|马尼拉/i, 'Manila'],
  [/\bho chi minh\b|胡志明/i, 'Ho Chi Minh'],
  [/\bkuala lumpur\b|吉隆坡/i, 'Kuala Lumpur'],
]

function extractPlace(query: string): string | null {
  const lower = query.toLowerCase()
  for (const [re, name] of PLACES) {
    if (re.test(lower)) return name
  }
  let p = lower
    .replace(/'s/g, ' ')
    .replace(/[\u4e00-\u9fff]+/g, ' ')
    .replace(
      /\b(what|which|who|where|when|how|is|are|was|were|the|a|an|of|in|on|at|for|to|and|or|weather|forecast|temperature|humidity|like|today|tonight|tomorrow|now|current|hourly|daily|this|week|weekend|will|be|it|please|tell|me|get|look|up|right|news|latest)\b/g,
      ' ',
    )
    .replace(/[^a-z\s-]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
  return p.length >= 2 ? p : null
}

async function weather(query: string): Promise<WebResult | null> {
  if (
    !/\b(weather|forecast|temperature|degrees?|°)\b/.test(query.toLowerCase()) &&
    !/(天氣|天气|温度|溫度|气温|氣溫|幾度|多少度|降雨)/.test(query)
  ) {
    return null
  }
  const place = extractPlace(query)
  if (!place) return null
  let geo: any
  try {
    const text = await getText(`${GEO_API}${encodeURIComponent(place)}`)
    geo = JSON.parse(text)
  } catch {
    return null
  }
  const g = geo?.results?.[0]
  if (!g) return null
  const tz = g.timezone ?? 'UTC'
  let f: any
  try {
    const text = await getText(
      `${METEO_API}latitude=${g.latitude}&longitude=${g.longitude}&current_weather=true&daily=temperature_2m_max,temperature_2m_min&timezone=${encodeURIComponent(tz)}&forecast_days=1`,
    )
    f = JSON.parse(text)
  } catch {
    return null
  }
  const cw = f?.current_weather
  if (!cw) return null
  const code = WMO[cw.weathercode] ?? `code ${cw.weathercode}`
  let s = `Current weather in ${g.name}${g.country_code ? ` (${g.country_code})` : ''}: ${cw.temperature}°C, ${code}, wind ${cw.windspeed} km/h.`
  const mn = f?.daily?.temperature_2m_min?.[0]
  const mx = f?.daily?.temperature_2m_max?.[0]
  if (mn != null && mx != null) s += ` Today ${mn}°C to ${mx}°C.`
  s += ` Source: Open-Meteo, ${cw.time}.`
  return {
    title: `${g.name} weather`,
    url: `https://open-meteo.com/en/weather`,
    snippet: s,
  }
}

export function shouldSearch(text: string): boolean {
  if (/(天氣|天气|下雨|降雨|濕度|湿度|溫度|温度|氣溫|气温|颱風|台风|新聞|新闻|氣象|气象|幾度|多少度)/.test(text)) return true
  const p = text.toLowerCase()
  if (/\b(weather|forecast|temperature|humidity|rain|sunny|cloudy|typhoon|degree|degrees)\b/.test(p)) return true
  if (/\b(news|headlines|breaking)\b/.test(p)) return true
  if (/\b(price|prices|stock|stocks|exchange rate|share price|gold price|oil price)\b/.test(p)) return true
  if (/\b(score|scores|result|results)\b/.test(p)) return true
  return false
}

export async function webQuery(
  query: string,
): Promise<{ results: WebResult[]; summary?: string }> {
  const results: WebResult[] = []
  let summary = `Today is ${todayStr()}.`

  const wx = await weather(query)
  if (wx) {
    summary = `${wx.snippet} ${summary}`
    results.push(wx)
  }

  const wiki = await fetchWiki(query)
  if (wiki) {
    results.push(wiki)
  }

  if (!wx) {
    try {
      const items = await news(query)
      for (const n of items) {
        if (!results.some(r => r.url === n.url)) results.push(n)
      }
    } catch {
      // news fetch failure is non-fatal if other sources provided context
    }
  }

  return { results: results.slice(0, 6), summary }
}

export function condenseForModel(results: WebResult[], summary?: string): string {
  if (!results.length && !summary) return ''
  const lines = ['Web search results (use this to answer):']
  if (summary) lines.push(summary)
  results.forEach(r => {
    lines.push(`- ${r.title} (${r.url}): ${r.snippet}`)
  })
  return lines.join('\n')
}
