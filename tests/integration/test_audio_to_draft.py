"""
集成测试: 音频上传到初稿生成完整流程

测试场景1: 上传音频文件生成会议记录
按照 /specs/001-ai/quickstart.md 的完整业务流程测试
"""
import json
import time
import pytest
from pathlib import Path


@pytest.mark.asyncio
@pytest.mark.integration
async def test_audio_upload_to_draft_complete_flow(async_client_with_aws):
    """
    完整流程测试: 音频上传 → 转录 → AI生成 → 保存到S3

    业务流程:
    1. 用户上传MP3音频文件
    2. 系统保存音频到S3
    3. AWS Transcribe异步转录音频
    4. AWS Bedrock Nova Pro提取会议信息
    5. 系统保存draft阶段会议记录到S3
    6. 返回Markdown格式的会议记录

    状态转换:
    - 初始: pending
    - 转录中: transcribing
    - 生成中: generating
    - 完成: draft

    预期失败原因: API路由和服务尚未实现
    """
    client, test_bucket, s3_client = async_client_with_aws

    # 步骤1: 准备测试音频文件
    test_audio_path = Path(__file__).parent.parent / "fixtures" / "sample_meeting.mp3"

    # 如果fixture不存在,创建一个小的测试文件
    if not test_audio_path.exists():
        test_audio_path.parent.mkdir(parents=True, exist_ok=True)
        # 创建一个最小的MP3文件头 (用于测试)
        test_audio_path.write_bytes(b"ID3\x04\x00\x00\x00\x00\x00\x00")

    # 步骤2: 上传音频文件到API
    with open(test_audio_path, "rb") as audio_file:
        response = await client.post(
            "/api/v1/meetings",
            files={"audio_file": ("sample_meeting.mp3", audio_file, "audio/mpeg")},
            data={"input_type": "audio"}
        )

    # 验证: 初始响应
    assert response.status_code == 200, f"上传失败: {response.text}"
    meeting_data = response.json()

    assert "id" in meeting_data, "响应中缺少meeting ID"
    assert "status" in meeting_data, "响应中缺少status字段"
    assert meeting_data["status"] == "pending", f"初始状态应为pending,实际为 {meeting_data['status']}"
    assert "created_at" in meeting_data, "响应中缺少created_at字段"

    meeting_id = meeting_data["id"]

    # 步骤3: 验证音频已上传到S3
    audio_key = f"meetings/{meeting_id}/audio/original.mp3"
    try:
        s3_response = s3_client.head_object(Bucket=test_bucket, Key=audio_key)
        assert s3_response["ResponseMetadata"]["HTTPStatusCode"] == 200
    except Exception as e:
        pytest.fail(f"音频文件未上传到S3: {e}")

    # 步骤4: 轮询等待处理完成 (最多等待30秒)
    max_retries = 30
    current_status = "pending"

    for i in range(max_retries):
        response = await client.get(f"/api/v1/meetings/{meeting_id}")
        assert response.status_code == 200, f"查询会议状态失败: {response.text}"

        meeting_status = response.json()
        current_status = meeting_status["status"]

        # 验证状态转换顺序
        if current_status == "draft":
            break
        elif current_status in ["transcribing", "generating"]:
            # 正常的中间状态
            pass
        elif current_status == "error":
            pytest.fail(f"处理失败: {meeting_status.get('error_message', '未知错误')}")
        elif current_status == "pending":
            # 仍在等待
            pass
        else:
            pytest.fail(f"未知状态: {current_status}")

        time.sleep(1)

    assert current_status == "draft", \
        f"处理超时或状态错误,当前状态: {current_status},预期: draft"

    # 步骤5: 验证draft阶段的会议记录已保存到S3
    meeting_json_key = f"meetings/{meeting_id}/meeting.json"

    try:
        s3_response = s3_client.get_object(Bucket=test_bucket, Key=meeting_json_key)
        meeting_json = json.loads(s3_response["Body"].read().decode("utf-8"))
    except Exception as e:
        pytest.fail(f"会议记录JSON未保存到S3: {e}")

    # 验证: meeting.json结构
    assert "stages" in meeting_json, "meeting.json缺少stages字段"

    draft_stage = None
    for stage in meeting_json["stages"]:
        if stage["stage_name"] == "draft":
            draft_stage = stage
            break

    assert draft_stage is not None, "未找到draft阶段数据"
    assert "content" in draft_stage, "draft阶段缺少content字段"
    assert draft_stage["content"] is not None, "draft内容为空"

    # 步骤6: 验证draft内容是Markdown格式
    draft_content = draft_stage["content"]

    # 必需的Markdown section
    required_sections = [
        "# 会议记录",
        "## 会议基本信息",
        "## 讨论议题",
        "## 决策事项",
        "## 行动项"
    ]

    for section in required_sections:
        assert section in draft_content, \
            f"draft内容缺少必需section: {section}"

    # 验证必需字段
    assert "会议主题" in draft_content, "缺少会议主题"
    assert "会议日期" in draft_content, "缺少会议日期"
    assert "参与者" in draft_content, "缺少参与者"

    # 步骤7: 验证API返回的最终响应
    final_response = await client.get(f"/api/v1/meetings/{meeting_id}")
    assert final_response.status_code == 200

    final_data = final_response.json()
    assert final_data["status"] == "draft"
    assert "stages" in final_data

    # 验证可以导出draft
    export_response = await client.get(
        f"/api/v1/meetings/{meeting_id}/export",
        params={"stage": "draft"}
    )
    assert export_response.status_code == 200
    assert export_response.headers["content-type"] == "text/markdown; charset=utf-8"

    exported_markdown = export_response.text
    assert "# 会议记录" in exported_markdown


@pytest.mark.asyncio
@pytest.mark.integration
async def test_audio_upload_with_invalid_format(async_client_with_aws):
    """
    测试: 上传非音频文件应返回错误

    预期失败原因: 参数验证逻辑尚未实现
    """
    client, test_bucket, s3_client = async_client_with_aws

    # 上传一个文本文件假冒音频
    response = await client.post(
        "/api/v1/meetings",
        files={"audio_file": ("test.txt", b"not an audio file", "text/plain")},
        data={"input_type": "audio"}
    )

    # 应该返回400错误
    assert response.status_code == 400, \
        f"应拒绝非音频文件,实际状态码: {response.status_code}"

    error_data = response.json()
    assert "detail" in error_data or "error" in error_data, \
        "错误响应应包含错误信息"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_audio_upload_missing_file(async_client_with_aws):
    """
    测试: 未提供音频文件应返回错误

    预期失败原因: 参数验证逻辑尚未实现
    """
    client, test_bucket, s3_client = async_client_with_aws

    # 不提供audio_file
    response = await client.post(
        "/api/v1/meetings",
        data={"input_type": "audio"}
    )

    # 应该返回422错误
    assert response.status_code == 422, \
        f"应要求提供音频文件,实际状态码: {response.status_code}"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_meeting_status_transitions(async_client_with_aws):
    """
    测试: 验证会议处理的状态转换顺序

    状态流转:
    pending → transcribing → generating → draft

    预期失败原因: 状态管理逻辑尚未实现
    """
    client, test_bucket, s3_client = async_client_with_aws

    # 创建测试音频
    test_audio_path = Path(__file__).parent.parent / "fixtures" / "sample_meeting.mp3"
    if not test_audio_path.exists():
        test_audio_path.parent.mkdir(parents=True, exist_ok=True)
        test_audio_path.write_bytes(b"ID3\x04\x00\x00\x00\x00\x00\x00")

    with open(test_audio_path, "rb") as audio_file:
        response = await client.post(
            "/api/v1/meetings",
            files={"audio_file": ("sample.mp3", audio_file, "audio/mpeg")},
            data={"input_type": "audio"}
        )

    assert response.status_code == 200
    meeting_id = response.json()["id"]

    # 记录状态转换历史
    status_history = []
    max_retries = 30

    for i in range(max_retries):
        response = await client.get(f"/api/v1/meetings/{meeting_id}")
        assert response.status_code == 200

        current_status = response.json()["status"]

        # 记录新状态
        if not status_history or status_history[-1] != current_status:
            status_history.append(current_status)

        if current_status in ["draft", "error"]:
            break

        time.sleep(1)

    # 验证状态转换序列
    assert len(status_history) > 1, "应该有多个状态转换"
    assert status_history[0] == "pending", "初始状态应为pending"
    assert status_history[-1] == "draft", f"最终状态应为draft,实际: {status_history[-1]}"

    # 验证不会出现状态回退
    valid_transitions = {
        "pending": ["transcribing", "generating", "draft"],
        "transcribing": ["generating", "draft"],
        "generating": ["draft"]
    }

    for i in range(len(status_history) - 1):
        current = status_history[i]
        next_status = status_history[i + 1]

        if current in valid_transitions:
            assert next_status in valid_transitions[current], \
                f"无效的状态转换: {current} → {next_status}"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_transcription_result_stored(async_client_with_aws):
    """
    测试: 验证转录结果保存到S3

    预期失败原因: Transcribe集成尚未实现
    """
    client, test_bucket, s3_client = async_client_with_aws

    test_audio_path = Path(__file__).parent.parent / "fixtures" / "sample_meeting.mp3"
    if not test_audio_path.exists():
        test_audio_path.parent.mkdir(parents=True, exist_ok=True)
        test_audio_path.write_bytes(b"ID3\x04\x00\x00\x00\x00\x00\x00")

    with open(test_audio_path, "rb") as audio_file:
        response = await client.post(
            "/api/v1/meetings",
            files={"audio_file": ("sample.mp3", audio_file, "audio/mpeg")},
            data={"input_type": "audio"}
        )

    meeting_id = response.json()["id"]

    # 等待处理完成
    max_retries = 30
    for i in range(max_retries):
        response = await client.get(f"/api/v1/meetings/{meeting_id}")
        if response.json()["status"] == "draft":
            break
        time.sleep(1)

    # 验证转录文本已保存
    transcription_key = f"meetings/{meeting_id}/transcription.txt"

    try:
        s3_response = s3_client.get_object(Bucket=test_bucket, Key=transcription_key)
        transcription_text = s3_response["Body"].read().decode("utf-8")

        assert len(transcription_text) > 0, "转录文本不应为空"
        assert isinstance(transcription_text, str), "转录文本应为字符串"
    except Exception as e:
        pytest.fail(f"转录文本未保存到S3: {e}")
