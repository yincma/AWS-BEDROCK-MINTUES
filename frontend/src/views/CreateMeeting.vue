<template>
  <div class="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 py-12 px-4">
    <div class="max-w-3xl mx-auto">
      <!-- 头部 -->
      <div class="text-center mb-8 relative">
        <div class="absolute top-0 right-0">
          <LanguageSwitcher />
        </div>
        <h1 class="text-4xl font-bold text-gray-900 mb-2">{{ t('header.title') }}</h1>
        <p class="text-gray-600">{{ t('header.subtitle') }}</p>
      </div>

      <!-- 主卡片 -->
      <div class="bg-white rounded-2xl shadow-xl p-8">
        <!-- Tab 切换 -->
        <div class="flex border-b border-gray-200 mb-6">
          <button
            @click="inputType = 'text'"
            :class="[
              'flex-1 py-3 px-6 font-medium transition-colors',
              inputType === 'text'
                ? 'border-b-2 border-blue-500 text-blue-600'
                : 'text-gray-500 hover:text-gray-700'
            ]"
          >
            {{ t('createMeeting.tabs.text') }}
          </button>
          <button
            @click="inputType = 'audio'"
            :class="[
              'flex-1 py-3 px-6 font-medium transition-colors',
              inputType === 'audio'
                ? 'border-b-2 border-blue-500 text-blue-600'
                : 'text-gray-500 hover:text-gray-700'
            ]"
          >
            {{ t('createMeeting.tabs.audio') }}
          </button>
        </div>

        <!-- 文字输入表单 -->
        <div v-if="inputType === 'text'" class="space-y-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">
              {{ t('createMeeting.textInput.label') }}
            </label>
            <textarea
              v-model="textContent"
              rows="15"
              class="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
              :placeholder="t('createMeeting.textInput.placeholder')"
            ></textarea>
            <p class="mt-2 text-sm text-gray-500">
              {{ t('createMeeting.textInput.charCount', { count: textContent.length }) }}
            </p>
          </div>
        </div>

        <!-- 音频上传表单 -->
        <div v-if="inputType === 'audio'" class="space-y-4">
          <div
            @dragover.prevent="isDragging = true"
            @dragleave="isDragging = false"
            @drop.prevent="handleFileDrop"
            :class="[
              'border-2 border-dashed rounded-lg p-12 text-center transition-colors cursor-pointer',
              isDragging
                ? 'border-blue-500 bg-blue-50'
                : 'border-gray-300 hover:border-blue-400'
            ]"
            @click="$refs.fileInput.click()"
          >
            <input
              ref="fileInput"
              type="file"
              accept="audio/mp3,audio/wav,audio/mp4,audio/mpeg"
              class="hidden"
              @change="handleFileSelect"
            />
            <div v-if="!audioFile">
              <svg class="mx-auto h-16 w-16 text-gray-400 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
              </svg>
              <p class="text-lg text-gray-700 mb-2">{{ t('createMeeting.audioUpload.dragText') }}</p>
              <p class="text-sm text-gray-500">{{ t('createMeeting.audioUpload.clickText') }}</p>
              <p class="text-xs text-gray-400 mt-4">{{ t('createMeeting.audioUpload.supportText') }}</p>
            </div>
            <div v-else class="text-left">
              <div class="flex items-center justify-between bg-gray-50 rounded-lg p-4">
                <div class="flex items-center space-x-3">
                  <svg class="h-10 w-10 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" />
                  </svg>
                  <div>
                    <p class="font-medium text-gray-900">{{ audioFile.name }}</p>
                    <p class="text-sm text-gray-500">{{ formatFileSize(audioFile.size) }}</p>
                  </div>
                </div>
                <button
                  @click.stop="audioFile = null"
                  class="text-red-500 hover:text-red-700"
                >
                  <svg class="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            </div>
          </div>
        </div>

        <!-- 提交按钮 -->
        <div class="mt-8">
          <button
            @click="createMeeting"
            :disabled="isSubmitting || !canSubmit"
            :class="[
              'w-full py-4 px-6 rounded-lg font-semibold text-white transition-all transform',
              canSubmit && !isSubmitting
                ? 'bg-blue-600 hover:bg-blue-700 hover:scale-[1.02] shadow-lg hover:shadow-xl'
                : 'bg-gray-300 cursor-not-allowed'
            ]"
          >
            <span v-if="!isSubmitting">{{ t('createMeeting.submit.button') }}</span>
            <span v-else class="flex items-center justify-center">
              <svg class="animate-spin h-5 w-5 mr-3" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              {{ t('createMeeting.submit.processing') }}
            </span>
          </button>
        </div>

        <!-- 错误提示 -->
        <div v-if="errorMessage" class="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
          <p class="text-red-700 text-sm">{{ t('createMeeting.errors.prefix') }} {{ errorMessage }}</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { meetingsAPI } from '../api/meetings'
import LanguageSwitcher from '../components/LanguageSwitcher.vue'

const router = useRouter()
const { t } = useI18n()

// 状态
const inputType = ref('text')
const textContent = ref('')
const audioFile = ref(null)
const isDragging = ref(false)
const isSubmitting = ref(false)
const errorMessage = ref('')

// 计算属性
const canSubmit = computed(() => {
  if (inputType.value === 'text') {
    return textContent.value.trim().length > 50
  } else {
    return audioFile.value !== null
  }
})

// 文件处理
const handleFileSelect = (event) => {
  const file = event.target.files[0]
  if (file) {
    validateAndSetFile(file)
  }
}

const handleFileDrop = (event) => {
  isDragging.value = false
  const file = event.dataTransfer.files[0]
  if (file) {
    validateAndSetFile(file)
  }
}

const validateAndSetFile = (file) => {
  const maxSize = 100 * 1024 * 1024 // 100MB
  const allowedTypes = ['audio/mp3', 'audio/mpeg', 'audio/wav', 'audio/mp4']

  if (file.size > maxSize) {
    errorMessage.value = t('createMeeting.audioUpload.fileTooLarge')
    return
  }

  if (!allowedTypes.includes(file.type)) {
    errorMessage.value = t('createMeeting.audioUpload.invalidFormat')
    return
  }

  errorMessage.value = ''
  audioFile.value = file
}

const formatFileSize = (bytes) => {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(2) + ' MB'
}

// 创建会议
const createMeeting = async () => {
  if (!canSubmit.value || isSubmitting.value) return

  isSubmitting.value = true
  errorMessage.value = ''

  try {
    let result
    if (inputType.value === 'text') {
      result = await meetingsAPI.createFromText(textContent.value)
    } else {
      result = await meetingsAPI.createFromAudio(audioFile.value)
    }

    // 跳转到会议详情页面
    router.push(`/meeting/${result.id}`)
  } catch (error) {
    console.error('创建会议失败:', error)
    errorMessage.value = error.response?.data?.detail || t('createMeeting.errors.createFailed')
  } finally {
    isSubmitting.value = false
  }
}
</script>
