"""S3客户端封装"""
import json
from typing import Optional, Any, Dict, List
from botocore.exceptions import ClientError
import boto3


class S3ClientWrapper:
    """
    S3客户端封装类

    提供JSON对象的读写、列表和删除操作
    """

    # 常量定义，避免魔法字符串
    MEETINGS_PREFIX = "meetings/"
    TEMPLATES_PREFIX = "templates/"
    AUDIO_PREFIX = "audio/"

    def __init__(self, bucket_name: str, region: str = "us-east-1"):
        """
        初始化S3客户端

        Args:
            bucket_name: S3 bucket名称
            region: AWS区域
        """
        self.bucket_name = bucket_name
        self.s3 = boto3.client('s3', region_name=region)

    async def get_json(self, key: str) -> Optional[Dict[str, Any]]:
        """
        从S3读取JSON对象

        Args:
            key: S3对象键

        Returns:
            JSON对象或None(如果不存在)

        Raises:
            ClientError: S3操作失败(除了NoSuchKey)
        """
        try:
            response = self.s3.get_object(Bucket=self.bucket_name, Key=key)
            data = json.loads(response['Body'].read().decode('utf-8'))
            # 保存ETag用于后续的条件更新
            data['__etag'] = response.get('ETag', '').strip('"')
            return data
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                return None
            raise

    async def put_json(
        self,
        key: str,
        data: Dict[str, Any],
        if_match: Optional[str] = None
    ) -> str:
        """
        保存JSON对象到S3

        Args:
            key: S3对象键
            data: 要保存的数据
            if_match: ETag值，用于乐观锁控制

        Returns:
            新的ETag值

        Raises:
            ClientError: S3操作失败
        """
        # 移除内部使用的__etag字段
        data_copy = data.copy()
        data_copy.pop('__etag', None)

        body = json.dumps(data_copy, ensure_ascii=False, indent=2)
        params = {
            'Bucket': self.bucket_name,
            'Key': key,
            'Body': body,
            'ContentType': 'application/json'
        }

        # 添加条件更新参数
        if if_match:
            params['IfMatch'] = if_match

        try:
            response = self.s3.put_object(**params)
            return response.get('ETag', '').strip('"')
        except ClientError as e:
            if e.response['Error']['Code'] == 'PreconditionFailed':
                raise ValueError("并发冲突：对象已被其他进程修改，请重试")
            raise

    async def list_keys(self, prefix: str) -> List[str]:
        """
        列出指定前缀的所有keys

        Args:
            prefix: 对象键前缀

        Returns:
            键名列表
        """
        keys = []

        # 使用分页处理大量对象
        paginator = self.s3.get_paginator('list_objects_v2')
        page_iterator = paginator.paginate(
            Bucket=self.bucket_name,
            Prefix=prefix
        )

        for page in page_iterator:
            if 'Contents' in page:
                keys.extend([obj['Key'] for obj in page['Contents']])

        return keys

    async def delete(self, key: str) -> None:
        """
        删除对象

        Args:
            key: S3对象键

        Raises:
            ClientError: S3操作失败
        """
        try:
            self.s3.delete_object(Bucket=self.bucket_name, Key=key)
        except ClientError as e:
            # 如果对象不存在，静默成功
            if e.response['Error']['Code'] != 'NoSuchKey':
                raise

    async def exists(self, key: str) -> bool:
        """
        检查对象是否存在

        Args:
            key: S3对象键

        Returns:
            True如果存在，False否则
        """
        try:
            self.s3.head_object(Bucket=self.bucket_name, Key=key)
            return True
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code in ['NoSuchKey', '404']:
                return False
            raise

    async def get_object_metadata(self, key: str) -> Optional[Dict[str, Any]]:
        """
        获取对象元数据

        Args:
            key: S3对象键

        Returns:
            元数据字典或None
        """
        try:
            response = self.s3.head_object(Bucket=self.bucket_name, Key=key)
            return {
                'ContentLength': response['ContentLength'],
                'ContentType': response['ContentType'],
                'ETag': response['ETag'].strip('"'),
                'LastModified': response['LastModified'].isoformat(),
                'Metadata': response.get('Metadata', {})
            }
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                return None
            raise