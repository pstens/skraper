import requests
import re
import hashlib
from functools import lru_cache
from flask import Flask
from flask import request
from flask import jsonify
from bs4 import BeautifulSoup as BS

nutrition_re = r"Brennwert = (.*) kJ \((.*) kcal\) Fett = (.*)g Kohlenhydrate = (.*)g Eiweiß = (.*)g"
base_url = "https://www.studierendenwerk-pb.de/gastronomie/speiseplaene/{}/?tx_pamensa_mensa[date]={}"
mensa_mappings = {'mensa-academica': 'mensa-academica-paderborn', 'mensa-forum': 'mensa-forum-paderborn', 'mensa-atrium-lippstadt': 'mensa-lippsadt', 'grillcafe': 'grill-cafe', 'mensa-basilica-hamm': 'mensa-hamm', 'bona-vista': 'one-way-snack'}
app = Flask(__name__)

def map_mensa_name_to_api(mensa):
    name = mensa_mappings[mensa] if mensa in mensa_mappings else mensa
    return name

def map_mensa_name_from_api(mensa):
    name = [key for key, value in mensa_mappings.items() if value == mensa]
    return name[0] if len(name) > 0 else mensa

def parse_nutrition(nutrition):
    try:
        re_groups = list(map(lambda x: float(x.replace(',', '.')), re.search(nutrition_re, nutrition).groups()))
        return {'kJ': re_groups[0], 'kcal': re_groups[1], 'fat': re_groups[2], 'carbs': re_groups[3], 'protein': re_groups[4]}
    except AttributeError:
        # some dishes do not provide nutrition facts
        return None


@lru_cache(maxsize=None)
def scrape(mensa, date):
    r = requests.get(base_url.format(mensa, date))
    soup = BS(r.text, 'html.parser')
    raw_nutritions = soup.select('div.row.ingredients-list > div.col-sm-6.nutritions > p')
    raw_dishes = soup.select('table.table-dishes')
    mapped_dishes = list(map(lambda x: x.select('h4'), raw_dishes))
    dishes = [item.text.strip() for sublist in mapped_dishes for item in sublist]
    ids = [hashlib.sha1("{}%{}%{}".format(dish, map_mensa_name_to_api(mensa), date).encode('utf-8')).hexdigest() for dish in dishes]
    nutritions = list(map(lambda x: parse_nutrition(x.text.strip()), raw_nutritions))
    return ids, dishes, nutritions

@app.route("/<mensa>/<date>")
def nutrition(mensa, date):
    web_mensa = map_mensa_name_from_api(mensa)
    print(web_mensa)
    ids, dishes, nutritions = scrape(web_mensa, date)
    json_array = [{'id': ids[i], 'dish': dishes[i], 'nutrition': nutritions[i]} for i in range(len(ids))]
    return jsonify(json_array)
