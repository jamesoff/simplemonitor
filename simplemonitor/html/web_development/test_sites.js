//An extract of address points from the LINZ bulk extract: http://www.linz.govt.nz/survey-titles/landonline-data/landonline-bde
//Should be this data set: http://data.linz.govt.nz/#/layer/779-nz-street-address-electoral/
var addressPoints = [
    [46.9784, -123.816528, "up", "Aberdeen School District"],
    [46.631243, -123.056327, "up", "Adna School District"],
    [47.70752, -118.940926, "up", "Almira School District"],
    [48.504402, -122.617639, "up", "Anacortes School District"],
    [48.195549, -122.122384, "up", "Arlington School District"],
    [46.412363, -117.043854, "up", "Asotin County Library"],
    [46.34045, -117.052155, "up", "Asotin-Anatone School District"],
    [47.311823, -122.217148, "up", "Auburn School District"],
    [47.636244, -122.523954, "down", "Bainbridge Island School District"],
    [47.251967, -122.446493, "down", "Bates Technical College"],
    [47.188512, -122.466768, "down", "Bates Technical College South"],
    [45.731551, -122.560421, "down", "Battle Ground School District"],
    [47.584567, -122.148542, "down", "Bellevue College"],
    [47.609185, -122.175862, "down", "Bellevue School District"],
    [48.759351, -122.487003, "down", "Bellingham School District"],
    [48.76628, -122.510107, "down", "Bellingham Technical College"],
    [46.910246, -118.100453, "down", "Benge School District"],
    [47.09463, -122.424469, "down", "Bethel School District"],
    [45.997856, -120.304793, "down", "Bickleton School District"],
    [47.186178, -119.328335, "down", "Big Bend Community College"],
    [48.992293, -122.73828, "down", "Blaine School District"],
    [46.550443, -123.131929, "down", "Boistfort School District"],
    [47.573349, -122.638573, "down", "Bremerton School District"],
    [48.094357, -119.787119, "down", "Brewster School District"],
    [48.006785, -119.676184, "down", "Bridgeport School District"],
    [47.696868, -122.904028, "down", "Brinnon School District"],
    [48.477951, -122.338306, "down", "Burlington-Edison School District"],
    [47.388419, -122.305146, "up", "CWU Des Moines (Highline CC)"],
    [47.000023, -120.544309, "up", "CWU Ellensburg"],
    [47.81684, -122.327696, "up", "CWU Lynnwood Center (Edmonds CC)"],
    [47.186178, -119.328335, "up", "CWU Moses Lake (Big Bend CC)"],
    [47.172695, -122.571471, "up", "CWU Pierce (Steilacoom)"],
    [47.610295, -122.033849, "up", "CWU Sammamish"],
    [47.430814, -120.333418, "up", "CWU Wenatchee (WWCC)"],
    [46.585015, -120.530154, "up", "CWU Yakima (YVCC)"],
    [45.587075, -122.402288, "up", "Camas Public Library"],
    [45.591506, -122.40201, "up", "Camas School District"],
    [48.265961, -124.332786, "up", "Cape Flattery School District"],
    [47.081006, -122.054128, "up", "Carbonado School District"],
    [47.602556, -120.654967, "up", "Cascade School District"],
    [47.76087, -122.191349, "up", "Cascadia Community College"],
    [47.514667, -120.476761, "up", "Cashmere School District"],
    [46.281779, -122.917314, "up", "Castle Rock School District"],
    [45.752851, -120.899691, "up", "Centerville School District"],
    [47.651581, -122.699028, "up", "Central Kitsap School District"],
    [46.714716, -122.961749, "up", "Centralia Community College"],
    [46.725975, -122.983141, "up", "Centralia School District"],
    [46.64909, -122.948924, "up", "Chehalis School District"],
    [47.503829, -117.575742, "up", "Cheney School District"],
    [48.277534, -117.704091, "up", "Chewelah Public Library"],
    [48.280847, -117.708481, "up", "Chewelah School District"],
    [47.706248, -122.580523, "up", "Chief Kitsap Academy"],
    [47.211859, -122.354866, "up", "Chief Leschi School District"],
    [48.013442, -122.778194, "up", "Chimacum School District"],
    [45.634682, -122.652496, "up", "Clark College"],
    [46.411157, -117.05812, "up", "Clarkston School District"],
    [47.158989, -122.519556, "up", "Clover Park School District"],
    [47.174874, -122.497828, "up", "Clover Park Technical College"],
    [46.891895, -117.361433, "up", "Colfax School District"],
    [46.030738, -118.386577, "up", "College Place School District"],
    [46.566797, -117.130206, "up", "Colton School District"],
    [46.252334, -119.121811, "up", "Columbia Basin Community College"],
    [46.20035, -119.009915, "up", "Columbia Walla Walla School District"],
    [48.159072, -118.074943, "up", "Columbia/Stevens School District"],
    [48.547241, -117.875682, "up", "Colville School District"],
    [48.532049, -121.757174, "up", "Concrete School District"],
    [48.340215, -122.319458, "up", "Conway School District"],
    [47.611018, -119.285007, "up", "Coulee-Hartline School District"],
    [47.038593, -122.89687, "up", "Council Of Presidents"],
    [48.207376, -122.685908, "up", "Coupeville School District"],
    [48.136023, -123.745679, "up", "Crescent School District"],
    [47.755021, -118.519973, "up", "Creston School District"],
    [48.873944, -118.602107, "up", "Curlew School District"],
    [48.337464, -117.299015, "up", "Cusick School District"],
    [48.247709, -121.601233, "up", "Darrington School District"],
    [47.651473, -118.149993, "up", "Davenport School District"],
    [46.31676, -117.974656, "up", "Dayton School District"],
    [47.954119, -117.462608, "up", "Deer Park School District"],
    [46.470804, -117.599713, "up", "Denny Ashby Memorial Library"],
    [47.248809, -122.162839, "up", "Dieringer School District"],
    [46.141921, -118.149751, "up", "Dixie School District"],
    [47.684665, -117.238363, "East Valley School District-Spokane"],
    ];