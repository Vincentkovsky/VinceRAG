import apiClient from './client'
import type { User, UserCreate, UserLogin, Token } from '@/types'

export const authApi = {
  /**
   * Register a new user
   */
  async register(userData: UserCreate): Promise<User> {
    const response = await apiClient.post<User>('/auth/register', userData)
    return response.data
  },

  /**
   * Login user with email and password
   */
  async login(userData: UserLogin): Promise<Token> {
    const response = await apiClient.post<Token>('/auth/login', userData)
    return response.data
  },

  /**
   * OAuth2 compatible token login (for form-based auth)
   */
  async loginForToken(username: string, password: string): Promise<Token> {
    const formData = new FormData()
    formData.append('username', username)
    formData.append('password', password)
    
    const response = await apiClient.post<Token>('/auth/token', formData, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    })
    return response.data
  },

  /**
   * Get current user info (requires authentication)
   */
  async getCurrentUser(): Promise<User> {
    const response = await apiClient.get<User>('/auth/me')
    return response.data
  },

  /**
   * Logout user (client-side token removal)
   */
  logout(): void {
    localStorage.removeItem('auth_token')
    localStorage.removeItem('user_data')
  },

  /**
   * Check if user is authenticated
   */
  isAuthenticated(): boolean {
    const token = localStorage.getItem('auth_token')
    return !!token
  },

  /**
   * Get stored token
   */
  getToken(): string | null {
    return localStorage.getItem('auth_token')
  },

  /**
   * Store token
   */
  setToken(token: string): void {
    localStorage.setItem('auth_token', token)
  },

  /**
   * Get stored user data
   */
  getStoredUser(): User | null {
    const userData = localStorage.getItem('user_data')
    return userData ? JSON.parse(userData) : null
  },

  /**
   * Store user data
   */
  setStoredUser(user: User): void {
    localStorage.setItem('user_data', JSON.stringify(user))
  }
}
