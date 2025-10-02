export default {
  common: {
    loading: '加载中...',
    submit: '提交',
    cancel: '取消',
    confirm: '确认',
    back: '返回',
    backHome: '返回首页',
    createNew: '创建新会议',
    download: '下载',
    copy: '复制',
    copied: '已复制到剪贴板',
    processing: '处理中...',
    delete: '删除',
    add: '添加'
  },

  header: {
    title: 'AWS Bedrock Minutes',
    subtitle: 'AI驱动的智能会议记录生成系统'
  },

  createMeeting: {
    tabs: {
      text: '📝 文字输入',
      audio: '🎤 音频上传'
    },
    textInput: {
      label: '会议内容',
      placeholder: `请输入会议内容，包括会议主题、参与者、讨论内容等...

示例：
会议主题：产品路线图规划会议
时间：2025年10月1日
参与者：张三（产品经理）、李四（技术总监）

张三：今天我们讨论一下下个季度的产品路线图...`,
      charCount: '已输入 {count} 字符'
    },
    audioUpload: {
      dragText: '拖拽音频文件到这里',
      clickText: '或点击选择文件',
      supportText: '支持 MP3, WAV, MP4 格式，最大 100MB',
      fileTooLarge: '文件大小不能超过 100MB',
      invalidFormat: '仅支持 MP3, WAV, MP4 格式的音频文件'
    },
    submit: {
      button: '🚀 开始生成会议记录',
      processing: '处理中...'
    },
    errors: {
      createFailed: '创建会议失败，请稍后重试',
      prefix: '❌ '
    }
  },

  meetingDetail: {
    title: '会议记录',
    id: 'ID',
    createdAt: '创建时间',

    stages: {
      draft: {
        title: 'Draft',
        subtitle: '初稿生成',
        processing: '⏳ 正在生成初稿...',
        processingDesc: 'AI正在分析会议内容并提取关键信息',
        estimated: '预计需要 60 秒',
        content: '📝 初稿内容',
        downloadButton: '📥 下载 Draft',
        version: '📝 Draft 版本'
      },
      review: {
        title: 'Review',
        subtitle: '审查反馈',
        formTitle: '💬 提交审查反馈',
        formDesc: '请仔细审查上面的初稿内容，如果发现需要改进的地方，可以添加反馈。也可以直接提交空反馈进入最终优化阶段。',
        globalSuggestionTitle: '🌐 全局优化建议',
        globalSuggestionDesc: '无需指定具体位置，直接给出整体性的优化方向，例如"整体语气更正式"、"增加技术细节"等',
        globalSuggestionLabel: '优化建议',
        globalSuggestionPlaceholder: '例如：整体语气应该更正式一些，多用专业术语...',
        globalLocation: '全局',
        addGlobalButton: '🌐 添加全局建议',
        feedbackType: '反馈类型',
        feedbackTypes: {
          inaccurate: '信息不准确',
          missing: '信息缺失',
          improvement: '需要改进'
        },
        sectionLabel: '章节名称',
        sectionPlaceholder: '例如: 会议内容',
        sectionHint: '请输入章节名称',
        lineLabel: '行号',
        linePlaceholder: '例如: 3',
        lineHint: '请输入行号（数字）',
        commentLabel: '具体说明',
        commentPlaceholder: '请描述需要改进的具体内容...',
        addButton: '➕ 添加反馈',
        submitButton: '✅提交 {count} 条反馈并优化',
        submitting: '提交中...',
        warning: '请至少添加一条反馈',
        lineFormat: '第{line}行'
      },
      final: {
        title: 'Final',
        subtitle: '最终版本',
        processing: '⏳ 正在优化内容...',
        processingDesc: 'AI正在根据您的反馈优化会议记录',
        content: '✅ 最终版本',
        downloadButton: '📥 下载 Final',
        version: '✅ Final 版本'
      }
    },

    errors: {
      loadFailed: '获取会议详情失败，请稍后重试',
      submitFeedbackFailed: '提交反馈失败，请稍后重试',
      downloadFailed: '下载失败',
      copyFailed: '复制失败',
      processingFailed: '❌ 处理失败'
    }
  }
}
