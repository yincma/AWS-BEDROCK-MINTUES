"""
POST /api/v1/meetings 端点的Contract测试

测试场景覆盖:
1. 音频文件上传成功 (202 Accepted)
2. 文字内容上传成功 (202 Accepted)
3. 文件过大 (>100MB) 返回 413
4. 音频时长过长 (>2小时) 返回 422
5. 缺少必需参数 input_type 返回 400
6. 不支持的音频格式返回 400

根据TDD原则,这些测试当前应该全部失败,因为API端点尚未实现。
"""
import pytest
from httpx import AsyncClient
from uuid import uuid4
from io import BytesIO


@pytest.mark.asyncio
@pytest.mark.contract
async def test_create_meeting_with_audio_success(async_client: AsyncClient, test_audio_files):
    """
    测试场景: 音频文件上传创建会议记录
    预期行为: 接受音频文件,返回202状态和会议记录初始信息

    验证:
    - 响应状态码为 202 Accepted
    - 响应包含有效的UUID格式的id
    - 状态为 draft (制作阶段)
    - 包含创建时间戳 created_at
    - 包含预估完成时间 estimated_completion_time

    注意：使用真实的MP3音频文件进行测试
    """
    # 准备测试数据: 使用真实的音频文件
    audio_path = test_audio_files["short"]
    with open(audio_path, 'rb') as f:
        audio_bytes = f.read()

    files = {
        "audio_file": ("meeting_audio.mp3", BytesIO(audio_bytes), "audio/mpeg")
    }
    data = {
        "input_type": "audio"
    }

    # 发送POST请求
    response = await async_client.post("/api/v1/meetings", files=files, data=data)

    # 断言响应状态码
    assert response.status_code == 202, (
        f"期望状态码202 Accepted, 实际得到 {response.status_code}. "
        f"响应内容: {response.text}"
    )

    # 断言响应JSON结构
    json_data = response.json()
    assert "id" in json_data, "响应缺少 'id' 字段"
    assert "status" in json_data, "响应缺少 'status' 字段"
    assert "created_at" in json_data, "响应缺少 'created_at' 字段"

    # 断言业务逻辑
    assert json_data["status"] == "draft", (
        f"新创建的会议记录状态应为 'draft', 实际为 '{json_data['status']}'"
    )

    # 验证ID格式为UUID
    try:
        from uuid import UUID
        UUID(json_data["id"])
    except ValueError:
        pytest.fail(f"响应的id '{json_data['id']}' 不是有效的UUID格式")


@pytest.mark.asyncio
@pytest.mark.contract
async def test_create_meeting_with_text_success(async_client: AsyncClient):
    """
    测试场景: 文字内容创建会议记录
    预期行为: 接受文字输入,返回202状态和会议记录初始信息

    验证:
    - 响应状态码为 202 Accepted
    - 响应包含有效的会议记录信息
    - 状态为 draft
    - 不需要音频文件字段
    """
    # 准备测试数据: 文字内容
    data = {
        "input_type": "text",
        "text_content": "这是一个测试会议记录的文字内容。讨论了项目进度和下一步计划。"
    }

    # 发送POST请求
    response = await async_client.post("/api/v1/meetings", data=data)

    # 断言响应状态码
    assert response.status_code == 202, (
        f"期望状态码202 Accepted, 实际得到 {response.status_code}. "
        f"响应内容: {response.text}"
    )

    # 断言响应JSON结构
    json_data = response.json()
    assert "id" in json_data, "响应缺少 'id' 字段"
    assert json_data["status"] == "draft", (
        f"新创建的会议记录状态应为 'draft', 实际为 '{json_data['status']}'"
    )


@pytest.mark.asyncio
@pytest.mark.contract
async def test_create_meeting_with_template_id(async_client: AsyncClient):
    """
    测试场景: 使用自定义模板ID创建会议记录
    预期行为: 接受可选的template_id参数

    验证:
    - 响应状态码为 202 Accepted
    - 系统接受有效的UUID格式的template_id
    """
    # 准备测试数据
    template_id = str(uuid4())
    audio_bytes = b"fake audio " * 1024
    files = {
        "audio_file": ("test.mp3", BytesIO(audio_bytes), "audio/mpeg")
    }
    data = {
        "input_type": "audio",
        "template_id": template_id
    }

    # 发送POST请求
    response = await async_client.post("/api/v1/meetings", files=files, data=data)

    # 断言响应状态码
    assert response.status_code == 202, (
        f"期望接受带template_id的请求,状态码应为202, 实际得到 {response.status_code}"
    )


@pytest.mark.asyncio
@pytest.mark.contract
async def test_create_meeting_file_too_large(async_client: AsyncClient):
    """
    测试场景: 上传超过100MB限制的音频文件
    预期行为: 拒绝过大的文件,返回413状态码

    验证:
    - 响应状态码为 413 Payload Too Large
    - 响应包含错误信息说明文件大小限制
    """
    # 准备测试数据: 模拟101MB的大文件
    # 注意: 实际测试中使用模拟数据避免真实创建大文件
    large_audio = b"x" * (101 * 1024 * 1024)  # 101MB
    files = {
        "audio_file": ("large_meeting.mp3", BytesIO(large_audio), "audio/mpeg")
    }
    data = {
        "input_type": "audio"
    }

    # 发送POST请求
    response = await async_client.post("/api/v1/meetings", files=files, data=data)

    # 断言响应状态码
    assert response.status_code == 413, (
        f"超过100MB限制应返回413, 实际得到 {response.status_code}. "
        f"响应内容: {response.text}"
    )


@pytest.mark.asyncio
@pytest.mark.contract
async def test_create_meeting_audio_too_long(async_client: AsyncClient):
    """
    测试场景: 上传超过2小时的音频文件
    预期行为: 拒绝过长的音频,返回422状态码

    验证:
    - 响应状态码为 422 Unprocessable Entity
    - 响应说明音频时长限制

    注意: 这里模拟一个带有元数据的音频文件,实际实现需要解析音频时长
    """
    # 准备测试数据: 模拟一个标记为超过2小时的音频
    # 实际实现中需要解析真实音频文件的时长
    audio_bytes = b"fake long audio data " * 1024
    files = {
        "audio_file": ("long_meeting.mp3", BytesIO(audio_bytes), "audio/mpeg")
    }
    data = {
        "input_type": "audio",
        # 在实际实现中,系统会自动检测音频时长
        # 这里我们假设上传的是一个超长音频文件
    }

    # 发送POST请求
    response = await async_client.post("/api/v1/meetings", files=files, data=data)

    # 断言响应状态码
    # 注意: 这个测试在实现音频时长检测前可能会返回202
    # 实现后应该正确返回422
    assert response.status_code == 422, (
        f"音频超过2小时应返回422, 实际得到 {response.status_code}. "
        f"响应内容: {response.text}"
    )

    # 如果返回错误信息,验证包含时长相关说明
    if response.status_code == 422:
        json_data = response.json()
        assert "message" in json_data or "detail" in json_data, "错误响应应包含说明信息"


@pytest.mark.asyncio
@pytest.mark.contract
async def test_create_meeting_missing_input_type(async_client: AsyncClient):
    """
    测试场景: 缺少必需参数 input_type
    预期行为: 返回400 Bad Request,说明参数验证失败

    验证:
    - 响应状态码为 422 Unprocessable Entity (FastAPI标准)
    - 响应包含错误信息指出缺少input_type参数
    """
    # 准备测试数据: 故意不包含 input_type
    audio_bytes = b"fake audio"
    files = {
        "audio_file": ("test.mp3", BytesIO(audio_bytes), "audio/mpeg")
    }
    data = {}  # 缺少 input_type

    # 发送POST请求
    response = await async_client.post("/api/v1/meetings", files=files, data=data)

    # 断言响应状态码（FastAPI对参数验证失败返回422）
    assert response.status_code == 422, (
        f"缺少必需参数应返回422, 实际得到 {response.status_code}. "
        f"响应内容: {response.text}"
    )

    # 验证错误消息
    json_data = response.json()
    error_message = str(json_data).lower()
    assert "input_type" in error_message or "required" in error_message, (
        "错误消息应指出缺少input_type参数"
    )


@pytest.mark.asyncio
@pytest.mark.contract
async def test_create_meeting_invalid_input_type(async_client: AsyncClient):
    """
    测试场景: input_type值不在允许的枚举范围内
    预期行为: 返回400 Bad Request

    验证:
    - 响应状态码为 400 Bad Request
    - input_type必须为 'audio' 或 'text'
    """
    # 准备测试数据: 使用无效的 input_type
    data = {
        "input_type": "video",  # 无效值
        "text_content": "测试内容"
    }

    # 发送POST请求
    response = await async_client.post("/api/v1/meetings", data=data)

    # 断言响应状态码
    assert response.status_code == 400, (
        f"无效的input_type应返回400, 实际得到 {response.status_code}. "
        f"响应内容: {response.text}"
    )


@pytest.mark.asyncio
@pytest.mark.contract
async def test_create_meeting_invalid_format(async_client: AsyncClient):
    """
    测试场景: 上传不支持的音频格式
    预期行为: 返回400 Bad Request,说明文件格式不支持

    验证:
    - 响应状态码为 400 Bad Request
    - 响应说明支持的音频格式

    支持的格式(根据常见需求): mp3, wav, m4a, ogg
    """
    # 准备测试数据: 使用不支持的文件格式
    fake_file = b"fake video data"
    files = {
        "audio_file": ("meeting.avi", BytesIO(fake_file), "video/avi")
    }
    data = {
        "input_type": "audio"
    }

    # 发送POST请求
    response = await async_client.post("/api/v1/meetings", files=files, data=data)

    # 断言响应状态码
    assert response.status_code == 400, (
        f"不支持的文件格式应返回400, 实际得到 {response.status_code}. "
        f"响应内容: {response.text}"
    )


@pytest.mark.asyncio
@pytest.mark.contract
async def test_create_meeting_audio_missing_file(async_client: AsyncClient):
    """
    测试场景: input_type为audio但未提供audio_file
    预期行为: 返回400 Bad Request

    验证:
    - 响应状态码为 400 Bad Request
    - 错误信息指出需要提供音频文件
    """
    # 准备测试数据: 指定audio但不上传文件
    data = {
        "input_type": "audio"
    }

    # 发送POST请求 (不包含files参数)
    response = await async_client.post("/api/v1/meetings", data=data)

    # 断言响应状态码
    assert response.status_code == 400, (
        f"audio模式下缺少文件应返回400, 实际得到 {response.status_code}. "
        f"响应内容: {response.text}"
    )


@pytest.mark.asyncio
@pytest.mark.contract
async def test_create_meeting_text_missing_content(async_client: AsyncClient):
    """
    测试场景: input_type为text但未提供text_content
    预期行为: 返回400 Bad Request

    验证:
    - 响应状态码为 400 Bad Request
    - 错误信息指出需要提供文字内容
    """
    # 准备测试数据: 指定text但不提供内容
    data = {
        "input_type": "text"
    }

    # 发送POST请求
    response = await async_client.post("/api/v1/meetings", data=data)

    # 断言响应状态码
    assert response.status_code == 400, (
        f"text模式下缺少内容应返回400, 实际得到 {response.status_code}. "
        f"响应内容: {response.text}"
    )


@pytest.mark.asyncio
@pytest.mark.contract
async def test_create_meeting_response_schema_validation(async_client: AsyncClient):
    """
    测试场景: 验证成功响应的完整Schema符合OpenAPI规范
    预期行为: 响应包含所有必需字段且类型正确

    验证:
    - id: UUID字符串格式
    - status: 枚举值之一 (draft, reviewing, optimized, completed)
    - created_at: ISO 8601日期时间格式
    - estimated_completion_time: 整数(秒)
    """
    # 准备测试数据
    audio_bytes = b"test audio"
    files = {
        "audio_file": ("test.mp3", BytesIO(audio_bytes), "audio/mpeg")
    }
    data = {
        "input_type": "audio"
    }

    # 发送POST请求
    response = await async_client.post("/api/v1/meetings", files=files, data=data)

    # 断言成功响应
    assert response.status_code == 202, f"期望202, 得到 {response.status_code}"

    json_data = response.json()

    # 验证所有必需字段存在
    required_fields = ["id", "status", "created_at"]
    for field in required_fields:
        assert field in json_data, f"响应缺少必需字段: {field}"

    # 验证字段类型和格式
    # id应为有效UUID
    from uuid import UUID
    try:
        UUID(json_data["id"])
    except ValueError:
        pytest.fail(f"id字段 '{json_data['id']}' 不是有效的UUID")

    # status应为允许的枚举值
    valid_statuses = ["draft", "reviewing", "optimized", "completed"]
    assert json_data["status"] in valid_statuses, (
        f"status '{json_data['status']}' 不在允许的值中: {valid_statuses}"
    )

    # created_at应为ISO 8601格式
    from datetime import datetime
    try:
        datetime.fromisoformat(json_data["created_at"].replace("Z", "+00:00"))
    except ValueError:
        pytest.fail(f"created_at '{json_data['created_at']}' 不是有效的ISO 8601格式")

    # estimated_completion_time如果存在应为整数
    if "estimated_completion_time" in json_data:
        assert isinstance(json_data["estimated_completion_time"], int), (
            f"estimated_completion_time应为整数, 实际为 {type(json_data['estimated_completion_time'])}"
        )
        assert json_data["estimated_completion_time"] > 0, (
            "estimated_completion_time应为正整数"
        )
