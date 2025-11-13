"""Предустановленные челленджи для пользователей"""
from datetime import datetime, timedelta
from typing import Dict, List
from data.storage import get_entries

# Доступные челленджи
AVAILABLE_CHALLENGES = {
    'weekly_1000': {
        'id': 'weekly_1000',
        'name': '⚡ 1000 за неделю',
        'description': 'Вышить 1000 крестиков за 7 дней',
        'type': 'count_period',
        'target': 1000,
        'period_days': 7,
        'emoji': '⚡'
    },
    'streak_30': {
        'id': 'streak_30',
        'name': '🔥 30 дней подряд',
        'description': 'Вышивать каждый день 30 дней подряд',
        'type': 'streak',
        'target': 30,
        'emoji': '🔥'
    },
    'streak_365': {
        'id': 'streak_365',
        'name': '🏆 365 дней подряд',
        'description': 'Вышивать каждый день целый год!',
        'type': 'streak',
        'target': 365,
        'emoji': '🏆'
    },
    'daily_300_7': {
        'id': 'daily_300_7',
        'name': '⭐ 7 дней по 300',
        'description': 'Вышивать минимум 300 крестиков каждый день в течение 7 дней',
        'type': 'daily_minimum',
        'target': 300,
        'period_days': 7,
        'emoji': '⭐'
    },
    'monthly_15000': {
        'id': 'monthly_15000',
        'name': '📅 15000 за месяц',
        'description': 'Вышить 15000 крестиков за месяц',
        'type': 'count_period',
        'target': 15000,
        'period_days': 30,
        'emoji': '📅'
    }
}

def get_available_challenges() -> List[Dict]:
    """Получить список всех доступных челленджей"""
    return list(AVAILABLE_CHALLENGES.values())

def get_challenge_by_id(challenge_id: str) -> Dict:
    """Получить челлендж по ID"""
    return AVAILABLE_CHALLENGES.get(challenge_id)

def calculate_streak(entries: List[Dict], start_date: datetime) -> int:
    """Вычислить текущую серию дней подряд"""
    if not entries:
        return 0
    
    # Получаем уникальные даты с записями (независимо от количества крестиков)
    dates_with_entries = set()
    for entry in entries:
        date_str = entry.get('date', '')
        if date_str:
            try:
                entry_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                if entry_date >= start_date.date():
                    dates_with_entries.add(entry_date)
            except:
                continue
    
    if not dates_with_entries:
        return 0
    
    # Проверяем серию с сегодняшнего дня назад
    today = datetime.now().date()
    streak = 0
    current_date = today
    
    # Начинаем проверку с сегодняшнего дня и идем назад
    while current_date >= start_date.date():
        if current_date in dates_with_entries:
            streak += 1
            current_date -= timedelta(days=1)
        else:
            # Если пропущен день, серия прерывается
            break
    
    return streak

def check_challenge_progress(user_id: int, challenge_id: str, user_challenge: Dict) -> Dict:
    """Проверить прогресс по челленджу"""
    challenge_data = get_challenge_by_id(challenge_id)
    if not challenge_data:
        return None
    
    entries = get_entries(user_id)
    start_date = datetime.strptime(user_challenge['startDate'], '%Y-%m-%d')
    today = datetime.now().date()
    
    if challenge_data['type'] == 'count_period':
        # Подсчет крестиков за период
        period_end = start_date + timedelta(days=challenge_data['period_days'])
        period_entries = []
        for entry in entries:
            try:
                entry_date = datetime.strptime(entry.get('date', ''), '%Y-%m-%d').date()
                if start_date.date() <= entry_date <= min(period_end.date(), today):
                    period_entries.append(entry)
            except:
                continue
        
        current = sum(e.get('count', 0) for e in period_entries)
        progress = (current / challenge_data['target']) * 100 if challenge_data['target'] > 0 else 0
        completed = current >= challenge_data['target']
        days_left = max(0, (period_end.date() - today).days)
        
        return {
            'current': current,
            'target': challenge_data['target'],
            'progress': min(progress, 100),
            'completed': completed,
            'days_left': days_left,
            'type': 'count'
        }
    
    elif challenge_data['type'] == 'streak':
        # Проверка серии дней
        current_streak = calculate_streak(entries, start_date)
        progress = (current_streak / challenge_data['target']) * 100 if challenge_data['target'] > 0 else 0
        completed = current_streak >= challenge_data['target']
        days_left = max(0, challenge_data['target'] - current_streak)
        
        return {
            'current': current_streak,
            'target': challenge_data['target'],
            'progress': min(progress, 100),
            'completed': completed,
            'days_left': days_left,
            'type': 'streak'
        }
    
    elif challenge_data['type'] == 'daily_minimum':
        # Проверка минимума каждый день
        period_end = start_date + timedelta(days=challenge_data['period_days'])
        days_completed = 0
        days_with_entries = {}
        
        for entry in entries:
            try:
                entry_date = datetime.strptime(entry.get('date', ''), '%Y-%m-%d').date()
                if start_date.date() <= entry_date <= min(period_end.date(), today):
                    if entry_date not in days_with_entries:
                        days_with_entries[entry_date] = 0
                    days_with_entries[entry_date] += entry.get('count', 0)
            except:
                continue
        
        # Проверяем каждый день периода
        current_date = start_date.date()
        while current_date <= min(period_end.date(), today):
            if current_date in days_with_entries and days_with_entries[current_date] >= challenge_data['target']:
                days_completed += 1
            current_date += timedelta(days=1)
        
        progress = (days_completed / challenge_data['period_days']) * 100
        completed = days_completed >= challenge_data['period_days']
        days_left = max(0, (period_end.date() - today).days)
        
        return {
            'current': days_completed,
            'target': challenge_data['period_days'],
            'progress': min(progress, 100),
            'completed': completed,
            'days_left': days_left,
            'type': 'daily_minimum',
            'daily_target': challenge_data['target']
        }
    
    return None

