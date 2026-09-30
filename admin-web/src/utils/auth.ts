const TOKEN_KEY = 'admin_token'
const STAFF_NAME_KEY = 'admin_staff_name'

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token)
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY)
}

export function getStaffName(): string {
  return localStorage.getItem(STAFF_NAME_KEY) ?? ''
}

export function setStaffName(name: string): void {
  localStorage.setItem(STAFF_NAME_KEY, name)
}

export function clearStaffName(): void {
  localStorage.removeItem(STAFF_NAME_KEY)
}

export function clearSession(): void {
  clearToken()
  clearStaffName()
}
