import {describe, expect, it} from 'vitest'
import {searchProducts} from '../src/features/rewards/search'
const products = [
  {title: 'Массаж рук', description: 'Тёплый вечер без спешки'},
  {title: 'Чухи-чухи', description: 'Почёсывание головы'},
  {title: 'Выбор фильма', description: 'Кино на двоих'},
]
describe('shop search', () => {
  it('matches title or description, ignores case and ё spelling', () => {
    expect(searchProducts(products, '  МАССАЖ   теплый ')).toEqual([products[0]])
    expect(searchProducts(products, 'почесывание')).toEqual([products[1]])
  })
  it('requires every word and returns no unrelated products', () => {
    expect(searchProducts(products, 'массаж кино')).toEqual([])
    expect(searchProducts(products, 'несуществующий')).toEqual([])
  })
  it('restores the original catalogue when cleared', () => {
    expect(searchProducts(products, '  ')).toBe(products)
  })
})
