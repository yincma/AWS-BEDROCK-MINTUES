"""
Pytest配置和共享fixtures - 使用真实AWS资源
"""
import os
import pytest
import boto3
from httpx import AsyncClient, ASGITransport
from src.api.main import app


@pytest.fixture(scope="session")
def aws_credentials():
    """确保AWS凭证已配置（从环境变量或~/.aws/credentials）"""
    # 不再设置mock凭证，使用真实的AWS凭证
    # 确保环境变量或AWS配置文件已设置
    region = os.getenv("AWS_REGION", "us-east-1")
    os.environ["AWS_REGION"] = region
    yield


@pytest.fixture(scope="function")
def s3_client(aws_credentials):
    """真实的S3客户端"""
    region = os.getenv("AWS_REGION", "us-east-1")
    client = boto3.client("s3", region_name=region)
    return client


@pytest.fixture(scope="function")
def test_bucket(s3_client):
    """使用真实的S3测试桶"""
    # 使用环境变量中的测试bucket，如果没有则使用默认名称
    bucket_name = os.getenv("TEST_S3_BUCKET", "meeting-minutes-test-1759289564")

    # 检查bucket是否存在，不存在则创建
    try:
        s3_client.head_bucket(Bucket=bucket_name)
    except:
        # Bucket不存在，创建它
        try:
            region = os.getenv("AWS_REGION", "us-east-1")
            # us-east-1不需要LocationConstraint
            if region == "us-east-1":
                s3_client.create_bucket(Bucket=bucket_name)
            else:
                # 其他region必须指定LocationConstraint
                s3_client.create_bucket(
                    Bucket=bucket_name,
                    CreateBucketConfiguration={'LocationConstraint': region}
                )
        except Exception as e:
            pytest.skip(f"无法创建测试bucket {bucket_name}: {e}")

    yield bucket_name

    # 测试后清理：删除测试期间创建的对象（可选）
    # 注意：不删除bucket本身，因为可能被多个测试使用


@pytest.fixture
async def async_client(test_bucket, monkeypatch):
    """提供AsyncClient fixture用于API测试 - 使用真实AWS资源"""
    # 设置环境变量
    monkeypatch.setenv("S3_BUCKET_NAME", test_bucket)

    # 使用真实的Bedrock模型
    model_id = os.getenv("BEDROCK_MODEL_ID", "amazon.nova-pro-v1:0")
    monkeypatch.setenv("BEDROCK_MODEL_ID", model_id)

    # 不再mock音频duration，使用真实的音频文件解析

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
async def async_client_with_aws(test_bucket, s3_client, monkeypatch):
    """提供带真实AWS资源的AsyncClient"""
    monkeypatch.setenv("S3_BUCKET_NAME", test_bucket)

    model_id = os.getenv("BEDROCK_MODEL_ID", "amazon.nova-pro-v1:0")
    monkeypatch.setenv("BEDROCK_MODEL_ID", model_id)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client, test_bucket, s3_client


@pytest.fixture(scope="session")
def test_audio_files():
    """提供测试用的真实音频文件

    注意：使用真实AWS资源测试时，需要真实的音频文件。
    这个fixture会在tests/fixtures/目录下查找音频文件。
    如果不存在，会创建最小的有效MP3文件。
    """
    import tempfile

    fixtures_dir = os.path.join(os.path.dirname(__file__), "fixtures")
    os.makedirs(fixtures_dir, exist_ok=True)

    # 最小的有效MP3文件（约1秒的静音）
    # 这是一个有效的MP3帧头 + 数据
    minimal_mp3 = (
        b'\xff\xfb\x90\x00' +  # MP3帧头
        b'\x00' * 1000         # 填充数据
    )

    # 创建短音频文件
    short_path = os.path.join(fixtures_dir, "test_short.mp3")
    if not os.path.exists(short_path):
        with open(short_path, 'wb') as f:
            f.write(minimal_mp3)

    # 创建长音频文件（通过重复MP3数据模拟）
    long_path = os.path.join(fixtures_dir, "test_long.mp3")
    if not os.path.exists(long_path):
        with open(long_path, 'wb') as f:
            # 写入多次以增加文件大小
            for _ in range(100):
                f.write(minimal_mp3)

    yield {
        "short": short_path,
        "long": long_path,
        "fixtures_dir": fixtures_dir
    }

    # 注意：不清理fixtures目录，保留用于后续测试
