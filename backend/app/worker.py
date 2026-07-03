from app.config.settings import get_settings


def main() -> None:
    """Validate worker importability until a Celery app is introduced in a later task."""
    settings = get_settings()
    print(f"{settings.app_name} worker is disabled for the foundation stage.", flush=True)


if __name__ == "__main__":
    main()
