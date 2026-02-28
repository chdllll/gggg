import json
from typing import Optional, Dict, Any, List

class ScriptManager:
    def __init__(self, db_manager):
        self.db = db_manager
    
    def get_current_chapter(self, world_id: int) -> Optional[Dict[str, Any]]:
        world = self.db.get_world(world_id)
        if not world or not world.script_enabled or not world.script_chapters:
            return None
        
        try:
            chapters = world.script_chapters
            if isinstance(chapters, str):
                chapters = json.loads(chapters)
            
            if not chapters:
                return None
            
            current_index = world.current_chapter_index or 0
            if current_index >= len(chapters):
                return None
            
            chapter = chapters[current_index]
            chapter['index'] = current_index
            chapter['total_chapters'] = len(chapters)
            
            return chapter
        except (json.JSONDecodeError, TypeError):
            return None
    
    def get_all_chapters(self, world_id: int) -> List[Dict[str, Any]]:
        world = self.db.get_world(world_id)
        if not world or not world.script_chapters:
            return []
        
        try:
            chapters = world.script_chapters
            if isinstance(chapters, str):
                chapters = json.loads(chapters)
            return chapters
        except (json.JSONDecodeError, TypeError):
            return []
    
    def advance_to_next_chapter(self, world_id: int) -> bool:
        world = self.db.get_world(world_id)
        if not world or not world.script_enabled or not world.script_chapters:
            return False
        
        try:
            chapters = world.script_chapters
            if isinstance(chapters, str):
                chapters = json.loads(chapters)
            
            current_index = world.current_chapter_index or 0
            
            if current_index + 1 >= len(chapters):
                return False
            
            self.db.update_world(
                world_id,
                current_chapter_index=current_index + 1
            )
            
            return True
        except (json.JSONDecodeError, TypeError):
            return False
    
    def is_script_enabled(self, world_id: int) -> bool:
        world = self.db.get_world(world_id)
        if not world:
            return False
        
        return bool(world.script_enabled)
    
    def get_script_progress(self, world_id: int) -> Dict[str, Any]:
        world = self.db.get_world(world_id)
        if not world or not world.script_enabled or not world.script_chapters:
            return {
                'enabled': False,
                'current_index': 0,
                'total_chapters': 0,
                'progress_percent': 0
            }
        
        try:
            chapters = world.script_chapters
            if isinstance(chapters, str):
                chapters = json.loads(chapters)
            
            current_index = world.current_chapter_index or 0
            total_chapters = len(chapters)
            progress_percent = int((current_index + 1) / total_chapters * 100) if total_chapters > 0 else 0
            
            return {
                'enabled': True,
                'current_index': current_index,
                'total_chapters': total_chapters,
                'progress_percent': progress_percent,
                'is_last_chapter': current_index >= total_chapters - 1
            }
        except (json.JSONDecodeError, TypeError):
            return {
                'enabled': False,
                'current_index': 0,
                'total_chapters': 0,
                'progress_percent': 0
            }
    
    def reset_script_progress(self, world_id: int) -> bool:
        world = self.db.get_world(world_id)
        if not world:
            return False
        
        self.db.update_world(
            world_id,
            current_chapter_index=0
        )
        
        return True
    
    def disable_script(self, world_id: int) -> bool:
        world = self.db.get_world(world_id)
        if not world:
            return False
        
        self.db.update_world(
            world_id,
            script_enabled=False
        )
        
        return True
    
    def enable_script(self, world_id: int) -> bool:
        world = self.db.get_world(world_id)
        if not world or not world.script_chapters:
            return False
        
        self.db.update_world(
            world_id,
            script_enabled=True
        )
        
        return True
    
    def update_chapters(self, world_id: int, chapters: List[Dict[str, Any]]) -> bool:
        if not chapters:
            return False
        
        chapters_json = json.dumps(chapters, ensure_ascii=False)
        
        self.db.update_world(
            world_id,
            script_chapters=chapters_json,
            current_chapter_index=0,
            script_enabled=True
        )
        
        return True
    
    def update_chapter(self, world_id: int, chapter_index: int, chapter_data: Dict[str, Any]) -> bool:
        world = self.db.get_world(world_id)
        if not world or not world.script_chapters:
            return False
        
        try:
            chapters = world.script_chapters
            if isinstance(chapters, str):
                chapters = json.loads(chapters)
            
            if chapter_index < 0 or chapter_index >= len(chapters):
                return False
            
            chapters[chapter_index]['title'] = chapter_data.get('title', chapters[chapter_index].get('title', ''))
            chapters[chapter_index]['description'] = chapter_data.get('description', chapters[chapter_index].get('description', ''))
            chapters[chapter_index]['estimated_rounds'] = chapter_data.get('estimated_rounds', chapters[chapter_index].get('estimated_rounds', 5))
            
            chapters_json = json.dumps(chapters, ensure_ascii=False)
            
            self.db.update_world(
                world_id,
                script_chapters=chapters_json
            )
            
            return True
        except (json.JSONDecodeError, TypeError):
            return False
    
    def set_current_chapter(self, world_id: int, chapter_index: int) -> bool:
        world = self.db.get_world(world_id)
        if not world or not world.script_chapters:
            return False
        
        try:
            chapters = world.script_chapters
            if isinstance(chapters, str):
                chapters = json.loads(chapters)
            
            if chapter_index < 0 or chapter_index >= len(chapters):
                return False
            
            self.db.update_world(
                world_id,
                current_chapter_index=chapter_index
            )
            
            return True
        except (json.JSONDecodeError, TypeError):
            return False
    

