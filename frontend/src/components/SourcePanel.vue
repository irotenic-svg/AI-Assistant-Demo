<template>
  <div v-if="sources && sources.length > 0" class="source-panel-comp">
    <el-popover
      placement="right"
      :width="420"
      trigger="click"
      popper-class="source-detail-popover"
    >
      <template #reference>
        <div class="source-toggle-btn">
          <span class="icon">▦</span>
          <span>引用来源 ({{ sources.length }})</span>
          <span class="arrow">→</span>
        </div>
      </template>
      <div class="source-popover-content">
        <div v-for="(src, i) in sources" :key="i" class="source-popover-item">
          <div class="source-header">
            <el-tag
              size="small"
              :type="src.source === 'PubMedQA' ? 'primary' : 'success'"
              effect="light"
            >
              {{ src.source }}
            </el-tag>
            <span class="source-index">{{ String(i + 1).padStart(2, '0') }}</span>
          </div>
          <div v-if="src.question" class="source-question">{{ src.question }}</div>
          <div class="source-content">{{ src.content }}</div>
        </div>
      </div>
    </el-popover>
  </div>
</template>

<script setup>
defineProps({
  sources: { type: Array, default: () => [] },
})
</script>
