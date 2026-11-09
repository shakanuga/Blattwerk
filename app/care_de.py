"""Blattwerk-Grunddaten: deutsche Pflegehinweise für häufige Garten-, Kübel- und Zimmerpflanzen.

Allgemeine Gärtnerregeln, keine Gewähr – jede Angabe lässt sich in der App überschreiben.
Schlüssel: botanischer Name in Kleinbuchstaben ("gattung art") oder nur die Gattung als Rückfall.

Felder:
  light        Standort
  water        Gieß-Hinweis als Satz
  interval     Gießen im Sommer etwa alle … Tage
  fertilize    Düngen
  min_temp     verträgt kurzzeitig bis … °C (Frostgrenze; positive Werte = muss frostfrei/warm stehen)
  winter       Überwinterung
  toxic        (Menschen, Haustiere) – True/False/None
  flowering, origin, pruning, soil, indoor (Zimmerpflanze geeignet)
"""

T, F, N = True, False, None

CARE = {
    # ------------------------------------------------------------- Kübelpflanzen
    "nerium oleander": dict(
        light="Vollsonnig und warm, gern vor einer Hauswand",
        water="Im Sommer reichlich gießen, Wasser im Untersetzer schadet nicht; im Winter sparsam.",
        interval=2, fertilize="Mai bis August wöchentlich", min_temp=-5,
        winter="Verträgt leichten Frost bis etwa −5 °C. Danach hell und kühl bei 5–10 °C überwintern, wenig gießen, nicht düngen.",
        toxic=(T, T), flowering="Juni bis September", origin="Mittelmeerraum",
        pruning="Im Frühjahr nur vorsichtig auslichten – Blüten erscheinen an den Triebspitzen"),
    "lantana camara": dict(
        light="Hell, sonnig bis halbschattig", water="Gut feucht halten, Erde nicht austrocknen lassen.",
        interval=2, fertilize="Mai bis September wöchentlich", min_temp=2,
        winter="Vor dem ersten Frost reinholen, hell bei 5–10 °C überwintern, wenig gießen. Im Frühjahr kräftig zurückschneiden.",
        toxic=(T, T), flowering="Mai bis zum Frost", origin="Süd- und Mittelamerika"),
    "olea europaea": dict(
        light="Vollsonnig", water="Mäßig gießen, Erde zwischendurch antrocknen lassen, keine Staunässe.",
        interval=5, fertilize="April bis September alle 2–3 Wochen", min_temp=-8,
        winter="Verträgt kurzzeitig −5 bis −10 °C. Bei Dauerfrost hell und kühl (5–10 °C) überwintern oder Krone und Topf gut einpacken.",
        toxic=(F, F), origin="Mittelmeerraum"),
    "citrus": dict(
        light="Vollsonnig, im Sommer draußen", water="Gleichmäßig feucht halten, kalkarmes Wasser, keine Staunässe.",
        interval=3, fertilize="März bis Oktober wöchentlich mit Zitrusdünger", min_temp=0,
        winter="Hell und kühl bei 5–12 °C überwintern, wenig gießen. Warm (über 15 °C) nur mit sehr viel Licht.",
        toxic=(F, T), origin="Südostasien"),
    "bougainvillea": dict(
        light="Vollsonnig und warm", water="Mäßig gießen, Erde zwischendurch abtrocknen lassen.",
        interval=4, fertilize="April bis August wöchentlich", min_temp=5,
        winter="Hell bei 8–12 °C überwintern, nur sehr wenig gießen; Laubabwurf ist normal.",
        toxic=(F, F), flowering="Mai bis Oktober", origin="Südamerika"),
    "hibiscus rosa-sinensis": dict(
        light="Hell bis sonnig, keine pralle Mittagssonne", water="Gleichmäßig feucht halten.",
        interval=2, fertilize="März bis September wöchentlich", min_temp=10,
        winter="Nicht frosthart. Hell bei 12–18 °C überwintern, etwas weniger gießen.",
        toxic=(F, F), flowering="März bis Oktober", origin="Asien", indoor=T),
    "hibiscus syriacus": dict(
        light="Sonnig", water="Mäßig feucht halten, verträgt kurze Trockenheit.",
        interval=4, fertilize="Frühjahr Kompost oder Langzeitdünger", min_temp=-20,
        winter="Winterhart. Junge Pflanzen und Kübel leicht schützen.",
        toxic=(F, F), flowering="Juli bis September", pruning="Im Frühjahr", origin="Asien"),
    "pelargonium": dict(
        light="Sonnig", water="Mäßig gießen, Erde antrocknen lassen, keine Staunässe.",
        interval=2, fertilize="Mai bis August wöchentlich", min_temp=2,
        winter="Vor Frost reinholen, hell und kühl bei 5–10 °C überwintern, kaum gießen. Im Februar/März zurückschneiden.",
        toxic=(F, T), flowering="Mai bis Oktober", origin="Südafrika"),
    "petunia": dict(
        light="Vollsonnig", water="Im Sommer täglich gießen, nicht austrocknen lassen.",
        interval=1, fertilize="Wöchentlich (Starkzehrer)", min_temp=5,
        winter="Meist einjährig kultiviert, Überwintern lohnt selten.",
        toxic=(F, F), flowering="Mai bis Oktober", origin="Südamerika"),
    "fuchsia": dict(
        light="Halbschattig, keine Mittagssonne", water="Gleichmäßig feucht halten.",
        interval=2, fertilize="April bis August wöchentlich", min_temp=0,
        winter="Vor stärkerem Frost reinholen, hell oder dunkel bei 5–10 °C überwintern, wenig gießen.",
        toxic=(F, F), flowering="Mai bis Oktober", origin="Mittel- und Südamerika"),
    "agapanthus": dict(
        light="Vollsonnig", water="Im Sommer reichlich, im Winter fast trocken.",
        interval=3, fertilize="April bis Juli alle 2 Wochen", min_temp=-5,
        winter="Hell und kühl bei 5–10 °C überwintern, kaum gießen. Enger Topf fördert die Blüte.",
        toxic=(T, T), flowering="Juli bis September", origin="Südafrika"),
    "mandevilla": dict(
        light="Sonnig und warm", water="Mäßig gießen, Erde antrocknen lassen.",
        interval=3, fertilize="Mai bis August wöchentlich", min_temp=8,
        winter="Hell bei 10–15 °C überwintern, wenig gießen.",
        toxic=(T, T), flowering="Mai bis Oktober", origin="Südamerika"),
    "brugmansia": dict(
        light="Sonnig bis halbschattig, windgeschützt", water="Sehr durstig – im Sommer täglich, an heißen Tagen zweimal gießen.",
        interval=1, fertilize="Mai bis August zweimal wöchentlich", min_temp=5,
        winter="Vor Frost reinholen, hell bei 10–15 °C oder dunkel bei 5–8 °C (dann ohne Laub) überwintern.",
        toxic=(T, T), flowering="Juni bis Oktober", origin="Südamerika"),
    "callistemon": dict(
        light="Vollsonnig", water="Gleichmäßig feucht, kalkarmes Wasser.",
        interval=3, fertilize="April bis August alle 2 Wochen", min_temp=-3,
        winter="Hell und kühl bei 5–10 °C überwintern.", toxic=(F, F), origin="Australien"),
    "laurus nobilis": dict(
        light="Sonnig bis halbschattig", water="Mäßig gießen, keine Staunässe.",
        interval=4, fertilize="April bis August alle 2–3 Wochen", min_temp=-5,
        winter="Bis etwa −5 °C robust; im Kübel hell und kühl überwintern oder gut einpacken.",
        toxic=(F, F), origin="Mittelmeerraum"),
    "ficus carica": dict(
        light="Vollsonnig, geschützt", water="Mäßig, an heißen Tagen mehr.",
        interval=3, fertilize="April bis Juli alle 2–3 Wochen", min_temp=-12,
        winter="Ausgepflanzt an geschützter Stelle bis etwa −12 °C; Kübel frostfrei und dunkel bei 0–5 °C überwintern.",
        toxic=(F, T), origin="Mittelmeerraum, Vorderasien"),
    "camellia japonica": dict(
        light="Halbschattig, keine Mittagssonne", water="Gleichmäßig feucht mit kalkarmem Wasser, Ballen nie austrocknen lassen.",
        interval=3, fertilize="März bis Juli alle 2 Wochen (Rhododendrondünger)", min_temp=-10,
        winter="Im Kübel hell und kühl bei 5–10 °C; ausgepflanzt geschützt mit Wurzelschutz.",
        toxic=(F, F), flowering="Februar bis April", origin="Ostasien"),
    "phoenix canariensis": dict(
        light="Sonnig", water="Mäßig, Erde zwischendurch antrocknen lassen.",
        interval=4, fertilize="April bis August alle 2 Wochen", min_temp=-5,
        winter="Hell und kühl bei 5–10 °C überwintern.", toxic=(F, F), origin="Kanaren"),
    "trachycarpus fortunei": dict(
        light="Sonnig bis halbschattig", water="Mäßig feucht, keine Staunässe.",
        interval=4, fertilize="April bis August monatlich", min_temp=-15,
        winter="Eine der winterhärtesten Palmen. Bei starkem Frost Herz und Topf schützen.", toxic=(F, F), origin="China"),
    "cycas revoluta": dict(
        light="Hell bis sonnig", water="Sparsam, Erde zwischendurch abtrocknen lassen.",
        interval=7, fertilize="Mai bis August monatlich", min_temp=-5,
        winter="Hell bei 5–15 °C überwintern, sehr wenig gießen.", toxic=(T, T), origin="Japan"),
    "solanum lycopersicum": dict(
        light="Vollsonnig, regengeschützt", water="Gleichmäßig gießen, nur von unten – Blätter trocken halten.",
        interval=1, fertilize="Ab Fruchtansatz wöchentlich Tomatendünger", min_temp=10,
        winter="Einjährig.", toxic=(F, T), origin="Südamerika"),
    "capsicum": dict(
        light="Vollsonnig und warm", water="Gleichmäßig feucht, keine Staunässe.",
        interval=2, fertilize="Ab Blüte wöchentlich", min_temp=10,
        winter="Meist einjährig; hell bei 10–15 °C überwintern ist möglich.", toxic=(F, F), origin="Mittel- und Südamerika"),
    "dahlia": dict(
        light="Sonnig", water="Gleichmäßig feucht, an heißen Tagen täglich.",
        interval=2, fertilize="Juni bis August alle 2 Wochen", min_temp=0,
        winter="Knollen nach dem ersten Frost ausgraben, trocknen und frostfrei bei 5–8 °C lagern.",
        toxic=(F, F), flowering="Juli bis zum Frost", origin="Mexiko"),
    "canna": dict(
        light="Vollsonnig und warm", water="Reichlich gießen.", interval=1, fertilize="Wöchentlich", min_temp=0,
        winter="Rhizome nach dem ersten Frost ausgraben und frostfrei bei 5–10 °C lagern.",
        toxic=(F, F), flowering="Juli bis Oktober", origin="Mittel- und Südamerika"),
    "begonia": dict(
        light="Halbschattig bis hell, keine pralle Sonne", water="Feucht halten, aber keine Staunässe; nicht über die Blätter gießen.",
        interval=2, fertilize="Alle 2 Wochen", min_temp=10,
        winter="Nicht frosthart. Knollenbegonien trocken bei 5–10 °C lagern, Zimmerbegonien hell bei Zimmertemperatur.",
        toxic=(F, T), origin="Tropen"),
    "impatiens": dict(
        light="Halbschattig bis schattig", water="Stets feucht halten.", interval=1, fertilize="Alle 1–2 Wochen", min_temp=5,
        winter="Meist einjährig.", toxic=(F, F), flowering="Mai bis Oktober"),

    # -------------------------------------------------------- Garten / Kräuter
    "hydrangea macrophylla": dict(
        light="Halbschattig", water="Viel gießen, Erde stets feucht halten – am besten kalkarmes Regenwasser.",
        interval=2, fertilize="März bis August alle 2 Wochen (Hortensiendünger)", min_temp=-15,
        winter="Winterhart, aber Blütenknospen sind frostempfindlich: bei Spätfrost abdecken, Kübel schützen.",
        toxic=(T, T), flowering="Juni bis September", origin="Japan",
        pruning="Im Frühjahr nur Verblühtes bis zum ersten kräftigen Knospenpaar entfernen"),
    "hydrangea paniculata": dict(
        light="Sonnig bis halbschattig", water="Gleichmäßig feucht.", interval=3, fertilize="Frühjahr und Juni",
        min_temp=-25, winter="Sehr winterhart.", toxic=(T, T), flowering="Juli bis Oktober",
        pruning="Im Spätwinter kräftig zurückschneiden – blüht am neuen Holz"),
    "lavandula": dict(
        light="Vollsonnig", water="Sparsam gießen – verträgt Trockenheit, keine Staunässe.",
        interval=7, fertilize="Kaum – höchstens etwas Kompost im Frühjahr", min_temp=-20,
        winter="Winterhart. Im Kübel vor Winternässe schützen.", toxic=(F, F),
        flowering="Juni bis August", origin="Mittelmeerraum",
        pruning="Nach der Blüte und im Frühjahr um etwa ein Drittel, nicht ins alte Holz"),
    "salvia rosmarinus": dict(
        light="Vollsonnig", water="Sparsam, zwischendurch abtrocknen lassen.", interval=5,
        fertilize="Kaum", min_temp=-10,
        winter="Bedingt winterhart. Im Kübel hell und kühl bei 2–10 °C überwintern, ausgepflanzt geschützt mit Vlies.",
        toxic=(F, F), origin="Mittelmeerraum"),
    "rosmarinus officinalis": "salvia rosmarinus",
    "salvia officinalis": dict(
        light="Vollsonnig", water="Sparsam gießen.", interval=5, fertilize="Kaum", min_temp=-15,
        winter="Winterhart; im Kübel vor Nässe schützen.", toxic=(F, F), origin="Mittelmeerraum",
        pruning="Im Frühjahr zurückschneiden"),
    "thymus": dict(
        light="Vollsonnig", water="Sparsam gießen.", interval=6, fertilize="Nicht nötig", min_temp=-15,
        winter="Winterhart.", toxic=(F, F), origin="Mittelmeerraum"),
    "ocimum basilicum": dict(
        light="Sonnig und warm", water="Gleichmäßig feucht, am besten morgens und von unten.",
        interval=1, fertilize="Alle 2 Wochen schwach", min_temp=10,
        winter="Nicht winterhart, meist einjährig.", toxic=(F, F)),
    "mentha": dict(
        light="Sonnig bis halbschattig", water="Feucht halten.", interval=2, fertilize="Frühjahr etwas Kompost",
        min_temp=-20, winter="Winterhart.", toxic=(F, F), pruning="Regelmäßig ernten"),
    "petroselinum crispum": dict(
        light="Halbschattig", water="Gleichmäßig feucht.", interval=2, fertilize="Monatlich schwach", min_temp=-10,
        winter="Zweijährig, meist winterhart.", toxic=(F, F)),
    "allium schoenoprasum": dict(
        light="Sonnig bis halbschattig", water="Feucht halten.", interval=2, fertilize="Monatlich schwach",
        min_temp=-25, winter="Winterhart, zieht im Winter ein.", toxic=(F, T)),
    "rosa": dict(
        light="Sonnig, luftig", water="Selten, dann durchdringend gießen; Blätter trocken halten.",
        interval=4, fertilize="Ende März und Ende Juni Rosendünger", min_temp=-20,
        winter="Winterhart. Veredelungsstelle anhäufeln, Kübel einpacken.", toxic=(F, F),
        flowering="Juni bis September", pruning="Im Frühjahr zur Forsythienblüte"),
    "buxus sempervirens": dict(
        light="Sonnig bis halbschattig", water="Mäßig feucht.", interval=4, fertilize="April bis Juli monatlich",
        min_temp=-20, winter="Winterhart; an frostfreien Tagen gießen.", toxic=(T, T), pruning="Mai/Juni und August"),
    "hedera helix": dict(
        light="Halbschattig bis schattig", water="Mäßig feucht.", interval=4, fertilize="Alle 4 Wochen",
        min_temp=-20, winter="Winterhart.", toxic=(T, T), indoor=T),
    "clematis": dict(
        light="Kopf in der Sonne, Fuß im Schatten", water="Gleichmäßig feucht.", interval=3,
        fertilize="März bis Juli alle 3–4 Wochen", min_temp=-20, winter="Winterhart.", toxic=(T, T)),
    "buddleja davidii": dict(
        light="Vollsonnig", water="Mäßig, verträgt Trockenheit.", interval=5, fertilize="Frühjahr Kompost",
        min_temp=-20, winter="Winterhart.", toxic=(F, F), flowering="Juli bis September",
        pruning="Im Frühjahr kräftig auf 30–50 cm"),
    "calluna vulgaris": dict(
        light="Sonnig bis halbschattig", water="Gleichmäßig feucht, kalkarmes Wasser.", interval=3,
        fertilize="Kaum", min_temp=-20, winter="Winterhart.", toxic=(F, F), flowering="August bis November"),
    "acer palmatum": dict(
        light="Halbschattig, windgeschützt", water="Gleichmäßig feucht.", interval=3, fertilize="Frühjahr",
        min_temp=-20, winter="Winterhart; Kübel schützen.", toxic=(F, F)),
    "prunus laurocerasus": dict(
        light="Sonnig bis schattig", water="Mäßig.", interval=4, fertilize="Frühjahr", min_temp=-20,
        winter="Winterhart; im Winter an frostfreien Tagen gießen.", toxic=(T, T)),
    "hosta": dict(
        light="Halbschattig bis schattig", water="Feucht halten.", interval=3, fertilize="Frühjahr Kompost",
        min_temp=-30, winter="Winterhart, zieht ein.", toxic=(F, T)),
    "hebe": dict(
        light="Sonnig", water="Mäßig.", interval=3, fertilize="Monatlich", min_temp=-5,
        winter="Bedingt winterhart; Kübel hell und kühl überwintern.", toxic=(F, F)),
    "chrysanthemum": dict(
        light="Sonnig", water="Gleichmäßig feucht.", interval=2, fertilize="Alle 2 Wochen bis zur Blüte",
        min_temp=-10, winter="Gartenchrysanthemen winterhart mit Laubschutz; Topfchrysanthemen meist einjährig.",
        toxic=(F, T), flowering="September bis November"),
    "cyclamen persicum": dict(
        light="Hell und kühl, keine direkte Sonne", water="Von unten gießen, nicht in die Knolle.",
        interval=3, fertilize="Während der Blüte alle 2 Wochen", min_temp=5,
        winter="Blüht im Winter am liebsten bei 12–16 °C.", toxic=(T, T), flowering="September bis April", indoor=T),
    "yucca filamentosa": dict(
        light="Vollsonnig", water="Sparsam.", interval=10, fertilize="Kaum", min_temp=-20,
        winter="Winterhart; vor Nässe schützen.", toxic=(F, T)),

    # --------------------------------------------------------- Zimmerpflanzen
    "monstera deliciosa": dict(
        light="Hell, keine direkte Mittagssonne", water="Gießen, wenn die oberen 2–3 cm Erde trocken sind; keine Staunässe.",
        interval=7, fertilize="März bis September alle 2 Wochen", min_temp=15,
        winter="Zimmerpflanze: nicht unter 15 °C, im Winter weniger gießen.", toxic=(T, T), origin="Mittelamerika", indoor=T),
    "epipremnum aureum": dict(
        light="Hell bis halbschattig", water="Gießen, wenn die Erde oben angetrocknet ist.",
        interval=7, fertilize="März bis September alle 2 Wochen", min_temp=15,
        winter="Zimmerpflanze, nicht unter 15 °C.", toxic=(T, T), indoor=T),
    "ficus benjamina": dict(
        light="Hell, ohne pralle Sonne; Standort nicht wechseln", water="Gleichmäßig leicht feucht, Oberfläche antrocknen lassen.",
        interval=5, fertilize="März bis September alle 2 Wochen", min_temp=15,
        winter="Zimmerpflanze, nicht unter 15 °C; Zugluft vermeiden.", toxic=(T, T), indoor=T),
    "ficus elastica": dict(
        light="Hell bis halbschattig", water="Mäßig, Erde zwischendurch antrocknen lassen.",
        interval=7, fertilize="März bis September alle 2 Wochen", min_temp=15,
        winter="Zimmerpflanze.", toxic=(T, T), indoor=T),
    "ficus lyrata": dict(
        light="Sehr hell, gern etwas Morgensonne", water="Gießen, wenn die oberen Zentimeter trocken sind.",
        interval=7, fertilize="März bis September alle 2 Wochen", min_temp=15,
        winter="Zimmerpflanze; nicht umstellen.", toxic=(T, T), indoor=T),
    "dracaena trifasciata": dict(
        light="Hell bis schattig – sehr anpassungsfähig", water="Sparsam, Erde komplett abtrocknen lassen.",
        interval=21, fertilize="April bis September monatlich", min_temp=12,
        winter="Zimmerpflanze; im Winter kaum gießen.", toxic=(T, T), indoor=T),
    "sansevieria trifasciata": "dracaena trifasciata",
    "dracaena": dict(
        light="Hell, keine pralle Sonne", water="Mäßig, Erde antrocknen lassen.",
        interval=7, fertilize="März bis September alle 2–3 Wochen", min_temp=15,
        winter="Zimmerpflanze.", toxic=(T, T), indoor=T),
    "zamioculcas zamiifolia": dict(
        light="Hell bis halbschattig", water="Sparsam – lieber zu wenig als zu viel; Erde ganz abtrocknen lassen.",
        interval=14, fertilize="April bis September monatlich", min_temp=15,
        winter="Zimmerpflanze; im Winter kaum gießen.", toxic=(T, T), indoor=T),
    "spathiphyllum": dict(
        light="Halbschattig bis hell", water="Gleichmäßig feucht halten – lässt die Blätter hängen, wenn es zu trocken ist.",
        interval=4, fertilize="März bis September alle 2 Wochen", min_temp=16,
        winter="Zimmerpflanze.", toxic=(T, T), indoor=T),
    "chlorophytum comosum": dict(
        light="Hell bis halbschattig", water="Mäßig feucht.", interval=5, fertilize="Alle 2 Wochen im Sommer",
        min_temp=10, winter="Zimmerpflanze.", toxic=(F, F), indoor=T),
    "phalaenopsis": dict(
        light="Hell, keine direkte Sonne", water="Einmal pro Woche kurz tauchen und gut abtropfen lassen; nie im Wasser stehen lassen.",
        interval=7, fertilize="Alle 2–4 Wochen Orchideendünger", min_temp=16,
        winter="Zimmerpflanze; für neue Blütenrispen einige Wochen nachts etwas kühler (ca. 16 °C).",
        toxic=(F, F), indoor=T),
    "goeppertia": dict(
        light="Halbschattig, keine direkte Sonne", water="Gleichmäßig feucht, kalkarmes zimmerwarmes Wasser; hohe Luftfeuchte.",
        interval=4, fertilize="März bis September alle 2 Wochen", min_temp=18,
        winter="Zimmerpflanze, warm und ohne Zugluft.", toxic=(F, F), indoor=T),
    "calathea": "goeppertia",
    "maranta": "goeppertia",
    "philodendron": dict(
        light="Hell bis halbschattig", water="Gießen, wenn die Erde oben angetrocknet ist.",
        interval=7, fertilize="März bis September alle 2 Wochen", min_temp=15, winter="Zimmerpflanze.",
        toxic=(T, T), indoor=T),
    "alocasia": dict(
        light="Hell, keine direkte Sonne", water="Gleichmäßig leicht feucht, keine Staunässe; hohe Luftfeuchte.",
        interval=5, fertilize="März bis September alle 2 Wochen", min_temp=18, winter="Zimmerpflanze, warm.",
        toxic=(T, T), indoor=T),
    "anthurium": dict(
        light="Hell, keine direkte Sonne", water="Mäßig feucht, kalkarm.", interval=5,
        fertilize="März bis September alle 2 Wochen", min_temp=16, winter="Zimmerpflanze.", toxic=(T, T), indoor=T),
    "crassula ovata": dict(
        light="Sonnig bis hell", water="Sparsam, Erde zwischendurch ganz abtrocknen lassen.",
        interval=14, fertilize="April bis September monatlich Kakteendünger", min_temp=5,
        winter="Hell und kühl bei 10–15 °C, kaum gießen – fördert die Blüte.", toxic=(F, T), indoor=T),
    "aloe vera": dict(
        light="Vollsonnig", water="Sparsam, Erde ganz abtrocknen lassen.", interval=14,
        fertilize="Mai bis August monatlich Kakteendünger", min_temp=8,
        winter="Hell bei 10–15 °C, fast trocken.", toxic=(F, T), indoor=T),
    "schlumbergera": dict(
        light="Hell, keine pralle Sonne", water="Mäßig feucht, nach der Blüte etwas trockener.",
        interval=7, fertilize="März bis August alle 2 Wochen", min_temp=10,
        winter="Ab September kühl (12–15 °C) und weniger gießen, damit er Knospen bildet; Knospen nicht drehen.",
        toxic=(F, F), flowering="November bis Januar", indoor=T),
    "euphorbia pulcherrima": dict(
        light="Hell, ohne Zugluft", water="Mäßig, keine Staunässe – zimmerwarmes Wasser.",
        interval=5, fertilize="Während der Blüte alle 2 Wochen", min_temp=15,
        winter="Zimmerpflanze, 18–20 °C.", toxic=(T, T), indoor=T),
    "strelitzia reginae": dict(
        light="Vollsonnig", water="Im Sommer reichlich, im Winter sparsam.", interval=4,
        fertilize="März bis September wöchentlich", min_temp=8,
        winter="Hell bei 10–14 °C überwintern.", toxic=(F, T), indoor=T),
    "pilea peperomioides": dict(
        light="Hell, keine pralle Sonne", water="Gießen, wenn die Erde oben trocken ist.",
        interval=7, fertilize="März bis September monatlich", min_temp=12, winter="Zimmerpflanze.", toxic=(F, F), indoor=T),
    "peperomia": dict(
        light="Hell bis halbschattig", water="Sparsam – Blätter speichern Wasser.", interval=10,
        fertilize="Monatlich im Sommer", min_temp=15, winter="Zimmerpflanze.", toxic=(F, F), indoor=T),
    "hoya": dict(
        light="Hell, etwas Morgensonne", water="Sparsam, Erde abtrocknen lassen.", interval=10,
        fertilize="März bis August monatlich", min_temp=12, winter="Zimmerpflanze; Blütenstiele nicht abschneiden.",
        toxic=(F, F), indoor=T),
    "beaucarnea recurvata": dict(
        light="Vollsonnig bis hell", water="Sparsam – der dicke Stamm speichert Wasser.", interval=14,
        fertilize="Monatlich im Sommer", min_temp=8, winter="Hell und kühl bei 10–15 °C, fast trocken.",
        toxic=(F, F), indoor=T),
    "kalanchoe blossfeldiana": dict(
        light="Hell bis sonnig", water="Sparsam.", interval=10, fertilize="Monatlich", min_temp=10,
        winter="Zimmerpflanze.", toxic=(F, T), indoor=T),
    "saintpaulia": dict(
        light="Hell, keine direkte Sonne", water="Von unten mit zimmerwarmem Wasser, Blätter nicht benetzen.",
        interval=5, fertilize="Alle 2 Wochen", min_temp=16, winter="Zimmerpflanze.", toxic=(F, F), indoor=T),
    "aglaonema": dict(
        light="Halbschattig", water="Gleichmäßig leicht feucht.", interval=7, fertilize="Alle 2 Wochen im Sommer",
        min_temp=16, winter="Zimmerpflanze.", toxic=(T, T), indoor=T),
    "dieffenbachia": dict(
        light="Hell bis halbschattig", water="Gleichmäßig leicht feucht.", interval=5,
        fertilize="Alle 2 Wochen im Sommer", min_temp=16, winter="Zimmerpflanze.", toxic=(T, T), indoor=T),
    "tradescantia": dict(
        light="Hell", water="Mäßig feucht.", interval=5, fertilize="Alle 2 Wochen im Sommer", min_temp=12,
        winter="Zimmerpflanze.", toxic=(F, T), indoor=T),
    "nephrolepis exaltata": dict(
        light="Hell bis halbschattig", water="Stets feucht halten, gern besprühen.", interval=3,
        fertilize="Alle 2–4 Wochen schwach", min_temp=15, winter="Zimmerpflanze; trockene Heizungsluft meiden.",
        toxic=(F, F), indoor=T),
    "dypsis lutescens": dict(
        light="Hell, keine pralle Sonne", water="Gleichmäßig feucht, kalkarm.", interval=4,
        fertilize="März bis September alle 2 Wochen", min_temp=16, winter="Zimmerpflanze.", toxic=(F, F), indoor=T),
    "howea forsteriana": dict(
        light="Halbschattig", water="Mäßig feucht.", interval=6, fertilize="Monatlich im Sommer", min_temp=12,
        winter="Zimmerpflanze.", toxic=(F, F), indoor=T),
    "yucca gigantea": dict(
        light="Sehr hell, im Sommer gern draußen", water="Mäßig, Erde antrocknen lassen.", interval=7,
        fertilize="März bis September alle 2 Wochen", min_temp=5,
        winter="Hell und eher kühl (10–15 °C), weniger gießen.", toxic=(F, T), indoor=T),
    "yucca elephantipes": "yucca gigantea",
}


def find(sci):
    """Pflegedaten zu einem botanischen Namen (Art, sonst Gattung)."""
    if not sci:
        return None
    words = sci.lower().replace("×", "").replace(" x ", " ").split()
    for k in (" ".join(words[:2]), words[0] if words else ""):
        v = CARE.get(k)
        if isinstance(v, str):
            v = CARE.get(v)
        if v:
            return v
    return None


def to_info(d):
    out = {k: d[k] for k in ("light", "fertilize", "winter", "flowering", "origin", "pruning", "soil") if d.get(k)}
    if d.get("water"):
        out["water_text"] = d["water"]
    tox = d.get("toxic") or (None, None)
    if tox[0] is not None:
        out["toxic_humans"] = tox[0]
    if tox[1] is not None:
        out["toxic_pets"] = tox[1]
    out["indoor_ok"] = bool(d.get("indoor"))
    return out
