import csv
import re
import math
import statistics
import json
import os

BASE = os.path.join(os.path.dirname(__file__), "..")
RES = os.path.join(BASE, "results")
DATA = os.path.join(BASE, "data")


def haversine(a, b):
    R = 6371000.0
    la1, lo1, la2, lo2 = map(math.radians, [a[0], a[1], b[0], b[1]])
    dla = la2 - la1
    dlo = lo2 - lo1
    h = math.sin(dla / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin(dlo / 2) ** 2
    return 2 * R * math.asin(math.sqrt(h))


def two_floats(s):
    nums = re.findall(r"-?\d+\.?\d*", s)
    if len(nums) >= 2:
        return float(nums[0]), float(nums[1])
    return None


def load(name):
    rows = {}
    with open(os.path.join(RES, name), encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line:
                continue
            parts = line.split("|")
            rows[int(parts[0])] = parts[1:]
    return rows


def city_of(text, cities):
    for c in cities:
        if c.lower() in text.lower():
            return c
    return None


def norm(s):
    return re.sub(r"[^а-яё0-9]", "", s.lower())


addresses = {}
with open(os.path.join(DATA, "addresses.csv"), encoding="utf-8-sig") as f:
    for r in csv.DictReader(f):
        addresses[int(r["id"])] = r["address"]

incoords = {}
with open(os.path.join(DATA, "coordinates.csv"), encoding="utf-8-sig") as f:
    for r in csv.DictReader(f):
        incoords[int(r["id"])] = (float(r["lat"]), float(r["lon"]))

y_fwd = load("yandex_forward.txt")
y_rev = load("yandex_reverse.txt")
d_fwd = load("dadata_forward.txt")
d_rev = load("dadata_reverse.txt")
g_fwd = load("gigachat_forward.txt")
g_rev = load("gigachat_reverse.txt")

print("=" * 64)
print("ПРЯМОЕ ГЕОКОДИРОВАНИЕ (адрес -> координаты), 100 адресов")
print("=" * 64)

Y, D, G = {}, {}, {}
for i in range(1, 101):
    p = y_fwd[i][1].split()
    if y_fwd[i][1] not in ("ERROR", "NOT_FOUND") and len(p) == 2:
        Y[i] = (float(p[1]), float(p[0]))
    if d_fwd[i][1] not in ("ERROR", "NOT_FOUND", ""):
        D[i] = (float(d_fwd[i][1]), float(d_fwd[i][2]))
    tf = two_floats(g_fwd[i][0])
    if tf:
        G[i] = tf

print(f"Успешно определено координат: Яндекс {len(Y)}/100, DaData {len(D)}/100, GigaChat {len(G)}/100")

yprec = {}
for i in range(1, 101):
    yprec[y_fwd[i][0]] = yprec.get(y_fwd[i][0], 0) + 1
dqc = {}
for i in range(1, 101):
    dqc[d_fwd[i][0]] = dqc.get(d_fwd[i][0], 0) + 1
print("Точность Яндекса (precision):", dict(sorted(yprec.items())))
print("Качество DaData (qc_geo, 0=точно):", dict(sorted(dqc.items())))


def pair_stats(A, B, label):
    dists = []
    for i in range(1, 101):
        if i in A and i in B:
            dists.append(haversine(A[i], B[i]))
    dists.sort()
    n = len(dists)
    pct = lambda thr: 100 * sum(1 for x in dists if x <= thr) / n
    print(f"\n  {label}  (сравнимых пар: {n})")
    print(f"    медиана расхождения : {statistics.median(dists):,.0f} м")
    print(f"    среднее расхождение : {statistics.mean(dists):,.0f} м")
    print(f"    совпадение <100 м   : {pct(100):.0f}%")
    print(f"    совпадение <500 м   : {pct(500):.0f}%")
    print(f"    совпадение <1 км    : {pct(1000):.0f}%")
    print(f"    совпадение <5 км    : {pct(5000):.0f}%")
    print(f"    грубых ошибок >50 км: {sum(1 for x in dists if x > 50000)}")
    return dists


print("\n--- Попарное расхождение координат ---")
yd = pair_stats(Y, D, "Яндекс <-> DaData")
yg = pair_stats(Y, G, "Яндекс <-> GigaChat")
dg = pair_stats(D, G, "DaData <-> GigaChat")

ref = {}
for i in range(1, 101):
    if i in Y and i in D and haversine(Y[i], D[i]) <= 100:
        ref[i] = ((Y[i][0] + D[i][0]) / 2, (Y[i][1] + D[i][1]) / 2)
print(f"\nЭталон (Яндекс и DaData согласны < 100 м): {len(ref)} адресов из 100")

gerr = sorted(haversine(G[i], ref[i]) for i in ref if i in G)
print("Ошибка GigaChat относительно эталона:")
print(f"    медиана : {statistics.median(gerr):,.0f} м")
print(f"    среднее : {statistics.mean(gerr):,.0f} м")
print(f"    в пределах 1 км : {100 * sum(1 for x in gerr if x <= 1000) / len(gerr):.0f}%")
print(f"    ошибка > 5 км   : {sum(1 for x in gerr if x > 5000)} адресов")
print(f"    ошибка > 100 км : {sum(1 for x in gerr if x > 100000)} адресов")

print()
print("=" * 64)
print("ОБРАТНОЕ ГЕОКОДИРОВАНИЕ (координаты -> адрес), 100 точек")
print("=" * 64)

CITIES = [
    "Санкт-Петербург", "Петропавловск-Камчатский", "Ростов-на-Дону",
    "Нижний Новгород", "Великий Новгород", "Южно-Сахалинск", "Йошкар-Ола",
    "Нарьян-Мар", "Верхняя Салда", "Красноуфимск", "Североуральск",
    "Москва", "Казань", "Омск", "Самара", "Екатеринбург", "Новосибирск",
    "Ижевск", "Краснодар", "Волгоград", "Уфа", "Магадан", "Сочи",
    "Севастополь", "Оренбург", "Салават", "Томск", "Барнаул", "Иркутск",
    "Сургут", "Салехард", "Мурманск", "Астрахань", "Симферополь",
    "Ярославль", "Смоленск", "Воронеж", "Брянск", "Калуга", "Енисейск",
    "Чита", "Чебоксары", "Рязань", "Новороссийск", "Хабаровск",
    "Благовещенск", "Пермь", "Тюмень", "Курган", "Южноуральск",
    "Магнитогорск", "Саратов", "Якутск", "Дубна", "Дмитров", "Серпухов",
    "Королёв", "Люберцы", "Видное", "Подольск", "Воскресенск", "Ступино",
    "Коломна", "Череповец", "Сыктывкар", "Челябинск", "Элиста",
    "Петрозаводск",
]

yc = {i: city_of(y_rev[i][1], CITIES) for i in range(1, 101)}
dc = {i: city_of(d_rev[i][0], CITIES) for i in range(1, 101)}
gc = {i: city_of(g_rev[i][0], CITIES) for i in range(1, 101)}

y_found = sum(1 for i in range(1, 101) if y_rev[i][1] not in ("ERROR", "NOT_FOUND"))
d_found = sum(1 for i in range(1, 101) if d_rev[i][0] not in ("ERROR", "NOT_FOUND"))
g_found = sum(1 for i in range(1, 101) if g_rev[i][0] not in ("ERROR", "NOT_FOUND"))
print(f"Получено адресов: Яндекс {y_found}/100, DaData {d_found}/100, GigaChat {g_found}/100")
print(f"DaData NOT_FOUND: {[i for i in range(1, 101) if d_rev[i][0] == 'NOT_FOUND']}")


def city_match(A, B, label):
    both = [i for i in range(1, 101) if A[i] and B[i]]
    same = sum(1 for i in both if A[i] == B[i])
    print(f"  {label}: совпадение города {same}/{len(both)} = {100 * same / len(both):.0f}%")
    return same, len(both)


print("\n--- Совпадение по городу ---")
city_match(yc, dc, "Яндекс <-> DaData  ")
city_match(yc, gc, "Яндекс <-> GigaChat")
city_match(dc, gc, "DaData <-> GigaChat")

g_uni = len(set(norm(g_rev[i][0]) for i in range(1, 101)))
y_uni = len(set(norm(y_rev[i][1]) for i in range(1, 101)))
d_uni = len(set(norm(d_rev[i][0]) for i in range(1, 101)))
print(f"\nУникальных ответов из 100: Яндекс {y_uni}, DaData {d_uni}, GigaChat {g_uni}")

top = {}
for i in range(1, 101):
    k = g_rev[i][0]
    top[k] = top.get(k, 0) + 1
top = sorted(top.items(), key=lambda x: -x[1])[:3]
print("Самые частые ответы GigaChat:")
for k, v in top:
    print(f'    {v} раз: "{k}"')

summary = {
    "forward": {
        "found": {"yandex": len(Y), "dadata": len(D), "gigachat": len(G)},
        "yandex_precision": yprec,
        "dadata_qc": dqc,
        "yd_median_m": round(statistics.median(yd)),
        "yd_under_500m_pct": round(100 * sum(1 for x in yd if x <= 500) / len(yd)),
        "yg_median_m": round(statistics.median(yg)),
        "gigachat_vs_ref_median_m": round(statistics.median(gerr)),
        "gigachat_over_5km": sum(1 for x in gerr if x > 5000),
        "gigachat_over_100km": sum(1 for x in gerr if x > 100000),
    },
    "reverse": {
        "found": {"yandex": y_found, "dadata": d_found, "gigachat": g_found},
        "unique_answers": {"yandex": y_uni, "dadata": d_uni, "gigachat": g_uni},
    },
}
with open(os.path.join(RES, "summary.json"), "w", encoding="utf-8") as f:
    json.dump(summary, f, ensure_ascii=False, indent=2)
print("\n[сводка сохранена в results/summary.json]")
