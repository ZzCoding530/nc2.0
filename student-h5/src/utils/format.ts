/**
 * 时间与文案格式化工具
 * 接口时间一律为 UTC ISO8601（2026-10-10T12:00:00Z），前端转北京时间展示
 */

/** UTC ISO8601 → 北京时间 "YYYY-MM-DD HH:mm" */
export function toBeijingTime(utc?: string | null): string {
  if (!utc) return ''
  const d = new Date(utc)
  if (isNaN(d.getTime())) return ''
  const bj = new Date(d.getTime() + 8 * 3600 * 1000)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${bj.getUTCFullYear()}-${pad(bj.getUTCMonth() + 1)}-${pad(bj.getUTCDate())} ${pad(bj.getUTCHours())}:${pad(bj.getUTCMinutes())}`
}

/** UTC ISO8601 → 北京时间 "MM-DD"（历史课展示用） */
export function toBeijingDate(utc?: string | null): string {
  const full = toBeijingTime(utc)
  return full ? full.slice(0, 10) : ''
}

/** UTC ISO8601 → 中文星期（按北京时间） */
export function weekdayCN(utc?: string | null): string {
  if (!utc) return ''
  const d = new Date(utc)
  if (isNaN(d.getTime())) return ''
  const bj = new Date(d.getTime() + 8 * 3600 * 1000)
  const names = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']
  return names[bj.getUTCDay()]
}

/** ISO → .ics 用 UTC 时间串 "YYYYMMDDTHHMMSSZ" */
export function toICSStamp(utc?: string | null): string {
  if (!utc) return ''
  const d = new Date(utc)
  if (isNaN(d.getTime())) return ''
  const pad = (n: number) => String(n).padStart(2, '0')
  return (
    `${d.getUTCFullYear()}${pad(d.getUTCMonth() + 1)}${pad(d.getUTCDate())}` +
    `T${pad(d.getUTCHours())}${pad(d.getUTCMinutes())}${pad(d.getUTCSeconds())}Z`
  )
}

/** 当前时间 → .ics DTSTAMP */
export function nowICSStamp(): string {
  return toICSStamp(new Date().toISOString())
}

/** ISO 时间 + 分钟 → 新 ISO（用于 DTEND = DTSTART + duration） */
export function plusMinutes(utc?: string | null, minutes = 0): string {
  if (!utc) return ''
  const d = new Date(utc)
  if (isNaN(d.getTime())) return ''
  return new Date(d.getTime() + minutes * 60000).toISOString()
}

/** 分钟 → "1h40m" 展示 */
export function durationCN(min?: number | null): string {
  if (!min || min <= 0) return ''
  const h = Math.floor(min / 60)
  const m = min % 60
  if (h > 0 && m > 0) return `${h}h${m}m`
  if (h > 0) return `${h}h`
  return `${m}min`
}

/** 距目标时间的相对文案（如"还有 2 天 3 小时"），目标可为空返回 '' */
export function countdownText(target?: string | null): string {
  if (!target) return ''
  const diff = new Date(target).getTime() - Date.now()
  if (isNaN(diff) || diff <= 0) return ''
  const mins = Math.floor(diff / 60000)
  const days = Math.floor(mins / (24 * 60))
  const hours = Math.floor((mins % (24 * 60)) / 60)
  if (days > 0) return `还有 ${days} 天${hours > 0 ? ` ${hours} 小时` : ''}`
  if (hours > 0) return `还有 ${hours} 小时${mins % 60 > 0 ? ` ${mins % 60} 分钟` : ''}`
  return `还有 ${Math.max(1, mins)} 分钟`
}

/** 是否在开课前 30 分钟内（呼吸高亮判定） */
export function isWithin30MinBefore(scheduledAt?: string | null): boolean {
  if (!scheduledAt) return false
  const start = new Date(scheduledAt).getTime()
  if (isNaN(start)) return false
  const diff = start - Date.now()
  return diff > 0 && diff <= 30 * 60000
}
