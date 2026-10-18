import {describe,expect,it} from 'vitest'
import {referenceAliases,searchReferences} from '../src/features/profile/reference-search'
const rows=[
  {name:'Фелляция',description:'Оральный секс.',category_uid:'sex',extra:{aliases:['Минет','Fellatio']}},
  {name:'Забота после практики',description:'Тёплый плед.',category_uid:'care',extra:{aliases:['Афтеркэр']}},
]
const categories=[{uid:'sex',name:'Секс и стимуляция'},{uid:'care',name:'Забота и восстановление'}]
describe('reference search',()=>{
  it('matches aliases, categories and descriptions with normalized case and ё',()=>{
    expect(searchReferences(rows,' МИНЕТ ',categories)).toEqual([rows[0]])
    expect(searchReferences(rows,'fellatio',categories)).toEqual([rows[0]])
    expect(searchReferences(rows,'теплый',categories)).toEqual([rows[1]])
    expect(searchReferences(rows,'восстановление',categories)).toEqual([rows[1]])
  })
  it('combines the category filter with all query words and restores cleared search',()=>{
    expect(searchReferences(rows,'минет',categories,'care')).toEqual([])
    expect(searchReferences(rows,'минет оральный',categories,'sex')).toEqual([rows[0]])
    expect(searchReferences(rows,'',categories,'care')).toEqual([rows[1]])
    expect(searchReferences(rows,'  ')).toBe(rows)
    expect(searchReferences(rows,'отсутствует')).toEqual([])
  })
  it('ignores malformed alias metadata',()=>{
    expect(referenceAliases({extra:{aliases:[null,3,'Нормальное имя']}})).toEqual(['Нормальное имя'])
    expect(referenceAliases({extra:{aliases:'строка'}})).toEqual([])
  })
})

describe('participant composition aliases',()=>{
  it('finds the same composition by alternate letter order',()=>{
    const compositions=[{name:'МЖМ',description:'Два мужчины и одна женщина.',category_uid:null,extra:{aliases:['ММЖ','ЖММ']}}]
    expect(searchReferences(compositions,'ммж')).toEqual(compositions)
    expect(searchReferences(compositions,'жмм')).toEqual(compositions)
    expect(searchReferences(compositions,'жмж')).toEqual([])
  })
})

describe('additional catalogue aliases',()=>{
  it('searches material and interaction-format aliases',()=>{
    const entries=[
      {name:'Искусственная кожа',description:'Материал.',category_uid:null,extra:{aliases:['Экокожа','Кожзам']}},
      {name:'Дистанционно',description:'На расстоянии.',category_uid:null,extra:{aliases:['Онлайн','Удалённо']}},
    ]
    expect(searchReferences(entries,'ЭКОКОЖА')).toEqual([entries[0]])
    expect(searchReferences(entries,'удаленно')).toEqual([entries[1]])
    expect(searchReferences(entries,'онлайн материал')).toEqual([])
  })
})


describe('health catalogue aliases',()=>{
  it('finds clinical terms by abbreviations and synonyms',()=>{
    const entries=[
      {name:'Посттравматическое стрессовое расстройство',description:'Термин.',category_uid:null,extra:{aliases:['ПТСР','PTSD']}},
      {name:'Белки натурального латекса',description:'Аллерген.',category_uid:null,extra:{aliases:['Натуральный латекс','Latex']}},
    ]
    expect(searchReferences(entries,'птср')).toEqual([entries[0]])
    expect(searchReferences(entries,'латекс')).toEqual([entries[1]])
    expect(searchReferences(entries,'латекс птср')).toEqual([])
  })
})

describe('existing catalogue groups',()=>{
  it('finds and filters fixation separately from accessories without extra entries',()=>{
    const rows=[
      {name:'Верёвка',description:'',category_uid:null,extra:{group:'Средства фиксации'}},
      {name:'Манжеты',description:'',category_uid:null,extra:{group:'Средства фиксации'}},
      {name:'Ошейник',description:'',category_uid:null,extra:{group:'Аксессуары динамики'}},
    ]
    expect(searchReferences(rows,'фиксации')).toEqual(rows.slice(0,2))
    expect(searchReferences(rows,'',[],'','Средства фиксации')).toEqual(rows.slice(0,2))
    expect(searchReferences(rows,'ошейник',[],'','Средства фиксации')).toEqual([])
    expect(searchReferences(rows,'',[],'','')).toBe(rows)
  })
  it('combines care category, group and query filters',()=>{
    const rows=[
      {name:'Массаж',description:'',category_uid:'care',extra:{group:'Телесная забота'}},
      {name:'Забота после практики',description:'',category_uid:'care',extra:{group:'После практики',aliases:['Афтеркэр']}},
    ]
    expect(searchReferences(rows,'афтеркэр',[],'care','После практики')).toEqual([rows[1]])
    expect(searchReferences(rows,'',[],'other','После практики')).toEqual([])
  })
})
