"""会议记录仓库"""
from typing import Optional, List
from datetime import datetime
from src.models.meeting import MeetingMinute, ProcessingStage, ReviewStage
from src.storage.s3_client import S3ClientWrapper


class MeetingRepository:
    """
    会议记录仓库类

    负责会议记录的持久化和检索
    """

    def __init__(self, s3_client: S3ClientWrapper):
        """
        初始化会议记录仓库

        Args:
            s3_client: S3客户端实例
        """
        self.s3 = s3_client

    async def get(self, meeting_id: str) -> Optional[MeetingMinute]:
        """
        获取会议记录

        Args:
            meeting_id: 会议记录ID

        Returns:
            MeetingMinute实例或None
        """
        key = f"{S3ClientWrapper.MEETINGS_PREFIX}{meeting_id}.json"
        data = await self.s3.get_json(key)

        if data is None:
            return None

        try:
            # 保存ETag用于后续更新
            etag = data.pop('__etag', None)
            meeting = MeetingMinute(**data)

            # 将ETag附加到实例上（用于并发控制）
            meeting.__dict__['__etag'] = etag
            return meeting
        except Exception as e:
            raise ValueError(f"解析会议记录失败: {str(e)}")

    async def save(self, meeting: MeetingMinute, if_match: Optional[str] = None) -> str:
        """
        保存会议记录

        Args:
            meeting: 会议记录实例
            if_match: ETag值，用于乐观锁控制

        Returns:
            新的ETag值
        """
        key = f"{S3ClientWrapper.MEETINGS_PREFIX}{meeting.id}.json"

        # 使用模型的model_dump方法获取数据
        data = meeting.model_dump(mode='json')

        # 如果meeting对象有__etag属性，使用它作为if_match
        if if_match is None and hasattr(meeting, '__etag'):
            if_match = getattr(meeting, '__etag', None)

        # 保存到S3
        etag = await self.s3.put_json(key, data, if_match)

        # 更新实例的ETag
        meeting.__dict__['__etag'] = etag
        return etag

    async def list_all(self) -> List[MeetingMinute]:
        """
        列出所有会议记录

        Returns:
            会议记录列表
        """
        keys = await self.s3.list_keys(S3ClientWrapper.MEETINGS_PREFIX)
        meetings = []

        for key in keys:
            # 跳过非JSON文件
            if not key.endswith('.json'):
                continue

            data = await self.s3.get_json(key)
            if data:
                try:
                    # 移除内部字段
                    data.pop('__etag', None)
                    meeting = MeetingMinute(**data)
                    meetings.append(meeting)
                except Exception as e:
                    # 记录错误但继续处理其他文件
                    print(f"警告: 无法解析文件 {key}: {str(e)}")
                    continue

        # 按创建时间降序排序
        meetings.sort(key=lambda m: m.created_at, reverse=True)
        return meetings

    async def list_by_status(self, status: str) -> List[MeetingMinute]:
        """
        按状态筛选会议记录

        Args:
            status: 会议状态

        Returns:
            符合条件的会议记录列表
        """
        all_meetings = await self.list_all()
        return [m for m in all_meetings if m.status == status]

    async def update_stage(
        self,
        meeting_id: str,
        stage_name: str,
        stage_data: ProcessingStage | ReviewStage
    ) -> None:
        """
        更新特定阶段的数据

        Args:
            meeting_id: 会议记录ID
            stage_name: 阶段名称 (draft/review/final)
            stage_data: 阶段数据

        Raises:
            ValueError: 会议记录不存在
        """
        # 获取现有会议记录
        meeting = await self.get(meeting_id)
        if not meeting:
            raise ValueError(f"会议记录 {meeting_id} 不存在")

        # 更新阶段数据
        meeting.update_stage(stage_name, stage_data)

        # 保存更新（使用乐观锁）
        await self.save(meeting)

    async def delete(self, meeting_id: str) -> None:
        """
        删除会议记录

        Args:
            meeting_id: 会议记录ID
        """
        # 删除会议记录JSON
        meeting_key = f"{S3ClientWrapper.MEETINGS_PREFIX}{meeting_id}.json"
        await self.s3.delete(meeting_key)

        # 可选：同时删除关联的音频文件
        audio_key = f"{S3ClientWrapper.AUDIO_PREFIX}{meeting_id}"
        # 尝试删除各种音频格式
        for ext in ['.mp3', '.wav', '.mp4', '.m4a']:
            await self.s3.delete(f"{audio_key}{ext}")

    async def exists(self, meeting_id: str) -> bool:
        """
        检查会议记录是否存在

        Args:
            meeting_id: 会议记录ID

        Returns:
            True如果存在，False否则
        """
        key = f"{S3ClientWrapper.MEETINGS_PREFIX}{meeting_id}.json"
        return await self.s3.exists(key)

    async def get_recent(self, limit: int = 10) -> List[MeetingMinute]:
        """
        获取最近的会议记录

        Args:
            limit: 返回数量限制

        Returns:
            最近的会议记录列表
        """
        all_meetings = await self.list_all()
        return all_meetings[:limit]

    async def search_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> List[MeetingMinute]:
        """
        按日期范围搜索会议记录

        Args:
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            符合日期范围的会议记录列表
        """
        all_meetings = await self.list_all()
        return [
            m for m in all_meetings
            if start_date <= m.created_at <= end_date
        ]