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
