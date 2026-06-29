"""S3 access with ETag-based conflict prevention.

A minimal ``DummyS3`` in-memory abstraction is provided for testing. It stores
raw strings with auto-incrementing ETags and honours ``IfMatch`` conditional
writes.
"""

import hashlib
import time


class ETagConflictError(Exception):
    """Raised when the stored ETag does not match the expected value."""


CONFLICT_MESSAGE = (
    "Board was modified since you last read it. "
    "Call `list_items` to refresh, then retry your operation."
)

# Keys preserved between read and write cycles so S3 object metadata
# (ContentType, custom Metadata, etc.) is never lost.
_PRESERVED_KEYS = frozenset({
    "ContentType",
    "ContentLanguage",
    "ContentDisposition",
    "ContentEncoding",
    "CacheControl",
    "Metadata",
})


class DummyS3:
    """In-memory S3 stand-in for tests.

    Stores raw strings keyed by ``(bucket, key)`` with auto-incrementing ETags.
    """

    def __init__(self) -> None:
        self._store: dict[tuple[str, str], tuple[str, str]] = {}
        self._counter = 0

    def _new_etag(self) -> str:
        self._counter += 1
        return f'"etag-{self._counter}"'

    def dummyS3_set_content(self, Bucket: str, Key: str, Body: str) -> str:
        etag = self._new_etag()
        self._store[(Bucket, Key)] = (Body, etag)
        return etag

    def get_object(self, Bucket: str, Key: str) -> dict:
        if (Bucket, Key) not in self._store:
            raise KeyError(f"Object not found: {Bucket}/{Key}")
        body, etag = self._store[(Bucket, Key)]
        return {"Body": body, "ETag": etag}

    def put_object(
        self, Bucket: str, Key: str, Body: str, IfMatch: str | None = None, **kwargs
    ) -> dict:
        existing = self._store.get((Bucket, Key))
        if IfMatch is not None:
            if existing is None or existing[1] != IfMatch:
                raise ETagConflictError(CONFLICT_MESSAGE)
        etag = self._new_etag()
        self._store[(Bucket, Key)] = (Body, etag)
        return {"ETag": etag}


class S3Client:
    """Thin wrapper over a boto3 S3 client with conditional-write support.

    Caches S3 object metadata from ``get_object`` and re-applies it on
    ``put_object`` so that per-object attributes (ContentType, custom
    Metadata dict, …) are preserved through the fetch-modify-write cycle
    without callers needing to thread them explicitly.
    """

    def __init__(self, client) -> None:
        self._client = client
        self._meta_cache: dict[tuple[str, str], dict] = {}

    def get_object(self, Bucket: str, Key: str) -> dict:
        resp = self._client.get_object(Bucket=Bucket, Key=Key)
        body = resp["Body"].read().decode("utf-8")
        # Cache metadata for the next put_object call.
        meta: dict = {}
        for k in _PRESERVED_KEYS:
            if k in resp:
                meta[k] = resp[k]
        self._meta_cache[(Bucket, Key)] = meta
        return {"Body": body, "ETag": resp["ETag"]}

    def put_object(
        self, Bucket: str, Key: str, Body: str, IfMatch: str | None = None,
    ) -> dict:
        kwargs: dict = {"Bucket": Bucket, "Key": Key, "Body": Body.encode("utf-8")}
        if IfMatch is not None:
            kwargs["IfMatch"] = IfMatch
        # Re-apply cached metadata, auto-refreshing obsidian fields.
        meta = self._meta_cache.pop((Bucket, Key), {})
        for k, v in meta.items():
            if k == "Metadata":
                m = dict(v)
                m["obsidian-device-id"] = "device-4c5060b72cb62539"
                m["obsidian-mtime"] = str(int(time.time() * 1000))
                m["obsidian-fingerprint"] = (
                    "sha256:" + hashlib.sha256(Body.encode()).hexdigest()
                )
                kwargs[k] = m
            else:
                kwargs[k] = v
        try:
            resp = self._client.put_object(**kwargs)
        except Exception as e:
            code = ""
            if hasattr(e, "response"):
                code = e.response.get("Error", {}).get("Code", "")
            if code in ("PreconditionFailed", "412"):
                raise ETagConflictError(CONFLICT_MESSAGE)
            raise
        return {"ETag": resp.get("ETag", "")}


def get_s3_client() -> S3Client:
    import boto3

    return S3Client(boto3.client("s3"))
