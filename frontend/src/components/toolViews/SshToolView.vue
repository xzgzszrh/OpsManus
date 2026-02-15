<template>
  <div
    class="h-[36px] flex items-center px-3 w-full bg-[var(--background-gray-main)] border-b border-[var(--border-main)] rounded-t-[12px] shadow-[inset_0px_1px_0px_0px_#FFFFFF] dark:shadow-[inset_0px_1px_0px_0px_#FFFFFF30]">
    <div class="flex-1 flex items-center justify-center">
      <div class="max-w-[250px] truncate text-[var(--text-tertiary)] text-sm font-medium text-center">{{ headerText }}</div>
    </div>
  </div>
  <div class="flex-1 min-h-0 w-full overflow-y-auto">
    <div dir="ltr" data-orientation="horizontal" class="flex flex-col flex-1 min-h-0">
      <div
        data-state="active"
        data-orientation="horizontal"
        role="tabpanel"
        tabindex="0"
        class="py-2 focus-visible:outline-none data-[state=inactive]:hidden flex-1 font-mono text-sm leading-relaxed px-3 outline-none overflow-auto whitespace-pre-wrap break-all"
        style="animation-duration: 0s;"
      >
        <code v-html="shell"></code>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue';
import type { ToolContent } from '@/types/message';
import { listNodeLogs, type SSHLogItem } from '@/api/node';

const props = defineProps<{
  sessionId: string;
  toolContent: ToolContent;
  live: boolean;
}>();

const shell = ref('');
const logs = ref<SSHLogItem[]>([]);
const refreshTimer = ref<number | null>(null);

const headerText = computed(() => {
  const nodeName = props.toolContent.content?.node_name;
  const nodeId = props.toolContent.content?.node_id || props.toolContent.args?.node_id;
  return nodeName ? `${nodeName} (${nodeId || ''})` : (nodeId || 'remote-node');
});

const nodeId = computed(() => props.toolContent.content?.node_id || props.toolContent.args?.node_id);

const renderConsole = () => {
  const command = props.toolContent.content?.command || props.toolContent.args?.command || '';
  const output = props.toolContent.content?.output || '';
  const pending = props.toolContent.status === 'calling' || props.toolContent.content?.approval_required;

  let view = '';
  for (const item of logs.value.slice().reverse()) {
    if (item.actor_type !== 'assistant') continue;
    view += `<span style=\"color: rgb(0, 187, 0);\">manus@remote:~$</span><span> ${escapeHtml(item.command)}</span>\n`;
    view += `<span>${escapeHtml(item.output || '(empty output)')}</span>\n`;
  }

  if (pending || (command && !view.includes(escapeHtml(command)))) {
    view += `<span style=\"color: rgb(0, 187, 0);\">manus@remote:~$</span><span> ${escapeHtml(command)}</span>\n`;
    view += `<span>${escapeHtml(output || (pending ? '(waiting for command completion)' : '(empty output)'))}</span>\n`;
  }

  if (!view) {
    view = `<span>(No SSH command output yet)</span>\n`;
  }

  shell.value = view;
};

const loadLogs = async () => {
  if (!nodeId.value) return;
  try {
    logs.value = await listNodeLogs(nodeId.value, 50);
  } catch (error) {
    console.error('Failed to load node logs:', error);
  } finally {
    renderConsole();
  }
};

const startAutoRefresh = () => {
  if (refreshTimer.value) clearInterval(refreshTimer.value);
  if (!props.live || !nodeId.value) return;
  refreshTimer.value = window.setInterval(() => {
    loadLogs();
  }, 3000);
};

const stopAutoRefresh = () => {
  if (refreshTimer.value) {
    clearInterval(refreshTimer.value);
    refreshTimer.value = null;
  }
};

const escapeHtml = (str: string): string =>
  str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');

watch(() => props.toolContent, () => {
  renderConsole();
  loadLogs();
}, { immediate: true, deep: true });

watch(() => props.toolContent.timestamp, () => {
  renderConsole();
  loadLogs();
});

watch(() => props.live, (live) => {
  if (live) {
    startAutoRefresh();
  } else {
    stopAutoRefresh();
  }
});

watch(nodeId, () => {
  loadLogs();
  startAutoRefresh();
});

onMounted(() => {
  loadLogs();
  startAutoRefresh();
});

onUnmounted(() => {
  stopAutoRefresh();
});
</script>
