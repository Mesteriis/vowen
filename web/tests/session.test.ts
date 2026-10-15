import { expect, it, vi } from 'vitest'
import { SessionClient } from '../src/features/auth/session'

it('keeps bearer in memory and clears it on logout', async () => {
  const fetcher = vi.fn()
    .mockResolvedValueOnce(new Response(JSON.stringify({access_token:'synthetic-access',refresh_token:'synthetic-refresh'})))
    .mockResolvedValueOnce(new Response(JSON.stringify({id:'demo',display_name:'Demo'})))
    .mockResolvedValueOnce(new Response(null,{status:204}))
    .mockResolvedValueOnce(new Response('{}',{status:401}))
  const client = new SessionClient(fetcher)
  await client.login('synthetic-init-data')
  await client.get('/me')
  expect(fetcher.mock.calls[1][1].headers.Authorization).toBe('Bearer synthetic-access')
  await client.logout()
  await expect(client.get('/me')).rejects.toThrow()
  expect(fetcher.mock.calls[3][1].headers.Authorization).toBeUndefined()
})

it('serializes refresh for simultaneous expired requests', async () => {
  let refreshed = false
  let refreshCount = 0
  const fetcher = vi.fn(async (input: RequestInfo | URL) => {
    const url=String(input)
    if(url.endsWith('/miniapp')) return new Response(JSON.stringify({access_token:'old',refresh_token:'refresh'}))
    if(url.endsWith('/refresh')) {
      refreshCount++
      await new Promise(resolve => setTimeout(resolve, 5))
      refreshed=true
      return new Response(JSON.stringify({access_token:'new',refresh_token:'rotated'}))
    }
    return refreshed ? new Response('{}') : new Response('{}',{status:401})
  })
  const client = new SessionClient(fetcher)
  await client.login('synthetic')
  await Promise.all([client.get('/me'),client.get('/sessions')])
  expect(refreshCount).toBe(1)
})

it('binds native fetch to its global receiver', async () => {
  const original=globalThis.fetch
  globalThis.fetch=function(this: unknown) {
    if(this!==globalThis) throw new TypeError('Illegal invocation')
    return Promise.resolve(new Response('{}'))
  }
  try { await expect(new SessionClient().get('/instance')).resolves.toEqual({}) }
  finally {globalThis.fetch=original}
})

it('invalidates private UI once when refresh is revoked without a retry loop',async()=>{
 const lost=vi.fn()
 const fetcher=vi.fn(async(input:RequestInfo|URL,options?:RequestInit)=>{void options;return String(input).endsWith('/miniapp')?new Response(JSON.stringify({access_token:'old',refresh_token:'revoked'})):new Response('{}',{status:401})})
 const client=new SessionClient(fetcher,lost)
 await client.login('synthetic')
 await expect(client.get('/me')).rejects.toThrow()
 expect(lost).toHaveBeenCalledTimes(1)
 expect(fetcher).toHaveBeenCalledTimes(3)
 await expect(client.get('/me')).rejects.toThrow()
 expect((fetcher.mock.calls[3]![1]?.headers as Record<string,string>).Authorization).toBeUndefined()
 expect(lost).toHaveBeenCalledTimes(1)
})

it('does not let a stale failed refresh clear a newer login',async()=>{
 let finishRefresh:((response:Response)=>void)|undefined
 let logins=0
 const lost=vi.fn()
 const fetcher=vi.fn(async(input:RequestInfo|URL,options?:RequestInit)=>{
  const path=String(input)
  if(path.endsWith('/miniapp')){logins++;return new Response(JSON.stringify({access_token:logins===1?'old':'new',refresh_token:'refresh'}))}
  if(path.endsWith('/refresh'))return new Promise<Response>(resolve=>{finishRefresh=resolve})
  return new Response('{}',{status:(options?.headers as Record<string,string>).Authorization==='Bearer new'?200:401})
 })
 const client=new SessionClient(fetcher,lost)
 await client.login('first')
 const pending=client.get('/me')
 const rejected=expect(pending).rejects.toThrow()
 await vi.waitFor(()=>expect(finishRefresh).toBeDefined())
 await client.login('second')
 finishRefresh!(new Response('{}',{status:401}))
 await rejected
 await expect(client.get('/me')).resolves.toEqual({})
 expect(lost).not.toHaveBeenCalled()
})

it('debug login uses a normal in-memory session and propagates denial',async()=>{
 const fetcher=vi.fn()
  .mockResolvedValueOnce(new Response(JSON.stringify({access_token:'dev-access',refresh_token:'dev-refresh'})))
  .mockResolvedValueOnce(new Response('{}'))
  .mockResolvedValueOnce(new Response(JSON.stringify({error:{code:'NOT_FOUND'}}),{status:404}))
  .mockResolvedValueOnce(new Response('{}',{status:401}))
 const client=new SessionClient(fetcher)
 await client.loginDebug('synthetic-user-id')
 expect(fetcher.mock.calls[0][0]).toBe('/api/v1/auth/debug')
 expect(JSON.parse(fetcher.mock.calls[0][1].body)).toEqual({user_id:'synthetic-user-id'})
 await client.get('/me')
 expect(fetcher.mock.calls[1][1].headers.Authorization).toBe('Bearer dev-access')
 await expect(client.loginDebug('denied')).rejects.toThrow('NOT_FOUND')
 await expect(client.get('/me')).rejects.toThrow()
 expect(fetcher.mock.calls[3][1].headers.Authorization).toBeUndefined()
})
