export default {
  common: {
    loading: 'Loading...',
    submit: 'Submit',
    cancel: 'Cancel',
    confirm: 'Confirm',
    back: 'Back',
    backHome: 'Back to Home',
    createNew: 'Create New Meeting',
    download: 'Download',
    copy: 'Copy',
    copied: 'Copied to clipboard',
    processing: 'Processing...',
    delete: 'Delete',
    add: 'Add'
  },

  header: {
    title: 'AWS Bedrock Minutes',
    subtitle: 'AI-Powered Intelligent Meeting Minutes Generation System'
  },

  createMeeting: {
    tabs: {
      text: '📝 Text Input',
      audio: '🎤 Audio Upload'
    },
    textInput: {
      label: 'Meeting Content',
      placeholder: `Please enter meeting content, including meeting topic, participants, discussion content, etc...

Example:
Meeting Topic: Product Roadmap Planning Meeting
Time: October 1, 2025
Participants: John (Product Manager), Jane (CTO)

John: Let's discuss next quarter's product roadmap...`,
      charCount: '{count} characters entered'
    },
    audioUpload: {
      dragText: 'Drag audio file here',
      clickText: 'or click to select file',
      supportText: 'Support MP3, WAV, MP4 format, max 100MB',
      fileTooLarge: 'File size cannot exceed 100MB',
      invalidFormat: 'Only MP3, WAV, MP4 format audio files are supported'
    },
    submit: {
      button: '🚀 Start Generating Minutes',
      processing: 'Processing...'
    },
    errors: {
      createFailed: 'Failed to create meeting, please try again later',
      prefix: '❌ '
    }
  },

  meetingDetail: {
    title: 'Meeting Minutes',
    id: 'ID',
    createdAt: 'Created At',

    stages: {
      draft: {
        title: 'Draft',
        subtitle: 'Draft Generation',
        processing: '⏳ Generating Draft...',
        processingDesc: 'AI is analyzing meeting content and extracting key information',
        estimated: 'Estimated 60 seconds',
        content: '📝 Draft Content',
        downloadButton: '📥 Download Draft',
        version: '📝 Draft Version'
      },
      review: {
        title: 'Review',
        subtitle: 'Review Feedback',
        formTitle: '💬 Submit Review Feedback',
        formDesc: 'Please carefully review the draft content above. If you find areas that need improvement, you can add feedback. You can also submit without feedback to proceed to final optimization.',
        globalSuggestionTitle: '🌐 Global Optimization Suggestions',
        globalSuggestionDesc: 'No need to specify exact locations, just provide overall optimization directions like "Make the tone more formal" or "Add more technical details"',
        globalSuggestionLabel: 'Optimization Suggestion',
        globalSuggestionPlaceholder: 'e.g.: The overall tone should be more formal, use more professional terminology...',
        globalLocation: 'Global',
        addGlobalButton: '🌐 Add Global Suggestion',
        feedbackType: 'Feedback Type',
        feedbackTypes: {
          inaccurate: 'Inaccurate Information',
          missing: 'Missing Information',
          improvement: 'Needs Improvement'
        },
        sectionLabel: 'Section Name',
        sectionPlaceholder: 'e.g.: Meeting Content',
        sectionHint: 'Please enter section name',
        lineLabel: 'Line Number',
        linePlaceholder: 'e.g.: 3',
        lineHint: 'Please enter line number (numeric)',
        commentLabel: 'Specific Description',
        commentPlaceholder: 'Please describe the specific content that needs improvement...',
        addButton: '➕ Add Feedback',
        submitButton: '✅ Submit {count} Feedback(s) and Optimize',
        submitting: 'Submitting...',
        warning: 'Please add at least one feedback',
        lineFormat: 'Line {line}'
      },
      final: {
        title: 'Final',
        subtitle: 'Final Version',
        processing: '⏳ Optimizing Content...',
        processingDesc: 'AI is optimizing meeting minutes based on your feedback',
        content: '✅ Final Version',
        downloadButton: '📥 Download Final',
        version: '✅ Final Version'
      }
    },

    errors: {
      loadFailed: 'Failed to load meeting details, please try again later',
      submitFeedbackFailed: 'Failed to submit feedback, please try again later',
      downloadFailed: 'Download failed',
      copyFailed: 'Copy failed',
      processingFailed: '❌ Processing Failed'
    }
  }
}
