import type { components } from '../../shared/api'
type Tokens = components['schemas']['SessionTokens']

export class SessionClient {
  private tokens: Tokens | null = null
  private refreshing: Promise<void> | null = null
  constructor(private fetcher: typeof fetch = fetch.bind(globalThis)) {}

  async login(initData: string): Promise<void> {
    this.tokens = null
    this.tokens = await this.send<Tokens>('/auth/telegram/miniapp', 'POST', {init_data:initData}, false)
  }

  async get<T>(path: string): Promise<T> { return this.send<T>(path, 'GET') }
  async post<T>(path: string, body?: unknown): Promise<T> { return this.send<T>(path, 'POST', body) }
  async put<T>(path: string, body: unknown): Promise<T> { return this.send<T>(path, 'PUT', body) }
  async patch<T>(path: string, body: unknown): Promise<T> { return this.send<T>(path, 'PATCH', body) }
  async delete(path: string): Promise<void> { return this.send<void>(path, 'DELETE') }

  async logout(): Promise<void> {
    try { await this.post('/auth/logout') } finally { this.tokens = null }
  }

  private async refresh(): Promise<void> {
    if(!this.tokens) throw new Error('INVALID_AUTH')
    try {
      this.tokens = await this.send<Tokens>('/auth/refresh','POST',{refresh_token:this.tokens.refresh_token},false)
    } catch(error) { this.tokens=null; throw error }
  }

  private async send<T>(path: string, method: string, body?: unknown, retry = true): Promise<T> {
    const usedAccess = this.tokens?.access_token
    const headers: Record<string,string> = {'Content-Type':'application/json'}
    if(usedAccess) headers.Authorization='Bearer '+usedAccess
    const response = await this.fetcher('/api/v1'+path, {method,headers,body: body === undefined ? undefined : JSON.stringify(body),cache:'no-store',credentials:'omit',redirect:'error'})
    if(response.status===401 && retry && this.tokens) {
      if(this.tokens.access_token===usedAccess) {
        this.refreshing ??= this.refresh().finally(()=>{this.refreshing=null})
        await this.refreshing
      }
      return this.send<T>(path,method,body,false)
    }
    if(!response.ok) {
      const error = await response.json().catch(()=>null) as {error?:{code?:string}} | null
      throw new Error(error?.error?.code ?? `HTTP_${response.status}`)
    }
    return response.status===204 ? undefined as T : await response.json() as T
  }
}
