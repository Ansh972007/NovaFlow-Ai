"""S3-compatible object storage (AWS S3, Cloudflare R2, MinIO, GCS interop)."""

from __future__ import annotations

import hashlib
import logging
from typing import BinaryIO

from app.data.storage.base import ObjectStorageProvider, StoredObject

logger = logging.getLogger(__name__)


class S3CompatibleStorage(ObjectStorageProvider):
    name = "s3"

    def __init__(
        self,
        *,
        bucket: str,
        endpoint: str = "",
        access_key: str = "",
        secret_key: str = "",
        region: str = "auto",
        provider_label: str = "s3",
    ):
        self.bucket = bucket
        self.endpoint = endpoint
        self.access_key = access_key
        self.secret_key = secret_key
        self.region = region
        self.name = provider_label
        self._client = None

    def _client_or_raise(self):
        if self._client is not None:
            return self._client
        try:
            import boto3
            from botocore.client import Config
        except ImportError as exc:
            raise RuntimeError(
                "boto3 is required for S3/R2/MinIO storage. pip install boto3"
            ) from exc
        kwargs = {
            "service_name": "s3",
            "aws_access_key_id": self.access_key or None,
            "aws_secret_access_key": self.secret_key or None,
            "region_name": self.region or "auto",
            "config": Config(signature_version="s3v4"),
        }
        if self.endpoint:
            kwargs["endpoint_url"] = self.endpoint
        self._client = boto3.client(**kwargs)
        return self._client

    def put(
        self,
        key: str,
        data: bytes | BinaryIO,
        *,
        content_type: str = "application/octet-stream",
        workspace_id: int | None = None,
    ) -> StoredObject:
        if workspace_id is not None and not key.startswith("ws/"):
            key = self.tenant_key(workspace_id, key)
        raw = data.read() if hasattr(data, "read") else data
        assert isinstance(raw, (bytes, bytearray))
        checksum = hashlib.sha256(raw).hexdigest()
        client = self._client_or_raise()
        resp = client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=raw,
            ContentType=content_type,
            Metadata={"sha256": checksum},
        )
        return StoredObject(
            key=key,
            bucket=self.bucket,
            size=len(raw),
            checksum=checksum,
            content_type=content_type,
            version_id=str(resp.get("VersionId") or ""),
            provider=self.name,
        )

    def get(self, key: str) -> bytes:
        client = self._client_or_raise()
        obj = client.get_object(Bucket=self.bucket, Key=key)
        return obj["Body"].read()

    def delete(self, key: str) -> None:
        client = self._client_or_raise()
        client.delete_object(Bucket=self.bucket, Key=key)

    def exists(self, key: str) -> bool:
        client = self._client_or_raise()
        try:
            client.head_object(Bucket=self.bucket, Key=key)
            return True
        except Exception:
            return False

    def signed_url(self, key: str, *, expires_seconds: int = 3600, method: str = "GET") -> str:
        client = self._client_or_raise()
        op = "get_object" if method.upper() == "GET" else "put_object"
        return client.generate_presigned_url(
            op,
            Params={"Bucket": self.bucket, "Key": key},
            ExpiresIn=expires_seconds,
        )

    def list_objects(self, *, prefix: str = "", limit: int = 1000) -> list[StoredObject]:
        client = self._client_or_raise()
        out: list[StoredObject] = []
        token = None
        while len(out) < limit:
            kwargs = {"Bucket": self.bucket, "Prefix": prefix, "MaxKeys": min(1000, limit - len(out))}
            if token:
                kwargs["ContinuationToken"] = token
            resp = client.list_objects_v2(**kwargs)
            for item in resp.get("Contents") or []:
                out.append(
                    StoredObject(
                        key=item["Key"],
                        bucket=self.bucket,
                        size=int(item.get("Size") or 0),
                        checksum=str(item.get("ETag") or "").strip('"'),
                        content_type="",
                        provider=self.name,
                    )
                )
            if not resp.get("IsTruncated"):
                break
            token = resp.get("NextContinuationToken")
            if not token:
                break
        return out[:limit]
