import os

def _settings():
    bucket = os.environ.get("S3_BUCKET", "").strip()
    if not bucket:
        return None
    return bucket


def client():
    if not _settings():
        return None
    import boto3
    from botocore.config import Config
    return boto3.client(
        "s3",
        endpoint_url=os.environ.get("S3_ENDPOINT") or None,
        aws_access_key_id=os.environ.get("S3_ACCESS_KEY", ""),
        aws_secret_access_key=os.environ.get("S3_SECRET_KEY", ""),
        region_name=os.environ.get("S3_REGION", "us-east-1"),
        config=Config(s3={"addressing_style": "path"}),
    )


def ensure_bucket():
    store = client()
    bucket = _settings()
    if not store:
        return
    names = [item["Name"] for item in store.list_buckets().get("Buckets", [])]
    if bucket not in names:
        store.create_bucket(Bucket=bucket)


def put_object(key, mime, raw):
    store = client()
    bucket = _settings()
    if not store:
        return
    store.put_object(Bucket=bucket, Key=key, Body=raw, ContentType=mime or "application/octet-stream")


def presign_put(key, mime, expires=300):
    store = client()
    bucket = _settings()
    if not store or not bucket:
        return None
    return store.generate_presigned_url(
        "put_object",
        Params={"Bucket": bucket, "Key": key, "ContentType": mime or "application/octet-stream"},
        ExpiresIn=expires,
    )


def get_object(key):
    store = client()
    bucket = _settings()
    if not store:
        return None
    try:
        return store.get_object(Bucket=bucket, Key=key)["Body"].read()
    except Exception as error:
        if getattr(error, "response", {}).get("Error", {}).get("Code") in {"NoSuchKey", "404"}:
            return None
        raise


def delete_object(key):
    store = client(); bucket = _settings()
    if store and key: store.delete_object(Bucket=bucket, Key=key)


def list_objects(prefix=""):
    store = client(); bucket = _settings()
    if not store: return []
    items=[]; token=None
    while True:
        params={"Bucket":bucket,"Prefix":prefix}
        if token: params["ContinuationToken"]=token
        result=store.list_objects_v2(**params); items.extend(x["Key"] for x in result.get("Contents",[]))
        if not result.get("IsTruncated"): break
        token=result.get("NextContinuationToken")
    return items


def repair_legacy_media_paths():
    """Point migrated media metadata at the object keys copied from V1 blobs."""
    if not client():
        return {"checked": 0, "repaired": 0}
    from sqlalchemy import text
    from app.database import SessionLocal
    stored = set(list_objects())
    repaired = checked = 0
    with SessionLocal() as db:
        rows = db.execute(text("SELECT id,original_path,preview_path,thumbnail_path FROM media_files")).all()
        for row in rows:
            checked += 1
            # The initial SQLite migration copied each legacy blob under its media id.
            if row.id not in stored:
                continue
            invalid = not row.original_path or ":/" in row.original_path or row.original_path.startswith("/")
            if invalid:
                db.execute(text("UPDATE media_files SET original_path=:key,preview_path=:key,thumbnail_path=:key WHERE id=:id"), {"key": row.id, "id": row.id})
                repaired += 1
        db.commit()
    return {"checked": checked, "repaired": repaired}
