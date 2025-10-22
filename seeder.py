from database import SessionLocal
from models import User, Post, Follow
import random
import string


try:
    db = SessionLocal()

    for i in range(15):
        username = ''.join(random.choices(string.ascii_letters, k=8))
        password = ''.join(random.choices(string.__all__, k=12))

        db.add(User(
            username=username,
            hashed_password=password,
            bio=f"my name is {username}",
            song_id=random.randint(1, 1000),
        ))
    db.commit()
    db.close()

    for i in range(15):
        title = ''.join(random.choices(string.ascii_letters + ' ', k=20))
        description = ''.join(random.choices(string.ascii_letters + ' ', k=100))

        db.add(Post(
            user_id=random.randint(1, 15),
            title=title,
            description=description,
        ))

    db.commit()
    db.close()

    for i in range(10):
        db.add(Follow(
            follower_id=random.randint(1, 15),
            following_id=random.randint(1, 15)
        ))

    db.commit()
    db.close()
except Exception as e:
    print("Error seeding database:", e)
