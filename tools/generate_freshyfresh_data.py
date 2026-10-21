#!/usr/bin/env python3
"""
Generate the synthetic "FreshyFresh Ops" dataset for the Microsoft Fabric POC.

Domain: refrigerated prepared foods (deli salads, side dishes, dips, entrees,
Mexican foods & tortillas, desserts, cut potatoes), retail + foodservice, US/MX/CA.

EVERYTHING HERE IS SYNTHETIC AND FICTIONAL. "FreshyFresh Foods" is an invented
company. Plant names, brands, customers, suppliers, volumes, shelf lives and prices
are placeholders for a demo. They are not any real company's data and must not be
presented as such.

Outputs (in --out):
  <table>.parquet           one file per table (load to Lakehouse Files -> bronze)
  reefer_telemetry.csv      historical telemetry for Eventhouse "Get data"
  golden_answers.json       expected answers for the planted storylines (agent/app evals)
  manifest.json             row counts + run parameters

Usage:
  python tools/generate_freshyfresh_data.py --out data/generated --seed 42
"""
from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

# ----------------------------------------------------------------------------------
# Reference data (fictional)
# ----------------------------------------------------------------------------------
FACILITIES = [
    # id, name, type, state/province, country, region
    ("P01", "Pacific Northwest Plant", "Plant", "OR", "US", "West"),
    ("P02", "Columbia Basin Plant", "Plant", "WA", "US", "West"),
    ("P03", "Great Lakes Plant", "Plant", "OH", "US", "Central"),
    ("P04", "Lone Star Plant", "Plant", "TX", "US", "South"),
    ("P05", "Carolina Plant", "Plant", "NC", "US", "East"),
    ("P06", "Bajio Plant", "Plant", "GTO", "MX", "Mexico"),
    ("P07", "Southeast DC", "DC", "GA", "US", "East"),
    ("P08", "Prairie DC", "DC", "AB", "CA", "Canada"),
]
PRODUCING = ["P01", "P02", "P03", "P04", "P05", "P06"]
# Which plants supply each shipping facility (DCs are fed by plants).
SUPPLY = {
    "P01": ["P01"], "P02": ["P02"], "P03": ["P03"], "P04": ["P04"],
    "P05": ["P05"], "P06": ["P06"], "P07": ["P05", "P03"], "P08": ["P01", "P02"],
}
PLANT_CATEGORIES = {
    "P01": ["Deli Salads", "Side Dishes", "Cut Potatoes"],
    "P02": ["Deli Salads", "Dips & Spreads", "Cut Potatoes"],
    "P03": ["Deli Salads", "Side Dishes", "Desserts", "Entrees"],
    "P04": ["Mexican Foods & Tortillas", "Dips & Spreads", "Deli Salads"],
    "P05": ["Dips & Spreads", "Deli Salads", "Side Dishes"],
    "P06": ["Mexican Foods & Tortillas", "Entrees"],
}

SUPPLIERS = [
    ("SUP01", "Valley Fresh Produce"), ("SUP02", "Basin Potato Growers"),
    ("SUP03", "Sunrise Egg Farms"), ("SUP04", "Cascade Dairy Co-op"),
    ("SUP05", "Heartland Mills"), ("SUP06", "Northfield Pantry Supply"),
    ("SUP07", "Prairie Protein Co"), ("SUP08", "Rio Verde Growers"),
]
# id, name, supplier, high-risk raw produce (used uncooked in RTE foods), allergen
INGREDIENTS = [
    ("ING01", "Russet Potatoes", "SUP02", False, None),
    ("ING02", "Yellow Onions, diced", "SUP01", True, None),
    ("ING03", "Celery, diced", "SUP01", True, None),
    ("ING04", "Eggs, cooked", "SUP03", False, "Egg"),
    ("ING05", "Mayonnaise", "SUP06", False, "Egg"),
    ("ING06", "Yellow Mustard", "SUP06", False, None),
    ("ING07", "Elbow Macaroni", "SUP05", False, "Wheat"),
    ("ING08", "Green Cabbage, shredded", "SUP01", True, None),
    ("ING09", "Carrots, shredded", "SUP01", True, None),
    ("ING10", "Sour Cream", "SUP04", False, "Milk"),
    ("ING11", "Cheddar Cheese", "SUP04", False, "Milk"),
    ("ING12", "Spinach", "SUP01", True, None),
    ("ING13", "Avocado Pulp", "SUP08", True, None),
    ("ING14", "Tomatoes, diced", "SUP01", True, None),
    ("ING15", "Jalapenos", "SUP01", True, None),
    ("ING16", "Cilantro", "SUP01", True, None),
    ("ING17", "Wheat Flour", "SUP05", False, "Wheat"),
    ("ING18", "Masa Harina", "SUP05", False, None),
    ("ING19", "Chicken, cooked", "SUP07", False, None),
    ("ING20", "Beef, cooked", "SUP07", False, None),
    ("ING21", "Milk", "SUP04", False, "Milk"),
    ("ING22", "Rice", "SUP05", False, None),
    ("ING23", "Bananas", "SUP08", True, None),
    ("ING24", "Beans, cooked", "SUP06", False, None),
    ("ING25", "Green Beans", "SUP01", True, None),
    ("ING26", "Sugar", "SUP06", False, None),
    ("ING27", "Vinegar", "SUP06", False, None),
    ("ING28", "Pasta, penne", "SUP05", False, "Wheat"),
    ("ING29", "Garlic", "SUP01", True, None),
    ("ING30", "Bell Peppers, diced", "SUP01", True, None),
]
# category -> (brand, default shelf life days, items)
# item = (name, [ingredient ids], has_foodservice_pack, shelf_life_override)
CATALOG = {
    "Deli Salads": ("Homestyle Kitchen", 45, [
        ("Classic Potato Salad", ["ING01", "ING02", "ING03", "ING04", "ING05", "ING06", "ING27"], True, None),
        ("Mustard Potato Salad", ["ING01", "ING02", "ING06", "ING05", "ING04", "ING26"], True, None),
        ("Macaroni Salad", ["ING07", "ING05", "ING02", "ING03", "ING30", "ING09"], True, None),
        ("Creamy Coleslaw", ["ING08", "ING09", "ING05", "ING26", "ING27"], True, None),
        ("Egg Salad", ["ING04", "ING05", "ING06", "ING03"], False, None),
        ("Three Bean Salad", ["ING24", "ING25", "ING02", "ING27", "ING26"], False, None),
        ("Pasta Primavera Salad", ["ING28", "ING14", "ING30", "ING29", "ING11"], False, None),
    ]),
    "Side Dishes": ("Homestyle Kitchen", 50, [
        ("Homestyle Mashed Potatoes", ["ING01", "ING21", "ING10"], True, None),
        ("Macaroni & Cheese", ["ING07", "ING11", "ING21"], True, None),
        ("Scalloped Potatoes", ["ING01", "ING21", "ING11", "ING02"], True, None),
        ("Baked Beans", ["ING24", "ING02", "ING26"], True, None),
        ("Garlic Green Beans", ["ING25", "ING29"], False, None),
    ]),
    "Dips & Spreads": ("Homestyle Kitchen", 60, [
        ("French Onion Dip", ["ING10", "ING02", "ING29"], True, None),
        ("Ranch Dip", ["ING10", "ING05", "ING29"], False, None),
        ("Spinach Dip", ["ING10", "ING12", "ING02", "ING11"], False, None),
        ("Guacamole", ["ING13", "ING02", "ING14", "ING16", "ING15"], True, 21),
        ("Pimento Cheese Spread", ["ING11", "ING05", "ING30"], False, None),
    ]),
    "Entrees": ("Bistro Select", 35, [
        ("Chicken Enchiladas", ["ING19", "ING18", "ING11", "ING02", "ING15"], False, None),
        ("Beef Pot Roast", ["ING20", "ING01", "ING09", "ING02"], False, None),
        ("Chicken Alfredo", ["ING19", "ING28", "ING21", "ING11", "ING29"], False, None),
        ("Homestyle Meatloaf", ["ING20", "ING02", "ING04", "ING17"], False, None),
    ]),
    "Mexican Foods & Tortillas": ("Casa Fresca", 45, [
        ("Flour Tortillas", ["ING17"], True, 60),
        ("Corn Tortillas", ["ING18"], True, None),
        ("Pico de Gallo", ["ING14", "ING02", "ING16", "ING15"], True, 14),
        ("Mild Salsa", ["ING14", "ING02", "ING15", "ING16", "ING27"], True, None),
        ("Bean & Cheese Burrito", ["ING17", "ING24", "ING11"], False, 40),
    ]),
    "Desserts": ("Homestyle Kitchen", 55, [
        ("Rice Pudding", ["ING22", "ING21", "ING26"], False, None),
        ("Banana Pudding", ["ING23", "ING21", "ING26", "ING04"], False, None),
        ("Tapioca Pudding", ["ING21", "ING26", "ING04"], False, None),
    ]),
    "Cut Potatoes": ("Harvest Table", 21, [
        ("Diced Potatoes", ["ING01"], True, None),
        ("Shredded Hash Browns", ["ING01"], True, None),
        ("Potato Wedges", ["ING01", "ING29"], True, None),
    ]),
}
CHANNELS = ["Retail Grocery", "Club", "Foodservice", "Convenience"]
CHANNEL_P = [0.50, 0.10, 0.30, 0.10]
CHANNEL_DISCOUNT = {"Retail Grocery": 0.0, "Club": 0.08, "Foodservice": 0.05, "Convenience": 0.0}
ORDERS_PER_WEEK = {"Retail Grocery": 2, "Club": 1, "Foodservice": 3, "Convenience": 2}
LINES_PER_ORDER = {"Retail Grocery": (4, 8), "Club": (3, 5), "Foodservice": (3, 6), "Convenience": (2, 4)}
CASES_PER_LINE = {"Retail Grocery": (3, 20), "Club": (10, 40), "Foodservice": (2, 12), "Convenience": (1, 5)}
CUSTOMERS_PER_FACILITY = {"P01": 15, "P02": 12, "P03": 20, "P04": 18, "P05": 14, "P06": 12, "P07": 18, "P08": 11}
ADJECTIVES = ["Maple", "Harbor", "Summit", "Cedar", "Prairie", "Lakeside", "Golden", "Riverbend",
              "Pinecrest", "Bluebird", "Sunset", "Meadow", "Granite", "Willow", "Copper", "Silverline",
              "Northgate", "Evergreen", "Sagebrush", "Coastal", "Juniper", "Aspen", "Redwood", "Brookside"]
NOUNS = {
    "Retail Grocery": ["Market", "Grocers", "Fresh Market", "Supermarkets", "Food Stores"],
    "Club": ["Warehouse Club", "Bulk Club"],
    "Foodservice": ["Bistro Group", "Catering Co", "Restaurant Partners", "Campus Dining", "Hospital Foodservice"],
    "Convenience": ["Quick Stop", "Corner Mart", "Fuel & Go"],
}

# Planted storylines (keep in sync with docs/data-model.md and golden_answers.json)
RECALL_PLANT, RECALL_INGREDIENT, RECALL_SUPPLIER = "P02", "ING02", "SUP01"
RECALL_RECEIPT = date(2026, 9, 8)
RECALL_NOTICE = date(2026, 9, 15)
REEFER_TRUCK, REEFER_FROM, REEFER_TO = "TRK-117", date(2026, 9, 10), date(2026, 9, 14)
OVERPROD_PLANT, OVERPROD_CATEGORY, OVERPROD_MONTH, OVERPROD_FACTOR = "P01", "Cut Potatoes", 8, 1.6
OTIF_FACILITY, OTIF_WEEKDAY, OTIF_CHANNEL, OTIF_LATE_P = "P07", 0, "Foodservice", 0.35  # Monday=0
BASE_LATE_P = 0.05
EXCURSION_C, SETPOINT_C, READING_MIN = 5.0, 2.0, 15

# Fleet / GPS extension. Uses its own RNG stream (seed, FLEET_STREAM) so Q1-Q8 stay byte-identical.
FLEET_STREAM = 7
# Approximate state-level coordinates (not a real site). Customers sit inside a land-ward bearing sector.
FACILITY_COORDS = {
    "P01": (45.4, -122.6), "P02": (46.2, -119.1), "P03": (40.0, -83.0), "P04": (32.8, -96.8),
    "P05": (35.2, -80.8), "P06": (20.5, -100.8), "P07": (33.7, -84.4), "P08": (51.0, -114.0),
}
CUSTOMER_BEARINGS = {  # degrees clockwise from north (lo, hi); hi may exceed 360
    "P01": (20, 160), "P02": (60, 180), "P03": (190, 290), "P04": (280, 420),
    "P05": (200, 340), "P06": (310, 345), "P07": (250, 390), "P08": (30, 150),
}
KM_PER_TRANSIT_HOUR = {"P06": 32.0}  # straight-line km per planned transit hour; P06: slower mountain roads
DEFAULT_KM_PER_TRANSIT_HOUR = 42.0  # (stops, hours-of-service)
ROAD_FACTOR = 1.25             # road km / straight-line km
DOCK_WAIT_BASE_H = (0.25, 0.75)
DRIVER_RATE_FACTOR = {"US": 1.0, "CA": 1.05, "MX": 0.45}
DOCK_WAIT_STORY_H = 2.0        # Q9: a late shipment is "dock-caused" when dock_wait_h exceeds this


def min_remaining_days(shelf_life: int) -> int:
    """Customers won't accept product with less remaining life than this (synthetic rule)."""
    return max(5, math.ceil(0.3 * shelf_life))


# ----------------------------------------------------------------------------------
def build(seed: int, start: date, days: int, upn_domain: str):
    rng = np.random.default_rng(seed)
    end = start + timedelta(days=days - 1)

    # ---------------- dimensions ----------------
    dim_facility = pd.DataFrame(FACILITIES, columns=[
        "facility_id", "facility_name", "facility_type", "state_province", "country", "region"])
    dim_facility["qa_manager_upn"] = [f"qa.manager.{f.lower()}@{upn_domain}" for f in dim_facility.facility_id]

    dim_supplier = pd.DataFrame(SUPPLIERS, columns=["supplier_id", "supplier_name"])
    dim_ingredient = pd.DataFrame(INGREDIENTS, columns=[
        "ingredient_id", "ingredient_name", "supplier_id", "is_high_risk_raw", "allergen"])
    ing_allergen = {i[0]: i[4] for i in INGREDIENTS}

    products, sku_ingredients = [], {}
    n = 0
    for category, (brand, shelf_default, items) in CATALOG.items():
        for name, ings, has_fs, shelf_override in items:
            packs = [("Retail", "2 lb tub", 6, 2.0)] + ([("Foodservice", "10 lb tub", 2, 10.0)] if has_fs else [])
            for pack_type, pack_desc, case_pack, lb in packs:
                n += 1
                sku = f"SKU{n:03d}"
                base_price = float(rng.uniform(3.5, 8.5))
                unit_price = round(base_price if pack_type == "Retail" else base_price * 3.4, 2)
                allergens = sorted({ing_allergen[i] for i in ings if ing_allergen[i]})
                shelf = shelf_override or shelf_default
                products.append(dict(
                    sku_id=sku, sku_name=f"{name} {pack_desc}", item_name=name, category=category,
                    brand=brand, pack_type=pack_type, case_pack=case_pack, unit_weight_lb=lb,
                    shelf_life_days=shelf, min_remaining_days=min_remaining_days(shelf),
                    storage_temp_max_c=4.0, allergens=", ".join(allergens) if allergens else "None",
                    list_price_per_unit_usd=unit_price,
                    unit_cost_usd=round(unit_price * float(rng.uniform(0.55, 0.66)), 2),
                ))
                sku_ingredients[sku] = ings
    dim_product = pd.DataFrame(products)
    prod = dim_product.set_index("sku_id")

    # customers
    customers, used = [], set()
    cid = 0
    for fac in [f[0] for f in FACILITIES]:
        frow = dim_facility.set_index("facility_id").loc[fac]
        for _ in range(CUSTOMERS_PER_FACILITY[fac]):
            cid += 1
            channel = CHANNELS[int(rng.choice(len(CHANNELS), p=CHANNEL_P))]
            nm = f"{ADJECTIVES[int(rng.integers(len(ADJECTIVES)))]} {NOUNS[channel][int(rng.integers(len(NOUNS[channel])))]}"
            base, k = nm, 2
            while nm in used:
                nm, k = f"{base} {k}", k + 1
            used.add(nm)
            transit_lo, transit_hi = (6, 28) if fac in ("P06", "P08") else (3, 20)
            customers.append(dict(
                customer_id=f"C{cid:04d}", customer_name=nm, channel=channel,
                ship_from_facility_id=fac, country=frow.country, region=frow.region,
                transit_hours=int(rng.integers(transit_lo, transit_hi + 1)),
                order_weekdays=",".join(str(d) for d in sorted(rng.choice(7, ORDERS_PER_WEEK[channel], replace=False).tolist())),
                contact_email=f"buyer{cid:04d}@example.com",
                contact_phone=f"555-01{cid % 100:02d}",
                credit_limit_usd=int(rng.integers(20, 400)) * 1000,
            ))
    dim_customer = pd.DataFrame(customers)

    # SKUs each producing plant makes; SKUs each shipping facility can sell (and who makes them)
    plant_skus = {p: dim_product[dim_product.category.isin(PLANT_CATEGORIES[p])].sku_id.tolist() for p in PRODUCING}
    sellable = {}  # facility -> {sku: producing plant}
    for fac, sups in SUPPLY.items():
        m = {}
        for p in sups:
            for s in plant_skus[p]:
                m.setdefault(s, p)
        sellable[fac] = m

    # ---------------- orders ----------------
    order_rows, line_rows = [], []
    oid = 0
    for c in customers:
        weekdays = {int(x) for x in c["order_weekdays"].split(",")}
        sku_pool = [s for s in sorted(sellable[c["ship_from_facility_id"]])
                    if (prod.loc[s, "pack_type"] == "Foodservice") == (c["channel"] == "Foodservice")]
        if not sku_pool:
            continue
        lo, hi = LINES_PER_ORDER[c["channel"]]
        clo, chi = CASES_PER_LINE[c["channel"]]
        for d in range(days):
            od = start + timedelta(days=d)
            if od.weekday() not in weekdays:
                continue
            oid += 1
            order_id = f"SO{oid:06d}"
            lead = 1 if c["channel"] == "Foodservice" else 2
            req = od + timedelta(days=lead)
            order_rows.append(dict(order_id=order_id, customer_id=c["customer_id"], order_date=od,
                                   requested_delivery_date=req, ship_from_facility_id=c["ship_from_facility_id"]))
            k = int(min(len(sku_pool), rng.integers(lo, hi + 1)))
            for ln, s in enumerate(sorted(rng.choice(sku_pool, k, replace=False).tolist()), start=1):
                line_rows.append(dict(order_id=order_id, order_line=ln, sku_id=s,
                                      cases_ordered=int(rng.integers(clo, chi + 1))))
    orders = pd.DataFrame(order_rows)
    order_lines = pd.DataFrame(line_rows)

    # ship timing (needed for demand planning)
    cust = dim_customer.set_index("customer_id")
    orders["requested_delivery_ts"] = pd.to_datetime(orders.requested_delivery_date) + pd.Timedelta(hours=10)
    orders["transit_hours"] = orders.customer_id.map(cust.transit_hours)
    orders["ship_ts"] = orders.requested_delivery_ts - pd.to_timedelta(orders.transit_hours + 2, unit="h")
    orders["ship_date"] = orders.ship_ts.dt.date

    ol = order_lines.merge(orders[["order_id", "ship_from_facility_id", "ship_date"]], on="order_id")
    ol["producing_plant_id"] = [sellable[f][s] for f, s in zip(ol.ship_from_facility_id, ol.sku_id)]
    demand = ol.groupby(["producing_plant_id", "sku_id", "ship_date"]).cases_ordered.sum()
    demand_map = defaultdict(dict)
    for (p, s, d), v in demand.items():
        demand_map[(p, s)][d] = int(v)

    # ---------------- ingredient receipts (weekly, anchored on the recall receipt date) ----------------
    first_receipt = RECALL_RECEIPT - timedelta(days=7 * ((RECALL_RECEIPT - (start - timedelta(days=21))).days // 7))
    receipt_dates = []
    d = first_receipt
    while d <= end:
        receipt_dates.append(d)
        d += timedelta(days=7)
    plant_ings = {p: sorted({i for s in plant_skus[p] for i in sku_ingredients[s]}) for p in PRODUCING}
    receipts = []
    for p in PRODUCING:
        for ing in plant_ings[p]:
            sup = dim_ingredient.set_index("ingredient_id").loc[ing, "supplier_id"]
            for rd in receipt_dates:
                receipts.append(dict(ingredient_lot_id=f"ILOT-{p}-{ing}-{rd:%Y%m%d}", ingredient_id=ing,
                                     supplier_id=sup, facility_id=p, receipt_date=rd,
                                     supplier_lot_ref=f"{sup}-{int(rng.integers(100000, 999999))}",
                                     qty_kg=round(float(rng.uniform(200, 2500)), 1), qa_status="Released"))
    fact_ingredient_receipt = pd.DataFrame(receipts)
    recall_ilot = f"ILOT-{RECALL_PLANT}-{RECALL_INGREDIENT}-{RECALL_RECEIPT:%Y%m%d}"
    assert recall_ilot in set(fact_ingredient_receipt.ingredient_lot_id), "recall receipt not generated"

    def ingredient_lot_for(p, ing, pd_):
        valid = [rd for rd in receipt_dates if rd <= pd_]
        return f"ILOT-{p}-{ing}-{valid[-1]:%Y%m%d}" if valid else None

    # ---------------- production lots ----------------
    lots, bridge, tests = [], [], []
    prod_start = start - timedelta(days=4)
    total_days = (end - prod_start).days + 1
    for p in PRODUCING:
        for s in plant_skus[p]:
            cycle = 2 if prod.loc[s, "pack_type"] == "Retail" else 3
            offset = int(rng.integers(cycle))
            shelf = int(prod.loc[s, "shelf_life_days"])
            for k in range(offset, total_days, cycle):
                pdate = prod_start + timedelta(days=k)
                need = sum(demand_map[(p, s)].get(pdate + timedelta(days=j), 0) for j in range(1, cycle + 1))
                if need == 0:
                    continue
                factor = 1.08 * float(rng.normal(1.0, 0.04))
                if p == OVERPROD_PLANT and prod.loc[s, "category"] == OVERPROD_CATEGORY and pdate.month == OVERPROD_MONTH:
                    factor *= OVERPROD_FACTOR
                planned = max(1, int(round(need * factor)))
                yld = float(np.clip(rng.normal(0.975, 0.012), 0.93, 0.995))
                produced = max(1, int(round(planned * yld)))
                lot_id = f"L{p}-{pdate:%y%m%d}-{s[3:]}"
                lots.append(dict(lot_id=lot_id, sku_id=s, facility_id=p, production_date=pdate,
                                 line_id=f"{p}-L{int(rng.integers(1, 5))}", cases_planned=planned,
                                 cases_produced=produced, yield_pct=round(produced / planned * 100, 2),
                                 best_by_date=pdate + timedelta(days=shelf)))
                for ing in sku_ingredients[s]:
                    il = ingredient_lot_for(p, ing, pdate)
                    if il:
                        bridge.append(dict(lot_id=lot_id, ingredient_lot_id=il, ingredient_id=ing))
                micro_fail = rng.random() < 0.008
                tests += [
                    dict(lot_id=lot_id, test_type="Micro screen (product)", result="Fail" if micro_fail else "Pass",
                         value=None, tested_on=pdate),
                    dict(lot_id=lot_id, test_type="pH", result="Pass", value=round(float(rng.normal(4.4, 0.1)), 2), tested_on=pdate),
                    dict(lot_id=lot_id, test_type="Pack temperature C", result="Pass",
                         value=round(float(rng.normal(2.6, 0.4)), 1), tested_on=pdate),
                ]
    fact_lot = pd.DataFrame(lots)
    bridge_lot_ingredient = pd.DataFrame(bridge)
    fact_quality_test = pd.DataFrame(tests)
    fact_quality_test.insert(0, "test_id", [f"QT{i:07d}" for i in range(1, len(fact_quality_test) + 1)])

    recall_lots = set(bridge_lot_ingredient.loc[bridge_lot_ingredient.ingredient_lot_id == recall_ilot, "lot_id"])
    failed_lots = set(fact_quality_test.loc[fact_quality_test.result == "Fail", "lot_id"])

    # ---------------- waste prep, damage, allocation (FEFO) ----------------
    remaining = dict(zip(fact_lot.lot_id, fact_lot.cases_produced))
    lot_info = fact_lot.set_index("lot_id")
    waste = []

    def add_waste(wdate, lot_id, reason, cases):
        if cases > 0:
            li = lot_info.loc[lot_id]
            waste.append(dict(waste_date=wdate, facility_id=li.facility_id, sku_id=li.sku_id, lot_id=lot_id,
                              reason=reason, cases=int(cases)))

    for lot_id in sorted(failed_lots):
        add_waste(lot_info.loc[lot_id, "production_date"] + timedelta(days=1), lot_id, "QA Reject", remaining[lot_id])
        remaining[lot_id] = 0
    for lot_id in fact_lot.lot_id:
        if remaining[lot_id] > 20 and rng.random() < 0.05:
            dmg = int(rng.integers(1, 4))
            add_waste(lot_info.loc[lot_id, "production_date"] + timedelta(days=1), lot_id, "Damaged", dmg)
            remaining[lot_id] -= dmg

    lots_by_ps = defaultdict(list)
    for r in fact_lot.sort_values(["production_date", "lot_id"]).itertuples():
        lots_by_ps[(r.facility_id, r.sku_id)].append(r.lot_id)

    orders = orders.sort_values(["ship_ts", "order_id"]).reset_index(drop=True)
    lines_by_order = {k: g for k, g in ol.groupby("order_id")}
    recall_destroyed = False
    alloc_rows = []  # shipment lines
    for o in orders.itertuples():
        if not recall_destroyed and o.ship_date >= RECALL_NOTICE:
            # supplier notice received: remaining stock of affected lots is placed on hold and destroyed next day
            for lot_id in sorted(recall_lots):
                add_waste(RECALL_NOTICE + timedelta(days=1), lot_id, "Supplier Recall", remaining[lot_id])
                remaining[lot_id] = 0
            recall_destroyed = True
        for ln in lines_by_order[o.order_id].itertuples():
            need = ln.cases_ordered
            shelf_min = int(prod.loc[ln.sku_id, "min_remaining_days"])
            for lot_id in lots_by_ps[(ln.producing_plant_id, ln.sku_id)]:
                if need == 0:
                    break
                li = lot_info.loc[lot_id]
                if li.production_date >= o.ship_date:
                    break  # lots are sorted by production date
                if remaining[lot_id] <= 0 or (li.best_by_date - o.ship_date).days < shelf_min:
                    continue
                take = min(need, remaining[lot_id])
                remaining[lot_id] -= take
                need -= take
                alloc_rows.append(dict(order_id=o.order_id, order_line=ln.order_line, sku_id=ln.sku_id,
                                       lot_id=lot_id, cases_shipped=int(take)))

    # aged-out: unsold stock is written off when it drops below customer min remaining life
    for lot_id, rem in remaining.items():
        if rem > 0:
            li = lot_info.loc[lot_id]
            aged = li.best_by_date - timedelta(days=int(prod.loc[li.sku_id, "min_remaining_days"]) - 1)
            if aged <= end:
                add_waste(aged, lot_id, "Aged Out", rem)
                remaining[lot_id] = 0

    # ---------------- shipments + delivery performance ----------------
    fac_index = {f[0]: i for i, f in enumerate(FACILITIES)}
    fleet = {f: [f"TRK-{100 + fac_index[f] * 6 + j}" for j in range(1, 7)] for f in fac_index}
    ship_rows, dock_delay_h = [], {}  # dock_delay_h: storyline delay spent at the dock (fleet extension)
    for o in orders.itertuples():
        truck = fleet[o.ship_from_facility_id][int(rng.integers(6))]
        channel = cust.loc[o.customer_id, "channel"]
        late_p = BASE_LATE_P
        in_story = (o.ship_from_facility_id == OTIF_FACILITY and channel == OTIF_CHANNEL
                    and o.requested_delivery_date.weekday() == OTIF_WEEKDAY)
        if in_story:
            late_p = OTIF_LATE_P
        noise_h = float(rng.normal(0, 0.4))  # same draw order as before: normal, random, uniform
        bump_h = float(rng.uniform(3.5, 7.0)) if rng.random() < late_p else 0.0
        delay_h = noise_h + bump_h
        dock_delay_h[f"SH{o.order_id[2:]}"] = bump_h if in_story else 0.0  # P07 story: trucks wait at the DC
        delivered = o.ship_ts + pd.Timedelta(hours=float(o.transit_hours + delay_h))
        excursion = truck == REEFER_TRUCK and REEFER_FROM <= o.ship_date <= REEFER_TO
        ship_rows.append(dict(shipment_id=f"SH{o.order_id[2:]}", order_id=o.order_id, customer_id=o.customer_id,
                              ship_from_facility_id=o.ship_from_facility_id, truck_id=truck, ship_ts=o.ship_ts,
                              requested_delivery_ts=o.requested_delivery_ts, delivered_ts=delivered,
                              on_time=bool(delivered <= o.requested_delivery_ts + pd.Timedelta(hours=1)),
                              rejected_on_delivery=bool(excursion),
                              rejection_reason="Temperature excursion" if excursion else None))
    fact_shipment = pd.DataFrame(ship_rows)
    fact_shipment["ship_date"] = fact_shipment.ship_ts.dt.date

    fact_shipment_line = pd.DataFrame(alloc_rows)
    fact_shipment_line["shipment_id"] = "SH" + fact_shipment_line.order_id.str[2:]
    rejected = set(fact_shipment.loc[fact_shipment.rejected_on_delivery, "shipment_id"])
    fact_shipment_line["cases_delivered"] = np.where(fact_shipment_line.shipment_id.isin(rejected), 0,
                                                     fact_shipment_line.cases_shipped)
    for r in fact_shipment_line[fact_shipment_line.shipment_id.isin(rejected)].itertuples():
        sdate = fact_shipment.set_index("shipment_id").loc[r.shipment_id, "delivered_ts"].date()
        add_waste(sdate, r.lot_id, "Temp Excursion", r.cases_shipped)
    fact_shipment_line = fact_shipment_line[["shipment_id", "order_id", "order_line", "sku_id", "lot_id",
                                             "cases_shipped", "cases_delivered"]]

    # order lines: shipped/delivered + revenue
    agg = fact_shipment_line.groupby(["order_id", "order_line"])[["cases_shipped", "cases_delivered"]].sum()
    fact_order_line = order_lines.merge(agg, on=["order_id", "order_line"], how="left").fillna(
        {"cases_shipped": 0, "cases_delivered": 0})
    fact_order_line[["cases_shipped", "cases_delivered"]] = fact_order_line[["cases_shipped", "cases_delivered"]].astype(int)
    fact_order_line = fact_order_line.merge(orders[["order_id", "customer_id", "order_date", "requested_delivery_date"]],
                                            on="order_id")
    ch = fact_order_line.customer_id.map(cust.channel)
    price_case = fact_order_line.sku_id.map(prod.list_price_per_unit_usd) * fact_order_line.sku_id.map(prod.case_pack)
    fact_order_line["net_price_per_case_usd"] = (price_case * (1 - ch.map(CHANNEL_DISCOUNT))).round(2)
    fact_order_line["net_revenue_usd"] = (fact_order_line.net_price_per_case_usd * fact_order_line.cases_delivered).round(2)
    fact_order_line = fact_order_line[["order_id", "order_line", "customer_id", "sku_id", "order_date",
                                       "requested_delivery_date", "cases_ordered", "cases_shipped",
                                       "cases_delivered", "net_price_per_case_usd", "net_revenue_usd"]]
    fact_order = orders[["order_id", "customer_id", "ship_from_facility_id", "order_date", "requested_delivery_date"]].copy()

    # ---------------- waste table ----------------
    fact_waste = pd.DataFrame(waste).sort_values(["waste_date", "lot_id", "reason"]).reset_index(drop=True)
    fact_waste.insert(0, "waste_id", [f"W{i:07d}" for i in range(1, len(fact_waste) + 1)])
    fact_waste["cost_usd"] = (fact_waste.cases * fact_waste.sku_id.map(prod.unit_cost_usd)
                              * fact_waste.sku_id.map(prod.case_pack)).round(2)

    # ---------------- daily inventory (plant x sku) ----------------
    ev = [fact_lot[["facility_id", "sku_id", "production_date", "cases_produced"]]
          .rename(columns={"production_date": "d", "cases_produced": "delta"})]
    sl = fact_shipment_line.merge(fact_shipment[["shipment_id", "ship_date"]], on="shipment_id")
    sl["facility_id"] = sl.lot_id.map(lot_info.facility_id)
    ev.append(sl[["facility_id", "sku_id", "ship_date", "cases_shipped"]]
              .rename(columns={"ship_date": "d", "cases_shipped": "delta"}).assign(delta=lambda x: -x.delta))
    nonship_waste = fact_waste[fact_waste.reason != "Temp Excursion"]  # excursion stock had already left the plant
    ev.append(nonship_waste[["facility_id", "sku_id", "waste_date", "cases"]]
              .rename(columns={"waste_date": "d", "cases": "delta"}).assign(delta=lambda x: -x.delta))
    ev = pd.concat(ev).groupby(["facility_id", "sku_id", "d"]).delta.sum().reset_index()
    cal = pd.date_range(prod_start, end, freq="D").date
    inv_parts = []
    for (f, s), g in ev.groupby(["facility_id", "sku_id"]):
        series = g.set_index("d").delta.reindex(cal, fill_value=0).cumsum()
        inv_parts.append(pd.DataFrame({"snapshot_date": cal, "facility_id": f, "sku_id": s,
                                       "cases_on_hand": series.values.astype(int)}))
    fact_inventory_daily = pd.concat(inv_parts)
    fact_inventory_daily = fact_inventory_daily[fact_inventory_daily.snapshot_date >= start].reset_index(drop=True)
    assert (fact_inventory_daily.cases_on_hand >= 0).all(), "negative inventory - check allocation logic"

    # ---------------- supplier notice ----------------
    fact_supplier_notice = pd.DataFrame([dict(
        notice_id="SN-2026-001", supplier_id=RECALL_SUPPLIER, ingredient_lot_id=recall_ilot,
        notice_date=RECALL_NOTICE, notice_type="Precautionary hold - potential contamination (synthetic scenario)",
        status="Open")])

    # ---------------- reefer telemetry ----------------
    tel = []
    for s in fact_shipment.itertuples():
        t0 = s.ship_ts.ceil(f"{READING_MIN}min")
        times = pd.date_range(t0, s.delivered_ts, freq=f"{READING_MIN}min")
        nread = len(times)
        if nread == 0:
            continue
        temp = SETPOINT_C + rng.normal(0, 0.3, nread)
        temp[0] += 0.8  # loading
        door = np.zeros(nread, dtype=bool)
        if s.rejected_on_delivery:
            ramp_at = max(1, int(nread * 0.25))
            peak = float(rng.uniform(7.5, 9.0))
            for i in range(ramp_at, nread):
                step = min(1.0, (i - ramp_at + 1) / 4)
                temp[i] = SETPOINT_C + step * (peak - SETPOINT_C) + float(rng.normal(0, 0.3))
        elif nread > 3 and rng.random() < 0.03:
            i = int(rng.integers(1, nread - 1))
            temp[i] = float(rng.uniform(5.2, 6.2))  # single door-open spike: 15 min out of range (below TOR threshold)
            door[i] = True
        temp = np.clip(temp, -1.0, None).round(2)
        for t, v, dflag in zip(times, temp, door):
            tel.append((t, s.truck_id, s.shipment_id, s.ship_from_facility_id, float(v), SETPOINT_C, bool(dflag),
                        "ALARM" if v > EXCURSION_C else "OK"))
    reefer = pd.DataFrame(tel, columns=["ts", "truck_id", "shipment_id", "facility_id", "temp_c", "setpoint_c",
                                        "door_open", "reefer_status"])

    # ---------------- date dimension ----------------
    dd = pd.date_range(prod_start - timedelta(days=10), end + timedelta(days=70), freq="D")
    dim_date = pd.DataFrame({"date": dd.date, "year": dd.year, "quarter": dd.quarter, "month": dd.month,
                             "month_name": dd.strftime("%B"), "year_month": dd.strftime("%Y-%m"),
                             "iso_week": dd.isocalendar().week.values.astype(int),
                             "weekday": dd.strftime("%A"), "is_weekend": dd.weekday >= 5})

    fact_lot = fact_lot.copy()
    fact_lot["has_failed_qa"] = fact_lot.lot_id.isin(failed_lots)

    dim_facility, dim_customer, dim_truck, fact_shipment, reefer = add_fleet(
        seed, fleet, dim_facility, dim_customer, fact_shipment, reefer, dock_delay_h)

    tables = dict(
        dim_facility=dim_facility, dim_product=dim_product, dim_customer=dim_customer.drop(columns=["order_weekdays"]),
        dim_truck=dim_truck,
        dim_supplier=dim_supplier, dim_ingredient=dim_ingredient, dim_date=dim_date,
        fact_ingredient_receipt=fact_ingredient_receipt, fact_lot=fact_lot, bridge_lot_ingredient=bridge_lot_ingredient,
        fact_quality_test=fact_quality_test, fact_order=fact_order, fact_order_line=fact_order_line,
        fact_shipment=fact_shipment.drop(columns=["ship_date"]), fact_shipment_line=fact_shipment_line,
        fact_waste=fact_waste, fact_inventory_daily=fact_inventory_daily, fact_supplier_notice=fact_supplier_notice,
        reefer_telemetry=reefer,
    )
    golden = compute_golden(tables, recall_ilot, start, end)
    return tables, golden


# ----------------------------------------------------------------------------------
def add_fleet(seed, fleet, dim_facility, dim_customer, fact_shipment, reefer, dock_delay_h):
    """Additive fleet layer: coordinates, dim_truck, actual departure and GPS on the reefer readings.

    Runs on its own RNG stream after everything else, so every pre-existing column and golden answer is unchanged.
    """
    frng = np.random.default_rng([seed, FLEET_STREAM])
    fac_country = dict(zip(dim_facility.facility_id, dim_facility.country))

    dim_facility = dim_facility.copy()
    dim_facility["latitude"] = dim_facility.facility_id.map(lambda f: FACILITY_COORDS[f][0])
    dim_facility["longitude"] = dim_facility.facility_id.map(lambda f: FACILITY_COORDS[f][1])

    # customers: straight-line distance consistent with transit_hours, on a land-ward bearing from their facility
    dim_customer = dim_customer.copy()
    lat0 = np.radians(dim_customer.ship_from_facility_id.map(lambda f: FACILITY_COORDS[f][0]).to_numpy())
    lon0 = np.radians(dim_customer.ship_from_facility_id.map(lambda f: FACILITY_COORDS[f][1]).to_numpy())
    lo = dim_customer.ship_from_facility_id.map(lambda f: CUSTOMER_BEARINGS[f][0]).to_numpy()
    hi = dim_customer.ship_from_facility_id.map(lambda f: CUSTOMER_BEARINGS[f][1]).to_numpy()
    bearing = np.radians(frng.uniform(lo, hi) % 360)
    kmh = dim_customer.ship_from_facility_id.map(lambda f: KM_PER_TRANSIT_HOUR.get(f, DEFAULT_KM_PER_TRANSIT_HOUR))
    km = dim_customer.transit_hours.to_numpy() * kmh.to_numpy() * frng.uniform(0.85, 1.0, len(dim_customer))
    d = km / 6371.0
    lat1 = np.arcsin(np.sin(lat0) * np.cos(d) + np.cos(lat0) * np.sin(d) * np.cos(bearing))
    lon1 = lon0 + np.arctan2(np.sin(bearing) * np.sin(d) * np.cos(lat0), np.cos(d) - np.sin(lat0) * np.sin(lat1))
    dim_customer["latitude"] = np.degrees(lat1).round(4)
    dim_customer["longitude"] = np.degrees(lon1).round(4)
    dim_customer["route_km"] = (km * ROAD_FACTOR).round(1)

    # trucks: reefer tractor-trailers; cost rates are demo assumptions, not market rates
    trucks = []
    for fac, ids in fleet.items():
        for tid in ids:
            trucks.append(dict(truck_id=tid, home_facility_id=fac, unit_type="Tractor + 53 ft reefer trailer",
                               model_year=int(frng.integers(2019, 2026)),
                               cost_per_km_usd=round(float(frng.uniform(1.05, 1.35)), 2),
                               driver_cost_per_hour_usd=round(float(frng.uniform(30, 38))
                                                              * DRIVER_RATE_FACTOR[fac_country[fac]], 2)))
    dim_truck = pd.DataFrame(trucks)

    # actual departure: short loading wait, plus the planted P07 delay spent at the dock (not on the road)
    fact_shipment = fact_shipment.copy()
    base = frng.uniform(*DOCK_WAIT_BASE_H, len(fact_shipment))
    dock_h = base + fact_shipment.shipment_id.map(dock_delay_h).to_numpy()
    departed = (fact_shipment.ship_ts + pd.to_timedelta(dock_h, unit="h")).dt.round("min")
    fact_shipment["departed_ts"] = departed.where(departed < fact_shipment.delivered_ts,
                                                  fact_shipment.delivered_ts - pd.Timedelta(minutes=30))

    # GPS on each reefer reading: at the dock until departure, then along a gently curved path to the customer
    cust = dim_customer.set_index("customer_id")
    sh = fact_shipment.set_index("shipment_id")
    curve = pd.Series(frng.uniform(-0.12, 0.12, len(sh)), index=sh.index)  # path bow, as a fraction of leg length
    r = reefer[["ts", "shipment_id", "facility_id", "door_open"]].copy()
    cid = r.shipment_id.map(sh.customer_id)
    dep, arr = r.shipment_id.map(sh.departed_ts), r.shipment_id.map(sh.delivered_ts)
    olat, olon = r.facility_id.map(lambda f: FACILITY_COORDS[f][0]), r.facility_id.map(lambda f: FACILITY_COORDS[f][1])
    dlat, dlon = cid.map(cust.latitude), cid.map(cust.longitude)
    frac = ((r.ts - dep) / (arr - dep)).clip(0, 1).to_numpy()
    bow = np.sin(np.pi * frac) * r.shipment_id.map(curve).to_numpy()
    lat = olat + frac * (dlat - olat) - bow * (dlon - olon)
    lon = olon + frac * (dlon - olon) + bow * (dlat - olat)
    moving = ((r.ts > dep) & (r.ts < arr)).to_numpy()
    drive_h = ((arr - dep).dt.total_seconds() / 3600).to_numpy()
    avg_kmh = cid.map(cust.route_km).to_numpy() / drive_h
    speed = avg_kmh * frng.uniform(0.85, 1.15, len(r))
    stopped = (frng.random(len(r)) < 0.04) | r.door_open.to_numpy()  # rest/fuel stops; door opens only when stopped
    speed = np.where(moving & ~stopped, speed, 0.0)
    jitter = np.where(moving, 0.003, 0.0003)
    reefer = reefer.copy()
    reefer["latitude"] = (lat + frng.normal(0, 1, len(r)) * jitter).round(5)
    reefer["longitude"] = (lon + frng.normal(0, 1, len(r)) * jitter).round(5)
    reefer["speed_kmh"] = speed.round(1)
    reefer["ignition_on"] = moving
    return dim_facility, dim_customer, dim_truck, fact_shipment, reefer


def trip_costs(t):
    """One row per shipment: dock wait, drive time and cost. Same formula as gold.fact_trip in NB_03."""
    s = t["fact_shipment"].merge(t["dim_truck"], on="truck_id").merge(
        t["dim_customer"][["customer_id", "channel", "route_km"]], on="customer_id")
    s["dock_wait_h"] = (s.departed_ts - s.ship_ts).dt.total_seconds() / 3600
    s["drive_h"] = (s.delivered_ts - s.departed_ts).dt.total_seconds() / 3600
    s["trip_cost_usd"] = (s.route_km * s.cost_per_km_usd
                          + (s.dock_wait_h + s.drive_h) * s.driver_cost_per_hour_usd).round(2)
    cases = t["fact_shipment_line"].groupby("shipment_id").cases_delivered.sum()
    s["cases_delivered"] = s.shipment_id.map(cases).fillna(0).astype(int)
    return s


# ----------------------------------------------------------------------------------
def compute_golden(t, recall_ilot, start, end):
    lot, bridge, sl, sh = t["fact_lot"], t["bridge_lot_ingredient"], t["fact_shipment_line"], t["fact_shipment"]
    cust, prod, waste, olines, tel = t["dim_customer"], t["dim_product"], t["fact_waste"], t["fact_order_line"], t["reefer_telemetry"]
    g = {"_note": "Expected answers for the planted storylines. Regenerated by tools/generate_freshyfresh_data.py. "
                  "Use them to evaluate the Ask FreshyFresh agent and to cross-check app KPIs."}

    # Q1 mock recall
    rl = sorted(bridge.loc[bridge.ingredient_lot_id == recall_ilot, "lot_id"].unique())
    rsl = sl[sl.lot_id.isin(rl)].merge(sh[["shipment_id", "customer_id"]], on="shipment_id")
    g["Q1_mock_recall"] = dict(
        question=f"Supplier notice SN-2026-001 flags ingredient lot {recall_ilot}. Which finished lots, customers and "
                 f"cases are in scope for a recall?",
        ingredient_lot_id=recall_ilot, finished_lot_count=len(rl), finished_lot_ids=rl,
        skus=sorted(lot[lot.lot_id.isin(rl)].sku_id.unique()),
        cases_produced=int(lot[lot.lot_id.isin(rl)].cases_produced.sum()),
        cases_shipped=int(rsl.cases_shipped.sum()), shipment_count=int(rsl.shipment_id.nunique()),
        customer_count=int(rsl.customer_id.nunique()), customer_ids=sorted(rsl.customer_id.unique()),
        cases_destroyed_supplier_recall=int(waste.loc[waste.reason == "Supplier Recall", "cases"].sum()),
        sources=["bridge_lot_ingredient", "fact_lot", "fact_shipment_line", "fact_shipment", "fact_waste"])

    # Q2 cold chain
    tor = (tel.assign(above=tel.temp_c > EXCURSION_C)
           .groupby(["shipment_id", "truck_id"]).agg(readings_above=("above", "sum"), max_temp_c=("temp_c", "max"))
           .reset_index())
    tor["tor_minutes"] = tor.readings_above * READING_MIN
    exc = tor[tor.tor_minutes >= 30].sort_values("shipment_id")
    exc_lines = sl[sl.shipment_id.isin(exc.shipment_id)]
    g["Q2_cold_chain_excursions"] = dict(
        question="Which shipments had a cold-chain excursion (cumulative time above 5.0 C >= 30 minutes) during the "
                 "data window, on which trucks, and how many cases were rejected?",
        rule="time_out_of_range_minutes = count(readings with temp_c > 5.0) * 15; excursion if >= 30",
        shipment_count=len(exc), shipments=[dict(shipment_id=r.shipment_id, truck_id=r.truck_id,
                                                  tor_minutes=int(r.tor_minutes), max_temp_c=float(r.max_temp_c))
                                             for r in exc.itertuples()],
        trucks=sorted(exc.truck_id.unique()), cases_rejected=int(exc_lines.cases_shipped.sum()),
        lots_affected=int(exc_lines.lot_id.nunique()),
        shipments_with_any_reading_above_5c=int((tor.readings_above > 0).sum()),
        sources=["ReeferTelemetry (KQL)", "fact_shipment_line"])

    # Q3 waste % by facility x category, August 2026 (aged-out + damaged + QA reject, excludes recall & excursion)
    p = prod.set_index("sku_id")
    lot_m = lot.assign(category=lot.sku_id.map(p.category), month=pd.to_datetime(lot.production_date).dt.month)
    produced = lot_m[lot_m.month == 8].groupby(["facility_id", "category"]).cases_produced.sum()
    w = waste.assign(category=waste.sku_id.map(p.category), month=pd.to_datetime(waste.waste_date).dt.month)
    w = w[(w.month == 8) & w.reason.isin(["Aged Out", "Damaged", "QA Reject"])]
    wasted = w.groupby(["facility_id", "category"]).cases.sum()
    wp = (wasted.reindex(produced.index, fill_value=0) / produced * 100).round(2).sort_values(ascending=False)
    g["Q3_waste_rate_aug_2026"] = dict(
        question="Which plant and category had the highest waste rate in August 2026?",
        rule="waste_rate_pct = waste cases (reasons Aged Out, Damaged, QA Reject; by waste_date in Aug 2026) / "
             "cases produced (by production_date in Aug 2026) * 100, per facility x category",
        top5=[dict(facility_id=f, category=c, waste_rate_pct=float(v)) for (f, c), v in wp.head(5).items()],
        network_median_pct=float(wp.median()), sources=["fact_waste", "fact_lot", "dim_product"])

    # Q4 OTIF
    ol_full = olines.groupby("order_id").apply(lambda x: bool((x.cases_delivered == x.cases_ordered).all()),
                                                 include_groups=False).rename("in_full")
    s = sh.merge(ol_full, left_on="order_id", right_index=True).merge(cust[["customer_id", "channel"]], on="customer_id")
    s["otif"] = s.on_time & s.in_full
    s["req_weekday"] = pd.to_datetime(s.requested_delivery_ts).dt.day_name()
    by_fac = (s.groupby("ship_from_facility_id").otif.mean() * 100).round(2)
    seg = s[(s.ship_from_facility_id == OTIF_FACILITY) & (s.channel == OTIF_CHANNEL)]
    segs = (s.groupby(["ship_from_facility_id", "channel", "req_weekday"])
            .agg(shipments=("on_time", "size"), on_time_pct=("on_time", "mean")).reset_index())
    segs = segs[segs.shipments >= 20].assign(on_time_pct=lambda x: (x.on_time_pct * 100).round(2))
    worst = segs.sort_values(["on_time_pct", "shipments"], ascending=[True, False]).head(3)
    g["Q4_otif"] = dict(
        question="What is OTIF % by shipping facility, and which facility x channel x requested-weekday segment "
                 "(min 20 shipments) has the worst on-time %?",
        worst_on_time_segments=[dict(facility_id=r.ship_from_facility_id, channel=r.channel,
                                     requested_weekday=r.req_weekday, shipments=int(r.shipments),
                                     on_time_pct=float(r.on_time_pct)) for r in worst.itertuples()],
        overall_on_time_pct=round(float(s.on_time.mean() * 100), 2),
        rule="OTIF = shipment on_time (delivered <= requested_delivery_ts + 1h) AND every order line delivered in full "
             "(cases_delivered = cases_ordered)",
        otif_pct_by_facility={k: float(v) for k, v in by_fac.sort_values().items()},
        on_time_pct_by_facility={k: float(v) for k, v in (s.groupby("ship_from_facility_id").on_time.mean() * 100).round(2).items()},
        p07_foodservice_on_time_pct_by_requested_weekday={k: float(v) for k, v in (seg.groupby("req_weekday").on_time.mean() * 100).round(2).items()},
        sources=["fact_shipment", "fact_order_line", "dim_customer"])

    # Q5 top SKUs by volume (Sept 2026)
    sep = olines[pd.to_datetime(olines.requested_delivery_date).dt.month == 9]
    top = sep.groupby("sku_id").cases_delivered.sum().sort_values(ascending=False).head(5)
    g["Q5_top5_skus_by_volume_sep_2026"] = dict(
        question="What were the top 5 best-selling SKUs in September 2026?",
        rule="best-selling = by cases delivered (volume), not revenue; month by requested_delivery_date",
        top5=[dict(sku_id=k, sku_name=p.loc[k, "sku_name"], cases_delivered=int(v)) for k, v in top.items()],
        sources=["fact_order_line", "dim_product"])

    # Q6 fill rate, Q7 revenue by channel, Q8 QA rejects
    g["Q6_fill_rate"] = dict(question="What is the overall case fill rate for the data window?",
                             rule="sum(cases_shipped) / sum(cases_ordered) * 100",
                             fill_rate_pct=round(float(olines.cases_shipped.sum() / olines.cases_ordered.sum() * 100), 2))
    rev = olines.merge(cust[["customer_id", "channel"]], on="customer_id").groupby("channel").net_revenue_usd.sum()
    g["Q7_revenue_by_channel"] = dict(question="What is net revenue by channel for the data window?",
                                      revenue_usd={k: round(float(v), 2) for k, v in rev.sort_values(ascending=False).items()})
    qa = waste[waste.reason == "QA Reject"]
    g["Q8_qa_rejects"] = dict(question="How many lots were rejected by QA and how many cases were destroyed?",
                              lots=int(qa.lot_id.nunique()), cases=int(qa.cases.sum()))

    # Q9 dock wait: P07's late Monday Foodservice deliveries are caused at the dock, not on the road
    tr = trip_costs(t)
    tr["req_weekday"] = pd.to_datetime(tr.requested_delivery_ts).dt.day_name()
    story = (tr.ship_from_facility_id == OTIF_FACILITY) & (tr.channel == OTIF_CHANNEL) & (tr.req_weekday == "Monday")
    late = ~tr.on_time
    dock_caused = tr.dock_wait_h > DOCK_WAIT_STORY_H
    g["Q9_dock_wait_p07"] = dict(
        question="P07 Southeast DC is late on Monday Foodservice deliveries. Is the delay at the dock or on the road?",
        rule=f"dock_wait_h = departed_ts - ship_ts (planned departure); drive_h = delivered_ts - departed_ts; "
             f"a late shipment is dock-caused when dock_wait_h > {DOCK_WAIT_STORY_H:g}",
        segment_shipments=int(story.sum()), segment_late_shipments=int((story & late).sum()),
        segment_late_dock_caused=int((story & late & dock_caused).sum()),
        segment_late_avg_dock_wait_h=round(float(tr.loc[story & late, "dock_wait_h"].mean()), 2),
        segment_late_avg_drive_h=round(float(tr.loc[story & late, "drive_h"].mean()), 2),
        segment_late_avg_planned_transit_h=round(float(
            tr.loc[story & late, "customer_id"].map(t["dim_customer"].set_index("customer_id").transit_hours).mean()), 2),
        network_avg_dock_wait_h=round(float(tr.dock_wait_h.mean()), 2),
        other_late_shipments=int((~story & late).sum()),
        other_late_dock_caused=int((~story & late & dock_caused).sum()),
        sources=["fact_trip (gold)", "fact_shipment", "dim_customer"])

    # Q10 trip cost: lanes and facilities
    lanes = (tr.groupby(["ship_from_facility_id", "customer_id"])
             .agg(trips=("shipment_id", "size"), route_km=("route_km", "first"),
                  total_cost_usd=("trip_cost_usd", "sum"), avg_cost_usd=("trip_cost_usd", "mean"))
             .reset_index().sort_values(["total_cost_usd", "customer_id"], ascending=[False, True]))
    fac = tr.groupby("ship_from_facility_id").agg(cost=("trip_cost_usd", "sum"), cases=("cases_delivered", "sum"))
    g["Q10_trip_cost"] = dict(
        question="What did trucking cost over the data window, which 5 lanes (facility -> customer) cost the most, "
                 "and what is the freight cost per case delivered by facility?",
        rule="trip_cost_usd = route_km * dim_truck.cost_per_km_usd + (dock_wait_h + drive_h) * "
             "dim_truck.driver_cost_per_hour_usd, rounded to cents per trip; one-way, no fuel surcharge or tolls. "
             "Rates are demo assumptions.",
        total_trip_cost_usd=round(float(tr.trip_cost_usd.sum()), 2), trips=len(tr),
        top5_lanes=[dict(facility_id=r.ship_from_facility_id, customer_id=r.customer_id, trips=int(r.trips),
                         route_km=float(r.route_km), total_cost_usd=round(float(r.total_cost_usd), 2),
                         avg_cost_usd=round(float(r.avg_cost_usd), 2)) for r in lanes.head(5).itertuples()],
        cost_per_case_by_facility={k: round(float(v.cost / v.cases), 2) for k, v in fac.iterrows()},
        sources=["fact_trip (gold)", "dim_truck", "dim_customer"])
    g["_window"] = dict(start=str(start), end=str(end))
    return g


# ----------------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default="data/generated")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--start", default="2026-07-01", help="first order date (YYYY-MM-DD)")
    ap.add_argument("--days", type=int, default=90)
    ap.add_argument("--upn-domain", default="yourtenant.onmicrosoft.com",
                    help="domain used for synthetic QA manager UPNs (RLS demos); map real test users later")
    a = ap.parse_args()

    start = date.fromisoformat(a.start)
    if not (start <= RECALL_RECEIPT and RECALL_NOTICE <= start + timedelta(days=a.days - 1)):
        raise SystemExit("The planted storylines need a window covering 2026-09-08..2026-09-15. Keep the defaults "
                         "or edit the storyline constants.")
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    tables, golden = build(a.seed, start, a.days, a.upn_domain)

    counts = {}
    for name, df in tables.items():
        df = df.copy()
        # Spark-friendly parquet: UTC-adjusted microsecond timestamps (no nanos, no NTZ inference surprises)
        for col in df.select_dtypes(include=["datetime64"]).columns:
            df[col] = df[col].dt.tz_localize("UTC").astype("datetime64[us, UTC]")
        df.to_parquet(out / f"{name}.parquet", index=False)
        counts[name] = len(df)
    tel = tables["reefer_telemetry"].copy()
    tel["ts"] = tel.ts.dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    tel["door_open"] = tel.door_open.map({True: "true", False: "false"})
    tel["ignition_on"] = tel.ignition_on.map({True: "true", False: "false"})
    tel.to_csv(out / "reefer_telemetry.csv", index=False)
    (out / "golden_answers.json").write_text(json.dumps(golden, indent=2, default=str))
    (out / "manifest.json").write_text(json.dumps(dict(seed=a.seed, start=a.start, days=a.days,
                                                       generated_at=datetime.now().isoformat(timespec="seconds"),
                                                       row_counts=counts), indent=2))
    for k, v in counts.items():
        print(f"{k:28s}{v:>10,}")
    print(f"\nWrote {len(counts)} parquet files + reefer_telemetry.csv + golden_answers.json to {out.resolve()}")


if __name__ == "__main__":
    main()
