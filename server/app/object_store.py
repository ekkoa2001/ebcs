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
