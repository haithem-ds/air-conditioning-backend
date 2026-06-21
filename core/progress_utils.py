"""Shared helpers for task progress (0–100%, 10% steps)."""

PROGRESS_STEP = 10


def normalize_progress_percent(value) -> int:
    """Clamp to 0–100 and snap to 10% increments."""
    try:
        percent = int(float(value))
    except (TypeError, ValueError):
        raise ValueError('progress_percentage must be a number')
    percent = max(0, min(100, percent))
    return int(round(percent / PROGRESS_STEP) * PROGRESS_STEP)


def apply_progress_update(instance, *, progress_percentage=None, quantity_completed=None):
    """
    Update a Traveaux / MaintenanceTraveaux instance.
    Prefer progress_percentage (stored on progress_percent); quantity_completed is legacy fallback.
    """
    if progress_percentage is not None:
        percent = normalize_progress_percent(progress_percentage)
        instance.progress_percent = percent
        if instance.quantity > 0:
            instance.quantity_completed = min(
                instance.quantity,
                max(0, round(instance.quantity * percent / 100)),
            )
        else:
            instance.quantity_completed = 0
    elif quantity_completed is not None:
        try:
            qc = int(quantity_completed)
        except (TypeError, ValueError):
            raise ValueError('quantity_completed must be a number')
        if qc < 0 or qc > instance.quantity:
            raise ValueError(f'quantity_completed must be between 0 and {instance.quantity}')
        instance.quantity_completed = qc
        if instance.quantity > 0:
            instance.progress_percent = normalize_progress_percent(
                round(qc / instance.quantity * 100)
            )
        else:
            instance.progress_percent = 0
    else:
        raise ValueError('progress_percentage or quantity_completed is required')

    instance.update_status()
    return instance
