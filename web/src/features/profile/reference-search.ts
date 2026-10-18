import type {components} from '../../shared/api'
type Entry = components['schemas']['ReferenceView']
function normalize(value: string): string {
  return value.normalize('NFKC').toLocaleLowerCase().replace(/ё/g, 'е').trim()
}
export function referenceAliases(entry: Pick<Entry, 'extra'>): string[] {
  const value = entry.extra?.aliases
  return Array.isArray(value) ? value.filter((alias): alias is string => typeof alias === 'string') : []
}
export function referenceGroup(entry: Pick<Entry, 'extra'>): string {
  const group = entry.extra?.group
  return typeof group === 'string' ? group.trim() : ''
}
export function searchReferences<T extends Pick<Entry, 'name' | 'description' | 'extra' | 'category_uid'>>(
  rows: T[], query: string, categories: Pick<Entry, 'uid' | 'name'>[] = [], categoryUid = '', group = '',
): T[] {
  const words = normalize(query).split(/\s+/).filter(Boolean)
  if (!words.length && !categoryUid && !group) return rows
  const categoryNames = new Map(categories.map(category => [category.uid, category.name]))
  return rows.filter(row => {
    if (categoryUid && row.category_uid !== categoryUid) return false
    if (group && referenceGroup(row) !== group) return false
    const text = normalize([row.name, row.description, referenceGroup(row), ...referenceAliases(row), categoryNames.get(row.category_uid ?? '') ?? ''].join(' '))
    return words.every(word => text.includes(word))
  })
}
