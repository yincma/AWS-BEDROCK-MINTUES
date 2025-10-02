import apiClient from './client'

/**
 * 会议记录 API
 */
export const meetingsAPI = {
  /**
   * 创建会议记录（文字输入）
   * @param {string} textContent - 会议文字内容
   * @param {string} templateId - 模板ID（默认 'default'）
   * @returns {Promise<{id: string, status: string, created_at: string, estimated_completion_time: number}>}
   */
  async createFromText(textContent, templateId = 'default') {
    const formData = new FormData()
    formData.append('input_type', 'text')
    formData.append('text_content', textContent)
    if (templateId) {
      formData.append('template_id', templateId)
    }

    const response = await apiClient.post('/meetings', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return response.data
  },

  /**
   * 创建会议记录（音频上传）
   * @param {File} audioFile - 音频文件
   * @param {string} templateId - 模板ID
   * @returns {Promise<{id: string, status: string, created_at: string, estimated_completion_time: number}>}
   */
  async createFromAudio(audioFile, templateId = 'default') {
    const formData = new FormData()
    formData.append('input_type', 'audio')
    formData.append('audio_file', audioFile)
    if (templateId) {
      formData.append('template_id', templateId)
    }

    const response = await apiClient.post('/meetings', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return response.data
  },

  /**
   * 获取会议记录详情
   * @param {string} meetingId - 会议ID
   * @returns {Promise<Object>} 会议记录详情
   */
  async getMeeting(meetingId) {
    const response = await apiClient.get(`/meetings/${meetingId}`)
    return response.data
  },

  /**
   * 提交审查反馈
   * @param {string} meetingId - 会议ID
   * @param {Array} feedbacks - 反馈列表
   * @returns {Promise<Object>}
   */
  async submitFeedback(meetingId, feedbacks) {
    const response = await apiClient.post(`/meetings/${meetingId}/feedback`, {
      feedbacks,
    })
    return response.data
  },

  /**
   * 导出会议记录
   * @param {string} meetingId - 会议ID
   * @param {string} stage - 阶段 ('draft', 'review', 'final')
   * @returns {Promise<string>} Markdown 内容
   */
  async exportMeeting(meetingId, stage = 'final') {
    const response = await apiClient.get(`/meetings/${meetingId}/export`, {
      params: { stage },
      responseType: 'text',
    })
    return response.data
  },
}
