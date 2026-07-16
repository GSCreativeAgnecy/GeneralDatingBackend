import asyncio
import random
import sys
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, delete

from core.database import async_session, init_db
from core.security import hash_password
from models import (
    User, UserPhoto, UserLanguage, UserPreferences, Swipe, Match, Message,
    BlockReport, Subscription, Notification, FamilyShare,
)
from female_names_data import FEMALE_USERS, MALE_FIRST, MALE_LAST, CITIES, random_male_full

INTENTS = ["lets_see", "serious_relationship", "casual", "friendship", "marriage"]
BIOS = [
    "Love traveling and trying new cuisines.",
    "Dog person, coffee addict, looking for genuine connections.",
    "Into fitness, music, and late-night conversations.",
    "Engineer by day, dreamer by night.",
    "Looking for someone who can match my energy.",
    "Foodie, bookworm, and occasional dancer.",
    "Exploring life one city at a time.",
    "Simple living, high thinking.",
    "Life is better with good company.",
    "Making memories, one day at a time.",
]
LANGUAGES = ["en", "hi", "te", "ta", "mr", "bn", "gu", "kn", "ml"]
COLLEGES = ["IIT Delhi", "BITS Pilani", "Delhi University", "Mumbai University", "Anna University", "IISc Bangalore", "NIT Trichy", "JNU Delhi", "BHU Varanasi", "Symbiosis Pune"]
WORKPLACES = ["Google", "Microsoft", "Infosys", "TCS", "Wipro", "Amazon", "Flipkart", "Reliance", "Tata Group", "Self-employed"]
RELIGIONS = ["Hindu", "Muslim", "Christian", "Sikh", "Jain", "Buddhist", "Parsi"]
CASTE_OPTIONS = ["General", "OBC", "SC", "ST", "Vanniyar", "Brahmin", "Kshatriya", "Vaishya", "Reddy", "Maratha"]
EARNINGS_OPTIONS = ["2-5 LPA", "5-10 LPA", "10-20 LPA", "20-30 LPA", "30-50 LPA", "50+ LPA"]
MARITAL_OPTIONS = ["single", "single", "single", "single", "married", "divorced", "widowed", "separated"]
SIBLINGS_OPTIONS = ["1 brother", "1 sister", "2 brothers", "2 sisters", "1 brother, 1 sister", "Only child"]
FAV_COLORS = ["Blue", "Black", "Red", "Green", "Yellow", "Purple", "Pink", "White", "Orange", "Teal"]
FAV_SPORTS = ["Cricket", "Football", "Badminton", "Tennis", "Kabaddi", "Hockey", "Basketball", "Chess", "Volleyball", "Swimming"]
EDUCATION_OPTIONS = ["B.Tech", "MBA", "M.Tech", "BSc", "BA", "BCom", "MBBS", "CA", "PhD", "MA"]
MESSAGE_TEXTS = [
    "Hey, how are you?",
    "Loved your profile!",
    "What's up?",
    "How was your day?",
    "Nice to meet you here!",
    "You seem interesting.",
    "Any plans for the weekend?",
    "What kind of music do you like?",
    "Have you been to this cafe before?",
    "Your bio caught my eye.",
    "Hi there!",
    "Hello, how's it going?",
    "Love the vibe of your profile.",
    "Fellow foodie here!",
    "Your photos are amazing!",
]


def rand_dt(days_ago_max=30):
    return datetime.now(timezone.utc) - timedelta(
        days=random.randint(0, days_ago_max),
        hours=random.randint(0, 23),
        minutes=random.randint(0, 59),
    )


async def reset_dummy_data(db=None):
    own_session = db is None
    if own_session:
        await init_db()
        db = async_session()
    try:
        dummy_users = (await db.execute(
            select(User).where(User.phone_number.like("999000%"))
        )).scalars().all()
        if not dummy_users:
            return {"deleted": 0, "message": "No dummy data found."}
        dummy_ids = [u.id for u in dummy_users]
        await db.execute(delete(FamilyShare).where(FamilyShare.user_id.in_(dummy_ids)))
        await db.execute(delete(Notification).where(Notification.user_id.in_(dummy_ids)))
        await db.execute(delete(Subscription).where(Subscription.user_id.in_(dummy_ids)))
        await db.execute(delete(BlockReport).where(
            BlockReport.reporter_id.in_(dummy_ids) | BlockReport.reported_id.in_(dummy_ids)
        ))
        await db.execute(delete(Message).where(Message.sender_id.in_(dummy_ids)))
        await db.execute(delete(Match).where(
            Match.user1_id.in_(dummy_ids) | Match.user2_id.in_(dummy_ids)
        ))
        await db.execute(delete(Swipe).where(
            Swipe.swiper_id.in_(dummy_ids) | Swipe.swiped_id.in_(dummy_ids)
        ))
        await db.execute(delete(UserPreferences).where(UserPreferences.user_id.in_(dummy_ids)))
        await db.execute(delete(UserPhoto).where(UserPhoto.user_id.in_(dummy_ids)))
        await db.execute(delete(UserLanguage).where(UserLanguage.user_id.in_(dummy_ids)))
        await db.execute(delete(User).where(User.id.in_(dummy_ids)))
        if own_session:
            await db.commit()
        else:
            await db.flush()
        return {"deleted": len(dummy_users), "message": f"Deleted {len(dummy_users)} dummy users and related data."}
    finally:
        if own_session:
            await db.close()


async def generate(db=None, male_count=10, female_count=10):
    own_session = db is None
    if own_session:
        await init_db()
        db = async_session()
    try:
        existing = (await db.execute(
            select(User).where(User.phone_number.like("999000%"))
        )).scalars().all()
        if existing:
            yield {"type": "error", "message": f"Dummy data already exists ({len(existing)} users). Reset first."}
            return

        yield {"type": "progress", "message": "Creating users...", "step": "users", "current": 0, "total": male_count + female_count}

        from female_names_data import FEMALE_USERS
        total_females = len(FEMALE_USERS)

        # ── Create male users ──
        users = []
        for i in range(male_count):
            name = random_male_full()
            parts = name.split(" ", 1)
            u = User(
                phone_number=f"99900010{str(i).zfill(3)}",
                phone_verified=True,
                password_hash=hash_password("test123"),
                first_name=parts[0],
                last_name=parts[1] if len(parts) > 1 else "",
                date_of_birth=f"{random.randint(1990, 2002)}-{random.randint(1,12):02d}-{random.randint(1,28):02d}",
                gender="male",
                bio=random.choice(BIOS), intent=random.choice(INTENTS),
                city=random.choice(CITIES), college=random.choice(COLLEGES),
                workplace=random.choice(WORKPLACES), religion=random.choice(RELIGIONS),
                education=random.choice(EDUCATION_OPTIONS), occupation=random.choice(WORKPLACES),
                caste=random.choice(CASTE_OPTIONS), earnings=random.choice(EARNINGS_OPTIONS),
                marital_status=random.choice(MARITAL_OPTIONS), siblings=random.choice(SIBLINGS_OPTIONS),
                favorite_color=random.choice(FAV_COLORS), favorite_sports=random.choice(FAV_SPORTS),
                height_cm=random.randint(155, 185),
                profile_complete=True, is_active=True,
                photo_verified=random.choice([True, False]),
                is_premium=random.choice([True, False, False]),
                created_at=rand_dt(90), last_active=rand_dt(3),
            )
            db.add(u)
            users.append(u)
            await db.flush()
            photo_count = random.randint(3, 5)
            for j in range(photo_count):
                db.add(UserPhoto(user_id=u.id, photo_url=f"https://picsum.photos/seed/{u.first_name.replace(' ', '')}{j}/400/600", is_primary=(j==0), sort_order=j))
            for lang in random.sample(LANGUAGES, random.randint(1, 3)):
                db.add(UserLanguage(user_id=u.id, language=lang))
            yield {"type":"progress","message":f"Male {i+1}/{male_count}: {name}","step":"users","current":i+1,"total":male_count + female_count}

        # ── Create female users ──
        import itertools
        entries = list(itertools.islice(itertools.cycle(FEMALE_USERS), female_count))
        for i, entry in enumerate(entries):
            name = f"{entry['first']} {entry['last']}"
            dob_year = 2026 - entry['age']
            u = User(
                phone_number=f"99900020{str(i).zfill(3)}",
                phone_verified=True,
                password_hash=hash_password("test123"),
                first_name=entry['first'],
                last_name=entry['last'],
                date_of_birth=f"{dob_year}-{random.randint(1,12):02d}-{random.randint(1,28):02d}",
                gender="female",
                bio=random.choice(BIOS), intent=random.choice(INTENTS),
                city=random.choice(CITIES), college=random.choice(COLLEGES),
                workplace=random.choice(WORKPLACES), religion=random.choice(RELIGIONS),
                education=random.choice(EDUCATION_OPTIONS), occupation=random.choice(WORKPLACES),
                caste=random.choice(CASTE_OPTIONS), earnings=random.choice(EARNINGS_OPTIONS),
                marital_status=random.choice(MARITAL_OPTIONS), siblings=random.choice(SIBLINGS_OPTIONS),
                favorite_color=random.choice(FAV_COLORS), favorite_sports=random.choice(FAV_SPORTS),
                height_cm=entry['height'],
                profile_complete=True, is_active=True,
                photo_verified=random.choice([True, False]),
                is_premium=random.choice([True, False, False]),
                created_at=rand_dt(90), last_active=rand_dt(3),
            )
            db.add(u); users.append(u)
            await db.flush()
            photo_count = random.randint(3, 5)
            for j in range(photo_count):
                db.add(UserPhoto(user_id=u.id, photo_url=f"https://picsum.photos/seed/{entry['first'].lower()}{entry['last'].lower()}{j}/400/600", is_primary=(j==0), sort_order=j))
            for lang in random.sample(LANGUAGES, random.randint(1, 3)):
                db.add(UserLanguage(user_id=u.id, language=lang))
            yield {"type":"progress","message":f"Female {i+1}/{female_count}: {name}","step":"users","current":male_count+i+1,"total":male_count + female_count}

        await db.flush()

        yield {"type":"progress","message":"Creating preferences...","step":"prefs","current":0,"total":len(users)}
        for u in users:
            pref = UserPreferences(user_id=u.id, min_age=18, max_age=random.choice([35,40,45,50]),
                preferred_gender="female" if u.gender=="male" else "male", max_distance_km=random.choice([25,50,75,100]))
            db.add(pref)
        await db.flush()

        yield {"type":"progress","message":"Creating swipes...","step":"swipes","current":0,"total":1}
        males = [u for u in users if u.gender=="male"]
        females_ = [u for u in users if u.gender=="female"]
        swipes_created = 0
        for m in males:
            if not females_: break
            targets = random.sample(females_, min(4, len(females_)))
            for f in targets[:2]:
                db.add(Swipe(swiper_id=m.id, swiped_id=f.id, direction="like", created_at=rand_dt(60))); swipes_created += 1
            for f in targets[2:]:
                db.add(Swipe(swiper_id=m.id, swiped_id=f.id, direction="pass", created_at=rand_dt(60))); swipes_created += 1
        for f in females_:
            if not males: break
            targets = random.sample(males, min(4, len(males)))
            for m in targets[:2]:
                db.add(Swipe(swiper_id=f.id, swiped_id=m.id, direction="like", created_at=rand_dt(60))); swipes_created += 1
            for m in targets[2:]:
                db.add(Swipe(swiper_id=f.id, swiped_id=m.id, direction="pass", created_at=rand_dt(60))); swipes_created += 1
        await db.flush()

        yield {"type":"progress","message":"Creating matches...","step":"matches","current":0,"total":1}
        likes = (await db.execute(select(Swipe).where(Swipe.direction=="like"))).scalars().all()
        like_map = {}
        for s in likes: like_map.setdefault(s.swiper_id, set()).add(s.swiped_id)
        matches_created = 0; matches_list = []
        for swiper_id, swiped_set in like_map.items():
            for swiped_id in swiped_set:
                if swiper_id < swiped_id:
                    if like_map.get(swiped_id) and swiper_id in like_map[swiped_id]:
                        m = Match(user1_id=swiper_id, user2_id=swiped_id, matched_at=rand_dt(30), is_active=True)
                        db.add(m); matches_list.append(m); matches_created += 1
        await db.flush()

        yield {"type":"progress","message":"Creating messages...","step":"messages","current":0,"total": len(matches_list)}
        messages_created = 0
        for mi, match in enumerate(matches_list):
            participants = [match.user1_id, match.user2_id]
            num_msgs = random.randint(3, 15)
            base_time = match.matched_at or datetime.now(timezone.utc)
            for k in range(num_msgs):
                sender = random.choice(participants)
                db.add(Message(match_id=match.id, sender_id=sender, message_type="text",
                    content=random.choice(MESSAGE_TEXTS), is_read=random.choice([True,True,True,False]),
                    created_at=base_time + timedelta(minutes=random.randint(5, 60*24*7))))
                messages_created += 1
            if mi % 10 == 0:
                yield {"type":"progress","message":f"Messages {mi+1}/{len(matches_list)}","step":"messages","current":mi+1,"total":len(matches_list)}
        await db.flush()

        for _ in range(min(3, len(users))):
            reporter = random.choice(users)
            reported = random.choice([u for u in users if u.id!=reporter.id])
            db.add(BlockReport(reporter_id=reporter.id, reported_id=reported.id, reason=random.choice(["Inappropriate behavior","Fake profile","Spam"]), type="report", created_at=rand_dt(14)))

        premium_users = [u for u in users if u.is_premium]
        for u in premium_users[:5]:
            start = rand_dt(60)
            db.add(Subscription(user_id=u.id, plan_type=random.choice(["monthly","yearly"]), starts_at=start, ends_at=start+timedelta(days=30 if random.random()>0.5 else 365), is_active=True))

        if own_session: await db.commit()
        else: await db.flush()

        result = {"users": len(users), "matches": matches_created, "messages": messages_created, "swipes": swipes_created,
            "message": f"Created {len(users)} users, {matches_created} matches, {messages_created} messages, {swipes_created} swipes."}
        yield {"type":"done","result":result}
    except Exception as e:
        yield {"type":"error","message":str(e)}
    finally:
        if own_session: await db.close()


if __name__ == "__main__":
    if "--reset" in sys.argv:
        asyncio.run(reset_dummy_data())
    else:
        asyncio.run(generate())
