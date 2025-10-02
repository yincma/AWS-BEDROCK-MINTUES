"""
AWS Bedrock Nova Pro AI Service
使用Nova Pro模型处理会议记录的核心AI引擎
"""

import json
import logging
from typing import Optional, Dict, Any
import boto3
from botocore.exceptions import ClientError

from ..models.template import Template
from ..models.meeting import UserFeedback
from .prompt_loader import PromptLoader

logger = logging.getLogger(__name__)


class AIService:
    """AI服务类 - 使用AWS Bedrock Nova Pro模型"""

    def __init__(
        self,
        model_id: str = "amazon.nova-pro-v1:0",
        region: str = "us-east-1",
        temperature: float = 0.3,
        max_tokens: int = 4000
    ):
        """
        初始化AI服务

        Args:
            model_id: Bedrock模型ID
            region: AWS区域
            temperature: 生成温度(0.3保证一致性)
            max_tokens: 最大token数
        """
        self.model_id = model_id
        self.temperature = temperature
        self.max_tokens = max_tokens

        # 初始化Bedrock客户端
        try:
            self.bedrock = boto3.client('bedrock-runtime', region_name=region)
            logger.info(f"Bedrock client initialized with model: {model_id}")
        except Exception as e:
            logger.error(f"Failed to initialize Bedrock client: {e}")
            raise

        # 初始化prompt加载器
        self.prompt_loader = PromptLoader()

    def detect_language(self, text: str) -> str:
        """
        检测文本语言

        使用简单规则：统计中文字符占比
        - 中文字符占比 > 30% → 中文
        - 否则 → 英文

        Args:
            text: 待检测的文本

        Returns:
            str: "Chinese (Simplified)" 或 "English"
        """
        if not text or not text.strip():
            return "English"

        # 统计中文字符数量（Unicode范围：\u4e00-\u9fff）
        chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')

        # 计算总字符数（忽略空格和换行）
        total_chars = len(text.replace(' ', '').replace('\n', '').replace('\t', ''))

        if total_chars == 0:
            return "English"

        # 计算中文字符占比
        chinese_ratio = chinese_chars / total_chars

        # 阈值设为 30%
        detected_lang = "Chinese (Simplified)" if chinese_ratio > 0.3 else "English"

        logger.debug(
            f"Language detection: {detected_lang} "
            f"(Chinese chars: {chinese_chars}/{total_chars} = {chinese_ratio:.2%})"
        )

        return detected_lang

    async def extract_meeting_info(
        self,
        transcript: str,
        template: Template
    ) -> Dict[str, Any]:
        """
        使用Nova Pro从转录文本提取会议信息,按模板格式化

        Args:
            transcript: 会议转录文本
            template: 模板对象(定义输出结构)

        Returns:
            dict: 包含formatted_markdown和metadata
                - formatted_markdown: Markdown格式的会议记录
                - metadata: 包含token使用量等信息
        """
        try:
            # 1. 检测输入语言
            output_language = self.detect_language(transcript)
            logger.info(f"Detected input language: {output_language}")

            # 2. 加载并渲染prompt模板
            prompt_template = self.prompt_loader.load_template('extract_info.txt')

            # 获取模板结构的字符串表示
            template_structure = self._format_template_structure(template)

            # 渲染prompt
            prompt = prompt_template.render(
                transcript=transcript,
                template_structure=template_structure,
                output_language=output_language
            )

            # 2. 调用Bedrock
            response = await self._invoke_model(prompt)

            # 3. 提取Markdown内容
            markdown_content = self._extract_content(response)

            # 4. 验证输出包含required字段
            validation_result = self._validate_output(markdown_content, template)
            if not validation_result['is_valid']:
                logger.warning(f"Missing required fields: {validation_result['missing_fields']}")

            # 5. 构建返回结果
            return {
                'formatted_markdown': markdown_content,
                'metadata': {
                    'model_id': self.model_id,
                    'input_tokens': response.get('usage', {}).get('inputTokens', 0),
                    'output_tokens': response.get('usage', {}).get('outputTokens', 0),
                    'total_tokens': response.get('usage', {}).get('totalTokens', 0),
                    'validation': validation_result
                }
            }

        except ClientError as e:
            logger.error(f"Bedrock API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Error extracting meeting info: {e}")
            raise

    async def optimize_with_feedback(
        self,
        original_content: str,
        feedbacks: list[UserFeedback],
        template: Template
    ) -> Dict[str, Any]:
        """
        根据用户反馈优化会议记录内容

        Args:
            original_content: draft阶段的Markdown内容
            feedbacks: 用户反馈列表
            template: 模板对象

        Returns:
            dict: 包含optimized_markdown和metadata
                - optimized_markdown: 优化后的Markdown
                - metadata: 包含token使用量等信息
        """
        try:
            # 1. 检测输出语言（保持与draft一致）
            output_language = self.detect_language(original_content)
            logger.info(f"Detected output language from draft: {output_language}")

            # 2. 加载并渲染prompt模板
            prompt_template = self.prompt_loader.load_template('optimize_content.txt')

            # 分离全局反馈和具体位置反馈
            global_feedbacks = []
            specific_feedbacks = []

            for fb in feedbacks:
                feedback_dict = {
                    'location': fb.location,
                    'feedback_type': fb.feedback_type,
                    'comment': fb.comment
                }
                if fb.is_global_feedback():
                    global_feedbacks.append(feedback_dict)
                else:
                    specific_feedbacks.append(feedback_dict)

            logger.info(
                f"Feedback breakdown - Global: {len(global_feedbacks)}, "
                f"Specific: {len(specific_feedbacks)}"
            )

            # 渲染prompt
            prompt = prompt_template.render(
                original_content=original_content,
                global_feedbacks=global_feedbacks,
                specific_feedbacks=specific_feedbacks,
                output_language=output_language
            )

            # 2. 调用Bedrock
            response = await self._invoke_model(
                prompt,
                temperature=0.4  # 稍高的温度以允许创造性改进
            )

            # 3. 提取优化后的内容
            optimized_content = self._extract_content(response)

            # 4. 构建返回结果
            return {
                'optimized_markdown': optimized_content,
                'metadata': {
                    'model_id': self.model_id,
                    'input_tokens': response.get('usage', {}).get('inputTokens', 0),
                    'output_tokens': response.get('usage', {}).get('outputTokens', 0),
                    'total_tokens': response.get('usage', {}).get('totalTokens', 0),
                    'feedback_count': len(feedbacks),
                    'feedback_types': list(set(fb.feedback_type for fb in feedbacks))
                }
            }

        except ClientError as e:
            logger.error(f"Bedrock API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Error optimizing with feedback: {e}")
            raise

    async def _invoke_model(
        self,
        prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> dict:
        """
        调用Bedrock InvokeModel API

        Args:
            prompt: 输入prompt
            temperature: 生成温度(覆盖默认值)
            max_tokens: 最大token数(覆盖默认值)

        Returns:
            dict: Bedrock响应
        """
        # 使用提供的参数或默认值
        temp = temperature if temperature is not None else self.temperature
        tokens = max_tokens if max_tokens is not None else self.max_tokens

        # 构建请求体
        request_body = {
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "text": prompt
                        }
                    ]
                }
            ],
            "inferenceConfig": {
                "temperature": temp,
                "maxTokens": tokens,
                "topP": 0.9  # 控制采样多样性
            }
        }

        try:
            # 调用Bedrock API
            logger.debug(f"Invoking Bedrock with model: {self.model_id}")
            response = self.bedrock.invoke_model(
                modelId=self.model_id,
                body=json.dumps(request_body),
                contentType='application/json',
                accept='application/json'
            )

            # 解析响应
            response_body = json.loads(response['body'].read())

            # 记录token使用
            if 'usage' in response_body:
                logger.info(
                    f"Token usage - Input: {response_body['usage'].get('inputTokens', 0)}, "
                    f"Output: {response_body['usage'].get('outputTokens', 0)}"
                )

            return response_body

        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']

            # 处理特定错误
            if error_code == 'ThrottlingException':
                logger.error(f"Rate limit exceeded: {error_message}")
                raise RuntimeError("API rate limit exceeded, please retry later")
            elif error_code == 'ModelTimeoutException':
                logger.error(f"Model timeout: {error_message}")
                raise RuntimeError("Model processing timeout")
            elif error_code == 'ValidationException':
                logger.error(f"Invalid request: {error_message}")
                raise ValueError(f"Invalid request parameters: {error_message}")
            else:
                logger.error(f"Bedrock API error [{error_code}]: {error_message}")
                raise

    def _extract_content(self, response: dict) -> str:
        """
        从Bedrock响应中提取内容

        Args:
            response: Bedrock响应

        Returns:
            str: 提取的内容
        """
        try:
            # Nova Pro响应格式
            output = response.get('output', {})
            message = output.get('message', {})
            content = message.get('content', [])

            if content and isinstance(content, list):
                # 提取文本内容
                text_content = []
                for item in content:
                    if isinstance(item, dict) and 'text' in item:
                        text_content.append(item['text'])

                return '\n'.join(text_content)

            # 备用提取路径
            return str(output)

        except Exception as e:
            logger.error(f"Error extracting content from response: {e}")
            raise ValueError("Unable to extract content from model response")

    def _format_template_structure(self, template: Template) -> str:
        """
        将模板结构格式化为字符串表示

        Args:
            template: 模板对象

        Returns:
            str: 模板结构的字符串表示
        """
        lines = []

        for section in template.structure.sections:
            # 添加section标题（默认使用##作为标题级别）
            lines.append(f"## {section.name}")

            # 添加字段说明
            for field in section.fields:
                required = " (必填)" if field.required else ""
                lines.append(f"- {field.label}{required}")

            lines.append("")  # 空行分隔

        return '\n'.join(lines)

    def _validate_output(self, content: str, template: Template) -> dict:
        """
        验证输出是否包含模板的必需字段

        Args:
            content: Markdown内容
            template: 模板对象

        Returns:
            dict: 验证结果
        """
        missing_fields = []

        # 检查所有required字段
        for section in template.structure.sections:
            for field in section.fields:
                if field.required:
                    # 简单检查字段标签是否出现在内容中
                    if field.label not in content:
                        missing_fields.append(f"{section.name}.{field.label}")

        return {
            'is_valid': len(missing_fields) == 0,
            'missing_fields': missing_fields
        }