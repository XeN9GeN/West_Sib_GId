# Аудит OSM-тегов и шага точек ЖД

Дата аудита: 2026-11-23T10:45:52.763918+00:00

Уточнения по запросу владельца: 2026-11-23, 21:40 (UTC+07:00).

Все запросы к БД выполняются в транзакции `READ ONLY`.

## Объекты и теги

### `osm_pois`

Всего объектов: **22223**.

| Ключ | Значение | Число объектов |
| --- | --- | --- |
| amenity | place_of_worship | 3186 |
| amenity | arts_centre | 340 |
| amenity | theatre | 331 |
| amenity | bench | 8 |
| amenity | community_centre | 7 |
| amenity | grave_yard | 7 |
| amenity | fountain | 6 |
| amenity | monastery | 5 |
| amenity | clock | 4 |
| amenity | townhall | 4 |
| amenity | cafe | 3 |
| amenity | shelter | 3 |
| amenity | library | 2 |
| amenity | restaurant | 2 |
| amenity | school | 2 |
| amenity | bar | 1 |
| amenity | car_rental | 1 |
| amenity | church | 1 |
| amenity | cinema | 1 |
| amenity | clinic | 1 |
| amenity | crypt | 1 |
| amenity | fire_station | 1 |
| amenity | hospital | 1 |
| amenity | marketplace | 1 |
| amenity | planetarium | 1 |
| amenity | prison | 1 |
| amenity | public_building | 1 |
| amenity | university | 1 |
| amenity | veterinary | 1 |
| attraction | animal | 102 |
| attraction | big_wheel | 7 |
| attraction | yes | 6 |
| attraction | carousel | 5 |
| attraction | natural | 5 |
| attraction | amusement_ride | 3 |
| attraction | bumper_car | 3 |
| attraction | pirate_ship | 3 |
| attraction | train | 3 |
| attraction | river_rafting | 2 |
| attraction | roller_coaster | 2 |
| attraction | swing_carousel | 2 |
| attraction | tunnel portal | 2 |
| attraction | artwork | 1 |
| attraction | boat_ride | 1 |
| attraction | canon | 1 |
| attraction | historic | 1 |
| attraction | jet | 1 |
| attraction | miniature_replica | 1 |
| attraction | sinkhole | 1 |
| attraction | spring | 1 |
| attraction | summer_toboggan | 1 |
| building | yes | 1941 |
| building | church | 1372 |
| building | chapel | 205 |
| building | temple | 136 |
| building | mosque | 114 |
| building | public | 82 |
| building | commercial | 60 |
| building | civic | 58 |
| building | cathedral | 44 |
| building | house | 40 |
| building | apartments | 30 |
| building | ruins | 28 |
| building | detached | 12 |
| building | construction | 11 |
| building | museum | 10 |
| building | collapsed | 9 |
| building | industrial | 9 |
| building | university | 8 |
| building | school | 7 |
| building | synagogue | 7 |
| building | retail | 6 |
| building | tower | 6 |
| building | warehouse | 6 |
| building | no | 5 |
| building | government | 4 |
| building | hospital | 4 |
| building | presbytery | 4 |
| building | mansion | 3 |
| building | office | 3 |
| building | residential | 3 |
| building | service | 3 |
| building | theatre | 3 |
| building | castle_tower | 2 |
| building | college | 2 |
| building | font | 2 |
| building | hotel | 2 |
| building | kindergarten | 2 |
| building | roof | 2 |
| building | ship | 2 |
| building | triumphal_arch | 2 |
| building | water_tower | 2 |
| building | abandoned | 1 |
| building | ammunition | 1 |
| building | cinema | 1 |
| building | circus | 1 |
| building | garage | 1 |
| building | guardhouse | 1 |
| building | houseboat | 1 |
| building | hut | 1 |
| building | kingdom_hall | 1 |
| building | silo | 1 |
| building | townhall | 1 |
| building | yes;public | 1 |
| denomination | russian_orthodox | 1099 |
| denomination | orthodox | 600 |
| denomination | sunni | 63 |
| denomination | baptist | 44 |
| denomination | catholic | 41 |
| denomination | old_believers | 22 |
| denomination | gelug | 20 |
| denomination | pentecostal | 15 |
| denomination | roman_catholic | 15 |
| denomination | lutheran | 14 |
| denomination | evangelical | 9 |
| denomination | karma_kagyu | 9 |
| denomination | protestant | 9 |
| denomination | seventh_day_adventist | 7 |
| denomination | armenian_apostolic | 6 |
| denomination | shia | 6 |
| denomination | jehovahs_witness | 5 |
| denomination | mormon | 4 |
| denomination | romanian_orthodox | 3 |
| denomination | nondenominational | 2 |
| denomination | slavic | 2 |
| denomination | ananda_marga | 1 |
| denomination | charismatic | 1 |
| denomination | conservative | 1 |
| denomination | evangelical_lutheran | 1 |
| denomination | greek_orthodox | 1 |
| denomination | methodist | 1 |
| denomination | presbyterian | 1 |
| denomination | reformed | 1 |
| denomination | russian_ortodox | 1 |
| denomination | vaishnavism | 1 |
| denomination | vajrayana | 1 |
| denomination | zen | 1 |
| heritage | 4 | 27 |
| heritage | 2 | 12 |
| heritage | 1 | 4 |
| heritage | yes | 2 |
| heritage | 98 | 1 |
| heritage:loc_name | Пентагон | 1 |
| heritage:name | Андреевская церковь | 1 |
| heritage:name | «Белый» дом | 1 |
| heritage:name | Главный корпус технологического института, в котором в 1904-1905 гг. на вечерних общеобразовательных курсах учился Киров Сергей Миронович | 1 |
| heritage:name | Дом В. И. Иванова | 1 |
| heritage:name | Дом, в котором в 1948 г. родился и жил В.И. Суриков | 1 |
| heritage:name | Дом горсовета № 5 ("Дом-коммуна") | 1 |
| heritage:name | Дом-музей Ф. М. Решетникова | 1 |
| heritage:name | Дом П. М. Флоринского | 1 |
| heritage:name | Дом Промышленности | 1 |
| heritage:name | Доходный дом Хребтовой | 1 |
| heritage:name | Здание бывшей типографии "Гранит" | 1 |
| heritage:name | Здание гостиницы "Даурия" | 1 |
| heritage:name | Здание Свердловского государственного академического театра драмы | 1 |
| heritage:name | Институт народного хозяйства | 1 |
| heritage:name | Первый дом гор. Магнитогорска | 1 |
| heritage:name | Смешанный 2-этажный дом, н. XX в. | 1 |
| heritage:name:ru | Усадьба Э. Ф. Филитц | 1 |
| heritage:note | Воссоздан в 1986 | 1 |
| heritage:note | "Русский" стиль, резьба | 1 |
| heritage:official_name | Водонапорная башня УЗТМ | 1 |
| heritage:official_name | Дом жилой В. И. Иванова | 1 |
| heritage:official_name | Дом жилой П. М. Флоринского | 1 |
| heritage:official_name | Здание Духовного училища. Учебный корпус Свердловского института народного хозяйства | 1 |
| heritage:official_name | Литературно-мемориальный дом-музей Ф. М. Решетникова | 1 |
| heritage:operator | whc | 5 |
| heritage:operator | Ministry of Culture of the Russian Federation | 2 |
| heritage:ref | 7400044000 | 1 |
| heritage:ref | 741410049220005 | 1 |
| heritage:ref | 741410067260005 | 1 |
| heritage:ref | 741410075740005 | 1 |
| heritage:ref | 741510267440005 | 1 |
| heritage:ref | 741610657110005 | 1 |
| heritage:ref | 7430355000 | 1 |
| heritage:website | https://pik174.ru/catalog/pamyatniki-arkhitektury/vodonapornaya-bashnya-gorodskogo-vodoprovoda-g-chelyabinsk-ul-vorovskogo-11a/ | 2 |
| heritage:website | http://kulturnoe-nasledie.ru/monuments.php?id=6610038000 | 1 |
| heritage:website | http://mugiso.midural.ru/organization/?ID=2538 | 1 |
| heritage:website | http://mugiso.midural.ru/organization/?ID=2601&SECTION_ID=260 | 1 |
| heritage:website | http://mugiso.midural.ru/organization/?ID=2603 | 1 |
| heritage:website | http://mugiso.midural.ru/organization/?ID=2606&SECTION_ID=260 | 1 |
| heritage:website | http://mugiso.midural.ru/organization/?ID=2802&SECTION_ID=260 | 1 |
| heritage:website | http://mugiso.midural.ru/region/okn/estateekt.php?ELEMENT_ID=611 | 1 |
| heritage:website | https://opendata.mkrf.ru/opendata/7705851331-egrkn/58/415159 | 1 |
| heritage:website | https://opendata.mkrf.ru/opendata/7705851331-egrkn/68/147693 | 1 |
| heritage:website | https://opendata.mkrf.ru/opendata/7705851331-egrkn/68/312251 | 1 |
| heritage:website | https://pik174.ru/catalog/pamyatniki-arkhitektury/aleksandro-nevskaya-tserkov-park-aloe-pole-pr-lenina-g-chelyabinsk/ | 1 |
| heritage:website | https://pik174.ru/catalog/pamyatniki-arkhitektury/naslednitskaya-krepost-bredinskiy-rayon-p-naslednitskiy-ul-titova-17/ | 1 |
| heritage:website | https://pik174.ru/catalog/pamyatniki-arkhitektury/nikolaevskaya-krepost-varnenskiy-rayon-s-nikolaevka-ul-tsentralnaya-28/ | 1 |
| heritage:website | https://pik174.ru/catalog/pamyatniki-arkhitektury/troitskaya-tserkov-g-chelyabinsk-ul-kirova-60a-/ | 1 |
| historic | memorial | 8071 |
| historic | tomb | 1472 |
| historic | boundary_stone | 1403 |
| historic | ruins | 643 |
| historic | archaeological_site | 591 |
| historic | yes | 419 |
| historic | building | 294 |
| historic | mound | 283 |
| historic | wayside_cross | 183 |
| historic | aircraft | 127 |
| historic | heritage | 83 |
| historic | tank | 81 |
| historic | monument | 58 |
| historic | wayside_shrine | 57 |
| historic | locomotive | 52 |
| historic | technical_monument | 47 |
| historic | vehicle | 38 |
| historic | church | 35 |
| historic | manor | 34 |
| historic | bomb_crater | 31 |
| historic | cannon | 29 |
| historic | castle | 26 |
| historic | quarry | 23 |
| historic | wreck | 23 |
| historic | citywalls | 17 |
| historic | railway | 16 |
| historic | city_gate | 10 |
| historic | epigraph | 10 |
| historic | mine | 8 |
| historic | stone | 8 |
| historic | weapon | 5 |
| historic | house | 4 |
| historic | mine_shaft | 4 |
| historic | bridge | 3 |
| historic | fort | 3 |
| historic | memorial_tablet | 3 |
| historic | monastery | 3 |
| historic | dam | 2 |
| historic | factory | 2 |
| historic | industrial | 2 |
| historic | ship | 2 |
| historic | train_station | 2 |
| historic | adit | 1 |
| historic | aircraft_wreck | 1 |
| historic | Armored personnel carrieryes | 1 |
| historic | bank | 1 |
| historic | bunker | 1 |
| historic | car | 1 |
| historic | charcoal_pile | 1 |
| historic | eternal_flame | 1 |
| historic | helicopter | 1 |
| historic | heritage_building | 1 |
| historic | historic | 1 |
| historic | hospital | 1 |
| historic | irrigation_system | 1 |
| historic | locomotve | 1 |
| historic | meteorite_explosion | 1 |
| historic | milestone | 1 |
| historic | military | 1 |
| historic | no | 1 |
| historic | old_street | 1 |
| historic | plaque | 1 |
| historic | prison | 1 |
| historic | rail_car | 1 |
| historic | railway_station | 1 |
| historic | razed:watermill | 1 |
| historic | retail | 1 |
| historic | school | 1 |
| historic | steam_locomotive | 1 |
| historic | time_capsule | 1 |
| historic | tower | 1 |
| historic | tractor | 1 |
| historic | warehouse | 1 |
| historic | water_tower | 1 |
| memorial | war_memorial | 921 |
| memorial | statue | 647 |
| memorial | plaque | 637 |
| memorial | stele | 577 |
| memorial | bust | 363 |
| memorial | stone | 245 |
| memorial | obelisk | 185 |
| memorial | sculpture | 171 |
| memorial | memorial | 139 |
| memorial | vehicle | 97 |
| memorial | tank | 33 |
| memorial | yes | 30 |
| memorial | cross | 25 |
| memorial | eternal_flame | 21 |
| memorial | blue_plaque | 15 |
| memorial | aircraft | 14 |
| memorial | relief | 13 |
| memorial | person | 6 |
| memorial | cannon | 5 |
| memorial | monument | 5 |
| memorial | building | 4 |
| memorial | anchor | 3 |
| memorial | column | 3 |
| memorial | locomotive | 3 |
| memorial | war_grave | 3 |
| memorial | трактор | 3 |
| memorial | cenotaph | 2 |
| memorial | pillar | 2 |
| memorial | паровоз | 2 |
| memorial | barelief | 1 |
| memorial | bas-relief | 1 |
| memorial | board | 1 |
| memorial | bowl | 1 |
| memorial | ghost_bike | 1 |
| memorial | grave | 1 |
| memorial | hazard_memorial | 1 |
| memorial | headstone | 1 |
| memorial | helicopter | 1 |
| memorial | installation | 1 |
| memorial | mausoleum | 1 |
| memorial | military_vehicle | 1 |
| memorial | mound | 1 |
| memorial | nature | 1 |
| memorial | ship | 1 |
| memorial | statue/bust/… | 1 |
| memorial | steam_locomotive | 1 |
| memorial | stela | 1 |
| memorial | tree | 1 |
| memorial | war | 1 |
| memorial | Защитникам Отечества | 1 |
| memorial | камень= | 1 |
| memorial | пожарная_машина_зил-131 | 1 |
| memorial | рабочее_колесо_гидротурбины_красноярской_гэс | 1 |
| memorial | самолёт | 1 |
| memorial | скульптура | 1 |
| memorial | танк | 1 |
| museum | history | 52 |
| museum | local | 11 |
| museum | art | 6 |
| museum | nature | 5 |
| museum | person | 5 |
| museum | military | 4 |
| museum | archaeological | 3 |
| museum | living_history | 3 |
| museum | railway | 3 |
| museum | technology | 3 |
| museum | aerospace | 1 |
| museum | aviation | 1 |
| museum | history, religion | 1 |
| museum | history;transport;railway | 1 |
| museum | nature;history;archaeological | 1 |
| museum | nature;science | 1 |
| museum | open_air | 1 |
| museum | transport | 1 |
| museum | transport;railway | 1 |
| railway | rail | 234 |
| railway | razed | 13 |
| railway | abandoned | 4 |
| railway | disused | 2 |
| railway | dismantled | 1 |
| railway | yard | 1 |
| ref:egrokn | 25 | 1 |
| ref:egrokn | 551510290360006 | 1 |
| ref:egrokn | 551711127260005 | 1 |
| ref:egrokn | 721410119250005 | 1 |
| ref:egrokn | 721610736910006 | 1 |
| ref:egrokn | 861410070420005 | 1 |
| ref:mkrf_museums | 18176 | 1 |
| ref:mkrf_museums | 7481 | 1 |
| ref:mkrf_museums | 8807 | 1 |
| ref:mkrf_theaters | 12431 | 1 |
| ref:mkrf_theaters | 12433 | 1 |
| ref:mkrf_theaters | 12497 | 1 |
| ref:mkrf_theaters | 12499 | 1 |
| ref:mkrf_theaters | 12669 | 1 |
| ref:mkrf_theaters | 12746 | 1 |
| ref:mkrf_theaters | 12843 | 1 |
| ref:mkrf_theaters | 12866 | 1 |
| ref:mkrf_theaters | 12980 | 1 |
| ref:mkrf_theaters | 12983 | 1 |
| ref:mkrf_theaters | 12984 | 1 |
| ref:mkrf_theaters | 13116 | 1 |
| ref:mkrf_theaters | 13117 | 1 |
| ref:mkrf_theaters | 13509 | 1 |
| ref:mkrf_theaters | 13511 | 1 |
| ref:mkrf_theaters | 13513 | 1 |
| ref:mkrf_theaters | 13514 | 1 |
| ref:mkrf_theaters | 13515 | 1 |
| ref:mkrf_theaters | 13516 | 1 |
| ref:mkrf_theaters | 13517 | 1 |
| ref:mkrf_theaters | 13518 | 1 |
| ref:mkrf_theaters | 13556 | 1 |
| ref:mkrf_theaters | 13558 | 1 |
| ref:mkrf_theaters | 13563 | 1 |
| ref:mkrf_theaters | 13565 | 1 |
| ref:mkrf_theaters | 13567 | 1 |
| ref:mkrf_theaters | 13569 | 1 |
| ref:mkrf_theaters | 13570 | 1 |
| ref:mkrf_theaters | 13603 | 1 |
| ref:mkrf_theaters | 13619 | 1 |
| ref:mkrf_theaters | 13621 | 1 |
| ref:mkrf_theaters | 13622 | 1 |
| ref:mkrf_theaters | 13626 | 1 |
| ref:mkrf_theaters | 13627 | 1 |
| ref:mkrf_theaters | 13629 | 1 |
| ref:mkrf_theaters | 13630 | 1 |
| ref:mkrf_theaters | 13631 | 1 |
| ref:mkrf_theaters | 13632 | 1 |
| ref:mkrf_theaters | 13640 | 1 |
| ref:mkrf_theaters | 13641 | 1 |
| ref:mkrf_theaters | 13646 | 1 |
| ref:mkrf_theaters | 13648 | 1 |
| ref:mkrf_theaters | 13657 | 1 |
| ref:mkrf_theaters | 13658 | 1 |
| ref:mkrf_theaters | 13660 | 1 |
| ref:mkrf_theaters | 13669 | 1 |
| ref:mkrf_theaters | 13674 | 1 |
| ref:mkrf_theaters | 14353 | 1 |
| ref:mkrf_theaters | 14354 | 1 |
| ref:mkrf_theaters | 14360 | 1 |
| ref:mkrf_theaters | 14361 | 1 |
| ref:mkrf_theaters | 14376 | 1 |
| ref:mkrf_theaters | 14377 | 1 |
| ref:mkrf_theaters | 14378 | 1 |
| ref:mkrf_theaters | 14662 | 1 |
| ref:mkrf_theaters | 15215 | 1 |
| ref:mkrf_theaters | 15219 | 1 |
| ref:mkrf_theaters | 15224 | 1 |
| ref:mkrf_theaters | 15247 | 1 |
| ref:mkrf_theaters | 15892 | 1 |
| ref:mkrf_theaters | 15990 | 1 |
| ref:mkrf_theaters | 16328 | 1 |
| ref:mkrf_theaters | 16448 | 1 |
| ref:mkrf_theaters | 16516 | 1 |
| ref:mkrf_theaters | 16984 | 1 |
| ref:mkrf_theaters | 16985 | 1 |
| ref:mkrf_theaters | 17011 | 1 |
| ref:mkrf_theaters | 17013 | 1 |
| ref:mkrf_theaters | 17040 | 1 |
| ref:mkrf_theaters | 17050 | 1 |
| ref:mkrf_theaters | 17086 | 1 |
| ref:mkrf_theaters | 17104 | 1 |
| ref:mkrf_theaters | 17592 | 1 |
| ref:mkrf_theaters | 17724 | 1 |
| ref:mkrf_theaters | 17851 | 1 |
| ref:mkrf_theaters | 17903 | 1 |
| ref:mkrf_theaters | 17911 | 1 |
| ref:mkrf_theaters | 18260 | 1 |
| ref:mkrf_theaters | 18293 | 1 |
| ref:mkrf_theaters | 18343 | 1 |
| ref:mkrf_theaters | 18670 | 1 |
| ref:mkrf_theaters | 19786 | 1 |
| ref:mkrf_theaters | 20454 | 1 |
| ref:mkrf_theaters | 20464 | 1 |
| ref:mkrf_theaters | 20815 | 1 |
| ref:mkrf_theaters | 20906 | 1 |
| ref:mkrf_theaters | 21014 | 1 |
| ref:mkrf_theaters | 21063 | 1 |
| ref:mkrf_theaters | 21482 | 1 |
| ref:mkrf_theaters | 24571 | 1 |
| ref:mkrf_theaters | 24856 | 1 |
| ref:mkrf_theaters | 28729 | 1 |
| ref:mkrf_theaters | 28860 | 1 |
| ref:mkrf_theaters | 29099 | 1 |
| ref:mkrf_theaters | 30819 | 1 |
| ref:mkrf_theaters | 31936 | 1 |
| ref:mkrf_theaters | 34307 | 1 |
| ref:mkrf_theaters | 36520 | 1 |
| ref:mkrf_theaters | 38056 | 1 |
| ref:mkrf_theaters | 7518 | 1 |
| ref:mkrf_theaters | 8889 | 1 |
| ref:mkrf_theaters | 9578 | 1 |
| ref:mkrf_theaters | 9688 | 1 |
| ref:mkrf_theaters | 9719 | 1 |
| ref:mkrf_theaters | 9720 | 1 |
| ref:mkrf_theaters | 9721 | 1 |
| ref:mkrf_theaters | 9722 | 1 |
| ref:mkrf_theaters | 9723 | 1 |
| ref:mkrf_theaters | 9873 | 1 |
| ref:okn | 701410330840006 | 1 |
| ref:okn | 721410019010006 | 1 |
| ref:okn | 721410024130005 | 1 |
| ref:okn | 7410020000 | 1 |
| ref:okn | 861410074480004 | 1 |
| ref:okn | 861410123780005 | 1 |
| ref:sobory.ru | 00020 | 1 |
| ref:sobory.ru | 00028 | 1 |
| ref:sobory.ru | 00103 | 1 |
| ref:sobory.ru | 00344 | 1 |
| ref:sobory.ru | 00345 | 1 |
| ref:sobory.ru | 00967 | 1 |
| ref:sobory.ru | 00970 | 1 |
| ref:sobory.ru | 00972 | 1 |
| ref:sobory.ru | 01205 | 1 |
| ref:sobory.ru | 01209 | 1 |
| ref:sobory.ru | 01214 | 1 |
| ref:sobory.ru | 03023 | 1 |
| ref:sobory.ru | 03030 | 1 |
| ref:sobory.ru | 03060 | 1 |
| ref:sobory.ru | 04175 | 1 |
| ref:sobory.ru | 04320 | 1 |
| ref:sobory.ru | 05376 | 1 |
| ref:sobory.ru | 05531 | 1 |
| ref:sobory.ru | 05532 | 1 |
| ref:sobory.ru | 05751 | 1 |
| ref:sobory.ru | 05753 | 1 |
| ref:sobory.ru | 05754 | 1 |
| ref:sobory.ru | 05755 | 1 |
| ref:sobory.ru | 05756 | 1 |
| ref:sobory.ru | 05757 | 1 |
| ref:sobory.ru | 06315 | 1 |
| ref:sobory.ru | 06673 | 1 |
| ref:sobory.ru | 06746 | 1 |
| ref:sobory.ru | 06747 | 1 |
| ref:sobory.ru | 06794 | 1 |
| ref:sobory.ru | 06806 | 1 |
| ref:sobory.ru | 07417 | 1 |
| ref:sobory.ru | 07422 | 1 |
| ref:sobory.ru | 07799 | 1 |
| ref:sobory.ru | 08029 | 1 |
| ref:sobory.ru | 08389 | 1 |
| ref:sobory.ru | 08394 | 1 |
| ref:sobory.ru | 09835 | 1 |
| ref:sobory.ru | 09950 | 1 |
| ref:sobory.ru | 10252 | 1 |
| ref:sobory.ru | 10254 | 1 |
| ref:sobory.ru | 10380 | 1 |
| ref:sobory.ru | 10663 | 1 |
| ref:sobory.ru | 10664 | 1 |
| ref:sobory.ru | 11055 | 1 |
| ref:sobory.ru | 11097 | 1 |
| ref:sobory.ru | 11112 | 1 |
| ref:sobory.ru | 11318 | 1 |
| ref:sobory.ru | 11376 | 1 |
| ref:sobory.ru | 11477 | 1 |
| ref:sobory.ru | 11502 | 1 |
| ref:sobory.ru | 11510 | 1 |
| ref:sobory.ru | 11556 | 1 |
| ref:sobory.ru | 11573 | 1 |
| ref:sobory.ru | 11684 | 1 |
| ref:sobory.ru | 11710 | 1 |
| ref:sobory.ru | 11854 | 1 |
| ref:sobory.ru | 12530 | 1 |
| ref:sobory.ru | 12782 | 1 |
| ref:sobory.ru | 12861 | 1 |
| ref:sobory.ru | 13239 | 1 |
| ref:sobory.ru | 13338 | 1 |
| ref:sobory.ru | 13782 | 1 |
| ref:sobory.ru | 14003 | 1 |
| ref:sobory.ru | 14313 | 1 |
| ref:sobory.ru | 14352 | 1 |
| ref:sobory.ru | 15103 | 1 |
| ref:sobory.ru | 15441 | 1 |
| ref:sobory.ru | 15552 | 1 |
| ref:sobory.ru | 15575 | 1 |
| ref:sobory.ru | 15930 | 1 |
| ref:sobory.ru | 16195 | 1 |
| ref:sobory.ru | 16292 | 1 |
| ref:sobory.ru | 16466 | 1 |
| ref:sobory.ru | 16467 | 1 |
| ref:sobory.ru | 16524 | 1 |
| ref:sobory.ru | 16525 | 1 |
| ref:sobory.ru | 16526 | 1 |
| ref:sobory.ru | 16548 | 1 |
| ref:sobory.ru | 16549 | 1 |
| ref:sobory.ru | 16569 | 1 |
| ref:sobory.ru | 16570 | 1 |
| ref:sobory.ru | 16571 | 1 |
| ref:sobory.ru | 17153 | 1 |
| ref:sobory.ru | 17894 | 1 |
| ref:sobory.ru | 18711 | 1 |
| ref:sobory.ru | 18727 | 1 |
| ref:sobory.ru | 18798 | 1 |
| ref:sobory.ru | 18987 | 1 |
| ref:sobory.ru | 19263 | 1 |
| ref:sobory.ru | 19265 | 1 |
| ref:sobory.ru | 19266 | 1 |
| ref:sobory.ru | 19267 | 1 |
| ref:sobory.ru | 19268 | 1 |
| ref:sobory.ru | 19269 | 1 |
| ref:sobory.ru | 19270 | 1 |
| ref:sobory.ru | 19277 | 1 |
| ref:sobory.ru | 19675 | 1 |
| ref:sobory.ru | 19913 | 1 |
| ref:sobory.ru | 20258 | 1 |
| ref:sobory.ru | 20259 | 1 |
| ref:sobory.ru | 20260 | 1 |
| ref:sobory.ru | 20325 | 1 |
| ref:sobory.ru | 20853 | 1 |
| ref:sobory.ru | 20897 | 1 |
| ref:sobory.ru | 20900 | 1 |
| ref:sobory.ru | 21850 | 1 |
| ref:sobory.ru | 22768 | 1 |
| ref:sobory.ru | 22922 | 1 |
| ref:sobory.ru | 23186 | 1 |
| ref:sobory.ru | 24005 | 1 |
| ref:sobory.ru | 24778 | 1 |
| ref:sobory.ru | 24825 | 1 |
| ref:sobory.ru | 24835 | 1 |
| ref:sobory.ru | 24841 | 1 |
| ref:sobory.ru | 24916 | 1 |
| ref:sobory.ru | 24924 | 1 |
| ref:sobory.ru | 25278 | 1 |
| ref:sobory.ru | 25283 | 1 |
| ref:sobory.ru | 25835 | 1 |
| ref:sobory.ru | 26065 | 1 |
| ref:sobory.ru | 26080 | 1 |
| ref:sobory.ru | 26253 | 1 |
| ref:sobory.ru | 26377 | 1 |
| ref:sobory.ru | 26626 | 1 |
| ref:sobory.ru | 26911 | 1 |
| ref:sobory.ru | 27263 | 1 |
| ref:sobory.ru | 27280 | 1 |
| ref:sobory.ru | 27284 | 1 |
| ref:sobory.ru | 28582 | 1 |
| ref:sobory.ru | 28975 | 1 |
| ref:sobory.ru | 29402 | 1 |
| ref:sobory.ru | 29426 | 1 |
| ref:sobory.ru | 30278 | 1 |
| ref:sobory.ru | 30405 | 1 |
| ref:sobory.ru | 30406 | 1 |
| ref:sobory.ru | 32066 | 1 |
| ref:sobory.ru | 32069 | 1 |
| ref:sobory.ru | 32073 | 1 |
| ref:sobory.ru | 32851 | 1 |
| ref:sobory.ru | 33522 | 1 |
| ref:sobory.ru | 33552 | 1 |
| ref:sobory.ru | 33978 | 1 |
| ref:sobory.ru | 34090 | 1 |
| ref:sobory.ru | 35428 | 1 |
| ref:sobory.ru | 35762 | 1 |
| ref:sobory.ru | 35779 | 1 |
| ref:sobory.ru | 35844 | 1 |
| ref:sobory.ru | 35946 | 1 |
| ref:sobory.ru | 36241 | 1 |
| ref:sobory.ru | 36242 | 1 |
| ref:sobory.ru | 36243 | 1 |
| ref:sobory.ru | 36244 | 1 |
| ref:sobory.ru | 36363 | 1 |
| ref:sobory.ru | 36711 | 1 |
| ref:sobory.ru | 36794 | 1 |
| ref:sobory.ru | 37089 | 1 |
| ref:sobory.ru | 37111 | 1 |
| ref:sobory.ru | 37156 | 1 |
| ref:sobory.ru | 37328 | 1 |
| ref:sobory.ru | 37498 | 1 |
| ref:sobory.ru | 37559 | 1 |
| ref:sobory.ru | 37655 | 1 |
| ref:sobory.ru | 37861 | 1 |
| ref:sobory.ru | 37938 | 1 |
| ref:sobory.ru | 38062 | 1 |
| ref:sobory.ru | 38137 | 1 |
| ref:sobory.ru | 38298 | 1 |
| ref:sobory.ru | 38306 | 1 |
| ref:sobory.ru | 39305 | 1 |
| ref:sobory.ru | 40410 | 1 |
| ref:sobory.ru | 40890 | 1 |
| ref:sobory.ru | 40898 | 1 |
| ref:sobory.ru | 40899 | 1 |
| ref:sobory.ru | 40905 | 1 |
| ref:sobory.ru | 41325 | 1 |
| ref:sobory.ru | 41398 | 1 |
| ref:sobory.ru | 41980 | 1 |
| ref:sobory.ru | 41995 | 1 |
| ref:sobory.ru | 42145 | 1 |
| ref:sobory.ru | 42504 | 1 |
| ref:sobory.ru | 43121 | 1 |
| ref:sobory.ru | 44309 | 1 |
| ref:sobory.ru | 44328 | 1 |
| ref:sobory.ru | 44395 | 1 |
| ref:sobory.ru | 44396 | 1 |
| ref:sobory.ru | 45387 | 1 |
| ref:sobory.ru | 45507 | 1 |
| ref:sobory.ru | 45508 | 1 |
| ref:sobory.ru | 45509 | 1 |
| ref:sobory.ru | 45614 | 1 |
| ref:sobory.ru | 45628 | 1 |
| ref:sobory.ru | 46489 | 1 |
| ref:sobory.ru | 46599 | 1 |
| ref:sobory.ru | 46709 | 1 |
| ref:sobory.ru | 47643 | 1 |
| ref:sobory.ru | 48286 | 1 |
| ref:sobory.ru | 48463 | 1 |
| ref:sobory.ru | 49444 | 1 |
| ref:sobory.ru | 50111 | 1 |
| ref:sobory.ru | 50489 | 1 |
| ref:sobory.ru | 50500 | 1 |
| ref:sobory.ru | 54317 | 1 |
| ref:sobory.ru | 54769 | 1 |
| ref:sobory.ru | 56262 | 1 |
| ref:sobory.ru | 56502 | 1 |
| ref:sobory.ru | 57169 | 1 |
| ref:sobory.ru | 57956 | 1 |
| ref:sobory.ru | 58882 | 1 |
| ref:sobory.ru | 58908 | 1 |
| ref:sobory.ru | 59941 | 1 |
| ref:sobory.ru | 60571 | 1 |
| ref:sobory.ru | 60736 | 1 |
| ref:sobory.ru | 61446 | 1 |
| ref:sobory.ru | 64493 | 1 |
| ref:sobory.ru | 64494 | 1 |
| ref:sobory.ru | 64646 | 1 |
| ref:temples.ru | 10007 | 1 |
| ref:temples.ru | 10264 | 1 |
| ref:temples.ru | 10268 | 1 |
| ref:temples.ru | 10359 | 1 |
| ref:temples.ru | 10360 | 1 |
| ref:temples.ru | 10588 | 1 |
| ref:temples.ru | 10925 | 1 |
| ref:temples.ru | 11035 | 1 |
| ref:temples.ru | 11684 | 1 |
| ref:temples.ru | 11857 | 1 |
| ref:temples.ru | 12345 | 1 |
| ref:temples.ru | 12346 | 1 |
| ref:temples.ru | 12349 | 1 |
| ref:temples.ru | 12350 | 1 |
| ref:temples.ru | 12351 | 1 |
| ref:temples.ru | 12352 | 1 |
| ref:temples.ru | 12355 | 1 |
| ref:temples.ru | 12359 | 1 |
| ref:temples.ru | 12708 | 1 |
| ref:temples.ru | 12806 | 1 |
| ref:temples.ru | 13603 | 1 |
| ref:temples.ru | 14196 | 1 |
| ref:temples.ru | 14204 | 1 |
| ref:temples.ru | 14372 | 1 |
| ref:temples.ru | 14405 | 1 |
| ref:temples.ru | 14536 | 1 |
| ref:temples.ru | 15101 | 1 |
| ref:temples.ru | 15156 | 1 |
| ref:temples.ru | 15309 | 1 |
| ref:temples.ru | 15767 | 1 |
| ref:temples.ru | 16061 | 1 |
| ref:temples.ru | 16226 | 1 |
| ref:temples.ru | 16639 | 1 |
| ref:temples.ru | 16640 | 1 |
| ref:temples.ru | 16641 | 1 |
| ref:temples.ru | 16642 | 1 |
| ref:temples.ru | 16643 | 1 |
| ref:temples.ru | 16692 | 1 |
| ref:temples.ru | 16693 | 1 |
| ref:temples.ru | 16925 | 1 |
| ref:temples.ru | 17409 | 1 |
| ref:temples.ru | 18267 | 1 |
| ref:temples.ru | 18552 | 1 |
| ref:temples.ru | 18586 | 1 |
| ref:temples.ru | 18676 | 1 |
| ref:temples.ru | 18704 | 1 |
| ref:temples.ru | 18826 | 1 |
| ref:temples.ru | 18827 | 1 |
| ref:temples.ru | 18828 | 1 |
| ref:temples.ru | 18829 | 1 |
| ref:temples.ru | 19195 | 1 |
| ref:temples.ru | 19196 | 1 |
| ref:temples.ru | 19283 | 1 |
| ref:temples.ru | 19284 | 1 |
| ref:temples.ru | 19285 | 1 |
| ref:temples.ru | 19286 | 1 |
| ref:temples.ru | 19325 | 1 |
| ref:temples.ru | 19843 | 1 |
| ref:temples.ru | 19935 | 1 |
| ref:temples.ru | 19936 | 1 |
| ref:temples.ru | 19938 | 1 |
| ref:temples.ru | 19939 | 1 |
| ref:temples.ru | 20330 | 1 |
| ref:temples.ru | 20578 | 1 |
| ref:temples.ru | 20656 | 1 |
| ref:temples.ru | 20719 | 1 |
| ref:temples.ru | 21257 | 1 |
| ref:temples.ru | 21278 | 1 |
| ref:temples.ru | 21458 | 1 |
| ref:temples.ru | 21519 | 1 |
| ref:temples.ru | 21685 | 1 |
| ref:temples.ru | 21926 | 1 |
| ref:temples.ru | 21943 | 1 |
| ref:temples.ru | 21944 | 1 |
| ref:temples.ru | 21958 | 1 |
| ref:temples.ru | 21962 | 1 |
| ref:temples.ru | 21964 | 1 |
| ref:temples.ru | 21966 | 1 |
| ref:temples.ru | 21968 | 1 |
| ref:temples.ru | 22461 | 1 |
| ref:temples.ru | 22476 | 1 |
| ref:temples.ru | 22643 | 1 |
| ref:temples.ru | 22983 | 1 |
| ref:temples.ru | 22984 | 1 |
| ref:temples.ru | 23122 | 1 |
| ref:temples.ru | 24565 | 1 |
| ref:temples.ru | 24566 | 1 |
| ref:temples.ru | 24671 | 1 |
| ref:temples.ru | 24991 | 1 |
| ref:temples.ru | 25497 | 1 |
| ref:temples.ru | 25633 | 1 |
| ref:temples.ru | 25855 | 1 |
| ref:temples.ru | 26531 | 1 |
| ref:temples.ru | 26654 | 1 |
| ref:temples.ru | 26694 | 1 |
| ref:temples.ru | 26720 | 1 |
| ref:temples.ru | 26855 | 1 |
| ref:temples.ru | 27106 | 1 |
| ref:temples.ru | 27107 | 1 |
| ref:temples.ru | 27108 | 1 |
| ref:temples.ru | 27245 | 1 |
| ref:temples.ru | 27246 | 1 |
| ref:temples.ru | 27312 | 1 |
| ref:temples.ru | 27567 | 1 |
| ref:temples.ru | 27988 | 1 |
| ref:temples.ru | 27994 | 1 |
| ref:temples.ru | 27995 | 1 |
| ref:temples.ru | 27999 | 1 |
| ref:temples.ru | 28000 | 1 |
| ref:temples.ru | 28450 | 1 |
| ref:temples.ru | 28461 | 1 |
| ref:temples.ru | 28462 | 1 |
| ref:temples.ru | 28833 | 1 |
| ref:temples.ru | 28834 | 1 |
| ref:temples.ru | 29267 | 1 |
| ref:temples.ru | 3424 | 1 |
| ref:temples.ru | 3490 | 1 |
| ref:temples.ru | 3506 | 1 |
| ref:temples.ru | 3732 | 1 |
| ref:temples.ru | 3734 | 1 |
| ref:temples.ru | 3740 | 1 |
| ref:temples.ru | 3741 | 1 |
| ref:temples.ru | 3742 | 1 |
| ref:temples.ru | 3743 | 1 |
| ref:temples.ru | 6797 | 1 |
| ref:temples.ru | 6798 | 1 |
| ref:temples.ru | 6799 | 1 |
| ref:temples.ru | 7558 | 1 |
| ref:temples.ru | 8098 | 1 |
| ref:temples.ru | 8343 | 1 |
| ref:temples.ru | 8638 | 1 |
| ref:temples.ru | 8770 | 1 |
| ref:temples.ru | 8771 | 1 |
| ref:temples.ru | 8842 | 1 |
| ref:temples.ru | 8853 | 1 |
| ref:temples.ru | 8854 | 1 |
| ref:temples.ru | 8855 | 1 |
| ref:temples.ru | 8856 | 1 |
| ref:temples.ru | 8919 | 1 |
| ref:temples.ru | 8942 | 1 |
| ref:temples.ru | 8944 | 1 |
| ref:temples.ru | 8966 | 1 |
| ref:temples.ru | 8976 | 1 |
| ref:temples.ru | 8980 | 1 |
| ref:temples.ru | 8981 | 1 |
| ref:temples.ru | 8992 | 1 |
| ref:temples.ru | 9001 | 1 |
| ref:temples.ru | 9004 | 1 |
| ref:temples.ru | 9033 | 1 |
| ref:temples.ru | 9097 | 1 |
| ref:temples.ru | 9176 | 1 |
| ref:temples.ru | 9432 | 1 |
| ref:temples.ru | 9436 | 1 |
| ref:temples.ru | 9480 | 1 |
| ref:temples.ru | 9483 | 1 |
| ref:temples.ru | 9490 | 1 |
| ref:temples.ru | 9497 | 1 |
| ref:temples.ru | 9510 | 1 |
| ref:temples.ru | 9511 | 1 |
| ref:temples.ru | 9521 | 1 |
| ref:vatin | 2466092089 | 1 |
| ref:whc | 768rev | 2 |
| ref:whc | 754 | 1 |
| ref:whc | 768-002 | 1 |
| religion | christian | 2602 |
| religion | muslim | 216 |
| religion | buddhist | 200 |
| religion | jewish | 10 |
| religion | pagan | 8 |
| religion | shamanic | 4 |
| religion | spiritualist | 4 |
| religion | hindu | 3 |
| religion | altai | 1 |
| religion | unitarian_universalist | 1 |
| religion | православие | 1 |
| religion | православная | 1 |
| religion | шаманизьм | 1 |
| theatre:genre | circus | 10 |
| theatre:genre | drama | 5 |
| theatre:genre | puppet | 5 |
| theatre:genre | philharmonic | 4 |
| theatre:genre | chamber music | 1 |
| theatre:genre | concert_hall | 1 |
| theatre:genre | musical | 1 |
| theatre:genre | opera | 1 |
| theatre:genre | opera;ballet | 1 |
| theatre:genre | puppet;marionette | 1 |
| tourism | attraction | 3094 |
| tourism | museum | 1040 |
| tourism | zoo | 77 |
| tourism | yes | 66 |
| tourism | artwork | 40 |
| tourism | gallery | 29 |
| tourism | information | 5 |
| tourism | viewpoint | 4 |
| tourism | camp_site | 1 |

Топ-50 имён железнодорожной тематики (имя и число совпавших объектов):

| Имя | Число объектов |
| --- | --- |
| Паровоз | 16 |
| Паровоз Черепановых | 5 |
| Дворец культуры железнодорожников | 3 |
| Братская могила повстанцев | 2 |
| Выставочный центр железнодорожной техники им. Н.А.Акулинина | 2 |
| Локомотив | 2 |
| Музейная экспозиция локомотивов СССР | 2 |
| паровоз Эм-730-73 | 2 |
| подстанция (разруш.) | 2 |
| Станция юных техников | 2 |
| Арочный железнодорожный мост | 1 |
| Арт-объект "Старинный паровоз" | 1 |
| Аттракцион "Паровозик" | 1 |
| База запаса.Отстой локомотивов и жд вагонов | 1 |
| Боро-боро, арктическая станция | 1 |
| Братская могила красноармейцев железнодорожников павших в боях против армии Колчака 1919 г. | 1 |
| Бывшая летноиспытательная станция ПО "Полёт" | 1 |
| Бывшая станция УЖД «ЛИГУЗ» | 1 |
| Бывшее депо узкоколейки | 1 |
| Водонапорная башня главных железнодорожных мастерских | 1 |
| Водоочистная станция Прогресса | 1 |
| Воинам вагонного депо ст. Челябинск в годы ВОВ | 1 |
| Воинам-железнодорожникам | 1 |
| В память о строительстве железной дороги Обская - Бованенково | 1 |
| Гидроэлектростанция 1930 г. | 1 |
| Дежурные комнаты паровозных бригад | 1 |
| Деревянный паровоз | 1 |
| ж/д "Чёртов мост" на БАМе | 1 |
| Железнодорожная экспозиция | 1 |
| Железнодорожникам | 1 |
| Железнодорожникам, погибшим в годы Великой Отечественной войны | 1 |
| Железнодорожникам, расстрелянным колчаковцами | 1 |
| Железнодорожнику | 1 |
| Железнодорожный локомотив | 1 |
| Железнодорожный мост | 1 |
| Железнодорожный мост через р. Исток | 1 |
| Жертвам ж/д катастрофы 1944 г. | 1 |
| Заброшенная насосная станция | 1 |
| Заброшенная тропосферная радиорелейная станция "Ока" | 1 |
| Здание бывшего аэровокзала местных воздушных линий | 1 |
| Здание железнодорожного вокзала | 1 |
| Здание старого ЖД вокзала | 1 |
| Здание электростанции И. И. Игнатова | 1 |
| Знак в память об основателе Западно-Сибирской железной дороги А.Н. Куломзине | 1 |
| Исторический привокзальный туалет | 1 |
| К 120-летию Западно-Сибирской железной дороги | 1 |
| каменные останцы | 1 |
| каменные останцы Краснинские слоны | 1 |
| Камень, заложенный при строительстве железнодорожного вокзала | 1 |
| Киркирей - место сбойки Кругобайкальской железной дороги | 1 |

### `osm_pois_near_railway`

Всего объектов: **3026**.

| Ключ | Значение | Число объектов |
| --- | --- | --- |
| amenity | place_of_worship | 503 |
| amenity | theatre | 90 |
| amenity | arts_centre | 69 |
| amenity | bench | 4 |
| amenity | fountain | 2 |
| amenity | car_rental | 1 |
| amenity | church | 1 |
| amenity | grave_yard | 1 |
| amenity | townhall | 1 |
| attraction | animal | 66 |
| attraction | amusement_ride | 2 |
| attraction | big_wheel | 2 |
| attraction | carousel | 2 |
| attraction | boat_ride | 1 |
| attraction | bumper_car | 1 |
| attraction | canon | 1 |
| attraction | jet | 1 |
| attraction | roller_coaster | 1 |
| attraction | swing_carousel | 1 |
| attraction | train | 1 |
| attraction | yes | 1 |
| building | yes | 393 |
| building | church | 153 |
| building | chapel | 53 |
| building | temple | 20 |
| building | public | 16 |
| building | mosque | 9 |
| building | cathedral | 8 |
| building | warehouse | 6 |
| building | civic | 5 |
| building | house | 5 |
| building | apartments | 3 |
| building | university | 3 |
| building | retail | 2 |
| building | commercial | 1 |
| building | detached | 1 |
| building | garage | 1 |
| building | government | 1 |
| building | houseboat | 1 |
| building | industrial | 1 |
| building | museum | 1 |
| building | residential | 1 |
| building | ruins | 1 |
| building | synagogue | 1 |
| denomination | orthodox | 154 |
| denomination | russian_orthodox | 96 |
| denomination | baptist | 13 |
| denomination | catholic | 8 |
| denomination | roman_catholic | 5 |
| denomination | pentecostal | 4 |
| denomination | lutheran | 3 |
| denomination | old_believers | 3 |
| denomination | armenian_apostolic | 2 |
| denomination | evangelical | 2 |
| denomination | karma_kagyu | 2 |
| denomination | seventh_day_adventist | 2 |
| denomination | ananda_marga | 1 |
| denomination | greek_orthodox | 1 |
| denomination | mormon | 1 |
| denomination | protestant | 1 |
| denomination | sunni | 1 |
| heritage | 4 | 3 |
| heritage | 2 | 2 |
| heritage:name | Главный корпус технологического института, в котором в 1904-1905 гг. на вечерних общеобразовательных курсах учился Киров Сергей Миронович | 1 |
| heritage:name | Смешанный 2-этажный дом, н. XX в. | 1 |
| heritage:operator | Ministry of Culture of the Russian Federation | 2 |
| heritage:website | https://opendata.mkrf.ru/opendata/7705851331-egrkn/68/147693 | 1 |
| historic | memorial | 1520 |
| historic | ruins | 62 |
| historic | aircraft | 42 |
| historic | building | 32 |
| historic | wayside_cross | 23 |
| historic | yes | 23 |
| historic | locomotive | 18 |
| historic | tank | 18 |
| historic | archaeological_site | 17 |
| historic | manor | 12 |
| historic | tomb | 9 |
| historic | monument | 8 |
| historic | city_gate | 5 |
| historic | bank | 1 |
| historic | bunker | 1 |
| historic | cannon | 1 |
| historic | castle | 1 |
| historic | helicopter | 1 |
| historic | locomotve | 1 |
| historic | milestone | 1 |
| historic | railway | 1 |
| historic | retail | 1 |
| historic | technical_monument | 1 |
| historic | train_station | 1 |
| historic | vehicle | 1 |
| memorial | plaque | 156 |
| memorial | war_memorial | 153 |
| memorial | statue | 140 |
| memorial | stele | 130 |
| memorial | bust | 79 |
| memorial | stone | 61 |
| memorial | sculpture | 47 |
| memorial | obelisk | 35 |
| memorial | memorial | 30 |
| memorial | tank | 10 |
| memorial | blue_plaque | 7 |
| memorial | vehicle | 6 |
| memorial | yes | 6 |
| memorial | cannon | 3 |
| memorial | monument | 3 |
| memorial | eternal_flame | 2 |
| memorial | locomotive | 2 |
| memorial | паровоз | 2 |
| memorial | aircraft | 1 |
| memorial | board | 1 |
| memorial | bowl | 1 |
| memorial | building | 1 |
| memorial | column | 1 |
| memorial | cross | 1 |
| memorial | helicopter | 1 |
| memorial | military_vehicle | 1 |
| memorial | nature | 1 |
| memorial | tree | 1 |
| memorial | war | 1 |
| memorial | Защитникам Отечества | 1 |
| memorial | самолёт | 1 |
| memorial | танк | 1 |
| memorial | трактор | 1 |
| museum | history | 7 |
| museum | aerospace | 1 |
| museum | art | 1 |
| museum | history, religion | 1 |
| museum | nature | 1 |
| museum | technology | 1 |
| ref:egrokn | 25 | 1 |
| ref:egrokn | 551510290360006 | 1 |
| ref:egrokn | 551711127260005 | 1 |
| ref:mkrf_museums | 18176 | 1 |
| ref:mkrf_museums | 7481 | 1 |
| ref:mkrf_museums | 8807 | 1 |
| ref:mkrf_theaters | 13509 | 1 |
| ref:mkrf_theaters | 13511 | 1 |
| ref:mkrf_theaters | 13513 | 1 |
| ref:mkrf_theaters | 13514 | 1 |
| ref:mkrf_theaters | 13515 | 1 |
| ref:mkrf_theaters | 13516 | 1 |
| ref:mkrf_theaters | 13517 | 1 |
| ref:mkrf_theaters | 13518 | 1 |
| ref:mkrf_theaters | 13619 | 1 |
| ref:mkrf_theaters | 13621 | 1 |
| ref:mkrf_theaters | 13622 | 1 |
| ref:mkrf_theaters | 13626 | 1 |
| ref:mkrf_theaters | 13627 | 1 |
| ref:mkrf_theaters | 13629 | 1 |
| ref:mkrf_theaters | 13657 | 1 |
| ref:mkrf_theaters | 13660 | 1 |
| ref:mkrf_theaters | 13669 | 1 |
| ref:mkrf_theaters | 13674 | 1 |
| ref:mkrf_theaters | 15224 | 1 |
| ref:mkrf_theaters | 15247 | 1 |
| ref:mkrf_theaters | 15892 | 1 |
| ref:mkrf_theaters | 16985 | 1 |
| ref:mkrf_theaters | 17011 | 1 |
| ref:mkrf_theaters | 17050 | 1 |
| ref:mkrf_theaters | 17724 | 1 |
| ref:mkrf_theaters | 17851 | 1 |
| ref:mkrf_theaters | 18293 | 1 |
| ref:mkrf_theaters | 18343 | 1 |
| ref:mkrf_theaters | 24571 | 1 |
| ref:mkrf_theaters | 24856 | 1 |
| ref:mkrf_theaters | 30819 | 1 |
| ref:mkrf_theaters | 31936 | 1 |
| ref:mkrf_theaters | 8889 | 1 |
| ref:okn | 701410330840006 | 1 |
| ref:okn | 721410019010006 | 1 |
| ref:okn | 721410024130005 | 1 |
| ref:sobory.ru | 00020 | 1 |
| ref:sobory.ru | 00028 | 1 |
| ref:sobory.ru | 00103 | 1 |
| ref:sobory.ru | 05376 | 1 |
| ref:sobory.ru | 09835 | 1 |
| ref:sobory.ru | 11502 | 1 |
| ref:sobory.ru | 14003 | 1 |
| ref:sobory.ru | 16195 | 1 |
| ref:sobory.ru | 18987 | 1 |
| ref:sobory.ru | 61446 | 1 |
| ref:temples.ru | 14196 | 1 |
| ref:temples.ru | 20656 | 1 |
| ref:temples.ru | 8343 | 1 |
| ref:temples.ru | 8638 | 1 |
| ref:temples.ru | 8770 | 1 |
| ref:temples.ru | 8771 | 1 |
| ref:temples.ru | 8842 | 1 |
| ref:temples.ru | 8853 | 1 |
| ref:temples.ru | 8854 | 1 |
| ref:temples.ru | 9033 | 1 |
| ref:temples.ru | 9480 | 1 |
| ref:temples.ru | 9483 | 1 |
| ref:temples.ru | 9490 | 1 |
| ref:temples.ru | 9497 | 1 |
| ref:temples.ru | 9510 | 1 |
| ref:temples.ru | 9511 | 1 |
| religion | christian | 433 |
| religion | muslim | 27 |
| religion | buddhist | 3 |
| religion | jewish | 3 |
| religion | hindu | 1 |
| religion | pagan | 1 |
| religion | unitarian_universalist | 1 |
| theatre:genre | circus | 3 |
| theatre:genre | puppet | 2 |
| theatre:genre | concert_hall | 1 |
| theatre:genre | drama | 1 |
| theatre:genre | musical | 1 |
| theatre:genre | philharmonic | 1 |
| tourism | attraction | 330 |
| tourism | museum | 171 |
| tourism | artwork | 15 |
| tourism | zoo | 13 |
| tourism | gallery | 6 |
| tourism | information | 1 |

Топ-50 имён железнодорожной тематики (имя и число совпавших объектов):

| Имя | Число объектов |
| --- | --- |
| Паровоз | 4 |
| Выставочный центр железнодорожной техники им. Н.А.Акулинина | 2 |
| Аттракцион "Паровозик" | 1 |
| Братская могила повстанцев | 1 |
| Бывшая летноиспытательная станция ПО "Полёт" | 1 |
| Водонапорная башня главных железнодорожных мастерских | 1 |
| Водоочистная станция Прогресса | 1 |
| Деревянный паровоз | 1 |
| Железнодорожникам, расстрелянным колчаковцами | 1 |
| Железнодорожный мост | 1 |
| Заброшенная насосная станция | 1 |
| Здание бывшего аэровокзала местных воздушных линий | 1 |
| Здание железнодорожного вокзала | 1 |
| Знак в память об основателе Западно-Сибирской железной дороги А.Н. Куломзине | 1 |
| К 120-летию Западно-Сибирской железной дороги | 1 |
| Локомотив А-1067 | 1 |
| Локомотив ЧС-2 | 1 |
| макет Паровоза Черепановых | 1 |
| Макет паровоза Черепановых | 1 |
| Музей Железнодорожного района | 1 |
| Музей Западно-Сибирской железной дороги | 1 |
| Памчтник к 80летию станции | 1 |
| Памятник воинам-железнодорожникам, погибшим в годы Великой Отечественной войны (1931-1945) | 1 |
| Памятник дежурному по станции | 1 |
| Памятник железнодорожникам, участникам Мартовского восстания | 1 |
| Памятник железнодорожному башмаку | 1 |
| памятник жертвам жд катастрофы | 1 |
| Памятник паровозу | 1 |
| Паровоз Л-0154 | 1 |
| Паровоз Л-0614 | 1 |
| паровоз Л-0697 | 1 |
| Паровоз Л-3238 | 1 |
| Паровоз Л-3609 | 1 |
| Паровоз Л-3808 | 1 |
| Паровоз Л-4738 | 1 |
| Паровоз-памятник Л-3815 | 1 |
| Паровоз-памятник ФД21-3000 | 1 |
| Паровоз-памятник ЭР 789-85 | 1 |
| Паровоз-памятник Эр 798-19 | 1 |
| Паровоз "Проворный" | 1 |
| Паровоз Эр790-68 | 1 |
| Пролёт первого железнодорожного моста через р. Обь | 1 |
| Станция Инская | 1 |
| Станция метро "Соборная" | 1 |
| Танк-паровоз фирмы Борзиг | 1 |

## Радиусы от точек ЖД

| Все osm_pois | ≤ 2500 м | ≤ 5000 м |
| --- | --- | --- |
| 22223 | 2125 | 3026 |

## Расстояния между соседними точками ЖД

| Соседних пар | Медиана, м | p95, м | Максимум, м | > 500 м |
| --- | --- | --- | --- | --- |
| 313959 | 119.64237824 | 778.203507811 | 2971.01791998 | 51391 |

### Неоднозначность порядка и стабильная диагностика

Основная статистика выше использует нормативный порядок `(track_id, km, measure)`. При повторяющихся ключах соседство не детерминировано. Таблица ниже показывает число совпадающих ключей и диагностический пересчёт с `id` как последним tie-breaker; это не меняет нормативный запрос.

| Уникальных ключей | Точек | Строк сверх первой в группе | Ключей с повторами | Максимальный размер группы |
| --- | --- | --- | --- | --- |
| 14892 | 319359 | 304467 | 14223 | 47 |

| Порядок | Соседних пар | Медиана, м | p95, м | Максимум, м | > 500 м |
| --- | --- | --- | --- | --- | --- |
| (track_id, km, measure, id) | 313959 | 30.00103747 | 537.2586264169998 | 2312.83946286 | 16618 |

## Сводка аудита этапа 0b

### Git и область изменений

- Текущая ветка: `feature/taxonomy`.
- HEAD: `2b9230c875efc06edbb8d8bf048ab3fcd1d8929f`.
- База относительно `reload-data`: `5a981935ff986281c8376b4e0b9e84e145c150cd`.
- Тег `backup-before-taxonomy` создан до изменений аудита и указывает на HEAD `2b9230c875efc06edbb8d8bf048ab3fcd1d8929f`.
- Код приложения, схема и содержимое БД, импортёры и исходные OSM-файлы не изменялись. Добавлены только этот отчёт и read-only скрипт `scripts/audit_tags.py`.
- Миграции, импорт, классификация и очистка данных не запускались. Запросы аудита выполнялись в транзакции `READ ONLY`.

### Фактическое состояние БД и данных

- PostgreSQL/PostGIS: PostGIS 3.4.3.
- `osm_pois`: 22 223 строки; `osm_pois_near_railway`: 3 026; `raw_railway_points`: 319 359; `culture_place`: 2 474.
- В `culture_place` 2 434 строки имеют OSM-идентичность, 40 — без неё; 125 строк имеют Wikidata ID, 46 — непустой `ai_summary`. Схема не позволяет только по отсутствию OSM ID достоверно определить происхождение этих 40 строк.
- Для аудита был запущен только сервис `db`; backend не запускался. После проверки сервис БД остановлен командой `docker compose stop db`; Docker volume и данные не удалялись.
- `osm_pois_near_railway` содержит столько же строк, сколько попадает в радиус 5 000 м: 3 026. В радиус 2 500 м попадают 2 125 строк. Следовательно, текущий импортный охват не соответствует целевому жёсткому радиусу 2 500 м.
- В БД пока нет схемы таксономии и новых полей, предусмотренных этапами ТЗ.
- Фактические `track_id`, `km`, `measure` в `raw_railway_points` допускают `NULL`, хотя ORM-модель объявляет их `NOT NULL`.
- Таблицы содержат пространственные индексы; аудит не менял схему и индексы.
- Сопоставление XML и БД для `raw_railway_points`: по 319 359 точек с совпадающими координатами; несовпадений не найдено.
- В локальном PBF были найдены 22 228 объектов по действующему фильтру и ещё 1 555 кандидатов по предварительным фильтрам D-5. Разница в пять объектов между PBF и `osm_pois` не объяснена; для фактических частот тегов источником отчёта служат таблицы БД.
- Распределения OSM-тегов и железнодорожных названий приведены выше по обеим таблицам. В частности, широко представлены `amenity=place_of_worship` (3 186), `building=yes` (1 941), `building=church` (1 372), а значения `attraction` разнородны. Эти данные подтверждают необходимость явных правил; одиночный тег или название сами по себе не подтверждают значимость объекта.

### Уточнение идентификации и ошибки импорта точек

В XML `TRACK` имеет вид двух числовых частей через запятую, например `TRACK="16912,1186"`. Импортёр в `scripts/init_data.py` использует регулярное выражение `TRACK="(\d+),[^"]+"`: в поле `track_id` сохраняется только первая часть (`16912`), а вторая (`1186`) отбрасывается. Код проекта не документирует семантику второй части. В текущем XML полная пара `TRACK` уникальна для каждой из 319 359 точек; это наблюдение не доказывает смысл или стабильность пары между версиями файла.

Дополнительно обнаружена ошибка извлечения `M`. Импортёр использует `re.compile(r'M="([\d\.]+)')` без границы атрибута. В строке XML атрибут `KM="2555"` встречается раньше `M="12.86"`; поиск находит подстроку `M="2555"` внутри `KM="2555"`. Поэтому фактическое поле БД `measure` оказалось равным `KM`, а не XML-атрибуту `M`. Read-only сопоставление каждой строки по координатам показало: 319 348 из 319 359 DB-строк имеют `measure=KM` и `measure!=XML.M`; совпали все координаты, но только 11 строк совпали также по `track_id`, `km` и истинному `M`.

Это меняет интерпретацию предшествующего расчёта шага: 14 223 группы с одинаковыми DB-ключами `(track_id, km, measure)` (304 467 строк сверх первой, максимальная группа 47) в первую очередь вызваны тем, что `measure` ошибочно скопировал километровый атрибут. Это не свидетельство, что исходный XML имеет столько же совпадающих `(первая часть TRACK, KM, M)` ключей: в проверенной XML-выгрузке все 319 359 таких троек уникальны. Метрики соседей, рассчитанные по текущему DB-полю `measure`, не пригодны для вывода о фактической плотности/шаге точек и не подтверждают прохождение порога p95 1 000 м. Их численные значения выше сохранены как описание того, что вычислял запрос над текущей БД, а не как корректная характеристика исходной геометрии.

### Алгоритм прежнего расчёта расстояний

Запрос строит `LAG(geom::geography)` в окне `PARTITION BY track_id ORDER BY km, measure`; для каждой строки, кроме первой в разделе, вычисляется `ST_Distance(текущая_geography, предыдущая_geography)`. Geography-расстояние `ST_Distance` возвращается в метрах и по умолчанию использует сфероид. Далее для ненулевых результатов SQL `percentile_cont(0.5)` даёт непрерывную медиану (при чётном числе значений интерполирует середину двух центральных), `percentile_cont(0.95)` — непрерывный 95-й процентиль, `MAX` — максимум, а `COUNT(*) FILTER (WHERE gap_m > 500)` — число промежутков строго более 500 м.

Равные `(track_id, km, measure)` не исключаются и не схлопываются; без дополнительного `ORDER BY` их взаимный порядок SQL не определяет, поэтому соседства внутри этих групп могут меняться. Диагностический вариант добавлял `id` в конец сортировки; это фиксирует порядок только для текущего набора DB-строк.

Фактические таблицы на момент уточнения содержат 0 строк с NULL в `track_id`, `km` или `measure`. Сам запрос, однако, не фильтрует такие строки: NULL `track_id`-значения попадут в общий NULL-раздел, а NULL `km`/`measure` в сортировке ASC PostgreSQL окажутся после ненулевых значений. Такие строки будут участвовать в LAG-цепочке; геометрия модели объявлена NOT NULL. Первые строки разделов дают NULL gap и исключаются из статистики фильтром `WHERE gap_m IS NOT NULL`.

### Финальный расчёт соседних расстояний непосредственно по XML

Для этой проверки XML читался отдельно от БД через `ElementTree`; атрибуты извлекались по точным именам XML, поэтому `KM` и `M` не смешиваются. `track_id` для группировки взят только из первой компоненты `TRACK`, как решил владелец; вторая компонента не использовалась. Точки внутри группы упорядочивались по `(KM, M, GNSSID)`, где `GNSSID` добавлен только как детерминированный tie-breaker текущей выгрузки. В исходнике 319 359 точек, 5 400 групп `track_id`; все ключи `(первая компонента TRACK, KM, M)` уникальны, так что в этой выгрузке tie-breaker фактически не потребовался. Это не утверждает стабильность `GNSSID` между выгрузками.

Для каждой группы вычислялось геодезическое расстояние между соседями после сортировки; использовано обратное решение Винсенти на эллипсоиде WGS84. Получено 313 959 соседних пар. Медиана и p95 рассчитаны как непрерывные процентили с линейной интерполяцией по рангу `(n-1)*p`; максимум — наибольшее расстояние; пороговый счёт включает только расстояния строго больше 500 м.

| Источник и порядок | Пар | Медиана, м | p95, м | Максимум, м | > 500 м |
| --- | ---: | ---: | ---: | ---: | ---: |
| Исходный XML: `(track_id, KM, M, GNSSID)` | 313959 | 29.95766895 | 30.83270876 | 2312.83946016 | 48 |

### Сопоставление XML-расчёта с прежними DB-результатами

| Расчёт | Медиана, м | p95, м | Максимум, м | > 500 м |
| --- | ---: | ---: | ---: | ---: |
| XML с настоящими `KM` и `M`; `GNSSID` для детерминированности | 29.95766895 | 30.83270876 | 2312.83946016 | 48 |
| БД с дополнительной сортировкой по surrogate `id` | 30.00103747 | 537.25862642 | 2312.83946 | 16618 |
| БД без tie-breaker, последний зафиксированный запуск | 119.64237824 | 778.20350781 | 2971.01791998 | 51391 |

Небольшое отличие медиан XML и БД с `id` не означает совпадения порядка. Основное расхождение — в хвосте распределения: ошибочное DB-поле `measure=KM` оставляло множество точек равными по `(track_id, km, measure)`, и `id` задавал их текущий порядок вставки вместо сортировки по исходному `M`. Отсюда намного больший DB p95 и число промежутков >500 м. Максимумы XML и DB с `id` близки, но это совпадение не исправляет некорректный порядок остальных точек. В варианте без tie-breaker порядок равных DB-ключей не определён и результаты менялись между запусками; эти значения не сравнимы как стабильная характеристика XML.

Расчёт XML воспроизводим для данной версии исходного файла и принятого порядка, но не гарантирует неизменность результатов при новой выгрузке: семантика/стабильность `GNSSID` ещё не подтверждена. Стабильный межверсионный ключ по-прежнему не утверждён.

### Источниковые идентификаторы и повторная загрузка

Поле `raw_railway_points.id` — суррогатный первичный ключ SQLAlchemy-модели (`Integer`, `primary_key=True`), назначаемый последовательностью БД. XML-загрузчик не передаёт `id`; он вставляет ORM-объекты с геометрией и извлечёнными полями.

При обычном повторном запуске `init_data.py` заполненная таблица, в которой нет NULL в `track_id/km/measure`, не загружается заново. Если загрузка всё же запускается через предусмотренную ветку пустой таблицы/неполных полей, код сначала удаляет существующие строки, а затем вставляет их заново; новые строки получают новые sequence ID (последовательность не сбрасывается обычным `DELETE`). Прямой вызов `load_railway_points` добавляет строки и сам не обеспечивает идемпотентность. Следовательно, DB `id` не является переносимым стабильным tie-breaker между повторными импортами.

В исходном XML нет отдельного атрибута порядкового номера. Порядок `<gnss>`-элементов в текущем файле можно пронумеровать при чтении, но загрузчик его не сохраняет, а стабильность позиции при новой выгрузке не гарантирована. Атрибут `GNSSID` присутствует у всех 319 359 текущих записей и уникален в этой выгрузке; также уникален здесь полный `TRACK`. Репозиторий не подтверждает, сохраняется ли `GNSSID` между выгрузками, поэтому его следует считать сильным кандидатом на source key, но не гарантированно стабильным без подтверждения поставщика/сравнения версий.

### Что именно сравнивалось: XML/БД и PBF/БД

Это были разные проверки и разные наборы данных:

- **XML ↔ `raw_railway_points`:** сравнивались мультимножества точных пар координат `(LON, LAT)` из XML и `(ST_X(geom), ST_Y(geom))` из БД: 319 359 записей с каждой стороны, совпадение полное, лишних/отсутствующих координат нет. Это подтверждает только сохранение координат и количества, не идентичность записей по `GNSSID`, `TRACK`, `KM`, `M` или исходному порядку. Повторная уточняющая проверка по координатам выявила описанную выше ошибку в атрибуте `measure`.
- **PBF ↔ `osm_pois`:** сопоставлялись только итоговые количества объектов, выбранных локальным PBF-сканером по действующему фильтру (22 228), и строк в таблице `osm_pois` (22 223). Пять объектов по OSM-идентичностям, координатам или тегам не сопоставлялись; причины разницы и конкретные записи не установлены. Это не проверка железнодорожных точек и не сравнение PBF с XML.

### Сверка кода с целевыми требованиями

- В репозитории отсутствует `config/taxonomy.yaml` и чистые модули таксономии/качества описания/единого запроса видимости из целевой архитектуры.
- Действующий импорт использует охват 5 000 м, а не обязательные 2 500 м; фильтры импорта ещё не соответствуют планируемой таксономии.
- В текущем API и классификаторе нет целевого правила показа «только после расчёта расстояния и классификации» и полного перехода в `pending_review` при неопределённости.
- Автоматический импорт сейчас не реализует все гарантии сохранения ручных решений, идемпотентности и реестра жёстких исключений, требуемые ТЗ.
- Скрипт инициализации содержит 40 demo-объектов, хотя его текст сообщает о 50. Demo-объекты нельзя считать освобождёнными от радиуса и правил классификации.
- Существующие тесты не покрывают ещё не реализованные требования таксономии; эта работа относится к следующим этапам, не к этапу 0b.

Это описание фиксирует расхождения, но не меняет код или данные и не предрешает помеченные в ТЗ решения владельца.

### Проверки и ограничения

- `python -m py_compile scripts\audit_tags.py` — успешно.
- `python -m scripts.audit_tags` — успешно; SQL-чтение фактических таблиц завершилось, отчёт сформирован. Запросы включают нормативную статистику и дополнительный детерминированный диагностический расчёт.
- Базовый запуск `python -m unittest discover -s tests` завершился успешно: 17 тестов пройдены на Python 3.14.5. Python 3.11 в среде отсутствует, поэтому целевая версия проекта этим запуском не сертифицирована.
- Архивные тесты запускались без изменения `archive/`. Команда из корня `transib-from-zero`: `python -m unittest discover -s archive\tests` — завершилась ошибками импорта (`ModuleNotFoundError: No module named 'scripts.export_novosibirsk_research'` и `scripts.import_novosibirsk_research`), потому что стандартный поиск импортировал `scripts` приложения, а не исторические модули из `archive/scripts`. Запуск из `archive` командой `python -m unittest discover -s tests` также завершился ошибками `ModuleNotFoundError: No module named 'app'`.
- Для изолированного прогона без изменения файлов использована команда из корня `transib-from-zero`: `python -c "import sys, types, pathlib, unittest; pkg=types.ModuleType('scripts'); pkg.__path__=[str(pathlib.Path('archive/scripts').resolve())]; sys.modules['scripts']=pkg; suite=unittest.defaultTestLoader.discover('archive/tests', pattern='test*.py'); result=unittest.TextTestRunner(verbosity=2).run(suite); raise SystemExit(not result.wasSuccessful())"` — **3 теста пройдены**.
- Интеграционные тесты не запускались: подключение к рабочей БД не является заменой предусмотренной отдельной `transsib_test`, и запуск миграций/тестовых изменений здесь запрещён.
- PBF-подсчёты — предварительная сверка кандидатов; установленный для сканирования временный инструмент удалён, зависимости проекта не менялись.

### Готовность и вопрос владельцу

Аудит этапа 0b и запрошенные уточнения завершены; этап 1 не начинался. Первоначальные DB-метрики шага недостоверны из-за ошибки извлечения `M`. Прямой расчёт по исходному XML с корректными `KM` и `M` даёт p95 30.83 м и 48 промежутков >500 м; для этой выгрузки результат не зависит от tie-breaker, поскольку сортировочные ключи уникальны. `GNSSID` остаётся только диагностическим ключом, а не утверждённой стабильной идентичностью.

### Отдельная рекомендация по стабильному ключу точек

Не использовать DB `id` как постоянную идентичность или стабильный tie-breaker между импортами. Рекомендуемый кандидат — сохраняемый `GNSSID`, поскольку он уникален для каждой строки в текущем XML; перед принятием требуется подтвердить у поставщика, что `GNSSID` стабилен между обновлениями исходника. Если это подтверждается, хранить его как исходный идентификатор и использовать как tie-breaker только после корректной загрузки `KM` и `M`. Сохранять позицию элемента XML можно как вспомогательную диагностику, но не как стабильный ключ. До подтверждения не трактовать вторую компоненту `TRACK` как источник идентичности/порядка, хотя полная пара уникальна в текущем файле.
