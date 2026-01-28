from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from . import models, schemas
from . import github, gpt_location
from .database import get_db, engine, SessionLocal
import asyncio
import traceback
from typing import List

models.Base.metadata.create_all(bind=engine)

app = FastAPI()


def get_saved_since_value(db_session):
    """Get saved 'since' value from database, or return 0 if not found"""
    state = db_session.query(models.FetchState).filter(models.FetchState.key == "github_since").first()
    if state:
        return state.since_value
    return 0


def save_since_value(db_session, since_value):
    """Save 'since' value to database"""
    state = db_session.query(models.FetchState).filter(models.FetchState.key == "github_since").first()
    if state:
        state.since_value = since_value
    else:
        state = models.FetchState(key="github_since", since_value=since_value)
        db_session.add(state)
    db_session.commit()
    print(f"[INFO] Saved since value: {since_value}")


@app.get("/git_users")
async def run():
    """Process GitHub users and save all users with country information to database"""
    stats = {
        "total_fetched": 0,
        "saved": 0,
        "errors": 0,
        "skipped_no_email": 0,
        "processed_users": [],
        "countries": {}  # Track users by country
    }
    
    db_session = SessionLocal()
    
    try:
        # Load saved 'since' value from database
        since = get_saved_since_value(db_session)
        print(f"[INFO] Starting from saved since value: {since}")
        
        async def process_user(user_data):
            """Process a single user"""
            user_db_session = SessionLocal()
            username = user_data.get("login", "unknown")
            
            try:
                # Get user details
                details = github.get_user_details(username)
                if not details or isinstance(details, dict) and "message" in details:
                    print(f"[ERROR] Failed to get details for @{username}: {details}")
                    stats["errors"] += 1
                    return
                
                location = details.get("location", "") or ""
                email = details.get("email")
                name = details.get("name") or username
                
                print(f"[INFO] Processing @{username} - Location: '{location}', Email: {email or 'None'}")

                # Try to get email from commits if not in profile
                if not email:
                    print(f"[INFO] No email in profile for @{username}, checking commits...")
                    name, email = github.get_email_from_commits(username)
                    if email:
                        print(f"[INFO] Found email from commits for @{username}: {email}")
                
                # Get country code or timezone
                country_code = None
                timezone = None
                
                if not location:
                    # If location is empty, try to get timezone from commits
                    print(f"[INFO] Location is empty for @{username}, checking commits for timezone...")
                    timezone = github.get_timezone_from_commits(username)
                    if timezone:
                        print(f"[Timezone] @{username} — Timezone: {timezone}")
                    else:
                        print(f"[Timezone] @{username} — No timezone found in commits (no verification data)")
                else:
                    # If location exists, get country code from location
                    country_code = await gpt_location.get_country_code(location)
                    if country_code:
                        print(f"[Location] @{username} — '{location}' → Country: {country_code}")
                    else:
                        print(f"[Location] @{username} — '{location}' → Country: Unknown")
                
                if not email:
                    print(f"[Skip] No email found for @{username}")
                    stats["skipped_no_email"] += 1
                    return

                # Check if user already exists by git_username or email
                existing_user = user_db_session.query(models.User).filter(
                    (models.User.git_username == username) | (models.User.email == email)
                ).first()
                if existing_user:
                    print(f"[Skip] User @{username} (email: {email}) already exists in database")
                    return

                # Save to database
                try:
                    # Use timezone if available, otherwise use country_code
                    country_or_timezone = timezone if timezone else country_code
                    
                    new_user = models.User(
                        name=name, 
                        location=location, 
                        email=email, 
                        git_username=username,
                        country=country_or_timezone
                    )
                    user_db_session.add(new_user)
                    user_db_session.commit()
                    stats["saved"] += 1
                    
                    # Track by country/timezone
                    country_key = country_or_timezone or "Unknown"
                    stats["countries"][country_key] = stats["countries"].get(country_key, 0) + 1
                    
                    stats["processed_users"].append({
                        "username": username,
                        "name": name,
                        "email": email,
                        "location": location,
                        "country": country_or_timezone
                    })
                    print(f"[SUCCESS] Saved user: {name} ({email}) with {'timezone' if timezone else 'country'}: {country_or_timezone or 'Unknown'}")
                except IntegrityError:
                    user_db_session.rollback()
                    print(f"[Skip] Duplicate user @{username} detected (database constraint violation)")
                    return

            except Exception as e:
                print(f"[ERROR] Error processing user @{username}: {e}")
                traceback.print_exc()
                stats["errors"] += 1
            finally:
                user_db_session.close()

        # Continuously fetch and process users batch by batch
        print("[INFO] Starting continuous fetch and process cycle...")
        
        while True:
            try:
                # Fetch a batch of users
                print(f"[INFO] Fetching users with since={since}...")
                users, next_since = github.get_active_github_users(since)
                
                if not users:
                    print(f"[INFO] No more users found. Stopping fetch.")
                    # Save current since value before stopping
                    save_since_value(db_session, since)
                    break
                
                if isinstance(users, dict) and "message" in users:
                    print(f"[ERROR] GitHub API error: {users.get('message')}")
                    # Save current since value on error
                    save_since_value(db_session, since)
                    break
                
                stats["total_fetched"] += len(users)
                print(f"[INFO] Fetched {len(users)} users (total fetched: {stats['total_fetched']})")
                
                # Process this batch immediately
                print(f"[INFO] Processing batch of {len(users)} users...")
                await asyncio.gather(*[process_user(u) for u in users], return_exceptions=True)
                print(f"[INFO] Finished processing batch. Stats: saved={stats['saved']}, errors={stats['errors']}")
                
                # Update 'since' for next iteration
                if next_since is None:
                    print(f"[INFO] No next_since value returned. Stopping fetch.")
                    save_since_value(db_session, since)
                    break
                
                # Save the next_since value after processing this batch
                since = next_since
                save_since_value(db_session, since)
                
                # If we got less than 100 users, we've reached the end
                if len(users) < 100:
                    print(f"[INFO] Received less than 100 users. Reached end of pagination.")
                    break
                    
            except Exception as e:
                print(f"[ERROR] Error in fetch/process cycle: {e}")
                traceback.print_exc()
                # Save current since value on error
                save_since_value(db_session, since)
                stats["errors"] += 1
                break
        
        return {
            "status": "complete",
            "stats": stats,
            "message": f"Processed {stats['total_fetched']} users. Saved {stats['saved']} users from {len(stats['countries'])} countries. Last since value: {since}",
            "last_since_value": since
        }
        
    except Exception as e:
        print(f"[ERROR] Fatal error: {e}")
        traceback.print_exc()
        # Save current since value on fatal error
        try:
            save_since_value(db_session, since)
        except:
            pass
        return {
            "status": "error",
            "message": str(e),
            "stats": stats,
            "last_since_value": since if 'since' in locals() else None
        }
    finally:
        db_session.close()


@app.get("/users", response_model=List[dict])
def get_users(db: Session = Depends(get_db)):
    """Get all saved users from database"""
    users = db.query(models.User).all()
    return [
        {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "location": user.location,
            "git_username": user.git_username,
            "country": user.country,
            "contacted": user.contacted,
            "responded": user.responded
        }
        for user in users
    ]


@app.get("/users/count")
def get_user_count(db: Session = Depends(get_db)):
    """Get count of saved users"""
    count = db.query(models.User).count()
    return {"total_users": count}


@app.get("/users/by-country")
def get_users_by_country(db: Session = Depends(get_db)):
    """Get count of users grouped by country"""
    from sqlalchemy import func
    results = db.query(
        models.User.country,
        func.count(models.User.id).label('count')
    ).group_by(models.User.country).all()
    
    return {
        "by_country": {country or "Unknown": count for country, count in results},
        "total_countries": len(results),
        "total_users": sum(count for _, count in results)
    }


@app.get("/users/country/{country_code}")
def get_users_by_country_code(country_code: str, db: Session = Depends(get_db)):
    """Get all users from a specific country"""
    users = db.query(models.User).filter(models.User.country == country_code.upper()).all()
    return [
        {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "location": user.location,
            "git_username": user.git_username,
            "country": user.country,
            "contacted": user.contacted,
            "responded": user.responded
        }
        for user in users
    ]
