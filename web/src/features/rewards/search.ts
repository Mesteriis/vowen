type SearchableProduct = {title: string; description: string}
function normalize(value: string): string {
  return value.toLocaleLowerCase().replaceAll('ё', 'е').trim()
}
export function searchProducts<T extends SearchableProduct>(items: T[], query: string): T[] {
  const terms = normalize(query).split(/\s+/).filter(Boolean)
  if (!terms.length) return items
  return items.filter(item => {
    const text = normalize(`${item.title} ${item.description}`)
    return terms.every(term => text.includes(term))
  })
}
