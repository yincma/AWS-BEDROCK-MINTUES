<template>
  <div class="min-h-screen bg-gray-50 py-8 px-4">
    <div class="max-w-5xl mx-auto">
      <!-- 语言切换器 -->
      <div class="mb-4 flex justify-end">
        <LanguageSwitcher />
      </div>

      <!-- 加载状态 -->
      <div v-if="loading" class="flex items-center justify-center py-20">
        <div class="text-center">
          <svg class="animate-spin h-12 w-12 text-blue-500 mx-auto mb-4" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          <p class="text-gray-600">{{ t('common.loading') }}</p>
        </div>
      </div>

      <!-- 错误状态 -->
      <div v-else-if="error" class="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
        <p class="text-red-700 mb-4">❌ {{ error }}</p>
        <button @click="$router.push('/')" class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
          {{ t('common.backHome') }}
        </button>
      </div>

      <!-- 会议内容 -->
      <div v-else-if="meeting">
        <!-- 头部 -->
        <div class="bg-white rounded-lg shadow-sm p-6 mb-6">
          <div class="flex items-center justify-between">
            <div>
              <h1 class="text-2xl font-bold text-gray-900 mb-2">{{ t('meetingDetail.title') }}</h1>
              <p class="text-sm text-gray-500">{{ t('meetingDetail.id') }}: {{ meeting.id }}</p>
              <p class="text-sm text-gray-500">{{ t('meetingDetail.createdAt') }}: {{ formatDate(meeting.created_at) }}</p>
            </div>
            <button @click="$router.push('/')" class="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200">
              ← {{ t('common.back') }}
            </button>
          </div>

          <!-- 阶段进度指示器 -->
          <div class="mt-6 flex items-center">
            <div class="flex items-center flex-1">
              <!-- Draft -->
              <div class="flex items-center">
                <div :class="[
                  'flex items-center justify-center w-10 h-10 rounded-full font-semibold',
                  getStageStatus('draft') === 'completed' ? 'bg-green-500 text-white' :
                  getStageStatus('draft') === 'processing' ? 'bg-blue-500 text-white' :
                  'bg-gray-300 text-gray-600'
                ]">
                  <span v-if="getStageStatus('draft') === 'completed'">✓</span>
                  <span v-else-if="getStageStatus('draft') === 'processing'" class="animate-pulse">⏳</span>
                  <span v-else>1</span>
                </div>
                <div class="ml-3">
                  <p class="text-sm font-medium text-gray-900">{{ t('meetingDetail.stages.draft.title') }}</p>
                  <p class="text-xs text-gray-500">{{ t('meetingDetail.stages.draft.subtitle') }}</p>
                </div>
              </div>

              <!-- 连接线 -->
              <div class="flex-1 h-1 mx-4" :class="[
                getStageStatus('draft') === 'completed' ? 'bg-green-500' : 'bg-gray-300'
              ]"></div>

              <!-- Review -->
              <div class="flex items-center">
                <div :class="[
                  'flex items-center justify-center w-10 h-10 rounded-full font-semibold',
                  getStageStatus('review') === 'completed' ? 'bg-green-500 text-white' :
                  getStageStatus('review') === 'waiting' ? 'bg-yellow-500 text-white' :
                  'bg-gray-300 text-gray-600'
                ]">
                  <span v-if="getStageStatus('review') === 'completed'">✓</span>
                  <span v-else-if="getStageStatus('review') === 'waiting'">⏸</span>
                  <span v-else>2</span>
                </div>
                <div class="ml-3">
                  <p class="text-sm font-medium text-gray-900">{{ t('meetingDetail.stages.review.title') }}</p>
                  <p class="text-xs text-gray-500">{{ t('meetingDetail.stages.review.subtitle') }}</p>
                </div>
              </div>

              <!-- 连接线 -->
              <div class="flex-1 h-1 mx-4" :class="[
                getStageStatus('review') === 'completed' ? 'bg-green-500' : 'bg-gray-300'
              ]"></div>

              <!-- Final -->
              <div class="flex items-center">
                <div :class="[
                  'flex items-center justify-center w-10 h-10 rounded-full font-semibold',
                  getStageStatus('final') === 'completed' ? 'bg-green-500 text-white' :
                  getStageStatus('final') === 'processing' ? 'bg-blue-500 text-white' :
                  'bg-gray-300 text-gray-600'
                ]">
                  <span v-if="getStageStatus('final') === 'completed'">✓</span>
                  <span v-else-if="getStageStatus('final') === 'processing'" class="animate-pulse">⏳</span>
                  <span v-else>3</span>
                </div>
                <div class="ml-3">
                  <p class="text-sm font-medium text-gray-900">{{ t('meetingDetail.stages.final.title') }}</p>
                  <p class="text-xs text-gray-500">{{ t('meetingDetail.stages.final.subtitle') }}</p>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Draft 阶段处理中 -->
        <div v-if="meeting.status === 'draft' || (meeting.status === 'processing' && !meeting.stages?.draft?.status)"
             class="bg-white rounded-lg shadow-sm p-8 text-center">
          <svg class="animate-spin h-16 w-16 text-blue-500 mx-auto mb-4" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          <h2 class="text-xl font-semibold text-gray-900 mb-2">{{ t('meetingDetail.stages.draft.processing') }}</h2>
          <p class="text-gray-600 mb-4">{{ t('meetingDetail.stages.draft.processingDesc') }}</p>
          <p class="text-sm text-gray-500">{{ t('meetingDetail.stages.draft.estimated') }}</p>
        </div>

        <!-- Draft 完成 - 等待审查 -->
        <div v-else-if="meeting.status === 'reviewing' && !feedbackSubmitted" class="space-y-6">
          <!-- Draft 内容展示 -->
          <div class="bg-white rounded-lg shadow-sm p-6">
            <div class="flex items-center justify-between mb-4">
              <h2 class="text-xl font-semibold text-gray-900">{{ t('meetingDetail.stages.draft.content') }}</h2>
              <button
                @click="downloadMarkdown('draft')"
                class="px-4 py-2 bg-blue-100 text-blue-700 rounded-lg hover:bg-blue-200 text-sm font-medium"
              >
                {{ t('meetingDetail.stages.draft.downloadButton') }}
              </button>
            </div>
            <div class="prose max-w-none bg-gray-50 rounded-lg p-6" v-html="renderMarkdown(meeting.stages?.draft?.content)"></div>
          </div>

          <!-- 反馈表单 -->
          <div class="bg-white rounded-lg shadow-sm p-6">
            <h2 class="text-xl font-semibold text-gray-900 mb-4">{{ t('meetingDetail.stages.review.formTitle') }}</h2>
            <p class="text-gray-600 mb-6">{{ t('meetingDetail.stages.review.formDesc') }}</p>

            <!-- 全局优化建议区域 (新增) -->
            <div class="border-2 border-purple-200 bg-purple-50 rounded-lg p-4 mb-6">
              <h3 class="text-lg font-semibold text-purple-900 mb-2 flex items-center">
                <svg class="h-5 w-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3.055 11H5a2 2 0 012 2v1a2 2 0 002 2 2 2 0 012 2v2.945M8 3.935V5.5A2.5 2.5 0 0010.5 8h.5a2 2 0 012 2 2 2 0 104 0 2 2 0 012-2h1.064M15 20.488V18a2 2 0 012-2h3.064M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                {{ t('meetingDetail.stages.review.globalSuggestionTitle') }}
              </h3>
              <p class="text-sm text-purple-700 mb-3">{{ t('meetingDetail.stages.review.globalSuggestionDesc') }}</p>
              <div class="space-y-3">
                <div>
                  <label class="block text-sm font-medium text-purple-900 mb-2">{{ t('meetingDetail.stages.review.feedbackType') }}</label>
                  <select v-model="globalFeedback.feedback_type" class="w-full px-3 py-2 border border-purple-300 rounded-lg bg-white">
                    <option value="improvement">{{ t('meetingDetail.stages.review.feedbackTypes.improvement') }}</option>
                    <option value="inaccurate">{{ t('meetingDetail.stages.review.feedbackTypes.inaccurate') }}</option>
                    <option value="missing">{{ t('meetingDetail.stages.review.feedbackTypes.missing') }}</option>
                  </select>
                </div>
                <div>
                  <label class="block text-sm font-medium text-purple-900 mb-2">{{ t('meetingDetail.stages.review.globalSuggestionLabel') }}</label>
                  <textarea
                    v-model="globalFeedback.comment"
                    rows="3"
                    :placeholder="t('meetingDetail.stages.review.globalSuggestionPlaceholder')"
                    class="w-full px-3 py-2 border border-purple-300 rounded-lg resize-none"
                  ></textarea>
                </div>
                <button
                  @click="addGlobalFeedback"
                  :disabled="!canAddGlobalFeedback"
                  :class="[
                    'px-4 py-2 rounded-lg font-medium',
                    canAddGlobalFeedback
                      ? 'bg-purple-600 text-white hover:bg-purple-700'
                      : 'bg-gray-300 text-gray-500 cursor-not-allowed'
                  ]"
                >
                  {{ t('meetingDetail.stages.review.addGlobalButton') }}
                </button>
              </div>
            </div>

            <!-- 反馈列表 -->
            <div v-if="feedbacks.length > 0" class="space-y-3 mb-6">
              <div v-for="(feedback, index) in feedbacks" :key="index"
                   class="bg-gray-50 rounded-lg p-4 flex items-start justify-between">
                <div class="flex-1">
                  <div class="flex items-center space-x-2 mb-2">
                    <span class="px-2 py-1 text-xs font-medium rounded" :class="{
                      'bg-red-100 text-red-700': feedback.feedback_type === 'inaccurate',
                      'bg-yellow-100 text-yellow-700': feedback.feedback_type === 'missing',
                      'bg-blue-100 text-blue-700': feedback.feedback_type === 'improvement'
                    }">
                      {{ feedbackTypeLabel(feedback.feedback_type) }}
                    </span>
                    <span class="text-sm text-gray-600">{{ formatLocation(feedback.location) }}</span>
                  </div>
                  <p class="text-gray-700">{{ feedback.comment }}</p>
                </div>
                <button @click="removeFeedback(index)" class="text-red-500 hover:text-red-700 ml-4">
                  <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            </div>

            <!-- 添加反馈表单 -->
            <div class="border border-gray-200 rounded-lg p-4 space-y-4">
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-2">{{ t('meetingDetail.stages.review.feedbackType') }}</label>
                <select v-model="newFeedback.feedback_type" class="w-full px-3 py-2 border border-gray-300 rounded-lg">
                  <option value="inaccurate">{{ t('meetingDetail.stages.review.feedbackTypes.inaccurate') }}</option>
                  <option value="missing">{{ t('meetingDetail.stages.review.feedbackTypes.missing') }}</option>
                  <option value="improvement">{{ t('meetingDetail.stages.review.feedbackTypes.improvement') }}</option>
                </select>
              </div>
              <div class="grid grid-cols-2 gap-4">
                <div>
                  <label class="block text-sm font-medium text-gray-700 mb-2">{{ t('meetingDetail.stages.review.sectionLabel') }}</label>
                  <input
                    v-model="newFeedback.section"
                    type="text"
                    :placeholder="t('meetingDetail.stages.review.sectionPlaceholder')"
                    class="w-full px-3 py-2 border border-gray-300 rounded-lg"
                  />
                  <p class="mt-1 text-xs text-gray-500">{{ t('meetingDetail.stages.review.sectionHint') }}</p>
                </div>
                <div>
                  <label class="block text-sm font-medium text-gray-700 mb-2">{{ t('meetingDetail.stages.review.lineLabel') }}</label>
                  <input
                    v-model="newFeedback.line"
                    type="number"
                    min="1"
                    :placeholder="t('meetingDetail.stages.review.linePlaceholder')"
                    class="w-full px-3 py-2 border border-gray-300 rounded-lg"
                  />
                  <p class="mt-1 text-xs text-gray-500">{{ t('meetingDetail.stages.review.lineHint') }}</p>
                </div>
              </div>
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-2">{{ t('meetingDetail.stages.review.commentLabel') }}</label>
                <textarea
                  v-model="newFeedback.comment"
                  rows="3"
                  :placeholder="t('meetingDetail.stages.review.commentPlaceholder')"
                  class="w-full px-3 py-2 border border-gray-300 rounded-lg resize-none"
                ></textarea>
              </div>
              <button
                @click="addFeedback"
                :disabled="!canAddFeedback"
                :class="[
                  'px-4 py-2 rounded-lg font-medium',
                  canAddFeedback
                    ? 'bg-blue-600 text-white hover:bg-blue-700'
                    : 'bg-gray-300 text-gray-500 cursor-not-allowed'
                ]"
              >
                {{ t('meetingDetail.stages.review.addButton') }}
              </button>
            </div>

            <!-- 提交按钮 -->
            <div class="mt-6 flex justify-end space-x-3">
              <div v-if="feedbacks.length === 0" class="flex items-center text-sm text-amber-600">
                <svg class="h-5 w-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
                {{ t('meetingDetail.stages.review.warning') }}
              </div>
              <button
                @click="submitFeedbacks"
                :disabled="isSubmittingFeedback || feedbacks.length === 0"
                class="px-6 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 font-semibold disabled:bg-gray-300 disabled:cursor-not-allowed"
              >
                <span v-if="!isSubmittingFeedback">
                  {{ t('meetingDetail.stages.review.submitButton', { count: feedbacks.length }) }}
                </span>
                <span v-else>{{ t('meetingDetail.stages.review.submitting') }}</span>
              </button>
            </div>
          </div>
        </div>

        <!-- Final 阶段处理中 -->
        <div v-else-if="meeting.status === 'optimizing' || (feedbackSubmitted && meeting.status === 'reviewing')"
             class="bg-white rounded-lg shadow-sm p-8 text-center">
          <svg class="animate-spin h-16 w-16 text-blue-500 mx-auto mb-4" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          <h2 class="text-xl font-semibold text-gray-900 mb-2">{{ t('meetingDetail.stages.final.processing') }}</h2>
          <p class="text-gray-600 mb-4">{{ t('meetingDetail.stages.final.processingDesc') }}</p>
        </div>

        <!-- Final 完成 -->
        <div v-else-if="meeting.status === 'completed'" class="space-y-6">
          <!-- 版本切换 -->
          <div class="bg-white rounded-lg shadow-sm p-4">
            <div class="flex space-x-2">
              <button
                @click="activeVersion = 'draft'"
                :class="[
                  'px-4 py-2 rounded-lg font-medium transition-colors',
                  activeVersion === 'draft'
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                ]"
              >
                {{ t('meetingDetail.stages.draft.version') }}
              </button>
              <button
                @click="activeVersion = 'final'"
                :class="[
                  'px-4 py-2 rounded-lg font-medium transition-colors',
                  activeVersion === 'final'
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                ]"
              >
                {{ t('meetingDetail.stages.final.version') }}
              </button>
            </div>
          </div>

          <!-- 内容展示 -->
          <div class="bg-white rounded-lg shadow-sm p-6">
            <div class="flex items-center justify-between mb-4">
              <h2 class="text-xl font-semibold text-gray-900">
                {{ activeVersion === 'draft' ? t('meetingDetail.stages.draft.content') : t('meetingDetail.stages.final.content') }}
              </h2>
              <div class="flex space-x-2">
                <button
                  @click="downloadMarkdown(activeVersion)"
                  class="px-4 py-2 bg-blue-100 text-blue-700 rounded-lg hover:bg-blue-200 text-sm font-medium"
                >
                  {{ activeVersion === 'draft' ? t('meetingDetail.stages.draft.downloadButton') : t('meetingDetail.stages.final.downloadButton') }}
                </button>
                <button
                  @click="copyToClipboard"
                  class="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 text-sm font-medium"
                >
                  📋 {{ t('common.copy') }}
                </button>
              </div>
            </div>
            <div class="prose max-w-none bg-gray-50 rounded-lg p-6" v-html="renderMarkdown(getActiveContent())"></div>
          </div>

          <!-- 操作按钮 -->
          <div class="bg-white rounded-lg shadow-sm p-6 flex justify-center">
            <button
              @click="$router.push('/')"
              class="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-semibold"
            >
              🔄 {{ t('common.createNew') }}
            </button>
          </div>
        </div>

        <!-- 失败状态 -->
        <div v-else-if="meeting.status === 'failed'" class="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
          <p class="text-red-700 mb-4">{{ t('meetingDetail.errors.processingFailed') }}</p>
          <button @click="$router.push('/')" class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
            {{ t('common.backHome') }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { meetingsAPI } from '../api/meetings'
import MarkdownIt from 'markdown-it'
import LanguageSwitcher from '../components/LanguageSwitcher.vue'

const route = useRoute()
const { t, locale } = useI18n()
const md = new MarkdownIt()

// 状态
const meeting = ref(null)
const loading = ref(true)
const error = ref('')
const pollingInterval = ref(null)
const activeVersion = ref('final')

// 反馈相关
const feedbacks = ref([])
const newFeedback = ref({
  feedback_type: 'inaccurate',
  section: '',
  line: '',
  comment: ''
})
const globalFeedback = ref({
  feedback_type: 'improvement',
  comment: ''
})
const isSubmittingFeedback = ref(false)
const feedbackSubmitted = ref(false)

// 计算属性
const canAddFeedback = computed(() => {
  return newFeedback.value.section.trim() &&
         newFeedback.value.line &&
         newFeedback.value.comment.trim()
})

const canAddGlobalFeedback = computed(() => {
  return globalFeedback.value.comment.trim()
})

// 生命周期
onMounted(async () => {
  await fetchMeeting()
  startPolling()
})

onUnmounted(() => {
  stopPolling()
})

// 方法
const fetchMeeting = async () => {
  try {
    loading.value = true
    meeting.value = await meetingsAPI.getMeeting(route.params.id)
    error.value = ''
  } catch (err) {
    console.error('获取会议详情失败:', err)
    error.value = t('meetingDetail.errors.loadFailed')
  } finally {
    loading.value = false
  }
}

const startPolling = () => {
  pollingInterval.value = setInterval(async () => {
    if (meeting.value && (
      meeting.value.status === 'draft' ||
      meeting.value.status === 'processing' ||
      meeting.value.status === 'optimizing' ||
      // 已提交反馈后，后端在reviewing状态下进行优化处理
      (meeting.value.status === 'reviewing' && feedbackSubmitted.value)
    )) {
      await fetchMeeting()
    } else {
      stopPolling()
    }
  }, 5000)
}

const stopPolling = () => {
  if (pollingInterval.value) {
    clearInterval(pollingInterval.value)
    pollingInterval.value = null
  }
}

const getStageStatus = (stage) => {
  if (!meeting.value) return 'pending'

  if (stage === 'draft') {
    if (meeting.value.stages?.draft?.status === 'completed') return 'completed'
    if (meeting.value.status === 'draft' || meeting.value.status === 'processing') return 'processing'
    return 'pending'
  }

  if (stage === 'review') {
    if (meeting.value.stages?.review?.status === 'completed') return 'completed'
    if (meeting.value.status === 'reviewing') return 'waiting'
    return 'pending'
  }

  if (stage === 'final') {
    if (meeting.value.stages?.final?.status === 'completed') return 'completed'
    if (meeting.value.status === 'optimizing') return 'processing'
    return 'pending'
  }

  return 'pending'
}

const renderMarkdown = (content) => {
  if (!content) return ''
  // 移除代码块标记
  const cleanContent = content.replace(/^```markdown\n?|```$/g, '')
  return md.render(cleanContent)
}

const getActiveContent = () => {
  if (activeVersion.value === 'draft') {
    return meeting.value?.stages?.draft?.content || ''
  } else {
    return meeting.value?.stages?.final?.content || ''
  }
}

const formatDate = (dateString) => {
  const date = new Date(dateString)
  const localeMap = {
    'zh-CN': 'zh-CN',
    'en-US': 'en-US'
  }
  return date.toLocaleString(localeMap[locale.value] || 'zh-CN')
}

const feedbackTypeLabel = (type) => {
  const typeMap = {
    'inaccurate': 'meetingDetail.stages.review.feedbackTypes.inaccurate',
    'missing': 'meetingDetail.stages.review.feedbackTypes.missing',
    'improvement': 'meetingDetail.stages.review.feedbackTypes.improvement'
  }
  return typeMap[type] ? t(typeMap[type]) : type
}

const formatLocation = (location) => {
  // 检查是否为全局建议
  if (location === 'global') {
    return t('meetingDetail.stages.review.globalLocation')
  }

  // 解析 "section:<名称>,line:<行号>" 格式
  try {
    const parts = location.split(',')
    const section = parts[0].replace('section:', '').trim()
    const line = parts[1].replace('line:', '').trim()
    return `${section} (${t('meetingDetail.stages.review.lineFormat', { line })})`
  } catch {
    return location
  }
}

const addFeedback = () => {
  if (!canAddFeedback.value) return

  // 拼接为后端要求的格式: "section:<名称>,line:<行号>"
  const location = `section:${newFeedback.value.section.trim()},line:${newFeedback.value.line}`

  feedbacks.value.push({
    feedback_type: newFeedback.value.feedback_type,
    location: location,
    comment: newFeedback.value.comment
  })

  newFeedback.value = {
    feedback_type: 'inaccurate',
    section: '',
    line: '',
    comment: ''
  }
}

const addGlobalFeedback = () => {
  if (!canAddGlobalFeedback.value) return

  // 全局建议使用 location="global"
  feedbacks.value.push({
    feedback_type: globalFeedback.value.feedback_type,
    location: 'global',
    comment: globalFeedback.value.comment
  })

  // 重置表单
  globalFeedback.value = {
    feedback_type: 'improvement',
    comment: ''
  }
}

const removeFeedback = (index) => {
  feedbacks.value.splice(index, 1)
}

const submitFeedbacks = async () => {
  isSubmittingFeedback.value = true
  try {
    console.log('准备提交的反馈数据:', JSON.stringify(feedbacks.value, null, 2))
    await meetingsAPI.submitFeedback(route.params.id, feedbacks.value)
    feedbackSubmitted.value = true
    // 重新开始轮询
    startPolling()
  } catch (err) {
    console.error('提交反馈失败:', err)
    console.error('错误详情:', JSON.stringify(err.response?.data, null, 2))
    const details = err.response?.data?.details
    if (details && details.length > 0) {
      console.error('验证错误详情:', details)
      error.value = `验证失败: ${details[0].msg}`
    } else {
      error.value = err.response?.data?.message || t('meetingDetail.errors.submitFeedbackFailed')
    }
  } finally {
    isSubmittingFeedback.value = false
  }
}

const downloadMarkdown = async (stage) => {
  try {
    const content = await meetingsAPI.exportMeeting(route.params.id, stage)
    const blob = new Blob([content], { type: 'text/markdown' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `meeting_${route.params.id}_${stage}.md`
    a.click()
    URL.revokeObjectURL(url)
  } catch (err) {
    console.error(t('meetingDetail.errors.downloadFailed'), err)
  }
}

const copyToClipboard = async () => {
  try {
    const content = getActiveContent().replace(/^```markdown\n?|```$/g, '')
    await navigator.clipboard.writeText(content)
    alert(t('common.copied'))
  } catch (err) {
    console.error(t('meetingDetail.errors.copyFailed'), err)
  }
}
</script>
