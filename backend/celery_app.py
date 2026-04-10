from celery import Celery
from celery.schedules import crontab

celery_app = Celery(
    'trading_bot',
    broker='redis://localhost:6379/0',
    backend='redis://localhost:6379/0',
    include=['tasks']
)

# Optional: Configure beat for scheduled tasks
celery_app.conf.beat_schedule = {
    'run-daily-backtest': {
        'task': 'tasks.run_backtest',
        'schedule': crontab(hour=0, minute=0),  # Daily at midnight
        'args': ('BTCUSDT', 30),
    },
}

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
)