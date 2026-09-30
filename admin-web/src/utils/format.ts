const BEIJING_OFFSET_MS = 8 * 3600 * 1000

function pad(n: number): string {
  return n < 10 ? `0${n}` : `${n}`
}

interface BeijingParts {
  y: number
  mo: number
  d: number
  h: number
  mi: number
  s: number
}

/**
 * 宽松解析后端时间字符串（约定为 UTC ISO8601，如 2026-10-10T12:00:00Z）。
 * 兼容缺失时区后缀的「裸 UTC」写法：按 UTC 解析。
 */
function parseAsDate(value: string): Date | null {
  const hasTimezone = /(?:Z|[+-]\d{2}:?\d{2})$/i.test(value)
  let d = new Date(hasTimezone ? value : `${value}Z`)
  if (Number.isNaN(d.getTime()) && !hasTimezone) d = new Date(value)
  return Number.isNaN(d.getTime()) ? null : d
}

function toBeijingParts(date: Date): BeijingParts {
  const b = new Date(date.getTime() + BEIJING_OFFSET_MS)
  return {
    y: b.getUTCFullYear(),
    mo: b.getUTCMonth() + 1,
    d: b.getUTCDate(),
    h: b.getUTCHours(),
    mi: b.getUTCMinutes(),
    s: b.getUTCSeconds(),
  }
}

/** UTC ISO8601 → 北京时间 "YYYY-MM-DD HH:mm"（表格展示用）；空值返回 "—" */
export function formatBeijing(value?: string | null): string {
  if (!value) return '—'
  const date = parseAsDate(value)
  if (!date) return value
  const p = toBeijingParts(date)
  return `${p.y}-${pad(p.mo)}-${pad(p.d)} ${pad(p.h)}:${pad(p.mi)}`
}

/** UTC ISO8601 → 北京时间 "YYYY-MM-DDTHH:mm:ss"（el-date-picker 绑定值）；空值返回 "" */
export function utcToBeijingInput(value?: string | null): string {
  if (!value) return ''
  const date = parseAsDate(value)
  if (!date) return ''
  const p = toBeijingParts(date)
  return `${p.y}-${pad(p.mo)}-${pad(p.d)}T${pad(p.h)}:${pad(p.mi)}:${pad(p.s)}`
}

/**
 * 北京时间输入值（el-date-picker 的 "YYYY-MM-DDTHH:mm:ss"，兼容空格分隔）
 * → UTC ISO8601（提交后端）；空值返回 null。
 */
export function beijingInputToUtc(value?: string | null): string | null {
  if (!value) return null
  const m = /^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2})(?::(\d{2}))?/.exec(value)
  if (!m) return null
  const utc = new Date(
    Date.UTC(
      Number(m[1]),
      Number(m[2]) - 1,
      Number(m[3]),
      Number(m[4]) - 8,
      Number(m[5]),
      m[6] ? Number(m[6]) : 0,
    ),
  )
  return utc.toISOString()
}

/** 比率格式化：0.8 → "80%"（预习已读率等）；空值返回 "—" */
export function formatRate(rate?: number | null): string {
  if (rate === null || rate === undefined) return '—'
  return `${Math.round(rate * 100)}%`
}
