import { describe, expect, it } from 'vitest'
import { statsOptions } from './queries'

describe('statsOptions', () => {
  it('does not reuse placeholder stats across query key changes', () => {
    const options = statsOptions('24h', 'Asia/Manila')

    expect(options.placeholderData).toBeUndefined()
  })
})
