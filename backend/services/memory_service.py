from sqlalchemy.orm import Session
from models.database import Conversation, UserProfile, Goal, EpisodicMemory
from models import schemas
import json
from datetime import datetime

class MemoryService:
    def __init__(self, db: Session):
        self.db = db

    def save_conversation(self, user_message: str, assistant_message: str, importance_score: float = 0.0) -> Conversation:
        conversation = Conversation(
            user_message=user_message,
            assistant_message=assistant_message,
            importance_score=importance_score
        )
        self.db.add(conversation)
        self.db.commit()
        self.db.refresh(conversation)
        return conversation

    def get_recent_conversations(self, limit: int = 10):
        return self.db.query(Conversation).order_by(Conversation.timestamp.desc()).limit(limit).all()

    def get_user_profile(self, key: str):
        return self.db.query(UserProfile).filter(UserProfile.key == key).first()
    
    def update_user_profile(self, key: str, value: str, category: str = None):
        profile = self.get_user_profile(key)
        if profile:
            profile.value = value
            if category:
                profile.category = category
        else:
            profile = UserProfile(key=key, value=value, category=category)
            self.db.add(profile)
        self.db.commit()
        return profile


    def get_all_user_profiles(self):
        return self.db.query(UserProfile).all()

    def get_active_goals(self):
        return self.db.query(Goal).filter(Goal.status == 'active').all()

    def construct_system_context(self) -> str:
        """
        Builds a context string from stored memories to be injected into the system prompt.
        """
        profiles = self.get_all_user_profiles()
        goals = self.get_active_goals()
        
        context_parts = []
        
        if profiles:
            context_parts.append("## User Profile Information:")
            for p in profiles:
                context_parts.append(f"- {p.key}: {p.value}")
        
        if goals:
            context_parts.append("\n## Current Goals:")
            for g in goals:
                deadline = f"(Deadline: {g.deadline})" if g.deadline else ""
                context_parts.append(f"- {g.title} {deadline}: {g.description or ''}")
        
        return "\n".join(context_parts)

    def save_extracted_information(self, extraction_result: dict):
        """
        Saves extracted user profiles and goals to the database.
        """
        # Save User Profiles
        for p in extraction_result.get("user_profile", []):
            self.update_user_profile(
                key=p.get("key"),
                value=p.get("value"),
                category=p.get("category")
            )
            print(f"Saved Profile: {p.get('key')} -> {p.get('value')}")
            
        # Save Goals
        for g in extraction_result.get("goals", []):
            # Simple deduplication check by title, otherwise create new
            existing = self.db.query(Goal).filter(Goal.title == g.get("title"), Goal.status == 'active').first()
            if not existing:
                new_goal = Goal(
                    title=g.get("title"),
                    description=g.get("description"),
                    priority=g.get("priority"),
                    # deadline processing would be needed here for string -> date
                )
                self.db.add(new_goal)
                print(f"New Goal Created: {g.get('title')}")
        
        self.db.commit()
