import type {components} from '../../shared/api'

export const rewardCategories = [
  {id: 'dates', ru: 'Свидания и близость', en: 'Dates and connection'},
  {id: 'food', ru: 'Еда и десерты', en: 'Food and desserts'},
  {id: 'drinks', ru: 'Чай и кофе', en: 'Tea and coffee'},
  {id: 'cinema', ru: 'Кино и сериалы', en: 'Films and series'},
  {id: 'music', ru: 'Музыка и танцы', en: 'Music and dancing'},
  {id: 'games', ru: 'Игры и книги', en: 'Games and books'},
  {id: 'outdoors', ru: 'Прогулки и природа', en: 'Walks and nature'},
  {id: 'travel', ru: 'Поездки и открытия', en: 'Trips and discoveries'},
  {id: 'creativity', ru: 'Творчество', en: 'Creativity'},
  {id: 'gifts', ru: 'Подарки и сюрпризы', en: 'Gifts and surprises'},
  {id: 'care', ru: 'Забота и отдых', en: 'Care and rest'},
  {id: 'touch', ru: 'Прикосновения и массаж', en: 'Touch and massage'},
  {id: 'together', ru: 'Время вместе', en: 'Time together'},
] as const satisfies ReadonlyArray<{id: components['schemas']['RewardContent']['category']; ru: string; en: string}>
