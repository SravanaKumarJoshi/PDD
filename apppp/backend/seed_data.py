"""Database Seeding Script for BioPolymer AI Platform.

Populates initial seed users and sample biomedical project runs into the database.
"""

import asyncio
from datetime import datetime, timezone

from sqlalchemy import select

from app.database import async_session, create_all_tables
from app.models.user import User
from app.models.project import Project

SEED_USERS = [
    {
        "id": "11111111-1111-1111-1111-111111111111",
        "auth_provider_id": "dev-user-001",
        "email": "user@biopolymer.ai",
        "display_name": "Demo Researcher",
        "role": "user",
    },
    {
        "id": "22222222-2222-2222-2222-222222222222",
        "auth_provider_id": "dev-admin-001",
        "email": "admin@biopolymer.ai",
        "display_name": "Dr. Sarah Admin",
        "role": "admin",
    },
    {
        "id": "33333333-3333-3333-3333-333333333333",
        "auth_provider_id": "dev-researcher-001",
        "email": "researcher@biopolymer.ai",
        "display_name": "Prof. Alex Chen",
        "role": "researcher",
    },
]

SEED_PROJECTS = [
    {
        "id": "p1111111-1111-1111-1111-111111111111",
        "user_id": "11111111-1111-1111-1111-111111111111",
        "title": "Wound Dressing Barrier Study",
        "requirements_json": '{"application_type": "Wound dressing packaging", "target_tensile_strength": 80.0, "target_flexibility": 7.0, "min_biocompatibility": 8}',
        "results_json": '{"top_recommendations": ["Chitosan", "Alginate", "Hyaluronic Acid"]}',
    },
    {
        "id": "p2222222-2222-2222-2222-222222222222",
        "user_id": "11111111-1111-1111-1111-111111111111",
        "title": "Drug Delivery Matrix Run #1",
        "requirements_json": '{"application_type": "Drug delivery film", "target_biodegradation_days": [30, 90], "requires_antimicrobial": true}',
        "results_json": '{"top_recommendations": ["Nanocellulose", "Chitosan"]}',
    },
]


async def seed_database():
    print("Creating tables if not exists...")
    await create_all_tables()

    async with async_session() as session:
        print("\n--- Seeding Users ---")
        for udata in SEED_USERS:
            res = await session.execute(
                select(User).where(User.auth_provider_id == udata["auth_provider_id"])
            )
            existing = res.scalar_one_or_none()
            if not existing:
                user = User(
                    id=udata["id"],
                    auth_provider_id=udata["auth_provider_id"],
                    email=udata["email"],
                    display_name=udata["display_name"],
                    role=udata["role"],
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                )
                session.add(user)
                print(f"  + Added User: {udata['email']} (Role: {udata['role']}, Auth ID: {udata['auth_provider_id']})")
            else:
                print(f"  = User already exists: {udata['email']} (Auth ID: {udata['auth_provider_id']})")

        print("\n--- Seeding Sample Projects ---")
        for pdata in SEED_PROJECTS:
            res = await session.execute(
                select(Project).where(Project.id == pdata["id"])
            )
            existing = res.scalar_one_or_none()
            if not existing:
                proj = Project(
                    id=pdata["id"],
                    user_id=pdata["user_id"],
                    title=pdata["title"],
                    requirements_json=pdata["requirements_json"],
                    results_json=pdata["results_json"],
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                )
                session.add(proj)
                print(f"  + Added Project: {pdata['title']}")
            else:
                print(f"  = Project already exists: {pdata['title']}")

        await session.commit()
        print("\n✅ Database seeding complete!")


if __name__ == "__main__":
    asyncio.run(seed_database())
