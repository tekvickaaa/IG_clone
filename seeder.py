from database import SessionLocal
from models import User, Post, Follow, PostLike
import random
import string


try:
    db = SessionLocal()

    for i in range(15):
        username = ''.join(random.choices(string.ascii_letters, k=8))
        password = ''.join(random.choices(string.__all__, k=12))
        nickname = username.lower()

        db.add(User(
            username=username,
            nickname=nickname,
            hashed_password=password,
            bio=f"my name is {username}",
            song_id=str(random.randint(1, 1000)),
        ))
    db.commit()
    db.close()

    try:
        for i in range(25):
            title = ''.join(random.choices(string.ascii_letters + ' ', k=20))
            description = ''.join(random.choices(string.ascii_letters + ' ', k=100))

            db.add(Post(
                user_id=random.randint(1, 15),
                title=title,
                description=description,
            ))
            db.refresh(Post)

        db.commit()
        db.close()

        db.query(Post).all()
    except Exception as e:
        print("Error seeding posts:", e)


    for i in range(10):
        followers_id = random.randint(1, 15)
        following_id = random.randint(1, 15)
        db.add(Follow(
            follower_id=followers_id,
            following_id=following_id,
        ))
        follower = db.query(User).get(followers_id)
        following = db.query(User).get(following_id)

        follower.following_count += 1
        following.followers_count += 1


    for i in range(70):
        post_id = random.randint(1, 25)
        db.add(PostLike(
            user_id=random.randint(1, 15),
            post_id=post_id
        ))
        post = db.query(Post).get(post_id)
        post.like_count+=1

    db.commit()
    db.close()
except Exception as e:
    print("Error seeding database:", e)
