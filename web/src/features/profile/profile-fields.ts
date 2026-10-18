import type {components} from '../../shared/api'
export type Reference=components['schemas']['ReferenceView']
export type Catalogue=Record<string,Reference[]>
export const chapters=[['identity','О себе','About me'],['dynamics','Динамика','Dynamics'],['preferences','Предпочтения','Preferences'],['boundaries','Границы','Boundaries'],['health','Здоровье и забота','Health & care'],['visibility','Видимость','Visibility']] as const
export const attitudeOptions=[['not_specified','Не указано','Not specified'],['like','Нравится','Like'],['want_to_try','Хочу попробовать','Want to try'],['conditional','При условиях','Conditional'],['taboo','Табу','Taboo']] as const
export const referenceKinds=['biological-sex','genders','practices','practice-categories','participant-compositions','devices','body-parts','materials','role-scenarios','interaction-formats','venues','health-conditions','allergens','relationship-types']
export function referenceName(catalogue:Catalogue,uid:string){for(const rows of Object.values(catalogue)){const found=rows.find(r=>r.uid===uid);if(found)return found.name}return '—'}
