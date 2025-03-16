# src/utils/db.py
import os
import sqlite3
import json
import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime

logger = logging.getLogger(__name__)

# Global database connection
_db_connection = None

def init_db():
    """Initialize the database"""
    global _db_connection
    
    db_path = os.getenv("DATABASE_URL", "sqlite:///./recipe_agent.db")
    
    # Extract SQLite file path from URL
    if db_path.startswith("sqlite:///"):
        db_path = db_path[len("sqlite:///"):]
    
    # Create database directory if needed
    db_dir = os.path.dirname(db_path)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
    
    # Connect to database
    try:
        _db_connection = sqlite3.connect(db_path, check_same_thread=False)
        _db_connection.row_factory = sqlite3.Row
        
        # Create tables if they don't exist
        cursor = _db_connection.cursor()
        
        # Users table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            created_at TEXT NOT NULL,
            preferences TEXT
        )
        ''')
        
        # Monitored accounts table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS monitored_accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            instagram_username TEXT UNIQUE NOT NULL,
            added_at TEXT NOT NULL,
            last_checked TEXT
        )
        ''')
        
        # User-account subscriptions table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_account_subscriptions (
            user_id INTEGER,
            account_id INTEGER,
            subscribed_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (account_id) REFERENCES monitored_accounts (id),
            PRIMARY KEY (user_id, account_id)
        )
        ''')
        
        # Processed recipes table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS processed_recipes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_url TEXT UNIQUE NOT NULL,
            title TEXT NOT NULL,
            json_data TEXT NOT NULL,
            processed_at TEXT NOT NULL,
            pdf_path TEXT
        )
        ''')
        
        # Delivered recipes table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS delivered_recipes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            recipe_id INTEGER,
            delivered_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (recipe_id) REFERENCES processed_recipes (id),
            PRIMARY KEY (user_id, recipe_id)
        )
        ''')
        
        _db_connection.commit()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")
        raise

def get_db():
    """Get the database connection"""
    global _db_connection
    
    if _db_connection is None:
        init_db()
    
    return DatabaseManager(_db_connection)

class DatabaseManager:
    """Database manager class for recipe agent"""
    
    def __init__(self, connection):
        self.conn = connection
    
    def add_user(self, email: str, instagram_account: Optional[str] = None, preferences: Dict = None) -> int:
        """Add a new user and optionally subscribe to an Instagram account"""
        try:
            cursor = self.conn.cursor()
            
            # Add user
            cursor.execute(
                "INSERT INTO users (email, created_at, preferences) VALUES (?, ?, ?)",
                (email, datetime.now().isoformat(), json.dumps(preferences or {}))
            )
            
            user_id = cursor.lastrowid
            
            # Add monitored Instagram account if provided
            if instagram_account:
                account_id = self.add_monitored_account(instagram_account)
                
                # Create subscription
                cursor.execute(
                    "INSERT INTO user_account_subscriptions (user_id, account_id, subscribed_at) VALUES (?, ?, ?)",
                    (user_id, account_id, datetime.now().isoformat())
                )
            
            self.conn.commit()
            logger.info(f"Added user with email: {email}")
            return user_id
        except sqlite3.IntegrityError:
            # User already exists, find and return their ID
            cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
            result = cursor.fetchone()
            
            if result:
                user_id = result[0]
                
                # Update preferences if provided
                if preferences:
                    cursor.execute(
                        "UPDATE users SET preferences = ? WHERE id = ?",
                        (json.dumps(preferences), user_id)
                    )
                
                # Add subscription if instagram account provided
                if instagram_account:
                    account_id = self.add_monitored_account(instagram_account)
                    
                    # Check if subscription already exists
                    cursor.execute(
                        "SELECT 1 FROM user_account_subscriptions WHERE user_id = ? AND account_id = ?",
                        (user_id, account_id)
                    )
                    
                    if not cursor.fetchone():
                        cursor.execute(
                            "INSERT INTO user_account_subscriptions (user_id, account_id, subscribed_at) VALUES (?, ?, ?)",
                            (user_id, account_id, datetime.now().isoformat())
                        )
                
                self.conn.commit()
                logger.info(f"Updated existing user with email: {email}")
                return user_id
            else:
                logger.error(f"Error finding user with email: {email}")
                return -1
        except Exception as e:
            logger.error(f"Error adding user: {str(e)}")
            self.conn.rollback()
            return -1
    
    def add_monitored_account(self, instagram_username: str) -> int:
        """Add a monitored Instagram account if it doesn't exist"""
        try:
            cursor = self.conn.cursor()
            
            # Check if account already exists
            cursor.execute(
                "SELECT id FROM monitored_accounts WHERE instagram_username = ?",
                (instagram_username,)
            )
            
            result = cursor.fetchone()
            
            if result:
                return result[0]
            
            # Add new account
            cursor.execute(
                "INSERT INTO monitored_accounts (instagram_username, added_at) VALUES (?, ?)",
                (instagram_username, datetime.now().isoformat())
            )
            
            account_id = cursor.lastrowid
            self.conn.commit()
            
            logger.info(f"Added monitored account: {instagram_username}")
            return account_id
        except Exception as e:
            logger.error(f"Error adding monitored account: {str(e)}")
            self.conn.rollback()
            return -1
    
    def update_account_checked_time(self, account_id: int) -> bool:
        """Update the last checked time for a monitored account"""
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "UPDATE monitored_accounts SET last_checked = ? WHERE id = ?",
                (datetime.now().isoformat(), account_id)
            )
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error updating account checked time: {str(e)}")
            self.conn.rollback()
            return False
    
    def add_processed_recipe(self, post_url: str, title: str, json_data: Dict, pdf_path: Optional[str] = None) -> int:
        """Add a processed recipe to the database"""
        try:
            cursor = self.conn.cursor()
            
            # Check if recipe already exists
            cursor.execute(
                "SELECT id FROM processed_recipes WHERE post_url = ?",
                (post_url,)
            )
            
            result = cursor.fetchone()
            
            if result:
                recipe_id = result[0]
                
                # Update existing recipe
                cursor.execute(
                    "UPDATE processed_recipes SET title = ?, json_data = ?, processed_at = ?, pdf_path = ? WHERE id = ?",
                    (title, json.dumps(json_data), datetime.now().isoformat(), pdf_path, recipe_id)
                )
            else:
                # Add new recipe
                cursor.execute(
                    "INSERT INTO processed_recipes (post_url, title, json_data, processed_at, pdf_path) VALUES (?, ?, ?, ?, ?)",
                    (post_url, title, json.dumps(json_data), datetime.now().isoformat(), pdf_path)
                )
                recipe_id = cursor.lastrowid
            
            self.conn.commit()
            logger.info(f"Added/updated processed recipe: {title}")
            return recipe_id
        except Exception as e:
            logger.error(f"Error adding processed recipe: {str(e)}")
            self.conn.rollback()
            return -1
    
    def record_delivery(self, user_id: int, recipe_id: int) -> bool:
        """Record that a recipe was delivered to a user"""
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "INSERT INTO delivered_recipes (user_id, recipe_id, delivered_at) VALUES (?, ?, ?)",
                (user_id, recipe_id, datetime.now().isoformat())
            )
            self.conn.commit()
            logger.info(f"Recorded recipe delivery - user_id: {user_id}, recipe_id: {recipe_id}")
            return True
        except sqlite3.IntegrityError:
            # Already delivered, just return success
            logger.info(f"Recipe already delivered - user_id: {user_id}, recipe_id: {recipe_id}")
            return True
        except Exception as e:
            logger.error(f"Error recording recipe delivery: {str(e)}")
            self.conn.rollback()
            return False
    
    def get_user_by_email(self, email: str) -> Optional[Dict]:
        """Get user information by email"""
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT id, email, created_at, preferences FROM users WHERE email = ?",
                (email,)
            )
            
            result = cursor.fetchone()
            
            if result:
                user = dict(result)
                if user.get('preferences'):
                    user['preferences'] = json.loads(user['preferences'])
                return user
            else:
                return None
        except Exception as e:
            logger.error(f"Error getting user by email: {str(e)}")
            return None
    
    def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        """Get user information by ID"""
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT id, email, created_at, preferences FROM users WHERE id = ?",
                (user_id,)
            )
            
            result = cursor.fetchone()
            
            if result:
                user = dict(result)
                if user.get('preferences'):
                    user['preferences'] = json.loads(user['preferences'])
                return user
            else:
                return None
        except Exception as e:
            logger.error(f"Error getting user by ID: {str(e)}")
            return None
    
    def get_monitored_accounts(self) -> List[Dict]:
        """Get all monitored Instagram accounts"""
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT id, instagram_username, added_at, last_checked FROM monitored_accounts"
            )
            
            results = cursor.fetchall()
            return [dict(row) for row in results]
        except Exception as e:
            logger.error(f"Error getting monitored accounts: {str(e)}")
            return []
    
    def get_user_subscriptions(self, user_id: int) -> List[Dict]:
        """Get Instagram accounts a user is subscribed to"""
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                """
                SELECT a.id, a.instagram_username, s.subscribed_at
                FROM monitored_accounts a
                JOIN user_account_subscriptions s ON a.id = s.account_id
                WHERE s.user_id = ?
                """,
                (user_id,)
            )
            
            results = cursor.fetchall()
            return [dict(row) for row in results]
        except Exception as e:
            logger.error(f"Error getting user subscriptions: {str(e)}")
            return []
    
    def get_recipe_by_id(self, recipe_id: int) -> Optional[Dict]:
        """Get recipe information by ID"""
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT id, post_url, title, json_data, processed_at, pdf_path FROM processed_recipes WHERE id = ?",
                (recipe_id,)
            )
            
            result = cursor.fetchone()
            
            if result:
                recipe = dict(result)
                if recipe.get('json_data'):
                    recipe['json_data'] = json.loads(recipe['json_data'])
                return recipe
            else:
                return None
        except Exception as e:
            logger.error(f"Error getting recipe by ID: {str(e)}")
            return None
    
    def get_recipe_by_url(self, post_url: str) -> Optional[Dict]:
        """Get recipe information by Instagram post URL"""
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT id, post_url, title, json_data, processed_at, pdf_path FROM processed_recipes WHERE post_url = ?",
                (post_url,)
            )
            
            result = cursor.fetchone()
            
            if result:
                recipe = dict(result)
                if recipe.get('json_data'):
                    recipe['json_data'] = json.loads(recipe['json_data'])
                return recipe
            else:
                return None
        except Exception as e:
            logger.error(f"Error getting recipe by URL: {str(e)}")
            return None
    
    def get_user_delivered_recipes(self, user_id: int) -> List[Dict]:
        """Get recipes delivered to a user"""
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                """
                SELECT r.id, r.post_url, r.title, r.processed_at, r.pdf_path, d.delivered_at
                FROM processed_recipes r
                JOIN delivered_recipes d ON r.id = d.recipe_id
                WHERE d.user_id = ?
                ORDER BY d.delivered_at DESC
                """,
                (user_id,)
            )
            
            results = cursor.fetchall()
            return [dict(row) for row in results]
        except Exception as e:
            logger.error(f"Error getting user delivered recipes: {str(e)}")
            return []
    
    def update_user_preferences(self, user_id: int, preferences: Dict) -> bool:
        """Update a user's preferences"""
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "UPDATE users SET preferences = ? WHERE id = ?",
                (json.dumps(preferences), user_id)
            )
            self.conn.commit()
            logger.info(f"Updated preferences for user_id: {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error updating user preferences: {str(e)}")
            self.conn.rollback()
            return False
