import type {Section} from '../workspace/context'
export type ProfileSection='profile'|'notifications'|'sessions'
export function accountDestination(section:Section):{section:Section;personal:ProfileSection}|null {
 if(section==='profile'||section==='notifications'||section==='sessions')return {section:'profile',personal:section}
 return null
}
export function mainNavigation(sections:Section[]):Section[]{return sections.filter(id=>!['notifications','sessions','profile','settings'].includes(id))}
