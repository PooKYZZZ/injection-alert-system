import { describe, expect, it, vi } from 'vitest'

import { operatorResetAdminMfa } from './operator_reset_admin_mfa.mjs'

describe('operator ADMIN recovery script', () => {
  it('requires explicit break-glass confirmation and never returns secrets', async () => {
    const rpc = vi.fn().mockResolvedValue({ error: null })
    await expect(operatorResetAdminMfa({ rpc }, {
      id: '7a7bb9de-1dff-44b7-9a44-12efe8a6716f',
      reason: 'lost authenticator',
      confirmation: 'CYBERTRACE_BREAK_GLASS',
    })).resolves.toEqual({ status: 'reset' })
    expect(rpc).toHaveBeenCalledWith('operator_reset_admin_mfa', expect.objectContaining({
      p_confirmation: 'CYBERTRACE_BREAK_GLASS',
    }))
    await expect(operatorResetAdminMfa({ rpc }, {
      id: '7a7bb9de-1dff-44b7-9a44-12efe8a6716f',
      reason: 'lost authenticator',
      confirmation: 'no',
    })).rejects.toThrow(/confirmation/i)
  })
})
