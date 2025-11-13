import json
import os
from typing import List, Dict, Optional
from datetime import datetime

def format_number(num: int) -> str:
    """Форматировать число с пробелами вместо запятых (1 115 вместо 1,115)"""
    return f"{num:,}".replace(',', ' ')

DATA_DIR = os.getenv('DATA_DIR', './data')
ENTRIES_FILE = os.path.join(DATA_DIR, 'entries.json')
PROJECTS_FILE = os.path.join(DATA_DIR, 'projects.json')
WISHLIST_FILE = os.path.join(DATA_DIR, 'wishlist.json')
NOTES_FILE = os.path.join(DATA_DIR, 'notes.json')
PLANS_FILE = os.path.join(DATA_DIR, 'plans.json')
CHALLENGES_FILE = os.path.join(DATA_DIR, 'user_challenges.json')
SUBSCRIPTIONS_FILE = os.path.join(DATA_DIR, 'subscriptions.json')
USERS_FILE = os.path.join(DATA_DIR, 'users.json')

# Создаём директорию если её нет
os.makedirs(DATA_DIR, exist_ok=True)

def _ensure_file(filepath: str):
    """Создаёт файл если его нет"""
    if not os.path.exists(filepath):
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump([], f, ensure_ascii=False)

_ensure_file(ENTRIES_FILE)
_ensure_file(PROJECTS_FILE)
_ensure_file(WISHLIST_FILE)
_ensure_file(NOTES_FILE)
_ensure_file(PLANS_FILE)
_ensure_file(CHALLENGES_FILE)
_ensure_file(SUBSCRIPTIONS_FILE)

# Для users.json используем список ID
if not os.path.exists(USERS_FILE):
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump([], f, ensure_ascii=False)

# === Авторизация (устарело, оставлено для совместимости) ===
def is_authorized(user_id: int) -> bool:
    """Проверить, авторизован ли пользователь (устарело, используйте is_subscribed)"""
    return is_subscribed(user_id)

# === Подписки ===
def get_user_subscription(user_id: int) -> Optional[Dict]:
    """Получить информацию о подписке пользователя"""
    with open(SUBSCRIPTIONS_FILE, 'r', encoding='utf-8') as f:
        subscriptions = json.load(f)
    for sub in subscriptions:
        if sub.get('userId') == user_id:
            return sub
    return None

def save_subscription(user_id: int, subscription_data: Dict):
    """Сохранить информацию о подписке"""
    subscriptions = []
    if os.path.exists(SUBSCRIPTIONS_FILE):
        with open(SUBSCRIPTIONS_FILE, 'r', encoding='utf-8') as f:
            subscriptions = json.load(f)
    
    # Удаляем старую подписку пользователя
    subscriptions = [s for s in subscriptions if s.get('userId') != user_id]
    
    # Добавляем новую
    subscription_data['userId'] = user_id
    subscriptions.append(subscription_data)
    
    with open(SUBSCRIPTIONS_FILE, 'w', encoding='utf-8') as f:
        json.dump(subscriptions, f, ensure_ascii=False, indent=2)

def is_subscribed(user_id: int) -> bool:
    """Проверить, есть ли активная подписка"""
    # Импортируем здесь, чтобы избежать циклических импортов
    try:
        from config import TEST_MODE
        if TEST_MODE:
            return True  # В тестовом режиме все имеют доступ
    except:
        # Если config не загружен, считаем что тестовый режим
        return True
    
    subscription = get_user_subscription(user_id)
    if not subscription:
        return False
    
    # Проверяем, не истекла ли подписка
    expires_at = subscription.get('expiresAt')
    if expires_at:
        try:
            expire_date = datetime.fromisoformat(expires_at)
            return datetime.now() < expire_date
        except:
            return False
    
    return subscription.get('active', False)

# === Пользователи ===
def save_user_id(user_id: int):
    """Сохранить ID пользователя (если его еще нет в списке)"""
    users = []
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r', encoding='utf-8') as f:
            users = json.load(f)
    
    if user_id not in users:
        users.append(user_id)
        with open(USERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(users, f, ensure_ascii=False, indent=2)

def get_all_user_ids() -> List[int]:
    """Получить список всех ID пользователей"""
    if not os.path.exists(USERS_FILE):
        return []
    
    with open(USERS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

# === Записи о крестиках ===
def get_entries(user_id: Optional[int] = None) -> List[Dict]:
    """Получить все записи или записи конкретного пользователя"""
    with open(ENTRIES_FILE, 'r', encoding='utf-8') as f:
        entries = json.load(f)
    if user_id:
        return [e for e in entries if e.get('userId') == user_id]
    return entries

def add_count_to_date(date: str, count: int, user_id: int, hashtag: Optional[str] = None):
    """Добавить крестики за дату с опциональным хэштегом"""
    entries = get_entries()
    # Ищем существующую запись за эту дату без хэштега или с таким же хэштегом
    found = False
    for entry in entries:
        if (entry.get('date') == date and 
            entry.get('userId') == user_id and 
            entry.get('hashtag') == hashtag):
            entry['count'] = entry.get('count', 0) + count
            found = True
            break
    
    if not found:
        entry_data = {
            'id': f"{date}-{user_id}-{int(datetime.now().timestamp())}",
            'date': date,
            'count': count,
            'userId': user_id
        }
        if hashtag:
            entry_data['hashtag'] = hashtag
        entries.append(entry_data)
    
    with open(ENTRIES_FILE, 'w', encoding='utf-8') as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)

def get_entries_by_hashtag(hashtag: str, user_id: int) -> List[Dict]:
    """Получить записи по хэштегу"""
    entries = get_entries(user_id)
    return [e for e in entries if e.get('hashtag') == hashtag]

def get_all_hashtags(user_id: int) -> List[str]:
    """Получить все уникальные хэштеги пользователя (из записей и проектов)"""
    entries = get_entries(user_id)
    projects = get_projects(user_id)
    hashtags = set()
    
    # Хэштеги из записей о крестиках
    for entry in entries:
        if entry.get('hashtag'):
            hashtags.add(entry.get('hashtag'))
    
    # Хэштеги из проектов
    for project in projects:
        if project.get('hashtag'):
            hashtags.add(project.get('hashtag'))
    
    return sorted(list(hashtags))

def get_projects_by_hashtag(hashtag: str, user_id: int) -> List[Dict]:
    """Получить проекты по хэштегу"""
    projects = get_projects(user_id)
    return [p for p in projects if p.get('hashtag') == hashtag]

# === Проекты ===
def get_projects(user_id: Optional[int] = None) -> List[Dict]:
    """Получить все проекты или проекты конкретного пользователя"""
    with open(PROJECTS_FILE, 'r', encoding='utf-8') as f:
        projects = json.load(f)
    if user_id:
        return [p for p in projects if p.get('userId') == user_id]
    return projects

def save_project(project: Dict):
    """Сохранить проект"""
    projects = get_projects()
    # Ищем существующий
    found = False
    for i, p in enumerate(projects):
        if p.get('id') == project.get('id'):
            projects[i] = project
            found = True
            break
    
    if not found:
        projects.append(project)
    
    with open(PROJECTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(projects, f, ensure_ascii=False, indent=2)

def remove_project_photo(project_id: str, user_id: int):
    """Удалить фото из проекта"""
    projects = get_projects()
    for i, p in enumerate(projects):
        if p.get('id') == project_id and p.get('userId') == user_id:
            if 'imageFileId' in projects[i]:
                del projects[i]['imageFileId']
            with open(PROJECTS_FILE, 'w', encoding='utf-8') as f:
                json.dump(projects, f, ensure_ascii=False, indent=2)
            return True
    return False

def delete_all_user_data(user_id: int):
    """Удалить все данные пользователя (ID остается в списке для статистики)"""
    # Удаляем записи
    entries = get_entries()
    entries = [e for e in entries if e.get('userId') != user_id]
    with open(ENTRIES_FILE, 'w', encoding='utf-8') as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)
    
    # Удаляем проекты
    projects = get_projects()
    projects = [p for p in projects if p.get('userId') != user_id]
    with open(PROJECTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(projects, f, ensure_ascii=False, indent=2)
    
    # Удаляем вишлист
    wishlist = get_wishlist()
    wishlist = [w for w in wishlist if w.get('userId') != user_id]
    with open(WISHLIST_FILE, 'w', encoding='utf-8') as f:
        json.dump(wishlist, f, ensure_ascii=False, indent=2)
    
    # Удаляем заметки
    notes = get_notes()
    notes = [n for n in notes if n.get('userId') != user_id]
    with open(NOTES_FILE, 'w', encoding='utf-8') as f:
        json.dump(notes, f, ensure_ascii=False, indent=2)
    
    # Удаляем планы
    plans = get_plans()
    plans = [p for p in plans if p.get('userId') != user_id]
    with open(PLANS_FILE, 'w', encoding='utf-8') as f:
        json.dump(plans, f, ensure_ascii=False, indent=2)
    
    # Удаляем челленджи
    challenges = get_user_challenges()
    challenges = [c for c in challenges if c.get('userId') != user_id]
    with open(CHALLENGES_FILE, 'w', encoding='utf-8') as f:
        json.dump(challenges, f, ensure_ascii=False, indent=2)
    
    # Удаляем подписки
    subscriptions = []
    if os.path.exists(SUBSCRIPTIONS_FILE):
        with open(SUBSCRIPTIONS_FILE, 'r', encoding='utf-8') as f:
            subscriptions = json.load(f)
    subscriptions = [s for s in subscriptions if s.get('userId') != user_id]
    with open(SUBSCRIPTIONS_FILE, 'w', encoding='utf-8') as f:
        json.dump(subscriptions, f, ensure_ascii=False, indent=2)
    
    # НЕ удаляем ID из списка пользователей - для статистики и истории использования бота

def delete_entry_by_date(date: str, user_id: int):
    """Удалить запись за конкретную дату"""
    entries = get_entries()
    entries = [e for e in entries if not (e.get('date') == date and e.get('userId') == user_id)]
    with open(ENTRIES_FILE, 'w', encoding='utf-8') as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)

# === Вишлист ===
def get_wishlist(user_id: Optional[int] = None) -> List[Dict]:
    """Получить вишлист пользователя"""
    with open(WISHLIST_FILE, 'r', encoding='utf-8') as f:
        wishlist = json.load(f)
    if user_id:
        return [w for w in wishlist if w.get('userId') == user_id]
    return wishlist

def add_to_wishlist(item: Dict):
    """Добавить элемент в вишлист"""
    wishlist = get_wishlist()
    wishlist.append(item)
    with open(WISHLIST_FILE, 'w', encoding='utf-8') as f:
        json.dump(wishlist, f, ensure_ascii=False, indent=2)

def remove_from_wishlist(item_id: str, user_id: int):
    """Удалить элемент из вишлиста"""
    wishlist = get_wishlist()
    wishlist = [w for w in wishlist if not (w.get('id') == item_id and w.get('userId') == user_id)]
    with open(WISHLIST_FILE, 'w', encoding='utf-8') as f:
        json.dump(wishlist, f, ensure_ascii=False, indent=2)

def update_wishlist_item(item_id: str, user_id: int, updates: Dict):
    """Обновить элемент вишлиста"""
    wishlist = get_wishlist()
    for i, item in enumerate(wishlist):
        if item.get('id') == item_id and item.get('userId') == user_id:
            wishlist[i].update(updates)
            break
    with open(WISHLIST_FILE, 'w', encoding='utf-8') as f:
        json.dump(wishlist, f, ensure_ascii=False, indent=2)

# === Заметки ===
def get_notes(user_id: Optional[int] = None) -> List[Dict]:
    """Получить заметки пользователя"""
    with open(NOTES_FILE, 'r', encoding='utf-8') as f:
        notes = json.load(f)
    if user_id:
        return [n for n in notes if n.get('userId') == user_id]
    return notes

def save_note(note: Dict):
    """Сохранить заметку"""
    notes = get_notes()
    found = False
    for i, n in enumerate(notes):
        if n.get('id') == note.get('id'):
            notes[i] = note
            found = True
            break
    if not found:
        notes.append(note)
    with open(NOTES_FILE, 'w', encoding='utf-8') as f:
        json.dump(notes, f, ensure_ascii=False, indent=2)

def delete_note(note_id: str, user_id: int):
    """Удалить заметку"""
    notes = get_notes()
    notes = [n for n in notes if not (n.get('id') == note_id and n.get('userId') == user_id)]
    with open(NOTES_FILE, 'w', encoding='utf-8') as f:
        json.dump(notes, f, ensure_ascii=False, indent=2)

# === Планы ===
def get_plans(user_id: Optional[int] = None) -> List[Dict]:
    """Получить планы пользователя"""
    with open(PLANS_FILE, 'r', encoding='utf-8') as f:
        plans = json.load(f)
    if user_id:
        return [p for p in plans if p.get('userId') == user_id]
    return plans

def save_plan(plan: Dict):
    """Сохранить план"""
    plans = get_plans()
    found = False
    for i, p in enumerate(plans):
        if p.get('id') == plan.get('id'):
            plans[i] = plan
            found = True
            break
    if not found:
        plans.append(plan)
    with open(PLANS_FILE, 'w', encoding='utf-8') as f:
        json.dump(plans, f, ensure_ascii=False, indent=2)

def delete_plan(plan_id: str, user_id: int):
    """Удалить план"""
    plans = get_plans()
    plans = [p for p in plans if not (p.get('id') == plan_id and p.get('userId') == user_id)]
    with open(PLANS_FILE, 'w', encoding='utf-8') as f:
        json.dump(plans, f, ensure_ascii=False, indent=2)

# === Челленджи ===
def get_user_challenges(user_id: Optional[int] = None) -> List[Dict]:
    """Получить челленджи пользователя"""
    with open(CHALLENGES_FILE, 'r', encoding='utf-8') as f:
        challenges = json.load(f)
    if user_id:
        return [c for c in challenges if c.get('userId') == user_id]
    return challenges

def add_user_challenge(challenge: Dict):
    """Добавить челлендж пользователю"""
    challenges = get_user_challenges()
    challenges.append(challenge)
    with open(CHALLENGES_FILE, 'w', encoding='utf-8') as f:
        json.dump(challenges, f, ensure_ascii=False, indent=2)

def update_user_challenge(challenge_id: str, user_id: int, updates: Dict):
    """Обновить челлендж пользователя"""
    challenges = get_user_challenges()
    for i, challenge in enumerate(challenges):
        if challenge.get('challengeId') == challenge_id and challenge.get('userId') == user_id:
            challenges[i].update(updates)
            break
    with open(CHALLENGES_FILE, 'w', encoding='utf-8') as f:
        json.dump(challenges, f, ensure_ascii=False, indent=2)

def delete_user_challenge(challenge_id: str, user_id: int):
    """Удалить челлендж пользователя"""
    challenges = get_user_challenges()
    challenges = [c for c in challenges if not (c.get('challengeId') == challenge_id and c.get('userId') == user_id)]
    with open(CHALLENGES_FILE, 'w', encoding='utf-8') as f:
        json.dump(challenges, f, ensure_ascii=False, indent=2)

def get_user_challenge(challenge_id: str, user_id: int) -> Optional[Dict]:
    """Получить конкретный челлендж пользователя"""
    challenges = get_user_challenges(user_id)
    return next((c for c in challenges if c.get('challengeId') == challenge_id), None)

