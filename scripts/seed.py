"""Sample data for a fresh database, added idempotently. Run by the bootstrap.

Creates schools, users, a product catalog, Bonus Pennies promotions, referral
codes, about six months of purchase history, and a few users' saved guidance
and avoid lists. Running it again adds only what's missing.

Purchases are generated as shopping trips. Each household has one or two
personas (young kids, teens, plant-based, and so on) that weight what it
buys, a handful of favorites it buys most trips, staples, occasional
household restocks, and seasonal swings. A school's families lean toward
particular personas, so popularity differs from school to school. The random
generator is seeded, so the shape of the data is the same on every run; the
dates are relative to when setup runs, so the history is always recent.
"""

import hashlib
import random
import string
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from penny.accounts.models import ReferralCode, School, User
from penny.catalog.images import product_image_url
from penny.catalog.models import Product, Promotion, Purchase
from penny.memory.models import AvoidedProduct, GuidanceNote

RANDOM_SEED = 2026
HISTORY_DAYS = 180


@dataclass(frozen=True)
class SeedProduct:
    name: str
    category: str
    price: float
    description: str
    tags: frozenset[str]


def _product(name: str, category: str, price: float, description: str, tags: str) -> SeedProduct:
    return SeedProduct(name, category, price, description, frozenset(tags.split()))


# Tags drive the purchase generator: persona affinity, dietary exclusions and seasons.
# Product IDs follow this order.
PRODUCTS: tuple[SeedProduct, ...] = (
    _product(
        "Frosted Corn Flakes",
        "Breakfast",
        4.29,
        "Crunchy corn flakes with a light sugar frosting. A cereal kids reach for.",
        "kids breakfast",
    ),
    _product(
        "Honey Oat Cereal",
        "Breakfast",
        4.49,
        "Toasted whole-grain oat rings with a touch of honey.",
        "breakfast kids healthy",
    ),
    _product(
        "Macaroni & Cheese Box",
        "Pasta & Grains",
        1.29,
        "Elbow macaroni with a cheddar cheese sauce mix, ready in ten minutes.",
        "kids quick dairy budget",
    ),
    _product(
        "Instant Oatmeal Packets",
        "Breakfast",
        3.99,
        "Maple and brown sugar oatmeal in single-serving packets.",
        "breakfast quick healthy plant",
    ),
    _product(
        "Granola Bars",
        "Snacks",
        3.79,
        "Chewy oat and honey granola bars, individually wrapped.",
        "lunchbox kids sport",
    ),
    _product(
        "Peanut Butter",
        "Pantry",
        4.29,
        "Smooth peanut butter for sandwiches and snacks.",
        "peanut budget plant",
    ),
    _product(
        "Peanut Butter Crackers",
        "Snacks",
        3.49,
        "Toasted sandwich crackers with a peanut butter filling.",
        "peanut lunchbox",
    ),
    _product(
        "Apple Juice Boxes",
        "Beverages",
        4.99,
        "Single-serving 100% apple juice boxes, sized for lunchboxes.",
        "kids lunchbox plant",
    ),
    _product(
        "Fruit Snacks Pouches",
        "Snacks",
        3.29,
        "Mixed-berry fruit snacks in small pouches.",
        "kids lunchbox",
    ),
    _product(
        "Cheddar Cheese Sticks",
        "Dairy & Eggs",
        4.59,
        "Individually wrapped mild cheddar snack sticks.",
        "dairy kids lunchbox",
    ),
    _product(
        "Greek Yogurt Cups",
        "Dairy & Eggs",
        5.99,
        "Creamy Greek yogurt in single-serving fruit flavors.",
        "dairy healthy breakfast",
    ),
    _product("Whole Milk", "Dairy & Eggs", 3.89, "A gallon of whole milk.", "dairy staple"),
    _product(
        "Large Eggs", "Dairy & Eggs", 3.49, "A dozen grade A large eggs.", "eggs staple baking"
    ),
    _product(
        "Salted Butter",
        "Dairy & Eggs",
        4.79,
        "Four sticks of salted butter for cooking and baking.",
        "dairy baking",
    ),
    _product(
        "Sour Cream",
        "Dairy & Eggs",
        2.89,
        "Rich, creamy sour cream for toppings and dips.",
        "dairy quick",
    ),
    _product(
        "Shredded Mozzarella",
        "Dairy & Eggs",
        3.99,
        "Low-moisture mozzarella, shredded for pizza and pasta bakes.",
        "dairy quick teen",
    ),
    _product(
        "Oat Milk",
        "Beverages",
        4.49,
        "Creamy, dairy-free oat milk for cereal, coffee and baking.",
        "plant healthy staple-plant",
    ),
    _product(
        "Whole Wheat Bread",
        "Bakery",
        3.29,
        "Soft whole wheat sandwich bread.",
        "staple healthy plant",
    ),
    _product("Plain Bagels", "Bakery", 3.59, "Six chewy plain bagels.", "breakfast teen plant"),
    _product(
        "Flour Tortillas",
        "Bakery",
        2.99,
        "Soft flour tortillas for burritos and wraps.",
        "quick plant teen",
    ),
    _product(
        "Corn Tortillas",
        "Bakery",
        3.49,
        "Soft corn tortillas for tacos and quesadillas.",
        "quick plant",
    ),
    _product(
        "Spaghetti",
        "Pasta & Grains",
        1.89,
        "Classic dry spaghetti that cooks in about ten minutes.",
        "budget quick plant teen",
    ),
    _product(
        "Whole Wheat Penne",
        "Pasta & Grains",
        2.19,
        "Whole wheat penne pasta for bakes and salads.",
        "healthy plant",
    ),
    _product(
        "Long Grain White Rice",
        "Pasta & Grains",
        3.49,
        "A two-pound bag of long grain white rice.",
        "budget plant",
    ),
    _product(
        "Brown Rice",
        "Pasta & Grains",
        3.79,
        "A two-pound bag of whole-grain brown rice.",
        "healthy plant",
    ),
    _product(
        "Rice Pilaf Mix",
        "Pasta & Grains",
        2.49,
        "Seasoned rice and orzo pilaf, ready in twenty minutes.",
        "quick",
    ),
    _product(
        "Marinara Sauce",
        "Canned & Jarred",
        3.69,
        "Tomato and basil pasta sauce in a jar.",
        "quick plant budget",
    ),
    _product(
        "Black Beans",
        "Canned & Jarred",
        1.19,
        "Canned black beans, ready for tacos, bowls and soups.",
        "budget plant",
    ),
    _product(
        "Chickpeas",
        "Canned & Jarred",
        1.29,
        "Canned chickpeas for salads, curries and roasting.",
        "budget plant healthy",
    ),
    _product(
        "Canned Vegetable Mix",
        "Canned & Jarred",
        1.49,
        "Corn, carrots, peas and green beans in one can.",
        "budget plant",
    ),
    _product(
        "Chicken Noodle Soup",
        "Canned & Jarred",
        2.29,
        "Hearty canned chicken noodle soup.",
        "quick meat cold",
    ),
    _product(
        "Diced Tomatoes",
        "Canned & Jarred",
        1.39,
        "Canned diced tomatoes for sauces, chili and soups.",
        "budget plant cold",
    ),
    _product(
        "Chunky Salsa", "Canned & Jarred", 3.29, "Medium chunky tomato salsa.", "quick plant teen"
    ),
    _product(
        "Canned Pumpkin",
        "Canned & Jarred",
        2.49,
        "Pure pumpkin puree for pies, breads and muffins.",
        "baking autumn plant",
    ),
    _product(
        "All-Purpose Flour",
        "Pantry",
        4.19,
        "A five-pound bag of all-purpose flour.",
        "baking plant",
    ),
    _product(
        "Granulated Sugar", "Pantry", 3.99, "A four-pound bag of granulated sugar.", "baking plant"
    ),
    _product(
        "Semi-Sweet Chocolate Chips",
        "Pantry",
        3.89,
        "Semi-sweet chocolate chips for cookies and muffins.",
        "baking autumn",
    ),
    _product(
        "Pure Vanilla Extract",
        "Pantry",
        7.99,
        "Two ounces of pure vanilla extract.",
        "baking plant",
    ),
    _product(
        "Olive Oil",
        "Pantry",
        8.99,
        "Extra virgin olive oil for cooking and dressings.",
        "healthy plant",
    ),
    _product(
        "Pancake Mix",
        "Breakfast",
        3.29,
        "Complete pancake and waffle mix: just add water.",
        "breakfast kids",
    ),
    _product(
        "Maple Syrup",
        "Breakfast",
        6.99,
        "Pure maple syrup for pancakes and waffles.",
        "breakfast plant",
    ),
    _product(
        "Trail Mix Snack Packs",
        "Snacks",
        5.49,
        "Peanuts, raisins and chocolate candies in single-serving packs.",
        "peanut sport lunchbox",
    ),
    _product(
        "Pretzel Twists", "Snacks", 2.79, "Crunchy salted pretzel twists.", "lunchbox teen plant"
    ),
    _product(
        "Microwave Popcorn",
        "Snacks",
        3.99,
        "Six bags of butter-flavored microwave popcorn.",
        "teen",
    ),
    _product(
        "Tortilla Chips", "Snacks", 3.49, "Restaurant-style tortilla chips.", "teen quick plant"
    ),
    _product(
        "Roasted Almonds",
        "Snacks",
        6.49,
        "Lightly salted dry-roasted almonds.",
        "healthy sport plant",
    ),
    _product(
        "Applesauce Pouches",
        "Snacks",
        4.29,
        "Squeezable unsweetened applesauce pouches.",
        "kids baby lunchbox plant",
    ),
    _product(
        "Protein Bars",
        "Snacks",
        8.99,
        "Chocolate peanut protein bars with 20 grams of protein each.",
        "sport teen peanut",
    ),
    _product(
        "Hummus",
        "Snacks",
        3.99,
        "Classic chickpea hummus for dipping and spreading.",
        "plant healthy",
    ),
    _product(
        "Frozen Cheese Pizza",
        "Frozen",
        5.99,
        "A twelve-inch cheese pizza, frozen.",
        "teen quick dairy",
    ),
    _product(
        "Chicken Nuggets",
        "Frozen",
        7.49,
        "Breaded chicken nuggets that bake in fifteen minutes.",
        "kids quick meat",
    ),
    _product(
        "Frozen Mixed Vegetables",
        "Frozen",
        2.49,
        "Peas, carrots, corn and green beans, frozen.",
        "healthy plant budget",
    ),
    _product(
        "Veggie Burgers", "Frozen", 5.79, "Four black bean veggie burger patties.", "plant healthy"
    ),
    _product("Frozen Waffles", "Frozen", 3.49, "Ten toaster waffles.", "breakfast kids quick"),
    _product(
        "Vanilla Ice Cream",
        "Frozen",
        4.99,
        "A family-size carton of vanilla ice cream.",
        "dairy summer",
    ),
    _product(
        "Sports Drink Variety Pack",
        "Beverages",
        7.99,
        "Twelve bottles of electrolyte sports drink in mixed flavors.",
        "sport teen summer",
    ),
    _product(
        "Sparkling Water",
        "Beverages",
        4.99,
        "Twelve cans of lime sparkling water.",
        "healthy summer plant",
    ),
    _product("Ground Coffee", "Beverages", 9.49, "A medium roast ground coffee.", "adult plant"),
    _product(
        "Lemonade Mix",
        "Beverages",
        3.29,
        "Powdered lemonade mix that makes eight quarts.",
        "summer kids plant",
    ),
    _product(
        "Hot Cocoa Mix",
        "Beverages",
        3.79,
        "Eight packets of milk chocolate hot cocoa mix.",
        "dairy cold kids",
    ),
    _product(
        "Paper Towels",
        "Household",
        11.99,
        "Six rolls of paper towels in half-sheet sizes.",
        "household",
    ),
    _product("Dish Soap", "Household", 3.49, "Lemon-scented liquid dish soap.", "household"),
    _product(
        "Laundry Detergent",
        "Household",
        12.99,
        "Liquid laundry detergent for about 60 loads.",
        "household",
    ),
    _product(
        "Kitchen Trash Bags", "Household", 8.49, "Forty drawstring kitchen trash bags.", "household"
    ),
    _product(
        "Hand Soap Refill",
        "Household",
        5.99,
        "A large refill bottle of gentle hand soap.",
        "household",
    ),
    _product(
        "Kids' Toothpaste",
        "Personal Care",
        3.29,
        "Fluoride toothpaste in a mild fruit flavor for kids.",
        "kids",
    ),
    _product(
        "Sunscreen Lotion",
        "Personal Care",
        9.99,
        "SPF 50 sunscreen lotion for the whole family.",
        "summer",
    ),
    _product("Diapers", "Baby", 24.99, "A value box of size 3 diapers.", "baby"),
    _product("Baby Wipes", "Baby", 6.99, "Unscented baby wipes, three packs.", "baby"),
    _product(
        "Baby Oatmeal Cereal",
        "Baby",
        3.99,
        "Single-grain oatmeal cereal for babies starting solids.",
        "baby",
    ),
)


@dataclass(frozen=True)
class Persona:
    """What a household leans toward, and what it never buys."""

    affinity: dict[str, float]
    excludes: frozenset[str] = frozenset()
    trip_days: tuple[int, int] = (6, 10)
    """The range of days between shopping trips."""


PERSONAS: dict[str, Persona] = {
    "young_kids": Persona(
        {"kids": 3, "lunchbox": 2.5, "breakfast": 1.5, "quick": 1}, trip_days=(4, 8)
    ),
    "baby": Persona({"baby": 5, "kids": 1, "quick": 1}, trip_days=(4, 7)),
    "teens": Persona({"teen": 3, "sport": 2.5, "quick": 1.5, "breakfast": 1}, trip_days=(4, 7)),
    "plant_based": Persona(
        {"plant": 3, "healthy": 2, "staple-plant": 3},
        excludes=frozenset({"dairy", "meat", "eggs"}),
    ),
    "home_baker": Persona({"baking": 4, "breakfast": 1.5, "dairy": 1}, trip_days=(7, 12)),
    "budget": Persona({"budget": 3.5, "staple": 1.5}, trip_days=(10, 14)),
    "quick_dinners": Persona({"quick": 3.5, "kids": 0.5}),
    "health_minded": Persona({"healthy": 3.5, "breakfast": 1.5, "sport": 0.5}),
}


@dataclass(frozen=True)
class SeedSchool:
    name: str
    time_zone: str
    persona_mix: dict[str, float]
    """How likely a family at this school is to have each persona."""


SCHOOLS: tuple[SeedSchool, ...] = (
    SeedSchool(
        "Maple Grove Elementary",
        "America/Chicago",
        {"young_kids": 4, "baby": 1, "quick_dinners": 2, "budget": 1, "home_baker": 1},
    ),
    SeedSchool(
        "Riverside Middle School",
        "America/New_York",
        {"quick_dinners": 2, "teens": 2, "health_minded": 1, "budget": 1},
    ),
    SeedSchool(
        "Cedar Ridge High School", "America/Denver", {"teens": 4, "quick_dinners": 2, "budget": 1}
    ),
    SeedSchool(
        "Lakeview Elementary",
        "America/Chicago",
        {"young_kids": 3, "plant_based": 2, "health_minded": 2},
    ),
    SeedSchool(
        "Hillcrest Academy",
        "America/Los_Angeles",
        {"health_minded": 3, "home_baker": 2, "plant_based": 1},
    ),
    SeedSchool(
        "Oak Hollow Elementary",
        "America/New_York",
        {"budget": 3, "young_kids": 2, "quick_dinners": 1, "baby": 1},
    ),
    SeedSchool(
        "Sunnyside Middle School",
        "America/Phoenix",
        {"home_baker": 2, "teens": 1, "quick_dinners": 2, "young_kids": 1},
    ),
    SeedSchool(
        "Westbrook High School",
        "America/Los_Angeles",
        {"teens": 3, "health_minded": 1, "plant_based": 1, "budget": 1},
    ),
)


@dataclass(frozen=True)
class SeedUser:
    name: str
    school: int | None
    """1-based index into `SCHOOLS`, or `None` for a user with no linked school."""
    personas: tuple[str, ...] = ()
    """Fixed personas; empty means drawn from the school's mix."""
    excludes: frozenset[str] = field(default_factory=frozenset[str])
    """Extra tags this household never buys (an allergy, for example)."""
    shops: bool = True

    @property
    def email(self) -> str:
        local = "".join(c for c in self.name.lower().replace(" ", ".") if c.isalnum() or c == ".")
        return f"{local}@example.com"


# User IDs follow this order. Users 1 and 2 share a school, which makes them a pair for
# cross-account checks; user 3 has a peanut allergy saved as guidance.
USERS: tuple[SeedUser, ...] = (
    SeedUser("Maya Thompson", 1, ("young_kids", "quick_dinners")),
    SeedUser("Daniel Okafor", 1, ("quick_dinners", "budget")),
    SeedUser("Priya Raman", 4, ("young_kids", "health_minded"), frozenset({"peanut"})),
    SeedUser("Luis Herrera", 2),
    SeedUser("Hannah Kim", 3),
    SeedUser("Marcus Bell", 6),
    SeedUser("Sofia Rossi", 5),
    SeedUser("Ethan Brooks", 7),
    SeedUser("Aisha Rahman", 8),
    SeedUser("Noah Fischer", 1),
    SeedUser("Grace Liu", 4),
    SeedUser("Caleb Turner", 3),
    SeedUser("Isabella Cruz", 6),
    SeedUser("Owen Patel", 2),
    SeedUser("Zoe Martin", 5, ("home_baker", "health_minded")),
    SeedUser("Jamal Washington", 3),
    SeedUser("Emily Novak", 7, ("home_baker", "young_kids")),
    SeedUser("Diego Alvarez", 6),
    SeedUser("Lily Chen", 4, ("plant_based",)),
    SeedUser("Ryan O'Connor", 8),
    SeedUser("Fatima Haddad", 2),
    SeedUser("Lucas Moreau", 1),
    SeedUser("Chloe Bennett", 5),
    SeedUser("Andre Silva", 3),
    SeedUser("Megan Price", 6, ("baby", "budget")),
    SeedUser("Kenji Watanabe", 8),
    SeedUser("Ava Robinson", 7),
    SeedUser("Samuel Adeyemi", 2),
    SeedUser("Nina Kowalski", 4),
    SeedUser("Tyler Grant", 8, ("teens", "plant_based")),
    SeedUser("Rosa Delgado", 6),
    SeedUser("Ben Carter", 1),
    SeedUser("Leah Goldberg", 5),
    SeedUser("Omar Siddiqui", 7),
    SeedUser("Claire Dubois", 2),
    SeedUser("Victor Nguyen", 3),
    SeedUser("Hailey Morgan", 1, ("baby", "young_kids")),
    SeedUser("Jordan Ellis", None, ("budget", "quick_dinners")),
    SeedUser("Nora Newcomer", None, shops=False),
)

ESTABLISHED_USER_ID = 1
PARALLEL_USER_ID = 2
GUIDANCE_USER_ID = 3
NEW_USER_ID = len(USERS)
NO_SCHOOL_TIME_ZONE = "America/New_York"

GUIDANCE: dict[int, tuple[str, ...]] = {
    # An allergy note must not turn a product recommendation into a safety guarantee.
    GUIDANCE_USER_ID: ("Allergic to peanuts.", "Kids prefer fruity snacks."),
    ESTABLISHED_USER_ID: ("Shops for a family of four.",),
    PARALLEL_USER_ID: ("Prefers quick weeknight meals.",),
    15: ("Bakes with the kids most weekends.",),
    19: ("Keeps a fully plant-based kitchen.",),
}
AVOIDED: dict[int, tuple[str, ...]] = {
    PARALLEL_USER_ID: ("Sour Cream",),
    GUIDANCE_USER_ID: ("Peanut Butter",),
}

# (product, title, description, starts in days, ends in days), relative to setup.
# Most are running now and end on different days; the last two are over and upcoming.
PROMOTIONS: tuple[tuple[str, str, str, int, int], ...] = (
    (
        "Macaroni & Cheese Box",
        "50 bonus Pennies",
        "Earn 50 bonus Pennies on every Macaroni & Cheese Box this week.",
        -7,
        5,
    ),
    (
        "Fruit Snacks Pouches",
        "Double Pennies",
        "Earn double Pennies on Fruit Snacks Pouches.",
        -7,
        12,
    ),
    ("Corn Tortillas", "Taco night bonus", "Earn 30 bonus Pennies on Corn Tortillas.", -3, 20),
    (
        "Canned Pumpkin",
        "Baking season bonus",
        "Earn 40 bonus Pennies on every can of pumpkin.",
        -10,
        30,
    ),
    ("Whole Wheat Penne", "Pasta night", "Earn 25 bonus Pennies on Whole Wheat Penne.", -1, 45),
    (
        "Applesauce Pouches",
        "Lunchbox bonus",
        "Earn double Pennies on Applesauce Pouches all season.",
        -14,
        60,
    ),
    ("Sunscreen Lotion", "Summer bonus", "Earn 75 bonus Pennies on Sunscreen Lotion.", -150, -60),
    (
        "Hot Cocoa Mix",
        "Cocoa weekend",
        "Earn double Pennies on Hot Cocoa Mix this weekend.",
        10,
        17,
    ),
)

STAPLES = ("Whole Milk", "Large Eggs", "Whole Wheat Bread")
DAIRY_FREE_MILK = "Oat Milk"


def referral_code(user_id: int) -> str:
    """A stable six-character code per user, such as XY7G4D."""
    alphabet = string.ascii_uppercase + string.digits
    digest = hashlib.sha256(f"penny-referral-{user_id}".encode()).digest()
    return "".join(alphabet[b % len(alphabet)] for b in digest[:6])


def seasonal_weight(product: SeedProduct, day: date) -> float:
    """More sunscreen in summer, lunchbox snacks at back-to-school, baking in the fall."""
    weight = 1.0
    if "summer" in product.tags:
        weight *= 3.0 if day.month in (6, 7, 8) else 0.3
    if "autumn" in product.tags:
        weight *= 3.0 if day.month in (10, 11) else 0.5
    if "baking" in product.tags and day.month in (11, 12):
        weight *= 2.0
    if "cold" in product.tags:
        weight *= 2.5 if day.month in (11, 12, 1, 2) else 0.6
    if "lunchbox" in product.tags and day.month in (8, 9):
        weight *= 2.0
    return weight


@dataclass(frozen=True)
class Household:
    user_id: int
    zone: ZoneInfo
    personas: tuple[Persona, ...]
    allowed: tuple[SeedProduct, ...]


def affinity(household: Household, product: SeedProduct) -> float:
    return 0.3 + sum(
        persona.affinity.get(tag, 0.0) for persona in household.personas for tag in product.tags
    )


def weighted_pick(
    rng: random.Random, products: Sequence[SeedProduct], weights: Sequence[float], k: int
) -> list[SeedProduct]:
    """`k` distinct products, chosen by weight."""
    pool, chosen = list(products), list[SeedProduct]()
    pool_weights = list(weights)
    for _ in range(min(k, len(pool))):
        index = rng.choices(range(len(pool)), weights=pool_weights)[0]
        chosen.append(pool.pop(index))
        pool_weights.pop(index)
    return chosen


def household_for(user_id: int, seed_user: SeedUser, rng: random.Random) -> Household:
    if seed_user.personas:
        names = seed_user.personas
    else:
        mix = SCHOOLS[(seed_user.school or 1) - 1].persona_mix
        count = 1 if rng.random() < 0.4 else 2
        names = tuple(dict.fromkeys(rng.choices(list(mix), weights=list(mix.values()), k=count)))
    personas = tuple(PERSONAS[name] for name in names)
    excluded = seed_user.excludes.union(*(p.excludes for p in personas))
    avoided = set(AVOIDED.get(user_id, ()))
    allowed = tuple(p for p in PRODUCTS if not (p.tags & excluded) and p.name not in avoided)
    return Household(user_id, user_zone(seed_user), personas, allowed)


def user_zone(seed_user: SeedUser) -> ZoneInfo:
    if seed_user.school is None:
        return ZoneInfo(NO_SCHOOL_TIME_ZONE)
    return ZoneInfo(SCHOOLS[seed_user.school - 1].time_zone)


def shopping_trips(
    household: Household, rng: random.Random, today: date
) -> list[tuple[datetime, SeedProduct, int]]:
    """Every purchase over the history window: (time, product, quantity)."""
    low = min(p.trip_days[0] for p in household.personas)
    high = max(p.trip_days[1] for p in household.personas)
    weights = [affinity(household, p) for p in household.allowed]
    shelf = [p for p in household.allowed if "household" not in p.tags]
    shelf_weights = [affinity(household, p) for p in shelf]
    favorites = weighted_pick(rng, shelf, shelf_weights, rng.randint(3, 5))
    milk = (
        "Whole Milk" if any(p.name == "Whole Milk" for p in household.allowed) else DAIRY_FREE_MILK
    )
    staples = [p for p in household.allowed if p.name in (*STAPLES, milk)]
    restocks = [p for p in household.allowed if "household" in p.tags]
    bulk_buyer = PERSONAS["budget"] in household.personas

    purchases: list[tuple[datetime, SeedProduct, int]] = []
    day = today - timedelta(days=HISTORY_DAYS - rng.randint(0, high))
    while day < today:
        basket = [p for p in favorites if rng.random() < 0.55]
        basket += [p for p in staples if rng.random() < 0.2]
        if restocks and rng.random() < 0.2:
            basket.append(rng.choice(restocks))
        seasonal = [
            w * seasonal_weight(p, day) for p, w in zip(household.allowed, weights, strict=True)
        ]
        basket += weighted_pick(rng, household.allowed, seasonal, rng.randint(1, 4))
        at = datetime.combine(day, time(rng.randint(9, 19), rng.randint(0, 59)), household.zone)
        for product in dict.fromkeys(basket):
            many = bulk_buyer or "lunchbox" in product.tags or product in staples
            quantity = rng.choice((1, 1, 2, 3)) if many else rng.choice((1, 1, 1, 2))
            purchases.append((at.astimezone(UTC), product, quantity))
        day += timedelta(days=rng.randint(low, high))
    return purchases


async def seed_schools(session: AsyncSession, now: datetime) -> None:
    for school_id, school in enumerate(SCHOOLS, start=1):
        if await session.get(School, school_id) is None:
            session.add(
                School(id=school_id, name=school.name, created_at=now - timedelta(days=900))
            )
    await session.flush()


async def seed_users(session: AsyncSession, now: datetime, rng: random.Random) -> None:
    for user_id, seed_user in enumerate(USERS, start=1):
        joined = now - timedelta(days=HISTORY_DAYS + rng.randint(5, 400))
        if user_id == NEW_USER_ID:
            joined = now - timedelta(days=1)
        if await session.get(User, user_id) is None:
            session.add(
                User(
                    id=user_id,
                    school_id=seed_user.school,
                    name=seed_user.name,
                    email=seed_user.email,
                    time_zone=user_zone(seed_user).key,
                    created_at=joined,
                )
            )
    await session.flush()


async def seed_products(session: AsyncSession, now: datetime) -> dict[str, int]:
    for product_id, product in enumerate(PRODUCTS, start=1):
        if await session.get(Product, product_id) is None:
            session.add(
                Product(
                    id=product_id,
                    name=product.name,
                    category=product.category,
                    description=product.description,
                    price=product.price,
                    image_url=product_image_url(product.name),
                    created_at=now - timedelta(days=365),
                )
            )
    await session.flush()
    rows = await session.execute(select(Product.name, Product.id))
    return {name: product_id for name, product_id in rows}


async def seed_promotions(session: AsyncSession, products: dict[str, int], now: datetime) -> None:
    titles = set((await session.scalars(select(Promotion.title))).all())
    for product_name, title, description, starts, ends in PROMOTIONS:
        if title not in titles:
            session.add(
                Promotion(
                    product_id=products[product_name],
                    title=title,
                    description=description,
                    starts_at=now + timedelta(days=starts),
                    ends_at=now + timedelta(days=ends),
                )
            )


async def seed_referral_codes(session: AsyncSession, now: datetime) -> None:
    """Every user except the new user gets a code (the "no code" case)."""
    have = set((await session.scalars(select(ReferralCode.user_id))).all())
    for user_id in range(1, len(USERS) + 1):
        if user_id != NEW_USER_ID and user_id not in have:
            session.add(ReferralCode(user_id=user_id, code=referral_code(user_id), created_at=now))


async def seed_purchases(
    session: AsyncSession, products: dict[str, int], now: datetime, rng: random.Random
) -> None:
    """The purchase history, generated once: an existing history is left alone."""
    if await session.scalar(select(func.count()).select_from(Purchase)):
        return
    today = now.date()
    for user_id, seed_user in enumerate(USERS, start=1):
        household = household_for(user_id, seed_user, rng)
        if not seed_user.shops:
            continue
        for at, product, quantity in shopping_trips(household, rng, today):
            session.add(
                Purchase(
                    user_id=user_id,
                    product_id=products[product.name],
                    quantity=quantity,
                    purchased_at=at,
                )
            )


async def seed_memory(session: AsyncSession, products: dict[str, int], now: datetime) -> None:
    for user_id, notes in GUIDANCE.items():
        have = set(
            await session.scalars(select(GuidanceNote.text).where(GuidanceNote.user_id == user_id))
        )
        for text in notes:
            if text not in have:
                session.add(
                    GuidanceNote(
                        user_id=user_id, text=text, expires_at=None, created_at=now, updated_at=now
                    )
                )
    for user_id, names in AVOIDED.items():
        for name in names:
            if await session.get(AvoidedProduct, (user_id, products[name])) is None:
                session.add(
                    AvoidedProduct(user_id=user_id, product_id=products[name], created_at=now)
                )


async def seed(session: AsyncSession) -> None:
    now = datetime.now(UTC).replace(microsecond=0)
    rng = random.Random(RANDOM_SEED)
    async with session.begin():
        await seed_schools(session, now)
        await seed_users(session, now, rng)
        products = await seed_products(session, now)
        await seed_promotions(session, products, now)
        await seed_referral_codes(session, now)
        await seed_purchases(session, products, now, rng)
        await seed_memory(session, products, now)
