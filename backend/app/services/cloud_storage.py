"""Private Vercel Blob persistence for public provider snapshots only."""
import os


def enabled():
    return bool(os.getenv('BLOB_READ_WRITE_TOKEN'))


def read(name: str) -> bytes | None:
    from vercel.blob import get, BlobNotFoundError
    try:
        result = get(f'fantasy/{name}', access='private', use_cache=False, timeout=20)
        return result.content if result else None
    except BlobNotFoundError:
        return None
    except Exception as exc:
        raise OSError('Cloud snapshot read failed') from exc


def write(name: str, content: bytes):
    from vercel.blob import put
    try:
        put(f'fantasy/{name}', content, access='private', content_type='application/json',
            overwrite=True, add_random_suffix=False, cache_control_max_age=60)
    except Exception as exc:
        raise OSError('Cloud snapshot write failed') from exc
