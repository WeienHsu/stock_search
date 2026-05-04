def start_background_scheduler(*args, **kwargs):
    from src.scheduler.scheduler import start_background_scheduler as _start_background_scheduler

    return _start_background_scheduler(*args, **kwargs)

__all__ = ["start_background_scheduler"]
