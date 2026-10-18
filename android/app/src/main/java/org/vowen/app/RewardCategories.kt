package org.vowen.app

data class RewardCategoryLabel(val id:String,val en:String,val ru:String)
val rewardCategories=listOf(
 RewardCategoryLabel("dates","Dates and connection","Свидания и близость"),
 RewardCategoryLabel("food","Food and desserts","Еда и десерты"),
 RewardCategoryLabel("drinks","Tea and coffee","Чай и кофе"),
 RewardCategoryLabel("cinema","Films and series","Кино и сериалы"),
 RewardCategoryLabel("music","Music and dancing","Музыка и танцы"),
 RewardCategoryLabel("games","Games and books","Игры и книги"),
 RewardCategoryLabel("outdoors","Walks and nature","Прогулки и природа"),
 RewardCategoryLabel("travel","Trips and discoveries","Поездки и открытия"),
 RewardCategoryLabel("creativity","Creativity","Творчество"),
 RewardCategoryLabel("gifts","Gifts and surprises","Подарки и сюрпризы"),
 RewardCategoryLabel("care","Care and rest","Забота и отдых"),
 RewardCategoryLabel("touch","Touch and massage","Прикосновения и массаж"),
 RewardCategoryLabel("together","Time together","Время вместе")
)
