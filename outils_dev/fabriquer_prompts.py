"""Fabrique catalogue/prompts.json (0.9.89) : la bibliothèque toute faite de l'atelier de création — pièces de vêtements
(hauts, bas, robes, vestes, chaussures, couvre-chefs, accessoires, matières), tenues complètes, lieux, véhicules, aéronefs et
autres transports, personnages types. Chaque entrée : nom et description en français, description anglaise envoyée aux IA,
image d'exemple facultative (catalogue/exemples/<id>.jpg, fabriquée à part, à la demande).

    python outils_dev/fabriquer_prompts.py      → réécrit catalogue/prompts.json
"""
import json, os

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# rubrique : (genre de la bibliothèque, nom fr, nom en)
RUBRIQUES = {
    "haut": ("piece", "Hauts", "Tops"), "bas": ("piece", "Bas", "Bottoms"), "robe": ("piece", "Robes et ensembles", "Dresses and sets"),
    "veste": ("piece", "Vestes, manteaux, survêtements", "Jackets, coats, outerwear"),
    "chaussures": ("piece", "Chaussures", "Shoes"), "chapeau": ("piece", "Chapeaux et casquettes", "Hats and caps"),
    "accessoire": ("piece", "Accessoires", "Accessories"), "matiere": ("piece", "Matières et finitions", "Materials and finish"),
    "tenue": ("tenue", "Tenues complètes", "Complete outfits"), "lieu": ("lieu", "Lieux", "Places"),
    "vehicule": ("objet", "Véhicules", "Vehicles"), "air": ("objet", "Avions et autres transports", "Aircraft and other transport"),
    "personnage": ("personnage", "Personnages types (inventés)", "Character types (invented)"),
}

# (id, rubrique, pour (f, h, m), nom fr, nom en, description fr, description en)
E = []


def a(rub, pour, ident, fr, en, dfr, den):
    E.append({"id": ident, "rubrique": rub, "pour": pour, "nom": {"fr": fr, "en": en}, "description": {"fr": dfr, "en": den},
              "en": den})


# ---------------------------------------------------------------- hauts
for i, p, fr, en, dfr, den in (
    ("chemise_blanche", "m", "Chemise blanche", "White shirt", "chemise blanche en coton, col classique", "white cotton shirt, classic collar"),
    ("chemise_lin", "m", "Chemise en lin", "Linen shirt", "chemise en lin légère, manches retroussées", "light linen shirt, rolled-up sleeves"),
    ("chemisier_soie", "f", "Chemisier en soie", "Silk blouse", "chemisier en soie fluide, col lavallière", "flowing silk blouse with pussy-bow collar"),
    ("tshirt", "m", "Tee-shirt", "T-shirt", "tee-shirt uni à col rond", "plain crew-neck t-shirt"),
    ("polo", "m", "Polo", "Polo shirt", "polo en piqué de coton", "cotton piqué polo shirt"),
    ("pull_cachemire", "m", "Pull en cachemire", "Cashmere jumper", "pull fin en cachemire, col rond", "fine cashmere crew-neck jumper"),
    ("col_roule", "m", "Col roulé", "Turtleneck", "pull col roulé en laine mérinos", "merino wool turtleneck"),
    ("sweat_capuche", "m", "Sweat à capuche", "Hoodie", "sweat à capuche en molleton", "fleece hoodie"),
    ("debardeur", "m", "Débardeur", "Tank top", "débardeur ajusté", "fitted tank top"),
    ("top_dentelle", "f", "Top en dentelle", "Lace top", "top en dentelle fine", "delicate lace top"),
    ("gilet_costume", "h", "Gilet de costume", "Suit waistcoat", "gilet de costume boutonné sur chemise", "buttoned suit waistcoat over a shirt"),
):
    a("haut", p, i, fr, en, dfr, den)
# ---------------------------------------------------------------- bas
for i, p, fr, en, dfr, den in (
    ("jean_droit", "m", "Jean droit", "Straight jeans", "jean bleu coupe droite", "blue straight-cut jeans"),
    ("jean_slim", "m", "Jean slim", "Slim jeans", "jean slim brut", "raw denim slim jeans"),
    ("chino", "m", "Pantalon chino", "Chinos", "pantalon chino beige", "beige chino trousers"),
    ("pantalon_costume", "m", "Pantalon de costume", "Suit trousers", "pantalon de costume à pli", "pleated suit trousers"),
    ("pantalon_cuir", "m", "Pantalon en cuir", "Leather trousers", "pantalon en cuir noir ajusté", "fitted black leather trousers"),
    ("jupe_crayon", "f", "Jupe crayon", "Pencil skirt", "jupe crayon au genou", "knee-length pencil skirt"),
    ("jupe_plissee", "f", "Jupe plissée", "Pleated skirt", "jupe plissée mi-longue", "midi pleated skirt"),
    ("minijupe", "f", "Minijupe", "Mini skirt", "minijupe trapèze", "A-line mini skirt"),
    ("short", "m", "Short", "Shorts", "short en toile", "canvas shorts"),
    ("legging", "f", "Legging", "Leggings", "legging noir", "black leggings"),
    ("jogging", "m", "Pantalon de jogging", "Joggers", "pantalon de jogging en molleton", "fleece joggers"),
):
    a("bas", p, i, fr, en, dfr, den)
# ---------------------------------------------------------------- robes et ensembles
for i, p, fr, en, dfr, den in (
    ("petite_robe_noire", "f", "Petite robe noire", "Little black dress", "petite robe noire droite au genou", "little black knee-length sheath dress"),
    ("robe_longue", "f", "Robe longue de soirée", "Long evening gown", "longue robe de soirée fluide", "flowing long evening gown"),
    ("robe_cocktail", "f", "Robe de cocktail", "Cocktail dress", "robe de cocktail ajustée", "fitted cocktail dress"),
    ("robe_ete", "f", "Robe d'été", "Summer dress", "robe d'été légère à fleurs", "light floral summer dress"),
    ("robe_chemise", "f", "Robe chemise", "Shirt dress", "robe chemise ceinturée", "belted shirt dress"),
    ("tailleur", "f", "Tailleur", "Skirt or trouser suit", "tailleur veste et pantalon assortis", "matching blazer and trouser suit"),
    ("costume_deux", "h", "Costume deux pièces", "Two-piece suit", "costume deux pièces bleu marine", "navy two-piece suit"),
    ("costume_trois", "h", "Costume trois pièces", "Three-piece suit", "costume trois pièces gris avec gilet", "grey three-piece suit with waistcoat"),
    ("smoking", "h", "Smoking", "Tuxedo", "smoking noir à revers satinés", "black tuxedo with satin lapels"),
    ("combinaison", "f", "Combinaison", "Jumpsuit", "combinaison pantalon élégante", "elegant jumpsuit"),
    ("survetement", "m", "Survêtement", "Tracksuit", "survêtement deux pièces", "two-piece tracksuit"),
):
    a("robe", p, i, fr, en, dfr, den)
# ---------------------------------------------------------------- vestes, manteaux
for i, p, fr, en, dfr, den in (
    ("blazer", "m", "Blazer", "Blazer", "blazer cintré", "tailored blazer"),
    ("perfecto", "m", "Blouson en cuir", "Leather jacket", "blouson en cuir noir style perfecto", "black leather biker jacket"),
    ("blouson_aviateur", "m", "Blouson d'aviateur", "Flight jacket", "blouson d'aviateur en cuir à col en mouton", "leather flight jacket with sheepskin collar"),
    ("trench", "m", "Trench", "Trench coat", "trench beige ceinturé", "belted beige trench coat"),
    ("manteau_laine", "m", "Manteau en laine", "Wool coat", "long manteau en laine camel", "long camel wool coat"),
    ("manteau_cachemire", "m", "Manteau en cachemire", "Cashmere coat", "manteau long en cachemire gris", "long grey cashmere coat"),
    ("doudoune", "m", "Doudoune", "Puffer jacket", "doudoune matelassée", "quilted puffer jacket"),
    ("veste_jean", "m", "Veste en jean", "Denim jacket", "veste en jean délavé", "washed denim jacket"),
    ("parka", "m", "Parka", "Parka", "parka kaki à capuche", "khaki hooded parka"),
    ("fourrure_synth", "f", "Manteau fausse fourrure", "Faux fur coat", "manteau en fausse fourrure", "faux fur coat"),
    ("cape", "f", "Cape", "Cape", "cape en laine", "wool cape"),
):
    a("veste", p, i, fr, en, dfr, den)
# ---------------------------------------------------------------- chaussures
for i, p, fr, en, dfr, den in (
    ("baskets_blanches", "m", "Baskets blanches", "White sneakers", "baskets blanches en cuir", "white leather sneakers"),
    ("baskets_course", "m", "Chaussures de course", "Running shoes", "chaussures de course légères", "light running shoes"),
    ("mocassins", "m", "Mocassins", "Loafers", "mocassins en cuir", "leather loafers"),
    ("richelieus", "h", "Richelieus", "Oxford shoes", "richelieus en cuir noir ciré", "polished black leather oxford shoes"),
    ("derbies", "h", "Derbies", "Derby shoes", "derbies en cuir marron", "brown leather derby shoes"),
    ("bottines", "m", "Bottines", "Ankle boots", "bottines en cuir", "leather ankle boots"),
    ("bottes_hautes", "f", "Bottes hautes", "Knee-high boots", "bottes hautes en cuir au genou", "knee-high leather boots"),
    ("santiags", "m", "Santiags", "Cowboy boots", "santiags en cuir", "leather cowboy boots"),
    ("boots_chantier", "m", "Chaussures de sécurité", "Work boots", "chaussures montantes de travail", "high work boots"),
    ("escarpins_hauts", "f", "Escarpins talons hauts", "High-heeled pumps", "escarpins à talons hauts de 10 cm", "4-inch high-heeled pumps"),
    ("escarpins_moyens", "f", "Escarpins talons moyens", "Mid-heel pumps", "escarpins à talons moyens de 6 cm", "mid-heel pumps"),
    ("talons_bas", "f", "Petits talons", "Kitten heels", "chaussures à petits talons", "kitten heels"),
    ("ballerines", "f", "Ballerines", "Ballet flats", "ballerines plates", "flat ballet shoes"),
    ("sandales", "m", "Sandales", "Sandals", "sandales en cuir", "leather sandals"),
    ("sandales_talons", "f", "Sandales à talons", "Heeled sandals", "sandales fines à talons", "strappy heeled sandals"),
    ("espadrilles", "m", "Espadrilles", "Espadrilles", "espadrilles en toile", "canvas espadrilles"),
    ("vernis", "h", "Chaussures vernies", "Patent shoes", "chaussures vernies noires", "black patent shoes"),
):
    a("chaussures", p, i, fr, en, dfr, den)
# ---------------------------------------------------------------- couvre-chefs
for i, p, fr, en, dfr, den in (
    ("casquette", "m", "Casquette", "Baseball cap", "casquette de baseball", "baseball cap"),
    ("casquette_gavroche", "m", "Casquette gavroche", "Newsboy cap", "casquette gavroche en tweed", "tweed newsboy cap"),
    ("borsalino", "h", "Borsalino", "Fedora", "chapeau feutre type borsalino", "felt fedora hat"),
    ("texan", "m", "Chapeau de cow-boy", "Cowboy hat", "chapeau texan en feutre", "felt cowboy hat"),
    ("panama", "m", "Panama", "Panama hat", "chapeau panama en paille", "straw panama hat"),
    ("bonnet", "m", "Bonnet", "Beanie", "bonnet en laine", "wool beanie"),
    ("beret", "m", "Béret", "Beret", "béret en laine", "wool beret"),
    ("capeline", "f", "Capeline", "Wide-brimmed hat", "capeline à large bord", "wide-brimmed sun hat"),
    ("chapeau_haut", "h", "Haut-de-forme", "Top hat", "chapeau haut-de-forme noir", "black top hat"),
    ("casquette_pilote", "m", "Casquette de pilote", "Pilot cap", "casquette d'uniforme de pilote", "pilot uniform cap"),
):
    a("chapeau", p, i, fr, en, dfr, den)
# ---------------------------------------------------------------- accessoires
for i, p, fr, en, dfr, den in (
    ("lunettes_soleil", "m", "Lunettes de soleil", "Sunglasses", "lunettes de soleil aviateur", "aviator sunglasses"),
    ("lunettes_vue", "m", "Lunettes de vue", "Glasses", "lunettes de vue à monture fine", "thin-framed glasses"),
    ("cravate", "h", "Cravate", "Tie", "cravate en soie unie", "plain silk tie"),
    ("noeud_pap", "h", "Nœud papillon", "Bow tie", "nœud papillon noir", "black bow tie"),
    ("echarpe", "m", "Écharpe", "Scarf", "écharpe en laine", "wool scarf"),
    ("foulard", "f", "Foulard", "Silk scarf", "foulard en soie noué au cou", "silk scarf tied at the neck"),
    ("sac_main", "f", "Sac à main", "Handbag", "sac à main en cuir", "leather handbag"),
    ("pochette", "f", "Pochette", "Clutch", "pochette de soirée", "evening clutch"),
    ("montre", "m", "Montre", "Watch", "montre classique à bracelet cuir", "classic leather-strap watch"),
    ("collier_perles", "f", "Collier de perles", "Pearl necklace", "collier de perles", "pearl necklace"),
    ("gants_cuir", "m", "Gants en cuir", "Leather gloves", "gants en cuir fins", "thin leather gloves"),
    ("ceinture", "m", "Ceinture", "Belt", "ceinture en cuir", "leather belt"),
):
    a("accessoire", p, i, fr, en, dfr, den)
# ---------------------------------------------------------------- matières
for i, fr, en, dfr, den in (
    ("luxe", "Luxe", "Luxury", "finitions de luxe, coupe impeccable", "luxury finish, impeccable tailoring"),
    ("cachemire", "Cachemire", "Cashmere", "en cachemire", "made of cashmere"),
    ("cuir", "Cuir", "Leather", "en cuir", "made of leather"),
    ("daim", "Daim", "Suede", "en daim", "made of suede"),
    ("laine", "Laine", "Wool", "en laine", "made of wool"),
    ("lin", "Lin", "Linen", "en lin", "made of linen"),
    ("soie", "Soie", "Silk", "en soie", "made of silk"),
    ("velours", "Velours", "Velvet", "en velours", "made of velvet"),
    ("denim", "Jean", "Denim", "en jean", "made of denim"),
    ("tweed", "Tweed", "Tweed", "en tweed", "made of tweed"),
    ("satin", "Satin", "Satin", "en satin", "made of satin"),
    ("coton", "Coton", "Cotton", "en coton", "made of cotton"),
    ("paillettes", "Paillettes", "Sequins", "à paillettes", "with sequins"),
):
    a("matiere", "m", i, fr, en, dfr, den)
# ---------------------------------------------------------------- tenues complètes
for i, p, fr, en, dfr, den in (
    ("t_tailleur_sombre", "f", "Tailleur sombre", "Dark trouser suit", "tailleur veste et pantalon bleu marine, chemisier blanc, escarpins noirs",
     "navy blue trouser suit, white blouse, black pumps"),
    ("t_costume_cravate", "h", "Costume cravate", "Suit and tie", "costume gris anthracite, chemise blanche, cravate unie, richelieus noirs",
     "charcoal grey suit, white shirt, plain tie, black oxford shoes"),
    ("t_chic_decontracte", "h", "Chic décontracté", "Smart casual", "blazer bleu, chemise blanche ouverte, chino beige, mocassins",
     "navy blazer, open white shirt, beige chinos, loafers"),
    ("t_robe_soiree", "f", "Robe de soirée", "Evening gown", "longue robe de soirée noire, bijoux discrets, sandales à talons",
     "long black evening gown, discreet jewellery, heeled sandals"),
    ("t_smoking", "h", "Smoking", "Tuxedo", "smoking noir, chemise blanche, nœud papillon, chaussures vernies",
     "black tuxedo, white shirt, bow tie, patent shoes"),
    ("t_hiver_ville", "m", "Hiver en ville", "Winter in town", "manteau en laine camel, écharpe, pull col roulé, bottines",
     "camel wool coat, scarf, turtleneck, ankle boots"),
    ("t_jean_baskets", "m", "Jean et baskets", "Jeans and sneakers", "jean bleu, tee-shirt blanc, baskets blanches",
     "blue jeans, white t-shirt, white sneakers"),
    ("t_sport", "m", "Sport", "Sport", "tenue de sport technique, chaussures de course", "technical sportswear, running shoes"),
    ("t_plage", "m", "Plage", "Beach", "chemise de lin ouverte, short, espadrilles, lunettes de soleil, panama",
     "open linen shirt, shorts, espadrilles, sunglasses, panama hat"),
    ("t_western", "m", "Western", "Western", "chemise en jean, jean, santiags, chapeau de cow-boy", "denim shirt, jeans, cowboy boots, cowboy hat"),
    ("t_pilote_ligne", "m", "Pilote de ligne", "Airline pilot", "uniforme de pilote bleu marine à galons dorés, chemise blanche, cravate, casquette",
     "navy airline pilot uniform with gold stripes, white shirt, tie, pilot cap"),
    ("t_pilote_prive", "m", "Pilote privé", "Private pilot", "blouson d'aviateur en cuir, chemise, chino, lunettes aviateur, casque audio au cou",
     "leather flight jacket, shirt, chinos, aviator sunglasses, headset around the neck"),
    ("t_medecin", "m", "Médecin", "Doctor", "blouse blanche, stéthoscope, tenue de ville", "white coat, stethoscope, city clothes"),
    ("t_pharmacien", "m", "Pharmacien", "Pharmacist", "blouse blanche de pharmacie, badge, chemise", "white pharmacy coat, name badge, shirt"),
    ("t_serveur", "m", "Serveur", "Waiter", "chemise blanche, gilet noir, long tablier noir, nœud papillon", "white shirt, black waistcoat, long black apron, bow tie"),
    ("t_chauffeur", "m", "Chauffeur", "Chauffeur", "costume noir, casquette de chauffeur, gants", "black suit, chauffeur cap, gloves"),
    ("t_cuisinier", "m", "Cuisinier", "Chef", "veste de cuisinier blanche, tablier, toque", "white chef jacket, apron, chef hat"),
    ("t_hotesse", "f", "Hôtesse de l'air", "Flight attendant", "uniforme d'hôtesse, foulard noué, escarpins moyens",
     "flight attendant uniform, tied scarf, mid-heel pumps"),
    ("t_ouvrier", "m", "Ouvrier", "Worker", "combinaison de travail, gilet fluorescent, chaussures de sécurité",
     "work overalls, high-visibility vest, safety boots"),
):
    a("tenue", p, i, fr, en, dfr, den)
# ---------------------------------------------------------------- lieux
for i, fr, en, dfr, den in (
    ("piscine", "Piscine", "Swimming pool", "piscine extérieure, eau turquoise, transats, plein soleil", "outdoor swimming pool, turquoise water, sun loungers, bright sun"),
    ("bord_mer", "Bord de mer", "Seaside", "promenade en bord de mer, sable clair, mer calme", "seaside promenade, light sand, calm sea"),
    ("plage", "Plage", "Beach", "plage de sable fin, vagues douces", "fine sandy beach, gentle waves"),
    ("port", "Port", "Harbour", "petit port avec bateaux de pêche et quais en pierre", "small harbour with fishing boats and stone quays"),
    ("montagne", "Montagne", "Mountains", "sommets enneigés, prairie d'alpage", "snowy peaks, alpine meadow"),
    ("foret", "Forêt", "Forest", "forêt de grands arbres, lumière filtrée", "forest of tall trees, filtered light"),
    ("campagne", "Campagne", "Countryside", "champs et collines, chemin de terre", "fields and hills, dirt road"),
    ("jardin", "Jardin", "Garden", "jardin fleuri avec pelouse et massifs", "flowering garden with lawn and flower beds"),
    ("terrasse", "Terrasse", "Terrace", "terrasse ensoleillée avec plantes en pots et vue", "sunny terrace with potted plants and a view"),
    ("maison_salon", "Salon", "Living room", "salon chaleureux, canapé, bibliothèque, lumière douce", "warm living room, sofa, bookshelves, soft light"),
    ("maison_cuisine", "Cuisine", "Kitchen", "cuisine claire et moderne, plan de travail", "bright modern kitchen, worktop"),
    ("maison_chambre", "Chambre", "Bedroom", "chambre calme, lit, lumière du matin", "quiet bedroom, bed, morning light"),
    ("villa", "Villa", "Villa", "villa méditerranéenne avec piscine et oliviers", "Mediterranean villa with pool and olive trees"),
    ("bureau", "Bureau de direction", "Executive office", "grand bureau de direction, baie vitrée, bois et cuir", "large executive office, picture window, wood and leather"),
    ("open_space", "Open space", "Open-plan office", "plateau de bureaux moderne, écrans", "modern open-plan office, screens"),
    ("salle_reunion", "Salle de réunion", "Meeting room", "salle de réunion, grande table, écran", "meeting room, long table, screen"),
    ("restaurant", "Restaurant", "Restaurant", "salle de restaurant élégante, tables dressées", "elegant restaurant dining room, set tables"),
    ("bar", "Bar", "Bar", "bar feutré, comptoir en bois, lumière tamisée", "cosy bar, wooden counter, dim light"),
    ("hotel", "Hall d'hôtel", "Hotel lobby", "hall d'hôtel de luxe, marbre, lustres", "luxury hotel lobby, marble, chandeliers"),
    ("escalier_marbre", "Escalier d'honneur", "Grand staircase", "grand escalier en marbre, boiseries", "grand marble staircase, wood panelling"),
    ("rue_nuit", "Rue de ville la nuit", "City street at night", "rue de ville la nuit, vitrines éclairées, pavés mouillés", "city street at night, lit shop windows, wet cobblestones"),
    ("place_village", "Place de village", "Village square", "place de village avec fontaine et platanes", "village square with fountain and plane trees"),
    ("parc", "Parc", "Park", "parc urbain, allées, bancs", "city park, paths, benches"),
    ("aeroport", "Aéroport", "Airport", "terminal d'aéroport lumineux, grandes baies", "bright airport terminal, large windows"),
    ("aerodrome", "Aérodrome", "Airfield", "petit aérodrome, piste en herbe, manche à air", "small airfield, grass runway, windsock"),
    ("hangar", "Hangar", "Hangar", "hangar d'aviation avec avion léger", "aircraft hangar with a light aircraft"),
    ("gare", "Gare", "Railway station", "hall de gare avec verrière", "station hall with glass roof"),
    ("cathedrale", "Cathédrale", "Cathedral", "cathédrale gothique, vitraux, voûtes", "gothic cathedral, stained glass, vaults"),
    ("chateau", "Château", "Castle", "château avec jardins à la française", "château with formal French gardens"),
    ("tour_eiffel", "Tour Eiffel", "Eiffel Tower", "vue sur la tour Eiffel à Paris", "view of the Eiffel Tower in Paris"),
    ("colisee", "Colisée", "Colosseum", "le Colisée à Rome", "the Colosseum in Rome"),
    ("pont_ville", "Pont en ville", "City bridge", "pont de pierre sur un fleuve en ville", "stone bridge over a river in a city"),
    ("pharmacie", "Pharmacie", "Pharmacy", "officine moderne, comptoir, rayonnages lumineux", "modern pharmacy, counter, bright shelves"),
):
    a("lieu", "m", i, fr, en, dfr, den)
# ---------------------------------------------------------------- véhicules
for i, fr, en, dfr, den in (
    ("limousine", "Limousine", "Limousine", "longue limousine noire, carrosserie brillante", "long black limousine, glossy bodywork"),
    ("sportive", "Voiture de sport", "Sports car", "voiture de sport rouge, basse et profilée", "low sleek red sports car"),
    ("citadine", "Citadine", "City car", "petite citadine moderne", "small modern city car"),
    ("berline", "Berline", "Saloon", "grande berline sombre", "large dark saloon car"),
    ("suv", "SUV", "SUV", "SUV haut et robuste", "tall rugged SUV"),
    ("cabriolet", "Cabriolet", "Convertible", "cabriolet décapoté", "convertible with the top down"),
    ("ancienne", "Voiture ancienne", "Classic car", "voiture de collection des années 1960", "1960s classic car"),
    ("pickup", "Pick-up", "Pick-up truck", "pick-up américain", "American pick-up truck"),
    ("taxi", "Taxi", "Taxi", "taxi avec lumineux sur le toit", "taxi with roof sign"),
    ("van", "Fourgon", "Van", "fourgon utilitaire blanc", "white delivery van"),
    ("moto", "Moto", "Motorbike", "moto routière", "road motorbike"),
    ("scooter", "Scooter", "Scooter", "scooter urbain", "city scooter"),
    ("velo", "Vélo", "Bicycle", "vélo de ville", "city bicycle"),
    ("bus", "Autobus", "Bus", "autobus de ville", "city bus"),
    ("camion", "Camion", "Lorry", "camion semi-remorque", "articulated lorry"),
):
    a("vehicule", "m", i, fr, en, dfr, den)
# ---------------------------------------------------------------- aéronefs et autres transports
for i, fr, en, dfr, den in (
    ("avion_ligne", "Avion de ligne", "Airliner", "avion de ligne biréacteur", "twin-engine airliner"),
    ("avion_leger", "Avion léger", "Light aircraft", "avion léger monomoteur à aile haute", "high-wing single-engine light aircraft"),
    ("jet_prive", "Jet privé", "Private jet", "jet privé d'affaires", "private business jet"),
    ("helicoptere", "Hélicoptère", "Helicopter", "hélicoptère léger", "light helicopter"),
    ("planeur", "Planeur", "Glider", "planeur blanc aux longues ailes", "white glider with long wings"),
    ("ulm", "ULM", "Microlight", "ULM pendulaire", "weight-shift microlight"),
    ("montgolfiere", "Montgolfière", "Hot-air balloon", "montgolfière colorée", "colourful hot-air balloon"),
    ("hydravion", "Hydravion", "Seaplane", "hydravion sur flotteurs", "seaplane on floats"),
    ("voilier", "Voilier", "Sailing boat", "voilier de croisière", "cruising sailing boat"),
    ("yacht", "Yacht", "Yacht", "yacht de luxe", "luxury yacht"),
    ("train", "Train", "Train", "train à grande vitesse", "high-speed train"),
):
    a("air", "m", i, fr, en, dfr, den)
# ---------------------------------------------------------------- personnages types (toujours inventés)
for i, p, fr, en, dfr, den in (
    ("directrice", "f", "Directrice", "Director (woman)", "femme d'une cinquantaine d'années, cheveux courts gris, regard assuré, allure élégante",
     "woman in her fifties, short grey hair, confident look, elegant bearing"),
    ("directeur", "h", "Directeur", "Director (man)", "homme d'une cinquantaine d'années, tempes grisonnantes, allure posée",
     "man in his fifties, greying temples, composed bearing"),
    ("secretaire", "f", "Assistante", "Assistant (woman)", "jeune femme d'une trentaine d'années, cheveux bruns en chignon, sourire", "woman in her thirties, dark hair in a bun, smiling"),
    ("assistant", "h", "Assistant", "Assistant (man)", "jeune homme d'une trentaine d'années, cheveux courts, lunettes", "man in his thirties, short hair, glasses"),
    ("chef_cuisine", "m", "Chef cuisinier", "Chef", "cuisinier d'une quarantaine d'années, barbe courte", "cook in his forties, short beard"),
    ("serveur", "m", "Serveur", "Waiter", "serveur d'une vingtaine d'années, cheveux courts", "waiter in his twenties, short hair"),
    ("medecin", "m", "Médecin", "Doctor", "médecin d'une quarantaine d'années, air rassurant", "doctor in their forties, reassuring look"),
    ("pilote", "m", "Pilote", "Pilot", "pilote d'une quarantaine d'années, hâlé, regard concentré", "pilot in their forties, tanned, focused look"),
    ("enfant", "m", "Enfant", "Child", "enfant de huit ans, joyeux", "eight-year-old child, cheerful"),
    ("adolescent", "m", "Adolescent", "Teenager", "adolescent de quinze ans, décontracté", "fifteen-year-old teenager, relaxed"),
    ("grand_mere", "f", "Grand-mère", "Grandmother", "femme de soixante-quinze ans, cheveux blancs, sourire doux", "seventy-five-year-old woman, white hair, gentle smile"),
    ("grand_pere", "h", "Grand-père", "Grandfather", "homme de soixante-quinze ans, moustache blanche", "seventy-five-year-old man, white moustache"),
    ("sportif", "m", "Sportif", "Athlete", "sportif d'une trentaine d'années, silhouette athlétique", "athlete in their thirties, athletic build"),
    ("touriste", "m", "Touriste", "Tourist", "touriste avec sac à dos et appareil photo", "tourist with backpack and camera"),
):
    a("personnage", p, i, fr, en, dfr, den)


def main():
    cat = {"format": 1, "note": "Bibliothèque toute faite de l'atelier de création (prompts). Fabriqué par outils_dev/fabriquer_prompts.py ; "
                                "images d'exemple facultatives dans catalogue/exemples/<id>.jpg.",
           "rubriques": {k: {"genre": g, "nom": {"fr": fr, "en": en}} for k, (g, fr, en) in RUBRIQUES.items()},
           "entrees": E}
    ids = [e["id"] for e in E]
    assert len(ids) == len(set(ids)), "identifiants en double"
    with open(os.path.join(RACINE, "catalogue", "prompts.json"), "w", encoding="utf-8") as f:
        json.dump(cat, f, ensure_ascii=False, indent=1)
        f.write("\n")
    print(len(E), "entrées")


if __name__ == "__main__":
    main()
