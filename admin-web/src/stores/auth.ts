import { defineStore } from 'pinia'
import {
  clearSession,
  getStaffName,
  getToken,
  setStaffName,
  setToken,
} from '../utils/auth'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: getToken() ?? '',
    staffName: getStaffName(),
  }),
  getters: {
    isLoggedIn: (state): boolean => Boolean(state.token),
  },
  actions: {
    setSession(token: string, staffName: string): void {
      this.token = token
      this.staffName = staffName
      setToken(token)
      setStaffName(staffName)
    },
    logout(): void {
      this.token = ''
      this.staffName = ''
      clearSession()
    },
  },
})
