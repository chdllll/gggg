import sqlite3
import os
import shutil
from datetime import datetime
from dataclasses import dataclass
from typing import Optional, List
import json
import threading

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')
WORLDS_DIR = os.path.join(DATA_DIR, 'worlds')
DB_PATH = os.path.join(DATA_DIR, 'roleplay.db')

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(WORLDS_DIR, exist_ok=True)

@dataclass
class World:
    id: int
    name: str
    background: Optional[str]
    created_at: str
    user_health_mouth: str = '口腔清洁，牙齿整齐，舌体灵活'
    user_health_anus: str = '括约肌正常，无异常分泌物，排便正常'
    user_health_buttocks: str = '皮肤光滑，肌肉紧实，弹性良好'
    user_health_penis: str = '外观正常，功能完整，勃起正常'
    user_health_testicles: str = '大小适中，质地均匀，触感正常'
    user_health_left_breast: str = '形状饱满，质地柔软，触感自然'
    user_health_right_breast: str = '形状饱满，质地柔软，触感自然'
    user_health_vagina: str = '结构完整，分泌物正常，功能良好'
    user_health_mouth_color: str = '#28a745'
    user_health_anus_color: str = '#28a745'
    user_health_buttocks_color: str = '#28a745'
    user_health_penis_color: str = '#28a745'
    user_health_testicles_color: str = '#28a745'
    user_health_left_breast_color: str = '#28a745'
    user_health_right_breast_color: str = '#28a745'
    user_health_vagina_color: str = '#28a745'
    user_message_count: int = 0
    current_date: str = '2024-01-01'
    current_time: str = '08:00:00'
    total_seconds: int = 0
    locations: Optional[str] = None
    user_location: Optional[str] = None
    communication_character: Optional[str] = None
    user_name: Optional[str] = None
    script_outline: Optional[str] = None
    script_chapters: Optional[str] = None
    current_chapter_index: int = 0
    script_enabled: bool = False
    map_image: Optional[str] = None

@dataclass
class Character:
    id: int
    world_id: int
    name: str
    background: Optional[str]
    description: Optional[str]
    avatar_path: Optional[str]
    created_at: str
    location: Optional[str]
    gender: str
    health_mouth: str
    health_anus: str
    health_buttocks: str
    health_penis: str
    health_testicles: str
    health_left_breast: str
    health_right_breast: str
    health_vagina: str
    health_mouth_color: str
    health_anus_color: str
    health_buttocks_color: str
    health_penis_color: str
    health_testicles_color: str
    health_left_breast_color: str
    health_right_breast_color: str
    health_vagina_color: str
    event_frequency: str
    days_since_last_seen: int
    relationship_with_user: str
    last_seen_date: str
    activity_score: int = 0

@dataclass
class Location:
    id: int
    world_id: int
    name: str
    image_path: Optional[str]
    created_at: str
    parent_location_id: Optional[int] = None
    x: int = 0
    y: int = 0

@dataclass
class TransportMode:
    id: int
    world_id: int
    name: str
    speed: float
    created_at: str

@dataclass
class BackgroundImage:
    id: int
    character_id: int
    image_path: str
    description: Optional[str]
    tags: Optional[str]
    created_at: str

@dataclass
class ChatSession:
    id: int
    world_id: int
    name: str
    created_at: str

@dataclass
class ChatMessage:
    id: int
    session_id: int
    character_id: Optional[int]
    character_name: Optional[str]
    content: str
    action: Optional[str]
    background_image_id: Optional[int]
    avatar_path: Optional[str]
    message_type: str
    created_at: str
    current_date: Optional[str]
    current_time: Optional[str]
    segments: Optional[str]
    location: Optional[str] = None
    is_time_separator: int = 0
    time_separator_start_date: Optional[str] = None
    time_separator_start_time: Optional[str] = None
    time_separator_end_date: Optional[str] = None
    time_separator_end_time: Optional[str] = None
    dialogue_round: Optional[int] = None

@dataclass
class Memory:
    id: int
    world_id: int
    character_id: Optional[int]
    memory_type: str
    content: str
    importance: int
    segment: int
    created_at: str
    is_short_term: bool = False

@dataclass
class ShortTermMemory:
    id: int
    world_id: int
    character_id: Optional[int]
    content: str
    importance: int
    created_at: str
    source_message_ids: str

@dataclass
class LongTermMemory:
    id: int
    world_id: int
    character_id: Optional[int]
    content: str
    importance: int
    created_at: str
    source_short_term_ids: str
    consolidated_at: str

@dataclass
class RemoteCharacterEvent:
    id: int
    character_id: int
    character_name: str
    event_type: str
    description: str
    target_date: str
    target_time: str
    is_processed: bool
    created_at: str

@dataclass
class ActiveCall:
    id: int
    world_id: int
    character_id: int
    character_name: str
    original_location: str
    call_start_date: str
    call_start_time: str
    created_at: str

@dataclass
class IncomingCallRequest:
    id: int
    world_id: int
    character_id: int
    character_name: str
    request_date: str
    request_time: str
    is_handled: bool
    created_at: str

@dataclass
class CharacterRelationship:
    id: int
    world_id: int
    source_character_id: int
    target_character_id: int
    relationship_type: str
    description: str
    importance: int
    created_at: str

@dataclass
class APIConfig:
    id: int
    api1_key: Optional[str]
    api1_model: Optional[str]
    api2_key: Optional[str]
    api2_model: Optional[str]

@dataclass
class LocationDialogueState:
    id: int
    world_id: int
    location: str
    dialogue_count: int
    last_dialogue_date: str
    last_dialogue_time: str

class DatabaseManager:
    _all_connections = {}
    _connections_lock = threading.Lock()
    
    def __init__(self):
        self._local = threading.local()
        self._lock = threading.Lock()
        self._init_connection()
        self.init_database()
    
    def _init_connection(self):
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            self._local.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
            self._local.conn.row_factory = sqlite3.Row
            thread_id = threading.get_ident()
            with self._connections_lock:
                self._all_connections[thread_id] = self._local.conn
    
    @property
    def conn(self):
        self._init_connection()
        return self._local.conn
    
    def _execute_write(self, query, params=None):
        with self._lock:
            cursor = self.conn.cursor()
            try:
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                self.conn.commit()
                return cursor.lastrowid
            except Exception as e:
                self.conn.rollback()
                raise e
            finally:
                cursor.close()
    
    def _execute_read(self, query, params=None):
        cursor = self.conn.cursor()
        try:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            result = cursor.fetchall()
            return result
        except Exception as e:
            raise e
        finally:
            cursor.close()
    
    def _execute_read_one(self, query, params=None):
        cursor = self.conn.cursor()
        try:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            result = cursor.fetchone()
            return result
        except Exception as e:
            raise e
        finally:
            cursor.close()
    
    def _get_world_dir(self, world_id: int) -> str:
        return os.path.join(WORLDS_DIR, f'world_{world_id}')
    
    def _create_world_dir(self, world_id: int) -> str:
        world_dir = self._get_world_dir(world_id)
        os.makedirs(world_dir, exist_ok=True)
        os.makedirs(os.path.join(world_dir, 'avatars'), exist_ok=True)
        os.makedirs(os.path.join(world_dir, 'backgrounds'), exist_ok=True)
        os.makedirs(os.path.join(world_dir, 'audio'), exist_ok=True)
        os.makedirs(os.path.join(world_dir, 'chats'), exist_ok=True)
        os.makedirs(os.path.join(world_dir, 'locations'), exist_ok=True)
        return world_dir
    
    def _delete_world_dir(self, world_id: int):
        world_dir = self._get_world_dir(world_id)
        if os.path.exists(world_dir):
            shutil.rmtree(world_dir)
    
    def _get_avatar_dir(self, world_id: int) -> str:
        return os.path.join(self._get_world_dir(world_id), 'avatars')
    
    def _get_background_dir(self, world_id: int) -> str:
        return os.path.join(self._get_world_dir(world_id), 'backgrounds')
    
    def _get_audio_dir(self, world_id: int) -> str:
        return os.path.join(self._get_world_dir(world_id), 'audio')
    
    def _get_chat_dir(self, world_id: int) -> str:
        return os.path.join(self._get_world_dir(world_id), 'chats')
    
    def init_database(self):
        cursor = self.conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS worlds (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                background TEXT,
                narrative_style TEXT,
                special_context TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                current_date TEXT DEFAULT '2024-01-01',
                current_time TEXT DEFAULT '08:00:00',
                total_seconds INTEGER DEFAULT 0,
                locations TEXT,
                user_location TEXT,
                communication_character TEXT,
                user_name TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS characters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                world_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                background TEXT,
                description TEXT,
                dialogue_examples TEXT,
                avatar_path TEXT,
                location TEXT,
                gender TEXT DEFAULT 'female',
                event_frequency TEXT DEFAULT '中等',
                days_since_last_seen INTEGER DEFAULT 0,
                relationship_with_user TEXT DEFAULT '普通',
                last_seen_date TEXT DEFAULT '2024-01-01',
                activity_score INTEGER DEFAULT 0,
                health_mouth TEXT DEFAULT '口腔清洁，牙齿整齐，舌体灵活',
                health_anus TEXT DEFAULT '括约肌正常，无异常分泌物，排便正常',
                health_buttocks TEXT DEFAULT '皮肤光滑，肌肉紧实，弹性良好',
                health_penis TEXT DEFAULT '外观正常，功能完整，勃起正常',
                health_testicles TEXT DEFAULT '大小适中，质地均匀，触感正常',
                health_left_breast TEXT DEFAULT '形状饱满，质地柔软，触感自然',
                health_right_breast TEXT DEFAULT '形状饱满，质地柔软，触感自然',
                health_vagina TEXT DEFAULT '结构完整，分泌物正常，功能良好',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (world_id) REFERENCES worlds(id) ON DELETE CASCADE
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS background_images (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                character_id INTEGER NOT NULL,
                image_path TEXT NOT NULL,
                description TEXT,
                tags TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS locations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                world_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                image_path TEXT,
                parent_location_id INTEGER,
                x INTEGER DEFAULT 0,
                y INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (world_id) REFERENCES worlds(id) ON DELETE CASCADE,
                FOREIGN KEY (parent_location_id) REFERENCES locations(id) ON DELETE SET NULL
            )
        ''')
        
        cursor.execute("PRAGMA table_info(locations)")
        columns = [column[1] for column in cursor.fetchall()]
        if 'parent_location_id' not in columns:
            cursor.execute('ALTER TABLE locations ADD COLUMN parent_location_id INTEGER')
            print("已添加 parent_location_id 列到 locations 表")
        if 'x' not in columns:
            cursor.execute('ALTER TABLE locations ADD COLUMN x INTEGER DEFAULT 0')
            print("已添加 x 列到 locations 表")
        if 'y' not in columns:
            cursor.execute('ALTER TABLE locations ADD COLUMN y INTEGER DEFAULT 0')
            print("已添加 y 列到 locations 表")
        
        cursor.execute("PRAGMA table_info(worlds)")
        world_columns = [column[1] for column in cursor.fetchall()]
        if 'map_image' not in world_columns:
            cursor.execute('ALTER TABLE worlds ADD COLUMN map_image TEXT')
            print("已添加 map_image 列到 worlds 表")
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transport_modes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                world_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                speed REAL NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (world_id) REFERENCES worlds(id) ON DELETE CASCADE
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chat_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                world_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (world_id) REFERENCES worlds(id) ON DELETE CASCADE
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                character_id INTEGER,
                character_name TEXT,
                content TEXT NOT NULL,
                action TEXT,
                background_image_id INTEGER,
                avatar_path TEXT,
                message_type TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                current_date TEXT,
                current_time TEXT,
                segments TEXT,
                FOREIGN KEY (session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE,
                FOREIGN KEY (character_id) REFERENCES characters(id),
                FOREIGN KEY (background_image_id) REFERENCES background_images(id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                world_id INTEGER NOT NULL,
                character_id INTEGER,
                memory_type TEXT NOT NULL,
                content TEXT NOT NULL,
                importance INTEGER DEFAULT 1,
                segment INTEGER DEFAULT 1,
                is_short_term BOOLEAN DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (world_id) REFERENCES worlds(id) ON DELETE CASCADE,
                FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS short_term_memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                world_id INTEGER NOT NULL,
                character_id INTEGER,
                content TEXT NOT NULL,
                importance INTEGER DEFAULT 1,
                source_message_ids TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (world_id) REFERENCES worlds(id) ON DELETE CASCADE,
                FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS long_term_memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                world_id INTEGER NOT NULL,
                character_id INTEGER,
                content TEXT NOT NULL,
                importance INTEGER DEFAULT 1,
                source_short_term_ids TEXT,
                consolidated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (world_id) REFERENCES worlds(id) ON DELETE CASCADE,
                FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS api_config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                api1_key TEXT,
                api1_model TEXT DEFAULT 'deepseek-chat',
                api2_key TEXT,
                api2_model TEXT DEFAULT 'deepseek-chat'
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS remote_character_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                character_id INTEGER NOT NULL,
                character_name TEXT NOT NULL,
                event_type TEXT NOT NULL,
                description TEXT NOT NULL,
                target_date TEXT NOT NULL,
                target_time TEXT NOT NULL,
                is_processed INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS location_transfers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                world_id INTEGER NOT NULL,
                character_id INTEGER,
                from_location TEXT NOT NULL,
                to_location TEXT NOT NULL,
                departure_date TEXT NOT NULL,
                departure_time TEXT NOT NULL,
                arrival_date TEXT NOT NULL,
                arrival_time TEXT NOT NULL,
                is_completed INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (world_id) REFERENCES worlds(id) ON DELETE CASCADE,
                FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS character_relationships (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                world_id INTEGER NOT NULL,
                source_character_id INTEGER NOT NULL,
                target_character_id INTEGER NOT NULL,
                relationship_type TEXT NOT NULL,
                description TEXT NOT NULL,
                importance INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (world_id) REFERENCES worlds(id) ON DELETE CASCADE,
                FOREIGN KEY (source_character_id) REFERENCES characters(id) ON DELETE CASCADE,
                FOREIGN KEY (target_character_id) REFERENCES characters(id) ON DELETE CASCADE,
                UNIQUE(world_id, source_character_id, target_character_id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS location_dialogue_states (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                world_id INTEGER NOT NULL,
                location TEXT NOT NULL,
                dialogue_count INTEGER DEFAULT 0,
                last_dialogue_date TEXT,
                last_dialogue_time TEXT,
                FOREIGN KEY (world_id) REFERENCES worlds(id) ON DELETE CASCADE,
                UNIQUE(world_id, location)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS active_calls (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                world_id INTEGER NOT NULL,
                character_id INTEGER NOT NULL,
                character_name TEXT NOT NULL,
                original_location TEXT NOT NULL,
                call_start_date TEXT NOT NULL,
                call_start_time TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (world_id) REFERENCES worlds(id) ON DELETE CASCADE,
                FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS incoming_call_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                world_id INTEGER NOT NULL,
                character_id INTEGER NOT NULL,
                character_name TEXT NOT NULL,
                request_date TEXT NOT NULL,
                request_time TEXT NOT NULL,
                is_handled INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (world_id) REFERENCES worlds(id) ON DELETE CASCADE,
                FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
            )
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_characters_world ON characters(world_id)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_background_images_character ON background_images(character_id)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_chat_messages_session ON chat_messages(session_id)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_memories_world ON memories(world_id)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_memories_character ON memories(character_id)
        ''')
        
        self._migrate_database()
    
    def _migrate_database(self):
        cursor = self.conn.cursor()
        
        cursor.execute("PRAGMA table_info(characters)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'gender' not in columns:
            cursor.execute("ALTER TABLE characters ADD COLUMN gender TEXT DEFAULT 'female'")
        if 'health_mouth' not in columns:
            cursor.execute("ALTER TABLE characters ADD COLUMN health_mouth TEXT DEFAULT '口腔清洁，牙齿整齐，舌体灵活'")
        if 'health_anus' not in columns:
            cursor.execute("ALTER TABLE characters ADD COLUMN health_anus TEXT DEFAULT '括约肌正常，无异常分泌物，排便正常'")
        if 'health_buttocks' not in columns:
            cursor.execute("ALTER TABLE characters ADD COLUMN health_buttocks TEXT DEFAULT '皮肤光滑，肌肉紧实，弹性良好'")
        if 'health_penis' not in columns:
            cursor.execute("ALTER TABLE characters ADD COLUMN health_penis TEXT DEFAULT '外观正常，功能完整，勃起正常'")
        if 'health_testicles' not in columns:
            cursor.execute("ALTER TABLE characters ADD COLUMN health_testicles TEXT DEFAULT '大小适中，质地均匀，触感正常'")
        if 'health_left_breast' not in columns:
            cursor.execute("ALTER TABLE characters ADD COLUMN health_left_breast TEXT DEFAULT '形状饱满，质地柔软，触感自然'")
        if 'health_right_breast' not in columns:
            cursor.execute("ALTER TABLE characters ADD COLUMN health_right_breast TEXT DEFAULT '形状饱满，质地柔软，触感自然'")
        if 'health_vagina' not in columns:
            cursor.execute("ALTER TABLE characters ADD COLUMN health_vagina TEXT DEFAULT '结构完整，分泌物正常，功能良好'")
        
        if 'health_mouth_color' not in columns:
            cursor.execute("ALTER TABLE characters ADD COLUMN health_mouth_color TEXT DEFAULT '#28a745'")
        if 'health_anus_color' not in columns:
            cursor.execute("ALTER TABLE characters ADD COLUMN health_anus_color TEXT DEFAULT '#28a745'")
        if 'health_buttocks_color' not in columns:
            cursor.execute("ALTER TABLE characters ADD COLUMN health_buttocks_color TEXT DEFAULT '#28a745'")
        if 'health_penis_color' not in columns:
            cursor.execute("ALTER TABLE characters ADD COLUMN health_penis_color TEXT DEFAULT '#28a745'")
        if 'health_testicles_color' not in columns:
            cursor.execute("ALTER TABLE characters ADD COLUMN health_testicles_color TEXT DEFAULT '#28a745'")
        if 'health_left_breast_color' not in columns:
            cursor.execute("ALTER TABLE characters ADD COLUMN health_left_breast_color TEXT DEFAULT '#28a745'")
        if 'health_right_breast_color' not in columns:
            cursor.execute("ALTER TABLE characters ADD COLUMN health_right_breast_color TEXT DEFAULT '#28a745'")
        if 'health_vagina_color' not in columns:
            cursor.execute("ALTER TABLE characters ADD COLUMN health_vagina_color TEXT DEFAULT '#28a745'")
        
        if 'activity_score' not in columns:
            print("执行数据库迁移：添加 activity_score 列")
            cursor.execute('ALTER TABLE characters ADD COLUMN activity_score INTEGER DEFAULT 0')
            self.conn.commit()
            print("数据库迁移完成：activity_score 列已添加")
        
        cursor.execute("PRAGMA table_info(worlds)")
        world_columns = [column[1] for column in cursor.fetchall()]
        
        if 'user_health_mouth' not in world_columns:
            cursor.execute("ALTER TABLE worlds ADD COLUMN user_health_mouth TEXT DEFAULT '口腔清洁，牙齿整齐，舌体灵活'")
        if 'user_health_anus' not in world_columns:
            cursor.execute("ALTER TABLE worlds ADD COLUMN user_health_anus TEXT DEFAULT '括约肌正常，无异常分泌物，排便正常'")
        if 'user_health_buttocks' not in world_columns:
            cursor.execute("ALTER TABLE worlds ADD COLUMN user_health_buttocks TEXT DEFAULT '皮肤光滑，肌肉紧实，弹性良好'")
        if 'user_health_penis' not in world_columns:
            cursor.execute("ALTER TABLE worlds ADD COLUMN user_health_penis TEXT DEFAULT '外观正常，功能完整，勃起正常'")
        if 'user_health_testicles' not in world_columns:
            cursor.execute("ALTER TABLE worlds ADD COLUMN user_health_testicles TEXT DEFAULT '大小适中，质地均匀，触感正常'")
        if 'user_health_left_breast' not in world_columns:
            cursor.execute("ALTER TABLE worlds ADD COLUMN user_health_left_breast TEXT DEFAULT '形状饱满，质地柔软，触感自然'")
        if 'user_health_right_breast' not in world_columns:
            cursor.execute("ALTER TABLE worlds ADD COLUMN user_health_right_breast TEXT DEFAULT '形状饱满，质地柔软，触感自然'")
        if 'user_health_vagina' not in world_columns:
            cursor.execute("ALTER TABLE worlds ADD COLUMN user_health_vagina TEXT DEFAULT '结构完整，分泌物正常，功能良好'")
        
        if 'user_health_mouth_color' not in world_columns:
            cursor.execute("ALTER TABLE worlds ADD COLUMN user_health_mouth_color TEXT DEFAULT '#28a745'")
        if 'user_health_anus_color' not in world_columns:
            cursor.execute("ALTER TABLE worlds ADD COLUMN user_health_anus_color TEXT DEFAULT '#28a745'")
        if 'user_health_buttocks_color' not in world_columns:
            cursor.execute("ALTER TABLE worlds ADD COLUMN user_health_buttocks_color TEXT DEFAULT '#28a745'")
        if 'user_health_penis_color' not in world_columns:
            cursor.execute("ALTER TABLE worlds ADD COLUMN user_health_penis_color TEXT DEFAULT '#28a745'")
        if 'user_health_testicles_color' not in world_columns:
            cursor.execute("ALTER TABLE worlds ADD COLUMN user_health_testicles_color TEXT DEFAULT '#28a745'")
        if 'user_health_left_breast_color' not in world_columns:
            cursor.execute("ALTER TABLE worlds ADD COLUMN user_health_left_breast_color TEXT DEFAULT '#28a745'")
        if 'user_health_right_breast_color' not in world_columns:
            cursor.execute("ALTER TABLE worlds ADD COLUMN user_health_right_breast_color TEXT DEFAULT '#28a745'")
        if 'user_health_vagina_color' not in world_columns:
            cursor.execute("ALTER TABLE worlds ADD COLUMN user_health_vagina_color TEXT DEFAULT '#28a745'")
        if 'user_message_count' not in world_columns:
            cursor.execute("ALTER TABLE worlds ADD COLUMN user_message_count INTEGER DEFAULT 0")
        if 'user_name' not in world_columns:
            cursor.execute("ALTER TABLE worlds ADD COLUMN user_name TEXT")
        
        cursor.execute("PRAGMA table_info(chat_messages)")
        message_columns = [column[1] for column in cursor.fetchall()]
        
        if 'location' not in message_columns:
            cursor.execute("ALTER TABLE chat_messages ADD COLUMN location TEXT")
        
        if 'is_time_separator' not in message_columns:
            cursor.execute("ALTER TABLE chat_messages ADD COLUMN is_time_separator INTEGER DEFAULT 0")
        
        if 'time_separator_start_date' not in message_columns:
            cursor.execute("ALTER TABLE chat_messages ADD COLUMN time_separator_start_date TEXT")
        
        if 'time_separator_start_time' not in message_columns:
            cursor.execute("ALTER TABLE chat_messages ADD COLUMN time_separator_start_time TEXT")
        
        if 'time_separator_end_date' not in message_columns:
            cursor.execute("ALTER TABLE chat_messages ADD COLUMN time_separator_end_date TEXT")
        
        if 'time_separator_end_time' not in message_columns:
            cursor.execute("ALTER TABLE chat_messages ADD COLUMN time_separator_end_time TEXT")
        
        if 'dialogue_round' not in message_columns:
            cursor.execute("ALTER TABLE chat_messages ADD COLUMN dialogue_round INTEGER")
        
        cursor.execute("PRAGMA table_info(location_transfers)")
        transfer_columns = [column[1] for column in cursor.fetchall()]
        
        if 'is_completed' not in transfer_columns:
            print("正在迁移数据库，添加location_transfers.is_completed字段...")
            cursor.execute('ALTER TABLE location_transfers ADD COLUMN is_completed INTEGER DEFAULT 0')
            self.conn.commit()
            print("数据库迁移完成")
        
        self.conn.commit()
        cursor.close()
    
    def _convert_date_format(self, date_str: str) -> str:
        if not date_str:
            return '2024-01-01'
        
        try:
            if '年' in date_str:
                date_str = date_str.replace('第', '')
                parts = date_str.replace('年', '-').replace('月', '-').replace('日', '').split('-')
                year = parts[0]
                month = parts[1].zfill(2) if len(parts) > 1 else '01'
                day = parts[2].zfill(2) if len(parts) > 2 else '01'
                return f"{year}-{month}-{day}"
            else:
                return date_str
        except Exception:
            return '2024-01-01'
    
    def _convert_time_format(self, time_str: str) -> str:
        if not time_str:
            return '08:00:00'
        
        try:
            if '时' in time_str:
                time_str = time_str.replace('时', ':')
            
            parts = time_str.split(':')
            hour = parts[0].zfill(2) if parts else '08'
            minute = parts[1].zfill(2) if len(parts) > 1 else '00'
            second = parts[2].zfill(2) if len(parts) > 2 else '00'
            return f"{hour}:{minute}:{second}"
        except Exception:
            return '08:00:00'
    
    def migrate_database(self):
        cursor = self.conn.cursor()
        try:
            cursor.execute("PRAGMA table_info(worlds)")
            world_columns = [column[1] for column in cursor.fetchall()]
            
            if 'current_date' not in world_columns:
                print("正在迁移数据库，添加current_date字段...")
                cursor.execute('ALTER TABLE worlds ADD COLUMN current_date TEXT DEFAULT "第1年1月1日"')
                self.conn.commit()
                print("数据库迁移完成")
            
            if 'current_time' not in world_columns:
                print("正在迁移数据库，添加current_time字段...")
                cursor.execute('ALTER TABLE worlds ADD COLUMN current_time TEXT DEFAULT "08:00:00"')
                self.conn.commit()
                print("数据库迁移完成")
            
            cursor.execute("SELECT id, current_date, current_time FROM worlds WHERE current_date LIKE '%年%' OR current_time LIKE '%时%'")
            world_datetime_rows = cursor.fetchall()
            if world_datetime_rows:
                print("正在迁移数据库，更新worlds日期时间格式...")
                for world_id, current_date, current_time in world_datetime_rows:
                    new_date = self._convert_date_format(current_date)
                    new_time = self._convert_time_format(current_time)
                    cursor.execute('UPDATE worlds SET current_date = ?, current_time = ? WHERE id = ?', (new_date, new_time, world_id))
                self.conn.commit()
                print(f"数据库迁移完成：已更新 {len(world_datetime_rows)} 个世界的日期时间格式")
            
            cursor.execute("PRAGMA table_info(memories)")
            columns = [column[1] for column in cursor.fetchall()]
            
            if 'segment' not in columns:
                print("正在迁移数据库，添加segment字段...")
                cursor.execute('ALTER TABLE memories ADD COLUMN segment INTEGER DEFAULT 1')
                self.conn.commit()
                print("数据库迁移完成")
            
            cursor.execute("PRAGMA index_list(memories)")
            indexes = [index[1] for index in cursor.fetchall()]
            
            if 'idx_memories_world_segment' not in indexes:
                print("正在创建索引 idx_memories_world_segment...")
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_memories_world_segment ON memories(world_id, segment)
                ''')
                self.conn.commit()
                print("索引创建完成")
            
            cursor.execute("PRAGMA table_info(characters)")
            char_columns = [column[1] for column in cursor.fetchall()]
            
            if 'location' not in char_columns:
                print("正在迁移数据库，添加location字段...")
                cursor.execute('ALTER TABLE characters ADD COLUMN location TEXT')
                self.conn.commit()
                print("数据库迁移完成")
            
            if 'gender' not in char_columns:
                print("正在迁移数据库，添加gender字段...")
                cursor.execute('ALTER TABLE characters ADD COLUMN gender TEXT DEFAULT "female"')
                self.conn.commit()
                print("数据库迁移完成")
            
            if 'event_frequency' not in char_columns:
                print("正在迁移数据库，添加event_frequency字段...")
                cursor.execute('ALTER TABLE characters ADD COLUMN event_frequency TEXT DEFAULT "中等"')
                self.conn.commit()
                print("数据库迁移完成")
            
            if 'days_since_last_seen' not in char_columns:
                print("正在迁移数据库，添加days_since_last_seen字段...")
                cursor.execute('ALTER TABLE characters ADD COLUMN days_since_last_seen INTEGER DEFAULT 0')
                self.conn.commit()
                print("数据库迁移完成")
            
            if 'relationship_with_user' not in char_columns:
                print("正在迁移数据库，添加relationship_with_user字段...")
                cursor.execute('ALTER TABLE characters ADD COLUMN relationship_with_user TEXT DEFAULT "普通"')
                self.conn.commit()
                print("数据库迁移完成")
            
            if 'last_seen_date' not in char_columns:
                print("正在迁移数据库，添加last_seen_date字段...")
                cursor.execute('ALTER TABLE characters ADD COLUMN last_seen_date TEXT DEFAULT "2024-01-01"')
                self.conn.commit()
                print("数据库迁移完成")
            
            cursor.execute("SELECT id, last_seen_date FROM characters WHERE last_seen_date LIKE '%年%'")
            char_date_rows = cursor.fetchall()
            if char_date_rows:
                print("正在迁移数据库，更新characters日期格式...")
                for char_id, last_seen_date in char_date_rows:
                    new_date = self._convert_date_format(last_seen_date)
                    cursor.execute('UPDATE characters SET last_seen_date = ? WHERE id = ?', (new_date, char_id))
                self.conn.commit()
                print(f"数据库迁移完成：已更新 {len(char_date_rows)} 个角色的日期格式")
            
            health_columns = ['health_head', 'health_body', 'health_left_hand', 'health_right_hand', 
                            'health_left_leg', 'health_right_leg', 'health_left_foot', 'health_right_foot',
                            'health_penis', 'health_testicles', 'health_left_breast', 'health_right_breast',
                            'health_vagina', 'health_anus']
            
            if 'health_head' in char_columns:
                cursor.execute('SELECT id, health_head FROM characters')
                rows = cursor.fetchall()
                if rows and rows[0][1] in ['健康', '轻微受伤', '受伤', '重伤', '昏迷', '死亡']:
                    print("正在迁移数据库，更新健康状态为详细描述...")
                    for row in rows:
                        char_id = row[0]
                        for col in health_columns:
                            cursor.execute(f'SELECT {col} FROM characters WHERE id = ?', (char_id,))
                            status = cursor.fetchone()[0]
                            new_status = self._convert_health_status_to_description(status)
                            cursor.execute(f'UPDATE characters SET {col} = ? WHERE id = ?', (new_status, char_id))
                    self.conn.commit()
                    print("数据库迁移完成")
            
            cursor.execute("PRAGMA table_info(api_config)")
            api_config_columns = [column[1] for column in cursor.fetchall()]
            
            if 'api1_key' not in api_config_columns:
                print("正在迁移数据库，添加api1_key字段...")
                cursor.execute('ALTER TABLE api_config ADD COLUMN api1_key TEXT')
                self.conn.commit()
                print("数据库迁移完成")
            
            if 'api1_model' not in api_config_columns:
                print("正在迁移数据库，添加api1_model字段...")
                cursor.execute('ALTER TABLE api_config ADD COLUMN api1_model TEXT DEFAULT "deepseek-chat"')
                self.conn.commit()
                print("数据库迁移完成")
            
            if 'api2_key' not in api_config_columns:
                print("正在迁移数据库，添加api2_key字段...")
                cursor.execute('ALTER TABLE api_config ADD COLUMN api2_key TEXT')
                self.conn.commit()
                print("数据库迁移完成")
            
            if 'api2_model' not in api_config_columns:
                print("正在迁移数据库，添加api2_model字段...")
                cursor.execute('ALTER TABLE api_config ADD COLUMN api2_model TEXT DEFAULT "deepseek-chat"')
                self.conn.commit()
                print("数据库迁移完成")
            
            cursor.execute("PRAGMA table_info(chat_messages)")
            chat_message_columns = [column[1] for column in cursor.fetchall()]
            
            if 'current_date' not in chat_message_columns:
                print("正在迁移数据库，添加chat_messages.current_date字段...")
                cursor.execute('ALTER TABLE chat_messages ADD COLUMN current_date TEXT')
                self.conn.commit()
                print("数据库迁移完成")
            
            if 'current_time' not in chat_message_columns:
                print("正在迁移数据库，添加chat_messages.current_time字段...")
                cursor.execute('ALTER TABLE chat_messages ADD COLUMN current_time TEXT')
                self.conn.commit()
                print("数据库迁移完成")
            
            cursor.execute("SELECT id, current_time FROM chat_messages WHERE current_time NOT LIKE '%分'")
            chat_time_rows = cursor.fetchall()
            if chat_time_rows:
                print("正在迁移数据库，更新chat_messages时间格式...")
                for msg_id, current_time in chat_time_rows:
                    new_time = f"{current_time}0分"
                    cursor.execute('UPDATE chat_messages SET current_time = ? WHERE id = ?', (new_time, msg_id))
                self.conn.commit()
                print(f"数据库迁移完成：已更新 {len(chat_time_rows)} 条消息的时间格式")
            
            cursor.execute("PRAGMA table_info(worlds)")
            worlds_columns = [column[1] for column in cursor.fetchall()]
            
            if 'locations' not in worlds_columns:
                print("正在迁移数据库，添加worlds.locations字段...")
                cursor.execute('ALTER TABLE worlds ADD COLUMN locations TEXT')
                self.conn.commit()
                print("数据库迁移完成")
            
            if 'user_location' not in worlds_columns:
                print("正在迁移数据库，添加worlds.user_location字段...")
                cursor.execute('ALTER TABLE worlds ADD COLUMN user_location TEXT')
                self.conn.commit()
                print("数据库迁移完成")
            
            if 'communication_character' not in worlds_columns:
                print("正在迁移数据库，添加worlds.communication_character字段...")
                cursor.execute('ALTER TABLE worlds ADD COLUMN communication_character TEXT')
                self.conn.commit()
                print("数据库迁移完成")
            
            cursor.execute("PRAGMA table_info(worlds)")
            world_columns = [column[1] for column in cursor.fetchall()]
            
            if 'script_outline' not in world_columns:
                print("正在迁移数据库，添加worlds.script_outline字段...")
                cursor.execute('ALTER TABLE worlds ADD COLUMN script_outline TEXT')
                self.conn.commit()
                print("数据库迁移完成")
            
            if 'script_chapters' not in world_columns:
                print("正在迁移数据库，添加worlds.script_chapters字段...")
                cursor.execute('ALTER TABLE worlds ADD COLUMN script_chapters TEXT')
                self.conn.commit()
                print("数据库迁移完成")
            
            if 'current_chapter_index' not in world_columns:
                print("正在迁移数据库，添加worlds.current_chapter_index字段...")
                cursor.execute('ALTER TABLE worlds ADD COLUMN current_chapter_index INTEGER DEFAULT 0')
                self.conn.commit()
                print("数据库迁移完成")
            
            if 'script_enabled' not in world_columns:
                print("正在迁移数据库，添加worlds.script_enabled字段...")
                cursor.execute('ALTER TABLE worlds ADD COLUMN script_enabled INTEGER DEFAULT 0')
                self.conn.commit()
                print("数据库迁移完成")
            
            cursor.execute("PRAGMA table_info(locations)")
            location_columns = [column[1] for column in cursor.fetchall()]
            
            if 'parent_location_id' not in location_columns:
                print("正在迁移数据库，添加locations.parent_location_id字段...")
                cursor.execute('ALTER TABLE locations ADD COLUMN parent_location_id INTEGER')
                self.conn.commit()
                print("数据库迁移完成")
            
            cursor.execute("PRAGMA table_info(location_transfers)")
            transfer_columns = [column[1] for column in cursor.fetchall()]
            
            if 'is_completed' not in transfer_columns:
                print("正在迁移数据库，添加location_transfers.is_completed字段...")
                cursor.execute('ALTER TABLE location_transfers ADD COLUMN is_completed INTEGER DEFAULT 0')
                self.conn.commit()
                print("数据库迁移完成")
            
            cursor.execute("SELECT id, location FROM characters WHERE location = '路上'")
            on_road_characters = cursor.fetchall()
            if on_road_characters:
                print("正在迁移数据库，更新'路上'状态为详细格式...")
                for char_id, _ in on_road_characters:
                    cursor.execute('UPDATE characters SET location = ? WHERE id = ?', ('未知位置', char_id))
                self.conn.commit()
                print(f"数据库迁移完成：已更新 {len(on_road_characters)} 个角色的'路上'状态")
            
            cursor.execute("SELECT id, departure_time, arrival_time FROM location_transfers WHERE departure_time NOT LIKE '%分' OR arrival_time NOT LIKE '%分'")
            transfer_time_rows = cursor.fetchall()
            if transfer_time_rows:
                print("正在迁移数据库，更新location_transfers时间格式...")
                for transfer_id, departure_time, arrival_time in transfer_time_rows:
                    new_departure_time = f"{departure_time}0分" if departure_time and not '分' in departure_time else departure_time
                    new_arrival_time = f"{arrival_time}0分" if arrival_time and not '分' in arrival_time else arrival_time
                    cursor.execute('UPDATE location_transfers SET departure_time = ?, arrival_time = ? WHERE id = ?', 
                                 (new_departure_time, new_arrival_time, transfer_id))
                self.conn.commit()
                print(f"数据库迁移完成：已更新 {len(transfer_time_rows)} 条转移记录的时间格式")
            
            cursor.execute("PRAGMA table_info(chat_messages)")
            chat_message_columns = [column[1] for column in cursor.fetchall()]
            
            if 'location' not in chat_message_columns:
                print("正在迁移数据库，添加chat_messages.location字段...")
                cursor.execute('ALTER TABLE chat_messages ADD COLUMN location TEXT')
                self.conn.commit()
                print("数据库迁移完成")
            
            if 'is_time_separator' not in chat_message_columns:
                print("正在迁移数据库，添加chat_messages.is_time_separator字段...")
                cursor.execute('ALTER TABLE chat_messages ADD COLUMN is_time_separator INTEGER DEFAULT 0')
                self.conn.commit()
                print("数据库迁移完成")
            
            if 'time_separator_start_date' not in chat_message_columns:
                print("正在迁移数据库，添加chat_messages.time_separator_start_date字段...")
                cursor.execute('ALTER TABLE chat_messages ADD COLUMN time_separator_start_date TEXT')
                self.conn.commit()
                print("数据库迁移完成")
            
            if 'time_separator_start_time' not in chat_message_columns:
                print("正在迁移数据库，添加chat_messages.time_separator_start_time字段...")
                cursor.execute('ALTER TABLE chat_messages ADD COLUMN time_separator_start_time TEXT')
                self.conn.commit()
                print("数据库迁移完成")
            
            if 'time_separator_end_date' not in chat_message_columns:
                print("正在迁移数据库，添加chat_messages.time_separator_end_date字段...")
                cursor.execute('ALTER TABLE chat_messages ADD COLUMN time_separator_end_date TEXT')
                self.conn.commit()
                print("数据库迁移完成")
            
            if 'time_separator_end_time' not in chat_message_columns:
                print("正在迁移数据库，添加chat_messages.time_separator_end_time字段...")
                cursor.execute('ALTER TABLE chat_messages ADD COLUMN time_separator_end_time TEXT')
                self.conn.commit()
                print("数据库迁移完成")
            
            if 'dialogue_round' not in chat_message_columns:
                print("正在迁移数据库，添加chat_messages.dialogue_round字段...")
                cursor.execute('ALTER TABLE chat_messages ADD COLUMN dialogue_round INTEGER')
                self.conn.commit()
                print("数据库迁移完成")
        finally:
            cursor.close()
    
    def _convert_health_status_to_description(self, status: str) -> str:
        if not status or status == '健康':
            return '功能正常，外观完好'
        elif status == '轻微受伤':
            return '有轻微伤痕，功能基本正常'
        elif status == '受伤':
            return '有明显伤痕，功能受到影响'
        elif status == '重伤':
            return '伤势严重，功能严重受损'
        elif status == '昏迷':
            return '处于昏迷状态，意识不清'
        elif status == '死亡':
            return '已经死亡，无生命体征'
        else:
            return status
    
    def create_world(self, name: str, background: str = None, locations: List[str] = None) -> World:
        import json
        locations_json = json.dumps(locations, ensure_ascii=False) if locations else None
        user_location = locations[0] if locations else None
        world_id = self._execute_write('''
            INSERT INTO worlds (name, background, locations, user_location, current_date, current_time)
            VALUES (?, ?, ?, ?, '2024-01-01', '08:00:00')
        ''', (name, background, locations_json, user_location))
        
        self._create_world_dir(world_id)
        
        return self.get_world(world_id)
    
    def get_world(self, world_id: int) -> Optional[World]:
        cursor = self.conn.cursor()
        try:
            cursor.execute('''
                SELECT 
                    w.id, w.name, w.background, w.created_at,
                    w.user_health_mouth, w.user_health_anus, w.user_health_buttocks, w.user_health_penis,
                    w.user_health_testicles, w.user_health_left_breast, w.user_health_right_breast, w.user_health_vagina,
                    w.user_health_mouth_color, w.user_health_anus_color, w.user_health_buttocks_color,
                    w.user_health_penis_color, w.user_health_testicles_color,
                    w.user_health_left_breast_color, w.user_health_right_breast_color, w.user_health_vagina_color,
                    w.user_message_count, w.current_date, w.current_time, w.total_seconds, w.locations, w.user_location, w.communication_character,
                    w.user_name,
                    w.script_outline, w.script_chapters, w.current_chapter_index, w.script_enabled,
                    w.map_image
                FROM worlds w WHERE w.id = ?
            ''', (world_id,))
            row = cursor.fetchone()
            if row:
                row_list = list(row)
                if len(row_list) > 23 and row_list[23] is not None:
                    try:
                        row_list[23] = int(row_list[23])
                    except (ValueError, TypeError):
                        row_list[23] = 0
                if len(row_list) > 24 and row_list[24] is not None:
                    try:
                        row_list[24] = json.loads(row_list[24])
                    except (json.JSONDecodeError, TypeError):
                        row_list[24] = None
                return World(*row_list)
            return None
        finally:
            cursor.close()
    
    def get_all_worlds(self) -> List[World]:
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT 
                w.id, w.name, w.background, w.created_at,
                w.user_health_mouth, w.user_health_anus, w.user_health_buttocks, w.user_health_penis,
                w.user_health_testicles, w.user_health_left_breast, w.user_health_right_breast, w.user_health_vagina,
                w.user_health_mouth_color, w.user_health_anus_color, w.user_health_buttocks_color,
                w.user_health_penis_color, w.user_health_testicles_color,
                w.user_health_left_breast_color, w.user_health_right_breast_color, w.user_health_vagina_color,
                w.user_message_count, w.current_date, w.current_time, w.total_seconds, w.locations, w.user_location, w.communication_character,
                w.user_name,
                w.script_outline, w.script_chapters, w.current_chapter_index, w.script_enabled,
                w.map_image
            FROM worlds w ORDER BY w.created_at DESC
        ''')
        rows = cursor.fetchall()
        worlds = []
        for row in rows:
            row_list = list(row)
            if len(row_list) > 23 and row_list[23] is not None:
                try:
                    row_list[23] = int(row_list[23])
                except (ValueError, TypeError):
                    row_list[23] = 0
            if len(row_list) > 24 and row_list[24] is not None:
                try:
                    row_list[24] = json.loads(row_list[24])
                except (json.JSONDecodeError, TypeError):
                    row_list[24] = None
            worlds.append(World(*row_list))
        return worlds
    
    def update_world(self, world_id: int, name: str = None, background: str = None, current_date: str = None, current_time: str = None, user_health_mouth: str = None, user_health_anus: str = None, user_health_buttocks: str = None, user_health_penis: str = None, user_health_testicles: str = None, user_health_left_breast: str = None, user_health_right_breast: str = None, user_health_vagina: str = None, user_health_mouth_color: str = None, user_health_anus_color: str = None, user_health_buttocks_color: str = None, user_health_penis_color: str = None, user_health_testicles_color: str = None, user_health_left_breast_color: str = None, user_health_right_breast_color: str = None, user_health_vagina_color: str = None, user_message_count: int = None, total_seconds: int = None, locations: List[str] = None, user_location: str = None, communication_character: str = None, script_outline: str = None, script_chapters: str = None, current_chapter_index: int = None, script_enabled: bool = None, user_name: str = None, map_image: str = None):
        updates = []
        params = []
        
        if name is not None:
            updates.append('name = ?')
            params.append(name)
        if background is not None:
            updates.append('background = ?')
            params.append(background)
        if current_date is not None:
            updates.append('current_date = ?')
            params.append(current_date)
        if current_time is not None:
            updates.append('current_time = ?')
            params.append(current_time)
        
        if user_health_mouth is not None:
            updates.append('user_health_mouth = ?')
            params.append(user_health_mouth)
        if user_health_anus is not None:
            updates.append('user_health_anus = ?')
            params.append(user_health_anus)
        if user_health_buttocks is not None:
            updates.append('user_health_buttocks = ?')
            params.append(user_health_buttocks)
        if user_health_penis is not None:
            updates.append('user_health_penis = ?')
            params.append(user_health_penis)
        if user_health_testicles is not None:
            updates.append('user_health_testicles = ?')
            params.append(user_health_testicles)
        if user_health_left_breast is not None:
            updates.append('user_health_left_breast = ?')
            params.append(user_health_left_breast)
        if user_health_right_breast is not None:
            updates.append('user_health_right_breast = ?')
            params.append(user_health_right_breast)
        if user_health_vagina is not None:
            updates.append('user_health_vagina = ?')
            params.append(user_health_vagina)
        if user_health_mouth_color is not None:
            updates.append('user_health_mouth_color = ?')
            params.append(user_health_mouth_color)
        if user_health_anus_color is not None:
            updates.append('user_health_anus_color = ?')
            params.append(user_health_anus_color)
        if user_health_buttocks_color is not None:
            updates.append('user_health_buttocks_color = ?')
            params.append(user_health_buttocks_color)
        if user_health_penis_color is not None:
            updates.append('user_health_penis_color = ?')
            params.append(user_health_penis_color)
        if user_health_testicles_color is not None:
            updates.append('user_health_testicles_color = ?')
            params.append(user_health_testicles_color)
        if user_health_left_breast_color is not None:
            updates.append('user_health_left_breast_color = ?')
            params.append(user_health_left_breast_color)
        if user_health_right_breast_color is not None:
            updates.append('user_health_right_breast_color = ?')
            params.append(user_health_right_breast_color)
        if user_health_vagina_color is not None:
            updates.append('user_health_vagina_color = ?')
            params.append(user_health_vagina_color)
        if user_message_count is not None:
            updates.append('user_message_count = ?')
            params.append(user_message_count)
        if total_seconds is not None:
            updates.append('total_seconds = ?')
            params.append(total_seconds)
        if locations is not None:
            import json
            updates.append('locations = ?')
            params.append(json.dumps(locations, ensure_ascii=False))
        if user_location is not None:
            updates.append('user_location = ?')
            params.append(user_location)
        if communication_character is not None:
            updates.append('communication_character = ?')
            params.append(communication_character)
        if script_outline is not None:
            updates.append('script_outline = ?')
            params.append(script_outline)
        if script_chapters is not None:
            updates.append('script_chapters = ?')
            params.append(script_chapters)
        if current_chapter_index is not None:
            updates.append('current_chapter_index = ?')
            params.append(current_chapter_index)
        if script_enabled is not None:
            updates.append('script_enabled = ?')
            params.append(1 if script_enabled else 0)
        if user_name is not None:
            updates.append('user_name = ?')
            params.append(user_name)
        if map_image is not None:
            updates.append('map_image = ?')
            params.append(map_image)
        
        if updates:
            params.append(world_id)
            self._execute_write(f'UPDATE worlds SET {", ".join(updates)} WHERE id = ?', params)
            return True
        return False
    
    def update_world_user_name(self, world_id: int, user_name: str) -> bool:
        return self.update_world(world_id, user_name=user_name)
    
    def delete_world(self, world_id: int):
        self._execute_write('DELETE FROM worlds WHERE id = ?', (world_id,))
        self._delete_world_dir(world_id)
    
    def create_character(self, world_id: int, name: str, background: str = None, description: str = None, avatar_path: str = None, location: str = None, gender: str = 'female', health_mouth: str = '口腔清洁，牙齿整齐，舌体灵活', health_anus: str = '括约肌正常，无异常分泌物，排便正常', health_buttocks: str = '皮肤光滑，肌肉紧实，弹性良好', health_penis: str = '外观正常，功能完整，勃起正常', health_testicles: str = '大小适中，质地均匀，触感正常', health_left_breast: str = '形状饱满，质地柔软，触感自然', health_right_breast: str = '形状饱满，质地柔软，触感自然', health_vagina: str = '结构完整，分泌物正常，功能良好', event_frequency: str = '中等', health_mouth_color: str = '#28a745', health_anus_color: str = '#28a745', health_buttocks_color: str = '#28a745', health_penis_color: str = '#28a745', health_testicles_color: str = '#28a745', health_left_breast_color: str = '#28a745', health_right_breast_color: str = '#28a745', health_vagina_color: str = '#28a745') -> Character:
        character_id = self._execute_write('''
            INSERT INTO characters (world_id, name, background, description, avatar_path, location, gender, health_mouth, health_anus, health_buttocks, health_penis, health_testicles, health_left_breast, health_right_breast, health_vagina, event_frequency, health_mouth_color, health_anus_color, health_buttocks_color, health_penis_color, health_testicles_color, health_left_breast_color, health_right_breast_color, health_vagina_color)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (world_id, name, background, description, avatar_path, location, gender, health_mouth, health_anus, health_buttocks, health_penis, health_testicles, health_left_breast, health_right_breast, health_vagina, event_frequency, health_mouth_color, health_anus_color, health_buttocks_color, health_penis_color, health_testicles_color, health_left_breast_color, health_right_breast_color, health_vagina_color))
        return self.get_character(character_id)
    
    def get_character(self, character_id: int) -> Optional[Character]:
        cursor = self.conn.cursor()
        try:
            cursor.execute('''
                SELECT id, world_id, name, background, description, avatar_path,
                       created_at, location, gender, health_mouth, health_anus, health_buttocks, health_penis, health_testicles, health_left_breast,
                       health_right_breast, health_vagina, health_mouth_color, health_anus_color, health_buttocks_color,
                       health_penis_color, health_testicles_color, health_left_breast_color, health_right_breast_color,
                       health_vagina_color, event_frequency, days_since_last_seen,
                       relationship_with_user, last_seen_date, activity_score
                FROM characters WHERE id = ?
            ''', (character_id,))
            row = cursor.fetchone()
            if row:
                return Character(*row)
            return None
        finally:
            cursor.close()
    
    def get_character_by_name(self, world_id: int, name: str) -> Optional[Character]:
        cursor = self.conn.cursor()
        try:
            cursor.execute('''
                SELECT id, world_id, name, background, description, avatar_path,
                       created_at, location, gender, health_mouth, health_anus, health_buttocks, health_penis, health_testicles, health_left_breast,
                       health_right_breast, health_vagina, health_mouth_color, health_anus_color, health_buttocks_color,
                       health_penis_color, health_testicles_color, health_left_breast_color, health_right_breast_color,
                       health_vagina_color, event_frequency, days_since_last_seen,
                       relationship_with_user, last_seen_date, activity_score
                FROM characters WHERE world_id = ? AND name = ?
            ''', (world_id, name))
            row = cursor.fetchone()
            if row:
                return Character(*row)
            return None
        finally:
            cursor.close()
    
    def get_characters_by_world(self, world_id: int) -> List[Character]:
        cursor = self.conn.cursor()
        try:
            cursor.execute('''
                SELECT id, world_id, name, background, description, avatar_path,
                       created_at, location, gender, health_mouth, health_anus, health_buttocks, health_penis, health_testicles, health_left_breast,
                       health_right_breast, health_vagina, health_mouth_color, health_anus_color, health_buttocks_color,
                       health_penis_color, health_testicles_color, health_left_breast_color, health_right_breast_color,
                       health_vagina_color, event_frequency, days_since_last_seen,
                       relationship_with_user, last_seen_date, activity_score
                FROM characters WHERE world_id = ? ORDER BY created_at
            ''', (world_id,))
            rows = cursor.fetchall()
            return [Character(*row) for row in rows]
        finally:
            cursor.close()
    
    def get_all_characters(self) -> List[Character]:
        cursor = self.conn.cursor()
        try:
            cursor.execute('''
                SELECT id, world_id, name, background, description, avatar_path,
                       created_at, location, gender, health_mouth, health_anus, health_buttocks, health_penis, health_testicles, health_left_breast,
                       health_right_breast, health_vagina, health_mouth_color, health_anus_color, health_buttocks_color,
                       health_penis_color, health_testicles_color, health_left_breast_color, health_right_breast_color,
                       health_vagina_color, event_frequency, days_since_last_seen,
                       relationship_with_user, last_seen_date, activity_score
                FROM characters ORDER BY created_at DESC
            ''')
            rows = cursor.fetchall()
            return [Character(*row) for row in rows]
        finally:
            cursor.close()
    
    def update_character(self, character_id: int, name: str = None, background: str = None, description: str = None, avatar_path: str = None, location: str = None, gender: str = None, event_frequency: str = None, days_since_last_seen: int = None, relationship_with_user: str = None, last_seen_date: str = None, health_mouth: str = None, health_anus: str = None, health_buttocks: str = None, health_penis: str = None, health_testicles: str = None, health_left_breast: str = None, health_right_breast: str = None, health_vagina: str = None, health_mouth_color: str = None, health_anus_color: str = None, health_buttocks_color: str = None, health_penis_color: str = None, health_testicles_color: str = None, health_left_breast_color: str = None, health_right_breast_color: str = None, health_vagina_color: str = None, activity_score: int = None):
        updates = []
        params = []
        
        if name is not None:
            updates.append('name = ?')
            params.append(name)
        if background is not None:
            updates.append('background = ?')
            params.append(background)
        if description is not None:
            updates.append('description = ?')
            params.append(description)
        if avatar_path is not None:
            updates.append('avatar_path = ?')
            params.append(avatar_path)
        if location is not None:
            updates.append('location = ?')
            params.append(location)
        if gender is not None:
            updates.append('gender = ?')
            params.append(gender)
        if event_frequency is not None:
            updates.append('event_frequency = ?')
            params.append(event_frequency)
        if days_since_last_seen is not None:
            updates.append('days_since_last_seen = ?')
            params.append(days_since_last_seen)
        if relationship_with_user is not None:
            updates.append('relationship_with_user = ?')
            params.append(relationship_with_user)
        if last_seen_date is not None:
            updates.append('last_seen_date = ?')
            params.append(last_seen_date)
        if activity_score is not None:
            updates.append('activity_score = ?')
            params.append(activity_score)
        if health_mouth is not None:
            updates.append('health_mouth = ?')
            params.append(health_mouth)
        if health_anus is not None:
            updates.append('health_anus = ?')
            params.append(health_anus)
        if health_buttocks is not None:
            updates.append('health_buttocks = ?')
            params.append(health_buttocks)
        if health_penis is not None:
            updates.append('health_penis = ?')
            params.append(health_penis)
        if health_testicles is not None:
            updates.append('health_testicles = ?')
            params.append(health_testicles)
        if health_left_breast is not None:
            updates.append('health_left_breast = ?')
            params.append(health_left_breast)
        if health_right_breast is not None:
            updates.append('health_right_breast = ?')
            params.append(health_right_breast)
        if health_vagina is not None:
            updates.append('health_vagina = ?')
            params.append(health_vagina)
        if health_mouth_color is not None:
            updates.append('health_mouth_color = ?')
            params.append(health_mouth_color)
        if health_anus_color is not None:
            updates.append('health_anus_color = ?')
            params.append(health_anus_color)
        if health_buttocks_color is not None:
            updates.append('health_buttocks_color = ?')
            params.append(health_buttocks_color)
        if health_penis_color is not None:
            updates.append('health_penis_color = ?')
            params.append(health_penis_color)
        if health_testicles_color is not None:
            updates.append('health_testicles_color = ?')
            params.append(health_testicles_color)
        if health_left_breast_color is not None:
            updates.append('health_left_breast_color = ?')
            params.append(health_left_breast_color)
        if health_right_breast_color is not None:
            updates.append('health_right_breast_color = ?')
            params.append(health_right_breast_color)
        if health_vagina_color is not None:
            updates.append('health_vagina_color = ?')
            params.append(health_vagina_color)
        
        if updates:
            params.append(character_id)
            self._execute_write(f'UPDATE characters SET {", ".join(updates)} WHERE id = ?', params)
    
    def delete_character(self, character_id: int):
        character = self._execute_read_one('''
            SELECT id, world_id, name, background, description, avatar_path,
                   created_at, location, gender, health_mouth, health_anus, health_buttocks, health_penis, health_testicles, health_left_breast,
                   health_right_breast, health_vagina, health_mouth_color, health_anus_color, health_buttocks_color,
                   health_penis_color, health_testicles_color, health_left_breast_color, health_right_breast_color,
                   health_vagina_color, event_frequency, days_since_last_seen,
                   relationship_with_user, last_seen_date, activity_score
            FROM characters WHERE id = ?
        ''', (character_id,))
        
        if character:
            character_obj = Character(*character)
            if character_obj.avatar_path and os.path.exists(character_obj.avatar_path):
                try:
                    os.remove(character_obj.avatar_path)
                    print(f"已删除角色头像: {character_obj.avatar_path}")
                except Exception as e:
                    print(f"删除角色头像失败: {e}")
        
        self._execute_write('DELETE FROM characters WHERE id = ?', (character_id,))
    
    def create_background_image(self, character_id: int, image_path: str, description: str = None, tags: str = None) -> BackgroundImage:
        bg_image_id = self._execute_write('''
            INSERT INTO background_images (character_id, image_path, description, tags)
            VALUES (?, ?, ?, ?)
        ''', (character_id, image_path, description, tags))
        return self.get_background_image(bg_image_id)
    
    def get_background_image(self, bg_image_id: int) -> Optional[BackgroundImage]:
        cursor = self.conn.cursor()
        try:
            cursor.execute('SELECT * FROM background_images WHERE id = ?', (bg_image_id,))
            row = cursor.fetchone()
            if row:
                return BackgroundImage(*row)
            return None
        finally:
            cursor.close()
    
    def get_background_images(self, character_id: int) -> List[BackgroundImage]:
        cursor = self.conn.cursor()
        try:
            cursor.execute('SELECT * FROM background_images WHERE character_id = ? ORDER BY created_at', (character_id,))
            rows = cursor.fetchall()
            return [BackgroundImage(*row) for row in rows]
        finally:
            cursor.close()
    
    def get_all_background_images(self, world_id: int) -> List[BackgroundImage]:
        cursor = self.conn.cursor()
        try:
            cursor.execute('''
                SELECT bi.* FROM background_images bi
                INNER JOIN characters c ON bi.character_id = c.id
                WHERE c.world_id = ?
                ORDER BY bi.created_at
            ''', (world_id,))
            rows = cursor.fetchall()
            return [BackgroundImage(*row) for row in rows]
        finally:
            cursor.close()
    
    def create_location(self, world_id: int, name: str, image_path: str = None, parent_location_id: int = None, x: int = 0, y: int = 0) -> Location:
        location_id = self._execute_write('''
            INSERT INTO locations (world_id, name, image_path, parent_location_id, x, y)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (world_id, name, image_path, parent_location_id, x, y))
        return self.get_location(location_id)
    
    def get_location(self, location_id: int) -> Optional[Location]:
        cursor = self.conn.cursor()
        try:
            cursor.execute('''
                SELECT id, world_id, name, image_path, created_at, parent_location_id, x, y 
                FROM locations WHERE id = ?
            ''', (location_id,))
            row = cursor.fetchone()
            if row:
                return Location(*row)
            return None
        finally:
            cursor.close()
    
    def get_locations(self, world_id: int) -> List[Location]:
        cursor = self.conn.cursor()
        try:
            cursor.execute('''
                SELECT id, world_id, name, image_path, created_at, parent_location_id, x, y 
                FROM locations WHERE world_id = ? ORDER BY created_at
            ''', (world_id,))
            rows = cursor.fetchall()
            return [Location(*row) for row in rows]
        finally:
            cursor.close()
    
    def get_primary_locations(self, world_id: int) -> List[Location]:
        cursor = self.conn.cursor()
        try:
            cursor.execute('''
                SELECT id, world_id, name, image_path, created_at, parent_location_id, x, y 
                FROM locations WHERE world_id = ? AND parent_location_id IS NULL ORDER BY created_at
            ''', (world_id,))
            rows = cursor.fetchall()
            return [Location(*row) for row in rows]
        finally:
            cursor.close()
    
    def get_sub_locations(self, parent_location_id: int) -> List[Location]:
        cursor = self.conn.cursor()
        try:
            cursor.execute('''
                SELECT id, world_id, name, image_path, created_at, parent_location_id, x, y 
                FROM locations WHERE parent_location_id = ? ORDER BY created_at
            ''', (parent_location_id,))
            rows = cursor.fetchall()
            return [Location(*row) for row in rows]
        finally:
            cursor.close()
    
    def update_location(self, location_id: int, name: str = None, image_path: str = None, x: int = None, y: int = None):
        cursor = self.conn.cursor()
        try:
            updates = []
            params = []
            
            if name is not None:
                updates.append('name = ?')
                params.append(name)
            if image_path is not None:
                updates.append('image_path = ?')
                params.append(image_path)
            if x is not None:
                updates.append('x = ?')
                params.append(x)
            if y is not None:
                updates.append('y = ?')
                params.append(y)
            
            if updates:
                params.append(location_id)
                cursor.execute(f'UPDATE locations SET {", ".join(updates)} WHERE id = ?', params)
                self.conn.commit()
        finally:
            cursor.close()
    
    def delete_location(self, location_id: int):
        cursor = self.conn.cursor()
        try:
            cursor.execute('SELECT * FROM locations WHERE id = ?', (location_id,))
            location = cursor.fetchone()
            
            if location:
                location_obj = Location(*location)
                if location_obj.image_path and os.path.exists(location_obj.image_path):
                    try:
                        os.remove(location_obj.image_path)
                        print(f"已删除位置图片: {location_obj.image_path}")
                    except Exception as e:
                        print(f"删除位置图片失败: {e}")
            
            cursor.execute('DELETE FROM locations WHERE id = ?', (location_id,))
            self.conn.commit()
        finally:
            cursor.close()
    
    def create_transport_mode(self, world_id: int, name: str, speed: float) -> TransportMode:
        cursor = self.conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO transport_modes (world_id, name, speed)
                VALUES (?, ?, ?)
            ''', (world_id, name, speed))
            self.conn.commit()
            transport_id = cursor.lastrowid
            return self.get_transport_mode(transport_id)
        finally:
            cursor.close()
    
    def get_transport_mode(self, transport_id: int) -> Optional[TransportMode]:
        cursor = self.conn.cursor()
        try:
            cursor.execute('SELECT * FROM transport_modes WHERE id = ?', (transport_id,))
            row = cursor.fetchone()
            if row:
                return TransportMode(*row)
            return None
        finally:
            cursor.close()
    
    def get_transport_modes(self, world_id: int) -> List[TransportMode]:
        cursor = self.conn.cursor()
        try:
            cursor.execute('SELECT * FROM transport_modes WHERE world_id = ? ORDER BY created_at', (world_id,))
            rows = cursor.fetchall()
            return [TransportMode(*row) for row in rows]
        finally:
            cursor.close()
    
    def update_transport_mode(self, transport_id: int, name: str = None, speed: float = None):
        cursor = self.conn.cursor()
        updates = []
        params = []
        
        if name is not None:
            updates.append('name = ?')
            params.append(name)
        if speed is not None:
            updates.append('speed = ?')
            params.append(speed)
        
        if updates:
            params.append(transport_id)
            cursor.execute(f'UPDATE transport_modes SET {", ".join(updates)} WHERE id = ?', params)
            self.conn.commit()
    
    def delete_transport_mode(self, transport_id: int):
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM transport_modes WHERE id = ?', (transport_id,))
        self.conn.commit()
    
    def create_location_transfer(self, world_id: int, character_id: int = None, from_location: str = None, to_location: str = None, departure_date: str = None, departure_time: str = None, arrival_date: str = None, arrival_time: str = None):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO location_transfers (world_id, character_id, from_location, to_location, departure_date, departure_time, arrival_date, arrival_time)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (world_id, character_id, from_location, to_location, departure_date, departure_time, arrival_date, arrival_time))
        self.conn.commit()
        return cursor.lastrowid
    
    def get_pending_transfers(self, world_id: int, current_date: str, current_time: str):
        cursor = self.conn.cursor()
        
        cursor.execute('''
            SELECT * FROM location_transfers 
            WHERE world_id = ? AND is_completed = 0 
            ORDER BY arrival_date, arrival_time
        ''', (world_id,))
        all_transfers = cursor.fetchall()
        
        return all_transfers
    
    def is_user_on_the_way(self, world_id: int, current_date: str, current_time: str) -> bool:
        cursor = self.conn.cursor()
        
        cursor.execute('''
            SELECT * FROM location_transfers 
            WHERE world_id = ? AND is_completed = 0 AND character_id IS NULL
        ''', (world_id,))
        user_transfers = cursor.fetchall()
        
        if not user_transfers:
            return False
        
        for transfer in user_transfers:
            transfer_id = transfer[0]
            from_location = transfer[3]
            to_location = transfer[4]
            departure_date = transfer[5]
            departure_time = transfer[6]
            arrival_date = transfer[7]
            arrival_time = transfer[8]
            
            has_departed = self._is_time_passed(current_date, current_time, departure_date, departure_time)
            has_arrived = self._is_time_passed(current_date, current_time, arrival_date, arrival_time)
            
            if has_departed and not has_arrived:
                return True
        
        return False
    
    def _is_time_passed(self, current_date: str, current_time: str, target_date: str, target_time: str) -> bool:
        try:
            current_date_parts = current_date.split('-')
            target_date_parts = target_date.split('-')
            current_time_parts = current_time.split(':')
            target_time_parts = target_time.split(':')
            
            if len(current_date_parts) < 3 or len(target_date_parts) < 3:
                return False
            
            current_year = int(current_date_parts[0])
            current_month = int(current_date_parts[1])
            current_day = int(current_date_parts[2])
            
            target_year = int(target_date_parts[0])
            target_month = int(target_date_parts[1])
            target_day = int(target_date_parts[2])
            
            if current_year > target_year:
                return True
            elif current_year < target_year:
                return False
            
            if current_month > target_month:
                return True
            elif current_month < target_month:
                return False
            
            if current_day > target_day:
                return True
            elif current_day < target_day:
                return False
            
            if len(current_time_parts) < 2 or len(target_time_parts) < 2:
                return False
            
            current_hour = int(current_time_parts[0])
            current_minute = int(current_time_parts[1]) if len(current_time_parts) > 1 else 0
            
            target_hour = int(target_time_parts[0])
            target_minute = int(target_time_parts[1]) if len(target_time_parts) > 1 else 0
            
            if current_hour > target_hour:
                return True
            elif current_hour < target_hour:
                return False
            
            if current_minute >= target_minute:
                return True
            
            return False
        except Exception:
            return False
    
    def complete_transfer(self, transfer_id: int, new_location: str):
        cursor = self.conn.cursor()
        try:
            cursor.execute('SELECT character_id FROM location_transfers WHERE id = ?', (transfer_id,))
            result = cursor.fetchone()
            
            if result and result[0]:
                character_id = result[0]
                cursor.execute('UPDATE characters SET location = ? WHERE id = ?', (new_location, character_id))
            
            cursor.execute('UPDATE location_transfers SET is_completed = 1 WHERE id = ?', (transfer_id,))
            
            self.conn.commit()
        except Exception as e:
            self.conn.rollback()
            raise e
        finally:
            cursor.close()
    
    def get_active_transfers(self, world_id: int):
        cursor = self.conn.cursor()
        try:
            cursor.execute('''
                SELECT * FROM location_transfers 
                WHERE world_id = ? AND is_completed = 0 
                ORDER BY departure_date, departure_time
            ''', (world_id,))
            rows = cursor.fetchall()
            return rows
        finally:
            cursor.close()
    
    def update_background_image(self, bg_image_id: int, description: str = None, tags: str = None, image_path: str = None):
        cursor = self.conn.cursor()
        updates = []
        params = []
        
        if description is not None:
            updates.append('description = ?')
            params.append(description)
        if tags is not None:
            updates.append('tags = ?')
            params.append(tags)
        if image_path is not None:
            updates.append('image_path = ?')
            params.append(image_path)
        
        if updates:
            params.append(bg_image_id)
            cursor.execute(f'UPDATE background_images SET {", ".join(updates)} WHERE id = ?', params)
            self.conn.commit()
    
    def delete_background_image(self, bg_image_id: int):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM background_images WHERE id = ?', (bg_image_id,))
        bg_image = cursor.fetchone()
        
        if bg_image:
            bg_image_obj = BackgroundImage(*bg_image)
            if bg_image_obj.image_path and os.path.exists(bg_image_obj.image_path):
                try:
                    os.remove(bg_image_obj.image_path)
                    print(f"已删除背景图片: {bg_image_obj.image_path}")
                except Exception as e:
                    print(f"删除背景图片失败: {e}")
        
        cursor.execute('DELETE FROM background_images WHERE id = ?', (bg_image_id,))
        self.conn.commit()
    
    def create_chat_session(self, world_id: int, name: str) -> ChatSession:
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO chat_sessions (world_id, name)
            VALUES (?, ?)
        ''', (world_id, name))
        self.conn.commit()
        return self.get_chat_session(cursor.lastrowid)
    
    def get_chat_session(self, session_id: int) -> Optional[ChatSession]:
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM chat_sessions WHERE id = ?', (session_id,))
        row = cursor.fetchone()
        if row:
            return ChatSession(*row)
        return None
    
    def get_chat_sessions_by_world(self, world_id: int) -> List[ChatSession]:
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM chat_sessions WHERE world_id = ? ORDER BY created_at DESC', (world_id,))
        rows = cursor.fetchall()
        return [ChatSession(*row) for row in rows]
    
    def create_chat_message(self, session_id: int, character_id: int = None, character_name: str = None, content: str = None, action: str = None, background_image_id: int = None, avatar_path: str = None, message_type: str = 'user', segments: str = None, current_date: str = None, current_time: str = None, location: str = None) -> ChatMessage:
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO chat_messages (session_id, character_id, character_name, content, action, background_image_id, avatar_path, message_type, segments, current_date, current_time, location)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (session_id, character_id, character_name, content, action, background_image_id, avatar_path, message_type, segments, current_date, current_time, location))
        self.conn.commit()
        return self.get_chat_message(cursor.lastrowid)
    
    def get_chat_message(self, message_id: int) -> Optional[ChatMessage]:
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT id, session_id, character_id, character_name, content, action,
                   background_image_id, avatar_path, message_type, created_at,
                   current_date, current_time, segments, location, is_time_separator,
                   time_separator_start_date, time_separator_start_time,
                   time_separator_end_date, time_separator_end_time, dialogue_round
            FROM chat_messages WHERE id = ?
        ''', (message_id,))
        row = cursor.fetchone()
        if row:
            return ChatMessage(*row)
        return None
    
    def get_chat_messages_by_session(self, session_id: int, limit: int = 50, location: str = None, after_time_separator: bool = False) -> List[ChatMessage]:
        cursor = self.conn.cursor()
        query = '''
            SELECT id, session_id, character_id, character_name, content, action,
                   background_image_id, avatar_path, message_type, created_at,
                   current_date, current_time, segments, location, is_time_separator,
                   time_separator_start_date, time_separator_start_time,
                   time_separator_end_date, time_separator_end_time, dialogue_round
            FROM chat_messages WHERE session_id = ?
        '''
        params = [session_id]
        if location:
            query += ' AND location = ?'
            params.append(location)
        query += ' ORDER BY created_at DESC LIMIT ?'
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        messages = [ChatMessage(*row) for row in rows][::-1]
        
        if after_time_separator:
            separator_index = None
            for i, msg in enumerate(messages):
                if msg.is_time_separator == 1:
                    separator_index = i
            if separator_index is not None:
                messages = messages[separator_index + 1:]
        
        return messages
    
    def create_time_separator(self, session_id: int, start_date: str, start_time: str, end_date: str, end_time: str, location: str) -> ChatMessage:
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO chat_messages (session_id, content, message_type, is_time_separator, time_separator_start_date, time_separator_start_time, time_separator_end_date, time_separator_end_time, location)
            VALUES (?, ?, ?, 1, ?, ?, ?, ?, ?)
        ''', (session_id, '', 'time_separator', start_date, start_time, end_date, end_time, location))
        self.conn.commit()
        return self.get_chat_message(cursor.lastrowid)
    
    def update_chat_message(self, message_id: int, content: str = None, action: str = None, segments: str = None):
        cursor = self.conn.cursor()
        update_fields = []
        update_values = []
        
        if content is not None:
            update_fields.append("content = ?")
            update_values.append(content)
        if action is not None:
            update_fields.append("action = ?")
            update_values.append(action)
        if segments is not None:
            update_fields.append("segments = ?")
            update_values.append(segments)
        
        if update_fields:
            update_values.append(message_id)
            cursor.execute(f'''
                UPDATE chat_messages 
                SET {', '.join(update_fields)}
                WHERE id = ?
            ''', update_values)
            self.conn.commit()
            print(f"已更新消息ID {message_id}")
    
    def delete_chat_messages_after(self, session_id: int, message_id: int, location: str = None):
        cursor = self.conn.cursor()
        if location:
            cursor.execute('''
                DELETE FROM chat_messages 
                WHERE session_id = ? AND id > ? AND location = ?
            ''', (session_id, message_id, location))
            self.conn.commit()
            print(f"已删除会话 {session_id} 中地点 '{location}' 内ID大于 {message_id} 的所有聊天消息")
        else:
            cursor.execute('''
                DELETE FROM chat_messages 
                WHERE session_id = ? AND id > ?
            ''', (session_id, message_id))
            self.conn.commit()
            print(f"已删除会话 {session_id} 中ID大于 {message_id} 的所有聊天消息")
    
    def delete_chat_messages_after_time(self, session_id: int, target_date: str, target_time: str, location: str):
        cursor = self.conn.cursor()
        cursor.execute('''
            DELETE FROM chat_messages 
            WHERE session_id = ? AND location = ? AND 
            (current_date > ? OR (current_date = ? AND current_time > ?))
        ''', (session_id, location, target_date, target_date, target_time))
        self.conn.commit()
        print(f"已删除会话 {session_id} 地点 '{location}' 中时间在 {target_date} {target_time} 之后的所有聊天消息")
    
    def delete_all_chat_messages(self, session_id: int):
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM chat_messages WHERE session_id = ?', (session_id,))
        self.conn.commit()
        print(f"已删除会话 {session_id} 的所有聊天消息")
    
    def delete_chat_session(self, session_id: int):
        self.delete_all_chat_messages(session_id)
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM chat_sessions WHERE id = ?', (session_id,))
        self.conn.commit()
        print(f"已删除会话 {session_id}")
    
    def create_memory(self, world_id: int, memory_type: str, content: str, importance: int = 1, character_id: int = None, segment: int = 1) -> Memory:
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO memories (world_id, character_id, memory_type, content, importance, segment)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (world_id, character_id, memory_type, content, importance, segment))
        self.conn.commit()
        return self.get_memory(cursor.lastrowid)
    
    def get_memory(self, memory_id: int) -> Optional[Memory]:
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM memories WHERE id = ?', (memory_id,))
        row = cursor.fetchone()
        if row:
            return Memory(*row)
        return None
    
    def get_memories_by_world(self, world_id: int, memory_type: str = None, limit: int = 20) -> List[Memory]:
        cursor = self.conn.cursor()
        if memory_type:
            cursor.execute('''
                SELECT * FROM memories WHERE world_id = ? AND memory_type = ? 
                ORDER BY importance DESC, created_at DESC LIMIT ?
            ''', (world_id, memory_type, limit))
        else:
            cursor.execute('''
                SELECT * FROM memories WHERE world_id = ? 
                ORDER BY importance DESC, created_at DESC LIMIT ?
            ''', (world_id, limit))
        rows = cursor.fetchall()
        return [Memory(*row) for row in rows]
    
    def get_memories_by_character(self, character_id: int, memory_type: str = None, limit: int = 20) -> List[Memory]:
        cursor = self.conn.cursor()
        if memory_type:
            cursor.execute('''
                SELECT * FROM memories WHERE character_id = ? AND memory_type = ? 
                ORDER BY importance DESC, created_at DESC LIMIT ?
            ''', (character_id, memory_type, limit))
        else:
            cursor.execute('''
                SELECT * FROM memories WHERE character_id = ? 
                ORDER BY importance DESC, created_at DESC LIMIT ?
            ''', (character_id, limit))
        rows = cursor.fetchall()
        return [Memory(*row) for row in rows]
    
    def update_memory(self, memory_id: int, content: str = None, importance: int = None):
        cursor = self.conn.cursor()
        updates = []
        params = []
        
        if content is not None:
            updates.append('content = ?')
            params.append(content)
        if importance is not None:
            updates.append('importance = ?')
            params.append(importance)
        
        if updates:
            params.append(memory_id)
            cursor.execute(f'UPDATE memories SET {", ".join(updates)} WHERE id = ?', params)
            self.conn.commit()
    
    def delete_memory(self, memory_id: int):
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM memories WHERE id = ?', (memory_id,))
        self.conn.commit()
    
    def delete_all_memories(self, world_id: int, character_id: int = None):
        cursor = self.conn.cursor()
        if character_id:
            cursor.execute('DELETE FROM memories WHERE world_id = ? AND character_id = ?', (world_id, character_id))
        else:
            cursor.execute('DELETE FROM memories WHERE world_id = ?', (world_id,))
        self.conn.commit()
    
    def create_character_relationship(self, world_id: int, source_character_id: int, target_character_id: int, relationship_type: str, description: str, importance: int = 1) -> CharacterRelationship:
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO character_relationships (world_id, source_character_id, target_character_id, relationship_type, description, importance)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (world_id, source_character_id, target_character_id, relationship_type, description, importance))
        self.conn.commit()
        return self.get_character_relationship(cursor.lastrowid)
    
    def get_character_relationship(self, relationship_id: int) -> Optional[CharacterRelationship]:
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM character_relationships WHERE id = ?', (relationship_id,))
        row = cursor.fetchone()
        if row:
            return CharacterRelationship(*row)
        return None
    
    def get_character_relationships(self, world_id: int, source_character_id: int = None, target_character_id: int = None) -> List[CharacterRelationship]:
        cursor = self.conn.cursor()
        if source_character_id and target_character_id:
            cursor.execute('''
                SELECT * FROM character_relationships 
                WHERE world_id = ? AND source_character_id = ? AND target_character_id = ?
                ORDER BY importance DESC, created_at DESC
            ''', (world_id, source_character_id, target_character_id))
        elif source_character_id:
            cursor.execute('''
                SELECT * FROM character_relationships 
                WHERE world_id = ? AND source_character_id = ?
                ORDER BY importance DESC, created_at DESC
            ''', (world_id, source_character_id))
        elif target_character_id:
            cursor.execute('''
                SELECT * FROM character_relationships 
                WHERE world_id = ? AND target_character_id = ?
                ORDER BY importance DESC, created_at DESC
            ''', (world_id, target_character_id))
        else:
            cursor.execute('''
                SELECT * FROM character_relationships 
                WHERE world_id = ?
                ORDER BY importance DESC, created_at DESC
            ''', (world_id,))
        rows = cursor.fetchall()
        return [CharacterRelationship(*row) for row in rows]
    
    def update_character_relationship(self, relationship_id: int, relationship_type: str = None, description: str = None, importance: int = None):
        cursor = self.conn.cursor()
        updates = []
        params = []
        
        if relationship_type is not None:
            updates.append('relationship_type = ?')
            params.append(relationship_type)
        if description is not None:
            updates.append('description = ?')
            params.append(description)
        if importance is not None:
            updates.append('importance = ?')
            params.append(importance)
        
        if updates:
            params.append(relationship_id)
            cursor.execute(f'UPDATE character_relationships SET {", ".join(updates)} WHERE id = ?', params)
            self.conn.commit()
    
    def delete_character_relationship(self, relationship_id: int):
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM character_relationships WHERE id = ?', (relationship_id,))
        self.conn.commit()
    
    def get_location_dialogue_state(self, world_id: int, location_name: str) -> Optional[LocationDialogueState]:
        cursor = self.conn.cursor()
        try:
            cursor.execute('SELECT * FROM location_dialogue_states WHERE world_id = ? AND location = ?', (world_id, location_name))
            row = cursor.fetchone()
            if row:
                return LocationDialogueState(*row)
            return None
        finally:
            cursor.close()
    
    def create_location_dialogue_state(self, world_id: int, location_name: str, current_date: str, current_time: str, dialogue_segment: int = 1) -> LocationDialogueState:
        cursor = self.conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO location_dialogue_states (world_id, location, dialogue_count, last_dialogue_date, last_dialogue_time)
                VALUES (?, ?, 1, ?, ?)
            ''', (world_id, location_name, current_date, current_time))
            self.conn.commit()
            return self.get_location_dialogue_state(world_id, location_name)
        finally:
            cursor.close()
    
    def update_location_dialogue_state(self, world_id: int, location_name: str, current_date: str = None, current_time: str = None, dialogue_segment: int = None):
        cursor = self.conn.cursor()
        try:
            updates = []
            params = []
            
            if current_date is not None:
                updates.append('last_dialogue_date = ?')
                params.append(current_date)
            if current_time is not None:
                updates.append('last_dialogue_time = ?')
                params.append(current_time)
            if dialogue_segment is not None:
                updates.append('dialogue_count = ?')
                params.append(dialogue_segment)
            
            if updates:
                params.extend([world_id, location_name])
                cursor.execute(f'UPDATE location_dialogue_states SET {", ".join(updates)} WHERE world_id = ? AND location = ?', params)
                self.conn.commit()
        finally:
            cursor.close()
    
    def get_memories_by_segment(self, world_id: int, segment: int, memory_type: str = None) -> List[Memory]:
        cursor = self.conn.cursor()
        try:
            if memory_type:
                cursor.execute('''
                    SELECT * FROM memories WHERE world_id = ? AND segment = ? AND memory_type = ?
                    ORDER BY importance DESC, created_at DESC
                ''', (world_id, segment, memory_type))
            else:
                cursor.execute('''
                    SELECT * FROM memories WHERE world_id = ? AND segment = ?
                    ORDER BY importance DESC, created_at DESC
                ''', (world_id, segment))
            rows = cursor.fetchall()
            return [Memory(*row) for row in rows]
        finally:
            cursor.close()
    
    def delete_memories_from_segment(self, world_id: int, from_segment: int, character_id: int = None):
        cursor = self.conn.cursor()
        try:
            if character_id:
                cursor.execute('DELETE FROM memories WHERE world_id = ? AND character_id = ? AND segment >= ?', 
                             (world_id, character_id, from_segment))
            else:
                cursor.execute('DELETE FROM memories WHERE world_id = ? AND segment >= ?', 
                             (world_id, from_segment))
            self.conn.commit()
        finally:
            cursor.close()
    
    def create_short_term_memory(self, world_id: int, content: str, importance: int = 1, character_id: int = None, source_message_ids: str = None) -> ShortTermMemory:
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO short_term_memories (world_id, character_id, content, importance, source_message_ids)
            VALUES (?, ?, ?, ?, ?)
        ''', (world_id, character_id, content, importance, source_message_ids))
        self.conn.commit()
        return self.get_short_term_memory(cursor.lastrowid)
    
    def get_short_term_memory(self, memory_id: int) -> Optional[ShortTermMemory]:
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM short_term_memories WHERE id = ?', (memory_id,))
        row = cursor.fetchone()
        if row:
            return ShortTermMemory(*row)
        return None
    
    def get_short_term_memories(self, world_id: int, character_id: int = None, limit: int = 20) -> List[ShortTermMemory]:
        cursor = self.conn.cursor()
        if character_id:
            cursor.execute('''
                SELECT * FROM short_term_memories WHERE world_id = ? AND character_id = ?
                ORDER BY importance DESC, created_at DESC LIMIT ?
            ''', (world_id, character_id, limit))
        else:
            cursor.execute('''
                SELECT * FROM short_term_memories WHERE world_id = ?
                ORDER BY importance DESC, created_at DESC LIMIT ?
            ''', (world_id, limit))
        rows = cursor.fetchall()
        return [ShortTermMemory(*row) for row in rows]
    
    def get_short_term_memory_count(self, world_id: int, character_id: int = None) -> int:
        cursor = self.conn.cursor()
        if character_id:
            cursor.execute('SELECT COUNT(*) FROM short_term_memories WHERE world_id = ? AND character_id = ?', 
                         (world_id, character_id))
        else:
            cursor.execute('SELECT COUNT(*) FROM short_term_memories WHERE world_id = ?', (world_id,))
        result = cursor.fetchone()[0]
        return result if result is not None else 0
    
    def delete_short_term_memory(self, memory_id: int):
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM short_term_memories WHERE id = ?', (memory_id,))
        self.conn.commit()
    
    def update_short_term_memory(self, memory_id: int, content: str = None, importance: int = None):
        cursor = self.conn.cursor()
        updates = []
        params = []
        
        if content is not None:
            updates.append('content = ?')
            params.append(content)
        if importance is not None:
            updates.append('importance = ?')
            params.append(importance)
        
        if updates:
            params.append(memory_id)
            cursor.execute(f'UPDATE short_term_memories SET {", ".join(updates)} WHERE id = ?', params)
            self.conn.commit()
    
    def delete_oldest_short_term_memories(self, world_id: int, character_id: int = None, count: int = 1):
        cursor = self.conn.cursor()
        if character_id:
            cursor.execute('''
                DELETE FROM short_term_memories WHERE id IN (
                    SELECT id FROM short_term_memories 
                    WHERE world_id = ? AND character_id = ? 
                    ORDER BY created_at ASC LIMIT ?
                )
            ''', (world_id, character_id, count))
        else:
            cursor.execute('''
                DELETE FROM short_term_memories WHERE id IN (
                    SELECT id FROM short_term_memories 
                    WHERE world_id = ? 
                    ORDER BY created_at ASC LIMIT ?
                )
            ''', (world_id, count))
        self.conn.commit()
    
    def create_long_term_memory(self, world_id: int, content: str, importance: int = 1, character_id: int = None, source_short_term_ids: str = None) -> LongTermMemory:
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO long_term_memories (world_id, character_id, content, importance, source_short_term_ids)
            VALUES (?, ?, ?, ?, ?)
        ''', (world_id, character_id, content, importance, source_short_term_ids))
        self.conn.commit()
        return self.get_long_term_memory(cursor.lastrowid)
    
    def get_long_term_memory(self, memory_id: int) -> Optional[LongTermMemory]:
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM long_term_memories WHERE id = ?', (memory_id,))
        row = cursor.fetchone()
        if row:
            return LongTermMemory(*row)
        return None
    
    def get_long_term_memories(self, world_id: int, character_id: int = None, limit: int = 20) -> List[LongTermMemory]:
        cursor = self.conn.cursor()
        if character_id:
            cursor.execute('''
                SELECT * FROM long_term_memories WHERE world_id = ? AND character_id = ?
                ORDER BY importance DESC, created_at DESC LIMIT ?
            ''', (world_id, character_id, limit))
        else:
            cursor.execute('''
                SELECT * FROM long_term_memories WHERE world_id = ?
                ORDER BY importance DESC, created_at DESC LIMIT ?
            ''', (world_id, limit))
        rows = cursor.fetchall()
        return [LongTermMemory(*row) for row in rows]
    
    def get_max_segment(self, world_id: int) -> int:
        cursor = self.conn.cursor()
        cursor.execute('SELECT MAX(segment) FROM memories WHERE world_id = ?', (world_id,))
        result = cursor.fetchone()[0]
        return result if result is not None else 0
    
    def update_long_term_memory(self, memory_id: int, content: str = None, importance: int = None):
        cursor = self.conn.cursor()
        updates = []
        params = []
        
        if content is not None:
            updates.append('content = ?')
            params.append(content)
        if importance is not None:
            updates.append('importance = ?')
            params.append(importance)
        
        if updates:
            params.append(memory_id)
            cursor.execute(f'UPDATE long_term_memories SET {", ".join(updates)} WHERE id = ?', params)
            self.conn.commit()
    
    def delete_long_term_memory(self, memory_id: int):
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM long_term_memories WHERE id = ?', (memory_id,))
        self.conn.commit()
    
    def save_api_config(self, api1_key: str = None, api1_model: str = None, api2_key: str = None, api2_model: str = None):
        cursor = self.conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM api_config')
        count = cursor.fetchone()[0]
        
        if count == 0:
            cursor.execute('''
                INSERT INTO api_config (api1_key, api1_model, api2_key, api2_model)
                VALUES (?, ?, ?, ?)
            ''', (api1_key, api1_model, api2_key, api2_model))
        else:
            updates = []
            params = []
            
            if api1_key is not None:
                updates.append('api1_key = ?')
                params.append(api1_key)
            if api1_model is not None:
                updates.append('api1_model = ?')
                params.append(api1_model)
            if api2_key is not None:
                updates.append('api2_key = ?')
                params.append(api2_key)
            if api2_model is not None:
                updates.append('api2_model = ?')
                params.append(api2_model)
            
            if updates:
                cursor.execute(f'UPDATE api_config SET {", ".join(updates)}', params)
        
        self.conn.commit()
    
    def get_api_config(self) -> Optional[APIConfig]:
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT id, api1_key, api1_model, api2_key, api2_model 
            FROM api_config LIMIT 1
        ''')
        row = cursor.fetchone()
        if row:
            return APIConfig(*row)
        return None
    
    def update_activity_score(self, character_id: int, delta: int):
        cursor = self.conn.cursor()
        cursor.execute('UPDATE characters SET activity_score = activity_score + ? WHERE id = ?', (delta, character_id))
        self.conn.commit()
    
    def reset_activity_score(self, character_id: int):
        cursor = self.conn.cursor()
        cursor.execute('UPDATE characters SET activity_score = 0 WHERE id = ?', (character_id,))
        self.conn.commit()
    
    def increment_all_activity_scores(self, world_id: int, delta: int):
        cursor = self.conn.cursor()
        cursor.execute('UPDATE characters SET activity_score = activity_score + ? WHERE world_id = ?', (delta, world_id))
        self.conn.commit()
    
    def close(self):
        with self._connections_lock:
            for thread_id, conn in list(self._all_connections.items()):
                try:
                    if conn:
                        conn.close()
                except Exception as e:
                    print(f"关闭线程 {thread_id} 的数据库连接时出错: {e}")
            self._all_connections.clear()
    
    def save_avatar(self, world_id: int, character_id: int, source_path: str) -> str:
        avatar_dir = self._get_avatar_dir(world_id)
        os.makedirs(avatar_dir, exist_ok=True)
        
        filename = f"character_{character_id}_{os.path.basename(source_path)}"
        dest_path = os.path.join(avatar_dir, filename)
        
        shutil.copy2(source_path, dest_path)
        
        return dest_path
    
    def save_background_image(self, world_id: int, character_id: int, source_path: str, description: str = None, tags: str = None) -> BackgroundImage:
        background_dir = self._get_background_dir(world_id)
        os.makedirs(background_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        ext = os.path.splitext(source_path)[1]
        filename = f"character_{character_id}_{timestamp}{ext}"
        dest_path = os.path.join(background_dir, filename)
        
        shutil.copy2(source_path, dest_path)
        
        return self.create_background_image(character_id, dest_path, description, tags)
    
    def save_audio(self, world_id: int, source_path: str) -> str:
        audio_dir = self._get_audio_dir(world_id)
        os.makedirs(audio_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        ext = os.path.splitext(source_path)[1]
        filename = f"audio_{timestamp}{ext}"
        dest_path = os.path.join(audio_dir, filename)
        
        shutil.copy2(source_path, dest_path)
        
        return dest_path
    
    def export_world(self, world_id: int, export_path: str) -> bool:
        try:
            world = self.get_world(world_id)
            if not world:
                return False
            
            world_dir = self._get_world_dir(world_id)
            if not os.path.exists(world_dir):
                return False
            
            shutil.make_archive(export_path, 'zip', world_dir)
            return True
        except Exception as e:
            print(f"导出世界失败: {e}")
            return False
    
    def import_world(self, world_id: int, import_path: str) -> bool:
        try:
            world = self.get_world(world_id)
            if not world:
                return False
            
            world_dir = self._get_world_dir(world_id)
            os.makedirs(world_dir, exist_ok=True)
            
            shutil.unpack_archive(import_path, world_dir)
            return True
        except Exception as e:
            print(f"导入世界失败: {e}")
            return False
    
    def create_remote_character_event(
        self,
        character_id: int,
        character_name: str,
        event_type: str,
        description: str,
        target_date: str,
        target_time: str
    ) -> RemoteCharacterEvent:
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO remote_character_events 
            (character_id, character_name, event_type, description, target_date, target_time, is_processed)
            VALUES (?, ?, ?, ?, ?, ?, 0)
        ''', (character_id, character_name, event_type, description, target_date, target_time))
        self.conn.commit()
        return self.get_remote_character_event(cursor.lastrowid)
    
    def get_remote_character_event(self, event_id: int) -> Optional[RemoteCharacterEvent]:
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM remote_character_events WHERE id = ?', (event_id,))
        row = cursor.fetchone()
        if row:
            return RemoteCharacterEvent(*row)
        return None
    
    def get_pending_remote_events(self, current_date: str, current_time: str) -> List[RemoteCharacterEvent]:
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM remote_character_events 
            WHERE is_processed = 0 
            AND (target_date < ? OR (target_date = ? AND target_time <= ?))
            ORDER BY target_date, target_time
        ''', (current_date, current_date, current_time))
        rows = cursor.fetchall()
        return [RemoteCharacterEvent(*row) for row in rows]
    
    def get_pending_events_for_character(self, character_id: int) -> List[RemoteCharacterEvent]:
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM remote_character_events 
            WHERE character_id = ? AND is_processed = 0
            ORDER BY target_date, target_time
        ''', (character_id,))
        rows = cursor.fetchall()
        return [RemoteCharacterEvent(*row) for row in rows]
    
    def mark_remote_event_as_processed(self, event_id: int):
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE remote_character_events 
            SET is_processed = 1 
            WHERE id = ?
        ''', (event_id,))
        self.conn.commit()
    
    def delete_old_remote_events(self, days: int = 7):
        cursor = self.conn.cursor()
        cursor.execute(f'''
            DELETE FROM remote_character_events 
            WHERE created_at < datetime('now', '-{days} days')
        ''')
        deleted_count = cursor.rowcount
        self.conn.commit()
        print(f"清理了{deleted_count}个旧事件")
    
    def create_active_call(self, world_id: int, character_id: int, character_name: str, original_location: str, call_start_date: str, call_start_time: str) -> ActiveCall:
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO active_calls (world_id, character_id, character_name, original_location, call_start_date, call_start_time)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (world_id, character_id, character_name, original_location, call_start_date, call_start_time))
        self.conn.commit()
        return self.get_active_call(cursor.lastrowid)
    
    def get_active_call(self, call_id: int) -> Optional[ActiveCall]:
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM active_calls WHERE id = ?', (call_id,))
        row = cursor.fetchone()
        if row:
            return ActiveCall(*row)
        return None
    
    def get_active_calls_by_world(self, world_id: int) -> List[ActiveCall]:
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM active_calls WHERE world_id = ?', (world_id,))
        rows = cursor.fetchall()
        return [ActiveCall(*row) for row in rows]
    
    def get_active_call_by_character(self, character_id: int) -> Optional[ActiveCall]:
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM active_calls WHERE character_id = ?', (character_id,))
        row = cursor.fetchone()
        if row:
            return ActiveCall(*row)
        return None
    
    def end_active_call(self, call_id: int):
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM active_calls WHERE id = ?', (call_id,))
        self.conn.commit()
    
    def end_all_calls_for_character(self, character_id: int):
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM active_calls WHERE character_id = ?', (character_id,))
        self.conn.commit()
    
    def is_character_on_call(self, character_id: int) -> bool:
        cursor = self.conn.cursor()
        cursor.execute('SELECT 1 FROM active_calls WHERE character_id = ?', (character_id,))
        return cursor.fetchone() is not None
    
    def create_incoming_call_request(self, world_id: int, character_id: int, character_name: str, request_date: str, request_time: str) -> IncomingCallRequest:
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO incoming_call_requests (world_id, character_id, character_name, request_date, request_time, is_handled)
            VALUES (?, ?, ?, ?, ?, 0)
        ''', (world_id, character_id, character_name, request_date, request_time))
        self.conn.commit()
        return self.get_incoming_call_request(cursor.lastrowid)
    
    def get_incoming_call_request(self, request_id: int) -> Optional[IncomingCallRequest]:
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM incoming_call_requests WHERE id = ?', (request_id,))
        row = cursor.fetchone()
        if row:
            return IncomingCallRequest(*row)
        return None
    
    def get_pending_call_requests(self, world_id: int) -> List[IncomingCallRequest]:
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM incoming_call_requests WHERE world_id = ? AND is_handled = 0', (world_id,))
        rows = cursor.fetchall()
        return [IncomingCallRequest(*row) for row in rows]
    
    def has_pending_call_requests(self, world_id: int) -> bool:
        cursor = self.conn.cursor()
        cursor.execute('SELECT 1 FROM incoming_call_requests WHERE world_id = ? AND is_handled = 0 LIMIT 1', (world_id,))
        return cursor.fetchone() is not None
    
    def mark_call_request_as_handled(self, request_id: int):
        cursor = self.conn.cursor()
        cursor.execute('UPDATE incoming_call_requests SET is_handled = 1 WHERE id = ?', (request_id,))
        self.conn.commit()
    
    def dismiss_call_request(self, request_id: int):
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM incoming_call_requests WHERE id = ?', (request_id,))
        self.conn.commit()
    
    def clear_all_call_requests_for_world(self, world_id: int):
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM incoming_call_requests WHERE world_id = ?', (world_id,))
        self.conn.commit()
