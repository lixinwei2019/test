from io import BytesIO

from minio import Minio
from minio.error import MinioException
from minio.helpers import check_bucket_name
from starlette.concurrency import run_in_threadpool
from urllib3 import PoolManager, Timeout
from urllib3.exceptions import HTTPError

from ai_code_check.core.config import settings

MINIO_CONNECT_TIMEOUT_SECONDS = 5
MINIO_READ_TIMEOUT_SECONDS = 30


class ObjectStorageError(Exception):
    """对象上传失败。"""


class MinioStorage:
    """向配置的 MinIO 存储桶上传对象。"""

    def __init__(self) -> None:
        """读取对象存储配置并创建共享客户端。

        Raises:
            ValueError: 对象存储配置缺失或格式错误。
        """
        endpoint = settings.MINIO_ENDPOINT
        bucket = settings.MINIO_BUCKET
        access_key = settings.MINIO_ACCESS_KEY
        secret_key = settings.MINIO_SECRET_KEY
        if not endpoint or not bucket or not access_key or not secret_key:
            raise ValueError(
                "请配置 MINIO_ENDPOINT、MINIO_BUCKET、MINIO_ACCESS_KEY 和 MINIO_SECRET_KEY"
            )

        check_bucket_name(bucket, strict=True, s3_check=True)
        self._bucket = bucket
        self._client = Minio(
            endpoint,
            access_key=access_key.get_secret_value(),
            secret_key=secret_key.get_secret_value(),
            secure=settings.MINIO_SECURE,
            http_client=PoolManager(
                timeout=Timeout(
                    connect=MINIO_CONNECT_TIMEOUT_SECONDS,
                    read=MINIO_READ_TIMEOUT_SECONDS,
                ),
                retries=False,
            ),
        )

    async def upload(
        self, object_name: str, content: bytes, *, content_type: str
    ) -> str:
        """上传对象并返回其地址。

        Args:
            object_name: 对象在存储桶中的名称，可以包含路径前缀。
            content: 要原样上传的对象字节。
            content_type: 对象的媒体类型。

        Returns:
            上传完成后的 S3 对象地址。

        Raises:
            ObjectStorageError: MinIO 拒绝上传或网络请求失败。
        """
        # MinIO SDK 使用同步网络请求，通过线程池避免阻塞事件循环。
        try:
            await run_in_threadpool(
                self._client.put_object,
                self._bucket,
                object_name,
                BytesIO(content),
                len(content),
                content_type=content_type,
            )
        except (MinioException, HTTPError, OSError) as exc:
            raise ObjectStorageError(str(exc)) from exc

        return f"s3://{self._bucket}/{object_name}"
